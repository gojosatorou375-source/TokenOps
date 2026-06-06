import re

REDUNDANT_PATTERNS = [
    r"\bbe\s+concise\b",
    r"\bkeep\s+(?:it|answers?|responses?)\s+short\b",
    r"\brespond\s+briefly\b",
    r"\bno\s+preamble\b",
    r"\bconcise\s+answers?\b",
    r"\bmake\s+it\s+brief\b",
    r"\bshort\s+responses?\b"
]

def analyze_prompt_content(system_prompt: str, user_prompt: str) -> list[dict]:
    """Analyzes system and user prompts for common inefficiencies."""
    issues = []
    all_text = (system_prompt + " " + user_prompt).lower()
    
    # 1. Redundant Instructions Check
    found_redundant = []
    for pattern in REDUNDANT_PATTERNS:
        matches = re.findall(pattern, all_text)
        if matches:
            found_redundant.append(matches[0])
            
    if len(found_redundant) > 1:
        issues.append({
            "category": "Redundant Instructions",
            "description": f"Found multiple conciseness instructions: {', '.join([repr(x) for x in found_redundant])}.",
            "suggestion": "Consolidate into a single directive (e.g. 'Respond concisely.').",
            "potential_savings": 15
        })

    # 2. Excessive Context Check (characters count heuristic)
    if len(user_prompt) > 12000:
        issues.append({
            "category": "Excessive Context",
            "description": f"User prompt size is large ({len(user_prompt)} characters).",
            "suggestion": "Reduce chunk budget, or prune files in extraction.",
            "potential_savings": 25
        })

    # 3. Oversized Examples Check
    examples_count = len(re.findall(r"\bexample\s*\d*[:\-]", all_text))
    if examples_count >= 3:
        issues.append({
            "category": "Oversized Examples",
            "description": f"Found {examples_count} few-shot examples.",
            "suggestion": "Prune few-shot examples to 1 or 2 high-quality instances.",
            "potential_savings": 20
        })

    return issues

def analyze_recent_requests(records: list[dict]) -> list[dict]:
    """Runs global analysis across a set of recent token usage logs."""
    recommendations = []
    if not records:
        return recommendations
        
    # 1. Repeated System Prompts Check
    system_prompts = []
    for r in records:
        msgs = r.get("messages", [])
        sys_msg = next((m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "system"), "")
        if sys_msg:
            system_prompts.append(sys_msg)
            
    if len(system_prompts) > 2:
        from collections import Counter
        counts = Counter(system_prompts)
        most_common, count = counts.most_common(1)[0]
        if count > 1 and len(most_common) > 100:
            percentage = (count / len(system_prompts)) * 100
            recommendations.append({
                "category": "Repeated System Prompts",
                "description": f"Same system prompt was sent {count} times ({percentage:.1f}% of requests).",
                "suggestion": "Consolidate requests or enable system prompt caching.",
                "potential_savings": 30
            })

    # 2. Compile individual prompt audit results from last 5 requests
    individual_issues = []
    for r in records[-5:]:
        msgs = r.get("messages", [])
        sys_msg = "".join([m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "system"])
        user_msg = "".join([m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "user"])
        
        issues = analyze_prompt_content(sys_msg, user_msg)
        for issue in issues:
            if not any(x["category"] == issue["category"] for x in individual_issues):
                individual_issues.append(issue)
                
    recommendations.extend(individual_issues)
    return recommendations
