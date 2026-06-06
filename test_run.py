import os
import sys

# Ensure TokenOps package is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tokenops import GuardedOpenAI

# Set a mock API key so we run in simulation mode
os.environ["OPENAI_API_KEY"] = "mock-key"

print("==================================================")
print("             AI GUARD INTEGRATION RUN             ")
print("==================================================")

# 1. Initialize the Guarded Client
client = GuardedOpenAI()

# 2. Test PII & Secret Scrubber
print("\n--- 1. Testing PII & Secret Scrubber ---")
dirty_prompt = "Contact me at mohan@example.com. My database credentials are mongodb://admin:secretPass123@localhost:27017/db."
print(f"Original Prompt:  {dirty_prompt}")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": dirty_prompt}]
)

# 3. Test Local Semantic Cache
print("\n--- 2. Testing Local Semantic Caching ---")
prompt_cache_test = "Tell me the distance from the Earth to the Sun."

print("First Call (Cache Miss - writing to DB cache):")
response1 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt_cache_test}]
)
print(f"Response: {response1.choices[0].message.content}")

print("\nSecond Call (Cache Hit - checking SQLite cache):")
response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt_cache_test}]
)
print(f"Response: {response2.choices[0].message.content}")

print("\n--- 3. Running Telemetry Report ---")
import subprocess
subprocess.run(["python", "-m", "tokenops.cli.main", "report"], cwd=os.path.abspath(os.path.dirname(__file__)))
