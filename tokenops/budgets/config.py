import os
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "project_name": "MyProject",
    "budgets": {
        "monthly_tokens": 5000000,
        "daily_tokens": 150000,
        "per_request": 8192
    },
    "thresholds": {
        "warning": 80,
        "optimize": 90,
        "block": 100
    },
    "fallback": {
        "enabled": True,
        "model": "gpt-4.1-mini"
    },
    "providers": {
        "openai": True,
        "anthropic": True,
        "gemini": False,
        "graphify": True
    },
    "ci": {
        "max_prompt_growth": 20
    }
}

_cached_config = None

def find_config_path() -> Path | None:
    """Finds tokenops.yaml by walking up from the current directory."""
    current = Path.cwd().resolve()
    for parent in [current] + list(current.parents):
        config_file = parent / "tokenops.yaml"
        if config_file.exists():
            return config_file
    return None

def load_config(force_reload: bool = False) -> dict:
    """Loads and returns the config dictionary, merging user config with defaults."""
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    config = {}
    # Make a deep copy of DEFAULT_CONFIG
    for k, v in DEFAULT_CONFIG.items():
        if isinstance(v, dict):
            config[k] = v.copy()
        else:
            config[k] = v

    config_path = find_config_path()
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
                for key, val in user_config.items():
                    if isinstance(val, dict) and key in config:
                        config[key].update(val)
                    else:
                        config[key] = val
        except Exception as e:
            import sys
            print(f"[tokenops] Warning: Failed to parse config file {config_path}: {e}", file=sys.stderr)
            
    _cached_config = config
    return _cached_config
