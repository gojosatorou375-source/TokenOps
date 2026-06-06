import unittest
import os
import tempfile
import time
from pathlib import Path

from tokenops.budgets.config import load_config
from tokenops.tracking.recorder import record_usage, get_db_path
from tokenops.tracking.aggregator import read_records, get_totals_for_timeframe, get_aggregated_by_provider_model
from tokenops.budgets.enforcer import check_budget, BudgetExceededError
from tokenops.optimization.analyzer import analyze_prompt_content

class TestAIGuard(unittest.TestCase):
    def setUp(self):
        # Use isolated temp directories to prevent modifying user configuration or logs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file_path = Path(self.temp_dir.name) / "test_usage.db"
        os.environ["AI_GUARD_DB_PATH"] = str(self.temp_file_path)

    def tearDown(self):
        self.temp_dir.cleanup()
        if "AI_GUARD_DB_PATH" in os.environ:
            del os.environ["AI_GUARD_DB_PATH"]

    def test_record_and_read_usage(self):
        # Record a dummy call with prompt message metadata
        messages = [{"role": "user", "content": "What is 2+2?"}]
        record_usage("openai", "gpt-4.1-mini", 15, 5, messages)
        
        records = read_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["provider"], "openai")
        self.assertEqual(records[0]["model"], "gpt-4.1-mini")
        self.assertEqual(records[0]["input_tokens"], 15)
        self.assertEqual(records[0]["output_tokens"], 5)
        self.assertEqual(records[0]["total_tokens"], 20)
        self.assertEqual(len(records[0]["messages"]), 1)
        self.assertEqual(records[0]["messages"][0]["content"], "What is 2+2?")

    def test_aggregator(self):
        # Record multiple calls across providers
        record_usage("openai", "gpt-4.1-mini", 100, 200)
        record_usage("openai", "gpt-4.1-mini", 200, 300)
        record_usage("anthropic", "claude-sonnet-4-6", 1000, 2000)
        
        # Verify cumulative total token calculation
        totals = get_totals_for_timeframe()
        self.assertEqual(totals, 3800)
        
        # Verify provider/model aggregation
        agg = get_aggregated_by_provider_model()
        self.assertEqual(agg[("openai", "gpt-4.1-mini")]["total_tokens"], 800)
        self.assertEqual(agg[("anthropic", "claude-sonnet-4-6")]["total_tokens"], 3000)

    def test_budget_enforcer(self):
        # 1. Verify per-request limit raises BudgetExceededError (default: 8192)
        with self.assertRaises(BudgetExceededError):
            check_budget("openai", estimated_tokens=10000)
            
        # 2. Verify daily limit raises block (default: 150000)
        # Populate log to cross limit
        record_usage("openai", "gpt-4.1-mini", 100000, 60000)
        
        with self.assertRaises(BudgetExceededError):
            check_budget("openai", estimated_tokens=100)

    def test_prompt_analyzer(self):
        # 1. Verify redundant instruction triggers
        sys_prompt = "Be concise. Keep answers short."
        user_prompt = "How does gravity work?"
        issues = analyze_prompt_content(sys_prompt, user_prompt)
        self.assertTrue(any(i["category"] == "Redundant Instructions" for i in issues))
        
        # 2. Verify few-shot count triggers
        sys_prompt = ""
        user_prompt = "Example-1: 1->A. Example-2: 2->B. Example-3: 3->C."
        issues = analyze_prompt_content(sys_prompt, user_prompt)
        self.assertTrue(any(i["category"] == "Oversized Examples" for i in issues))

    def test_prompt_refiner(self):
        from tokenops.optimization.refiner import refine_prompt
        refined, removed = refine_prompt("Be concise. Keep answers short. Explain gravity.")
        self.assertEqual(refined, "Explain gravity. Respond concisely.")
        self.assertIn("Be concise", removed)
        self.assertIn("Keep answers short", removed)
        
        refined_clean, removed_clean = refine_prompt("Explain gravity in detail.")
        self.assertEqual(refined_clean, "Explain gravity in detail.")
        self.assertEqual(len(removed_clean), 0)

    def test_scrubber(self):
        from tokenops.security.scrubber import scrub_text
        text = "Contact me at mohan@example.com using sk-proj-123456789012345678901234567890123456789012345678."
        scrubbed, detected = scrub_text(text)
        self.assertIn("Email Address", detected)
        self.assertIn("OpenAI Project API Key", detected)
        self.assertIn("[REDACTED_EMAIL_ADDRESS]", scrubbed)
        self.assertIn("[REDACTED_OPENAI_PROJECT_API_KEY]", scrubbed)

    def test_compressor(self):
        from tokenops.optimization.compressor import compress_prompt
        text = "# code imports\nimport sys\nimport sys\n// print result\nprint('done') # inline"
        compressed = compress_prompt(text)
        self.assertEqual(compressed, "import sys\nprint('done')")

    def test_semantic_cache(self):
        from tokenops.tracking.cache import save_cache, lookup_cache
        save_cache("What is the speed of light?", "299,792 km/s", "openai", "gpt-4.1-mini")
        
        hit1 = lookup_cache("What is the speed of light?", threshold=0.85)
        self.assertIsNotNone(hit1)
        self.assertEqual(hit1[0], "299,792 km/s")
        
        hit2 = lookup_cache("What is speed of light?", threshold=0.8)
        self.assertIsNotNone(hit2)
        self.assertEqual(hit2[0], "299,792 km/s")

if __name__ == "__main__":
    unittest.main()
