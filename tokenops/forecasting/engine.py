import time
from tokenops.tracking.aggregator import read_records, get_totals_for_timeframe
from tokenops.budgets.config import load_config

def generate_forecast() -> dict:
    """Estimates monthly token usage based on historical logs and predicts overrun metrics."""
    records = read_records()
    config = load_config()
    
    monthly_limit = config.get("budgets", {}).get("monthly_tokens", 5000000)
    current_month_usage = get_totals_for_timeframe(current_month_only=True)
    
    if not records:
        return {
            "current_month_usage": 0,
            "projected_monthly_usage": 0,
            "daily_burn_rate": 0,
            "monthly_limit": monthly_limit,
            "overrun_percent": 0.0,
            "exhaustion_date": "N/A"
        }
        
    # Gather unix epochs of logged items
    timestamps = []
    for r in records:
        ts_str = r.get("timestamp", "")
        try:
            struct_t = time.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            timestamps.append(time.mktime(struct_t) - time.timezone)
        except Exception:
            pass
            
    if len(timestamps) < 2:
        # Not enough span, use today's total as initial burn estimate
        daily_burn_rate = float(get_totals_for_timeframe(current_day_only=True))
    else:
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        span_seconds = max(max_ts - min_ts, 1)
        span_days = span_seconds / (24 * 3600)
        
        total_logs_tokens = sum(r.get("total_tokens", 0) for r in records)
        daily_burn_rate = total_logs_tokens / max(span_days, 1.0)
        
    # Ensure daily_burn_rate is at least today's usage
    today_usage = get_totals_for_timeframe(current_day_only=True)
    daily_burn_rate = max(daily_burn_rate, float(today_usage))
    
    # Project usage for a standard 30-day billing cycle
    projected_monthly_usage = int(daily_burn_rate * 30)
    
    overrun_percent = 0.0
    exhaustion_date = "No Exceedance Expected"
    
    if monthly_limit > 0:
        if projected_monthly_usage > monthly_limit:
            overrun_percent = ((projected_monthly_usage - monthly_limit) / monthly_limit) * 100
            
            if daily_burn_rate > 0:
                tokens_remaining = max(monthly_limit - current_month_usage, 0)
                days_until_exhaustion = tokens_remaining / daily_burn_rate
                exhaustion_epoch = time.time() + (days_until_exhaustion * 24 * 3600)
                exhaustion_date = time.strftime("%Y-%m-%d", time.gmtime(exhaustion_epoch))
            else:
                exhaustion_date = "N/A"
                
    return {
        "current_month_usage": current_month_usage,
        "projected_monthly_usage": projected_monthly_usage,
        "daily_burn_rate": int(daily_burn_rate),
        "monthly_limit": monthly_limit,
        "overrun_percent": round(overrun_percent, 1),
        "exhaustion_date": exhaustion_date
    }
