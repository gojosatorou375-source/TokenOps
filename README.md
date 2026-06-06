# TokenOps

TokenOps is a developer-first, open-source Python SDK, CLI, and local web dashboard designed to track, optimize, and govern Large Language Model (LLM) token usage and costs. It operates as a local control layer, enabling developers to proactively enforce budget limits, analyze prompt efficiency, and forecast spend with zero external data leakage.

---

## Key Features

- **Local-First Interception**: Intercepts OpenAI calls (`GuardedOpenAI`) and checks budgets before requests reach providers.
- **Graphify Bridge**: Runtime monkey-patching (`patch_graphify()`) that hooks into Graphify codebase extractions to monitor token consumption in real-time.
- **Budget Enforcer**: YAML-configured daily, monthly, and per-request limits with warning (80%), optimization (90%), and block (100%) thresholds.
- **Local Interactive Shell**: A beautiful terminal environment with command prompts (`/report`, `/check`, `/forecast`, `/optimize`, `/patch`, `/run`, `/dashboard`).
- **Premium Glassmorphic Dashboard**: A sleek dark-mode local web interface with dynamic Chart.js visualizations.

---

## Quick Start (Git Clone to Usage)

Once you clone the repository, install the package and its requirements:

```bash
# 1. Install dependencies
pip install pyyaml openai tiktoken --break-system-packages

# 2. Install TokenOps locally
pip install -e . --break-system-packages
```

### 1. Launch the Interactive Shell
Simply run `tokenops` in your console (or `python -m tokenops.cli.main` if not installed globally) to launch the interactive terminal environment:

```text
============================================================
   _    ___    ____ _   _  _    ____  ____  
  / \  |_ _|  / ___| | | |/ \  |  _ \|  _ \ 
 / _ \  | |  | |  _| | | / _ \ | |_) | | | |
/ ___ \ | |  | |_| | |_| / ___ \|  _ <| |_| |
/_/   \_\___|  \____|\___/_/   \_\_| \_\____/ 
============================================================

Tips for getting started:
1. Type /help to view all available commands.
2. Run '/run <prompt>' to test a guarded LLM request.
3. Enter '/patch' to test the Graphify integration bridge.

tokenops > 
```

### 2. Available Interactive Commands
Type these commands inside the shell:
- `/report` - Print a tabular breakdown of input/output tokens and estimated cost.
- `/check` - Validate daily/monthly budgets with visual progress indicators.
- `/forecast` - Project month-end spend, burn rates, and exhaustion dates.
- `/optimize` - Audit recent prompts for redundant statements or context waste.
- `/patch` - Apply the Graphify monkey-patch and run a simulated extraction.
- `/run <prompt>` - Send a completion prompt via `GuardedOpenAI` (simulated if no API key set).
- `/dashboard` - Spin up the premium local web dashboard.
- `/help` - Show help instructions.
- `/exit` - Exit the interactive shell.

---

## SDK & Integration Usage

### OpenAI Client Interception
Replace standard `openai.OpenAI` client instances with `GuardedOpenAI`:

```python
import os
from tokenops import GuardedOpenAI

# Set your API key
os.environ["OPENAI_API_KEY"] = "your-actual-api-key"

client = GuardedOpenAI()

# Budget is checked before sending, and actual tokens are recorded after response
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Explain gravity in one sentence."}]
)
print(response.choices[0].message.content)
```

### Graphify Monkey-Patching
Run `patch_graphify()` at the very startup of your application. TokenOps will automatically intercept all Graphify extraction calls:

```python
from tokenops import patch_graphify
from pathlib import Path

# 1. Activate runtime patch
patch_graphify()

# 2. Run Graphify extractions normally
from graphify.llm import extract_files_direct

result = extract_files_direct(
    files=[Path("my_project/src/main.py")],
    backend="openai"
)
print(f"Extracted {len(result['nodes'])} knowledge graph nodes.")
```

---

## Configuration (`tokenops.yaml`)

Initialize the default settings file using the shell or CLI (`tokenops init`). Customize limits, fallback models, and provider tracking:

```yaml
project_name: MyLLMApp

# Token limits
budgets:
  monthly_tokens: 5000000
  daily_tokens: 150000
  per_request: 8192

# Enforcement percentages
thresholds:
  warning: 80
  optimize: 90
  block: 100

# Rerouting rules
fallback:
  enabled: true
  model: gpt-4.1-mini
```
