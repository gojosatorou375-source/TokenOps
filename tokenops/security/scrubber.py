import re

PATTERNS = {
    "OpenAI API Key": r"\bsk-[a-zA-Z0-9]{48}\b",
    "OpenAI Project API Key": r"\bsk-proj-[a-zA-Z0-9\-_]{48,100}\b",
    "Anthropic API Key": r"\bsk-ant-[a-zA-Z0-9\-_]{30,100}\b",
    "Email Address": r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b",
    "Bearer Token": r"\bBearer\s+[a-zA-Z0-9_\-\.]{15,100}\b",
    "Database Password": r"\b[a-zA-Z0-9\+]+://[^:]+:([^@]+)@[^\s/]+\b"
}

def scrub_text(text: str) -> tuple[str, list[str]]:
    """
    Scans text for sensitive PII and secrets, replaces them with standard redacted tokens,
    and returns a tuple of (scrubbed_text, list_of_detected_categories).
    """
    if not text:
        return text, []
        
    scrubbed = text
    detected = []
    
    # Check Database Passwords first to capture the password specifically
    db_passwords = re.findall(PATTERNS["Database Password"], scrubbed)
    if db_passwords:
        detected.append("Database Password")
        for pwd in db_passwords:
            if len(pwd) > 2:
                scrubbed = scrubbed.replace(pwd, "[REDACTED_PASSWORD]")
                
    for label, pattern in PATTERNS.items():
        if label == "Database Password":
            continue
            
        matches = re.findall(pattern, scrubbed)
        if matches:
            detected.append(label)
            for match in set(matches):
                redacted_label = f"[REDACTED_{label.upper().replace(' ', '_')}]"
                scrubbed = scrubbed.replace(match, redacted_label)
                
    return scrubbed, detected
