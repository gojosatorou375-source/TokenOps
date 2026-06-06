import re

def compress_prompt(text: str) -> str:
    """
    Applies light context compression rules to reduce token count:
    - Normalizes excessive whitespace and multiple blank lines.
    - Removes consecutive duplicate lines.
    - Strips code comment lines (starting with # or //) to save tokens.
    """
    if not text:
        return text
        
    lines = text.splitlines()
    compressed_lines = []
    prev_line = None
    
    for line in lines:
        cleaned = line.strip()
        
        # 1. Strip comment-only lines
        if cleaned.startswith("#") or cleaned.startswith("//"):
            continue
            
        # 2. Strip inline comments (handling URL slashes safely)
        line_no_comments = line
        if " #" in line_no_comments:
            line_no_comments = line_no_comments.split(" #", 1)[0]
        if " //" in line_no_comments:
            line_no_comments = line_no_comments.split(" //", 1)[0]
            
        # 3. Deduplicate consecutive identical lines
        if line_no_comments.strip() == prev_line:
            continue
            
        compressed_lines.append(line_no_comments)
        prev_line = line_no_comments.strip()
        
    result = "\n".join(compressed_lines)
    # Replace 3 or more consecutive newlines with 2 newlines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
