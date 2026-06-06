import json
import threading
import urllib.request
import urllib.error
import sys

def _post_sync(url: str, payload: dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "AI-Guard-Agent/0.1"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            pass
    except urllib.error.URLError as e:
        # Log to stderr silently to avoid raising runtime exceptions in user scripts
        print(f"[tokenops-sync] Warning: Telemetry sync failed: {e}", file=sys.stderr)
    except Exception:
        pass

def sync_telemetry(url: str, provider: str, model: str, input_tokens: int, output_tokens: int, cost: float):
    """
    Spins up a background daemon thread to send usage metrics to a central team endpoint.
    """
    if not url:
        return
        
    payload = {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost": cost
    }
    
    thread = threading.Thread(target=_post_sync, args=(url, payload), daemon=True)
    thread.start()
