from tokenops.optimization.analyzer import analyze_recent_requests

def get_recommendations(records: list[dict]) -> dict:
    """Generates a summary of optimization recommendations and estimates total token savings."""
    if not records:
        return {
            "estimated_savings_percent": 0,
            "total_tokens_evaluated": 0,
            "recommendations": []
        }
        
    recommendations = analyze_recent_requests(records)
    total_tokens_evaluated = sum(r.get("total_tokens", 0) for r in records)
    
    # Calculate potential savings percentage (capped at 65% maximum optimization potential)
    savings_pct = sum(r["potential_savings"] for r in recommendations)
    savings_pct = min(savings_pct, 65)
    
    return {
        "estimated_savings_percent": savings_pct,
        "total_tokens_evaluated": total_tokens_evaluated,
        "recommendations": recommendations
    }
