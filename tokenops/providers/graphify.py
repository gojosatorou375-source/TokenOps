import threading
import sys
from pathlib import Path

# Session accumulator to track metrics for the current corpus extraction
_session_lock = threading.Lock()
_session_active = False
_session_stats = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cost": 0.0,
    "calls": 0
}

def reset_session():
    global _session_active
    with _session_lock:
        _session_active = True
        _session_stats["input_tokens"] = 0
        _session_stats["output_tokens"] = 0
        _session_stats["cost"] = 0.0
        _session_stats["calls"] = 0

def add_to_session(provider, model, input_tokens, output_tokens):
    with _session_lock:
        if not _session_active:
            return
        _session_stats["input_tokens"] += input_tokens
        _session_stats["output_tokens"] += output_tokens
        _session_stats["calls"] += 1
        
        # Estimate cost using estimate_cost from CLI main
        from tokenops.cli.main import estimate_cost
        _session_stats["cost"] += estimate_cost(provider, model, input_tokens, output_tokens)

def print_auto_summary():
    """Prints a beautiful console summary of the completed extraction session."""
    global _session_active
    with _session_lock:
        if not _session_active or _session_stats["calls"] == 0:
            return
        _session_active = False
        
        input_tokens = _session_stats["input_tokens"]
        output_tokens = _session_stats["output_tokens"]
        total_tokens = input_tokens + output_tokens
        cost = _session_stats["cost"]
        calls = _session_stats["calls"]
        
    print("\n" + "=" * 60)
    print("                AI GUARD TELEMETRY SUMMARY")
    print("=" * 60)
    print(f"Total API Calls:          {calls}")
    print(f"Tokens Consumed (Input):  {input_tokens:,}")
    print(f"Tokens Consumed (Output): {output_tokens:,}")
    print(f"Total Tokens:             {total_tokens:,}")
    print(f"Estimated Session Cost:   ${cost:.4f}")
    
    # Print budget progress bars
    from tokenops.tracking.aggregator import get_totals_for_timeframe
    from tokenops.budgets.config import load_config
    from tokenops.reporting.formatter import get_progress_bar
    
    config = load_config()
    daily_limit = config.get("budgets", {}).get("daily_tokens", 150000)
    daily_usage = get_totals_for_timeframe(current_day_only=True)
    
    if daily_limit > 0:
        daily_percent = (daily_usage / daily_limit) * 100
        print(f"Daily Budget Status:      {get_progress_bar(daily_percent, width=20)}")
        
    # Analyze recent prompts for optimization suggestions
    from tokenops.tracking.aggregator import read_records
    from tokenops.optimization.recommender import get_recommendations
    
    records = read_records()
    analysis = get_recommendations(records[-calls:])
    
    recs = analysis.get("recommendations", [])
    if recs:
        print("-" * 60)
        print(f"Cost Saving Insights (Estimated Savings: {analysis['estimated_savings_percent']}%):")
        for idx, rec in enumerate(recs, start=1):
            print(f"  {idx}. [{rec['category']}] -> {rec['suggestion']}")
            
    print("=" * 60)

def patch_graphify():
    """Call once at startup — all graphify calls become tracked and budget-checked."""
    try:
        import graphify.llm as _llm
    except ImportError:
        print("[tokenops] Warning: Could not find graphify installation to patch.", file=sys.stderr)
        return

    _original_direct = _llm.extract_files_direct
    _original_parallel = getattr(_llm, "extract_corpus_parallel", None)

    def _patched_direct(files, backend=None, **kwargs):
        from tokenops.budgets.enforcer import check_budget
        from tokenops.tracking.recorder import record_usage
        
        # Check if this is a standalone call or inside a parallel session
        standalone = False
        with _session_lock:
            if not _session_active:
                standalone = True
                
        if standalone:
            reset_session()
            
        # Check budget before call
        check_budget(provider=f"graphify/{backend or 'auto'}")
        
        # Execute original graphify LLM call
        result = _original_direct(files, backend=backend, **kwargs)
        
        # Record tokens consumed after call
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        model = result.get("model", backend or "unknown")
        provider = f"graphify/{backend or 'auto'}"
        
        record_usage(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        
        # Add to the current session stats
        add_to_session(provider, model, input_tokens, output_tokens)
        
        if standalone:
            print_auto_summary()
            
        return result

    _llm.extract_files_direct = _patched_direct

    if _original_parallel:
        def _patched_parallel(*args, **kwargs):
            reset_session()
            try:
                result = _original_parallel(*args, **kwargs)
                return result
            finally:
                print_auto_summary()
                
        _llm.extract_corpus_parallel = _patched_parallel


def guarded_extract(files, backend=None, **kwargs):
    """Explicit wrapper API that budget-checks, tracks, and prints summary."""
    from tokenops.budgets.enforcer import check_budget
    from tokenops.tracking.recorder import record_usage
    import graphify.llm as _llm
    
    reset_session()
    check_budget(provider=f"graphify/{backend or 'auto'}")
    try:
        result = _llm.extract_files_direct(files, backend=backend, **kwargs)
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        model = result.get("model", backend or "unknown")
        provider = f"graphify/{backend or 'auto'}"
        
        record_usage(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        add_to_session(provider, model, input_tokens, output_tokens)
        return result
    finally:
        print_auto_summary()
