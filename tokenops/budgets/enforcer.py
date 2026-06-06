import sys
from tokenops.budgets.config import load_config
from tokenops.tracking.aggregator import get_totals_for_timeframe

class BudgetExceededError(Exception):
    """Exception raised when LLM calls are blocked due to budget exhaustions."""
    pass

def check_budget(provider: str, estimated_tokens: int = 0):
    """Enforces token budget limits based on current aggregates and active thresholds."""
    config = load_config()
    
    # If the provider is explicitly disabled, skip tracking/enforcement
    active_providers = config.get("providers", {})
    prov_key = "graphify" if provider.startswith("graphify") else provider
    if not active_providers.get(prov_key, True):
        return

    budgets = config.get("budgets", {})
    thresholds = config.get("thresholds", {"warning": 80, "optimize": 90, "block": 100})
    
    # 1. Per Request Limit Check
    per_request_limit = budgets.get("per_request", 8192)
    if estimated_tokens > per_request_limit:
        raise BudgetExceededError(
            f"Per-request limit exceeded: estimated {estimated_tokens} tokens, limit is {per_request_limit}."
        )

    # 2. Daily Budget Check
    daily_limit = budgets.get("daily_tokens", 150000)
    daily_usage = get_totals_for_timeframe(current_day_only=True)
    
    if daily_limit > 0:
        daily_percent = (daily_usage / daily_limit) * 100
        if daily_percent >= thresholds.get("block", 100):
            raise BudgetExceededError(
                f"Daily budget block: current usage is {daily_usage} / {daily_limit} ({daily_percent:.1f}%)."
            )
        elif daily_percent >= thresholds.get("optimize", 90):
            print(
                f"[tokenops] OPTIMIZATION REQUIRED: Daily token usage is at {daily_percent:.1f}% ({daily_usage}/{daily_limit}).\n"
                f"Suggestions:\n"
                f" - Consider reducing context size.\n"
                f" - Switch to fallback model: {config.get('fallback', {}).get('model', 'gpt-4.1-mini')}.\n"
                f" - Run 'tokenops optimize' for detailed prompt suggestions.",
                file=sys.stderr
            )
        elif daily_percent >= thresholds.get("warning", 80):
            print(
                f"[tokenops] WARNING: Daily token usage has reached {daily_percent:.1f}% ({daily_usage}/{daily_limit}).",
                file=sys.stderr
            )

    # 3. Monthly Budget Check
    monthly_limit = budgets.get("monthly_tokens", 5000000)
    monthly_usage = get_totals_for_timeframe(current_month_only=True)
    
    if monthly_limit > 0:
        monthly_percent = (monthly_usage / monthly_limit) * 100
        if monthly_percent >= thresholds.get("block", 100):
            raise BudgetExceededError(
                f"Monthly budget block: current usage is {monthly_usage} / {monthly_limit} ({monthly_percent:.1f}%)."
            )
        elif monthly_percent >= thresholds.get("optimize", 90):
            print(
                f"[tokenops] OPTIMIZATION REQUIRED: Monthly token usage is at {monthly_percent:.1f}% ({monthly_usage}/{monthly_limit}).\n"
                f"Suggestions:\n"
                f" - Consolidate duplicate system instructions.\n"
                f" - Enable semantic caching.\n"
                f" - Swap to cheaper model.",
                file=sys.stderr
            )
        elif monthly_percent >= thresholds.get("warning", 80):
            print(
                f"[tokenops] WARNING: Monthly token usage has reached {monthly_percent:.1f}% ({monthly_usage}/{monthly_limit}).",
                file=sys.stderr
            )
