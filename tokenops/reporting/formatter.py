def format_table(headers: list[str], rows: list[list]) -> str:
    """Formats a tabular dataset into a cleanly-aligned ASCII text table."""
    if not headers:
        return ""
    
    # Stringify all cell contents
    str_rows = [[str(cell) for cell in row] for row in rows]
    
    # Calculate maximum widths of columns
    col_widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, val in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(val))
            
    header_line = "  ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    divider_line = "  ".join("-" * w for w in col_widths)
    
    formatted_rows = []
    for row in str_rows:
        row_line = "  ".join(f"{val:<{col_widths[i]}}" for i, val in enumerate(row))
        formatted_rows.append(row_line)
        
    return "\n".join([header_line, divider_line] + formatted_rows)

def get_progress_bar(percent: float, width: int = 25) -> str:
    """Returns an ASCII progress bar block representation of budget usage."""
    percent = max(0.0, min(percent, 100.0))
    filled_len = int(round(width * percent / 100.0))
    bar = "#" * filled_len + "-" * (width - filled_len)
    return f"[{bar}] {percent:.1f}%"
