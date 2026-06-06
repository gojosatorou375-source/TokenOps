import sys
import time
from openai import OpenAI
from tokenops.tracking.recorder import record_usage
from tokenops.budgets.enforcer import check_budget, BudgetExceededError
from tokenops.budgets.config import load_config

# Helper Mock Response classes for cache hits
class MockUsage:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

class MockMessage:
    def __init__(self, content):
        self.content = content
        self.role = "assistant"

class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)
        self.finish_reason = "stop"
        self.index = 0

class MockResponse:
    def __init__(self, content, model):
        self.id = "chatcmpl-mock"
        self.choices = [MockChoice(content)]
        self.created = int(time.time())
        self.model = model + "-cached"
        self.object = "chat.completion"
        self.usage = MockUsage()

class GuardedOpenAI(OpenAI):
    """Guarded wrapper for OpenAI client. Intercepts chat completions to enforce cost limits."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_create = self.chat.completions.create
        self.chat.completions.create = self._guarded_create

    def _guarded_create(self, **kwargs):
        model = kwargs.get("model", "gpt-4.1-mini")
        config = load_config()
        
        # 1. PII and Secret Scrubber
        scrub_enabled = config.get("security", {}).get("scrub_pii", True)
        if scrub_enabled:
            from tokenops.security.scrubber import scrub_text
            scrubbed_messages = []
            for msg in kwargs.get("messages", []):
                if isinstance(msg, dict) and "content" in msg:
                    scrubbed_content, _ = scrub_text(msg["content"])
                    new_msg = dict(msg)
                    new_msg["content"] = scrubbed_content
                    scrubbed_messages.append(new_msg)
                else:
                    scrubbed_messages.append(msg)
            kwargs["messages"] = scrubbed_messages

        # 2. Context Compressor
        compress_enabled = config.get("compression", {}).get("auto_compress", False)
        if compress_enabled:
            from tokenops.optimization.compressor import compress_prompt
            compressed_messages = []
            for msg in kwargs.get("messages", []):
                if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                    new_msg = dict(msg)
                    new_msg["content"] = compress_prompt(msg["content"])
                    compressed_messages.append(new_msg)
                else:
                    compressed_messages.append(msg)
            kwargs["messages"] = compressed_messages

        # Estimate prompt tokens for per_request budget check
        estimated_tokens = 0
        try:
            import tiktoken
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            
            messages = kwargs.get("messages", [])
            text = "".join([m.get("content", "") for m in messages if isinstance(m, dict)])
            estimated_tokens = len(encoding.encode(text))
        except Exception:
            # Fallback estimation heuristic: 1 token ~= 4 characters
            messages = kwargs.get("messages", [])
            text = "".join([m.get("content", "") for m in messages if isinstance(m, dict)])
            estimated_tokens = len(text) // 4

        # Proactive prompt efficiency audit pre-flight
        try:
            from tokenops.optimization.analyzer import analyze_prompt_content
            messages = kwargs.get("messages", [])
            sys_msg = "".join([m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "system"])
            user_msg = "".join([m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "user"])
            
            issues = analyze_prompt_content(sys_msg, user_msg)
            if issues:
                print(f"[tokenops] Prompt Efficiency Recommendations for '{model}':", file=sys.stderr)
                for issue in issues:
                    print(f"  - [{issue['category']}] Suggestion: {issue['suggestion']} (Potential saving: {issue['potential_savings']}%).", file=sys.stderr)
        except Exception:
            pass

        # 3. Local Semantic Cache Lookup
        cache_enabled = config.get("cache", {}).get("enabled", True)
        prompt_key = "".join([m.get("content", "") for m in kwargs.get("messages", []) if isinstance(m, dict) and m.get("role") == "user"])
        
        if cache_enabled and prompt_key:
            try:
                from tokenops.tracking.cache import lookup_cache
                threshold = config.get("cache", {}).get("similarity_threshold", 0.85)
                hit = lookup_cache(prompt_key, threshold=threshold)
                if hit:
                    cached_res, cached_prov, cached_model = hit
                    print(f"[tokenops] local semantic cache hit (Jaccard Match >= {threshold})!", file=sys.stderr)
                    
                    # Record a free cache telemetry entry
                    record_usage(
                        provider="openai-cache",
                        model=model + "-cached",
                        input_tokens=0,
                        output_tokens=0,
                        messages=kwargs.get("messages", [])
                    )
                    return MockResponse(cached_res, model)
            except Exception:
                pass

        # Simulated mode fallback for testing offline/without key
        import os
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY", "")
        if api_key == "mock-key" or not api_key:
            print("[tokenops] Running in SIMULATED mode (no valid OpenAI key detected).", file=sys.stderr)
            mock_res_text = f"Simulated response content for prompt: '{prompt_key[:45]}...'"
            input_tokens = estimated_tokens
            output_tokens = 50
            
            # Save to cache if enabled
            if cache_enabled and prompt_key:
                try:
                    from tokenops.tracking.cache import save_cache
                    save_cache(prompt_key, mock_res_text, "openai", model)
                except Exception:
                    pass
            
            record_usage(
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                messages=kwargs.get("messages", [])
            )
            return MockResponse(mock_res_text, model)

        try:
            check_budget(provider="openai", estimated_tokens=estimated_tokens)
        except BudgetExceededError as e:
            fallback_cfg = config.get("fallback", {})
            if fallback_cfg.get("enabled", True) and model != fallback_cfg.get("model"):
                fallback_model = fallback_cfg.get("model", "gpt-4.1-mini")
                print(
                    f"[tokenops] Budget exceeded for primary model '{model}'. "
                    f"Rerouting to fallback model '{fallback_model}'...",
                    file=sys.stderr
                )
                kwargs["model"] = fallback_model
                # Re-check budget with fallback (this will raise the error if global budgets are fully exhausted)
                check_budget(provider="openai", estimated_tokens=estimated_tokens)
            else:
                raise e

        # 4. Retry and Failover Routing Shielding
        retries = 3
        backoff = 1.0
        resp = None
        last_exception = None
        
        for attempt in range(retries):
            try:
                resp = self._original_create(**kwargs)
                break
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                # Retry on rate limit, connection, timeout, or server overload errors
                if any(x in err_str for x in ["rate", "quota", "limit", "connection", "timeout", "503", "429"]):
                    print(f"[tokenops] API error: {e}. Retrying in {backoff}s (attempt {attempt+1}/{retries})...", file=sys.stderr)
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise e

        if resp is None:
            # Fallback failover routing if primary model fully failed
            fallback_cfg = config.get("fallback", {})
            if fallback_cfg.get("enabled", True) and model != fallback_cfg.get("model"):
                fallback_model = fallback_cfg.get("model", "gpt-4.1-mini")
                print(
                    f"[tokenops] API failed for primary model '{model}'. "
                    f"Failing over to fallback model '{fallback_model}'...",
                    file=sys.stderr
                )
                kwargs["model"] = fallback_model
                try:
                    resp = self._original_create(**kwargs)
                except Exception as e:
                    raise last_exception or e
            else:
                raise last_exception or Exception("API execution failed.")

        # Record actual tokens consumed
        input_tokens = resp.usage.prompt_tokens if (resp.usage and resp.usage.prompt_tokens) else 0
        output_tokens = resp.usage.completion_tokens if (resp.usage and resp.usage.completion_tokens) else 0
        actual_model = resp.model if resp.model else model
        
        # Save to semantic cache if enabled and valid response received
        if cache_enabled and prompt_key and resp.choices and resp.choices[0].message.content:
            try:
                from tokenops.tracking.cache import save_cache
                save_cache(prompt_key, resp.choices[0].message.content, "openai", actual_model)
            except Exception:
                pass

        record_usage(
            provider="openai",
            model=actual_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            messages=kwargs.get("messages", [])
        )

        # 5. Team Telemetry Sync (Asynchronous)
        sync_cfg = config.get("team_sync", {})
        if sync_cfg.get("enabled", False) and sync_cfg.get("sync_url"):
            try:
                from tokenops.tracking.sync import sync_telemetry
                from tokenops.cli.main import estimate_cost
                cost = estimate_cost("openai", actual_model, input_tokens, output_tokens)
                sync_telemetry(sync_cfg["sync_url"], "openai", actual_model, input_tokens, output_tokens, cost)
            except Exception:
                pass
        
        return resp
