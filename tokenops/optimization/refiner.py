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

def refine_prompt(prompt: str) -> tuple[str, list[str]]:
    """
    Scans a prompt, removes redundant conciseness instructions,
    and returns the optimized prompt along with the list of removed phrases.
    If any phrase is removed, it appends 'Respond concisely.' at the end.
    """
    removed = []
    refined = prompt
    
    for pattern in REDUNDANT_PATTERNS:
        matches = re.findall(pattern, refined, re.IGNORECASE)
        if matches:
            for match in matches:
                # Store the exact matched text
                if match not in removed:
                    removed.append(match)
            
            # Construct a regex to match the pattern, optional punctuation, and optional trailing whitespace
            # Since pattern starts with \b, pattern[2:] gets the rest of the pattern without \b
            clean_pattern = pattern
            if pattern.startswith(r"\b"):
                clean_pattern = pattern[2:]
            if clean_pattern.endswith(r"\b"):
                clean_pattern = clean_pattern[:-2]
                
            regex_to_replace = re.compile(r"\b" + clean_pattern + r"\b[\.,!?;]*\s*", re.IGNORECASE)
            refined = regex_to_replace.sub("", refined)
            
    # Clean up duplicate whitespace and stray punctuation at the start/middle
    refined = re.sub(r"\s+", " ", refined).strip()
    
    # If we removed any redundant instructions, append a single standard instruction
    if removed:
        # Strip trailing periods/whitespace from the prompt before appending
        refined = refined.strip()
        if refined and not refined.endswith(".") and not refined.endswith("!") and not refined.endswith("?"):
            refined += "."
        if refined:
            refined += " Respond concisely."
        else:
            refined = "Respond concisely."
            
    return refined, removed
