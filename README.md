<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=blur&height=200&color=gradient&text=TokenOps&fontSize=90&fontAlignY=40&animation=fadeIn" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active%20Development-blue" />
  <img src="https://img.shields.io/badge/Language-Python-3776AB" />
  <img src="https://img.shields.io/badge/SDK-OpenAI-black" />
  <img src="https://img.shields.io/badge/Dashboard-Chart.js-FF6384" />
  <img src="https://img.shields.io/badge/CLI-Terminal-success" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,git,github,vscode" />
</p>

<h1 align="center">TokenOps</h1>

<p align="center">
  Developer-first token governance, cost control, and observability for Large Language Models.
</p>

<p align="center">
  Monitor usage, enforce budgets, optimize prompts, forecast costs, and govern AI spending entirely on your local machine.
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation">Installation</a> •
  <a href="#roadmap">Roadmap</a>
</p>

---

## Overview

TokenOps is an open-source Python SDK, CLI, and local dashboard that provides complete visibility and governance over LLM token consumption.

Modern AI applications often suffer from:

* Uncontrolled token growth
* Unexpected API bills
* Prompt inefficiencies
* Missing cost visibility
* Lack of enforcement controls

TokenOps acts as a local control plane between your application and model providers, allowing teams to proactively monitor, optimize, and enforce token budgets before costs escalate.

All monitoring, analytics, and enforcement operate locally with zero external telemetry requirements.

---

## Features

### Guarded OpenAI Client

Replace standard OpenAI clients with a budget-aware wrapper.

Capabilities include:

* Pre-request budget validation
* Token estimation
* Cost calculation
* Usage logging
* Request blocking

---

### Graphify Runtime Integration

TokenOps includes a runtime monkey-patching bridge that integrates directly with Graphify workloads.

Features:

* Automatic extraction monitoring
* Real-time token tracking
* Usage attribution
* Cost visibility across graph operations

---

### Budget Enforcement Engine

Configure governance policies through a simple YAML file.

Supported controls:

* Daily limits
* Monthly limits
* Per-request limits
* Warning thresholds
* Automatic blocking
* Model fallback routing

---

### Interactive Developer Shell

A fully interactive command-line environment designed for token operations management.

Supported Commands:

| Command      | Description                       |
| ------------ | --------------------------------- |
| `/report`    | Usage reports and cost breakdowns |
| `/check`     | Budget validation                 |
| `/forecast`  | Spend forecasting                 |
| `/optimize`  | Prompt efficiency analysis        |
| `/patch`     | Activate Graphify bridge          |
| `/run`       | Execute guarded requests          |
| `/dashboard` | Launch web dashboard              |
| `/help`      | CLI documentation                 |
| `/exit`      | Exit session                      |

---

### Local Dashboard

A premium dark-mode dashboard built for token observability.

Capabilities:

* Daily usage charts
* Monthly consumption reports
* Budget tracking
* Cost forecasting
* Prompt efficiency analytics
* Threshold monitoring

---

## Architecture

```text
                    ┌──────────────────┐
                    │  Developer App   │
                    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    TokenOps      │
                    │ Control Layer    │
                    └─────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼

 Budget Engine         Usage Tracker       Graphify Bridge
        │                     │                     │
        ▼                     ▼                     ▼

 Forecasting         Cost Analytics      Runtime Hooks
        │                     │
        └─────────────┬───────┘
                      ▼

              Local Dashboard
                      │
                      ▼

              OpenAI Provider
```

---

## Quick Start

### Installation

```bash
pip install pyyaml openai tiktoken

pip install -e .
```

---

### Launch Interactive Shell

```bash
tokenops
```

or

```bash
python -m tokenops.cli.main
```

---

## OpenAI Integration

Replace the standard client:

```python
from tokenops import GuardedOpenAI

client = GuardedOpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": "Explain gravity in one sentence."
        }
    ]
)
```

Every request automatically receives:

* Budget validation
* Token accounting
* Cost tracking
* Usage reporting

---

## Graphify Integration

```python
from tokenops import patch_graphify

patch_graphify()
```

All Graphify extraction calls become observable and budget-governed automatically.

---

## Configuration

```yaml
project_name: MyLLMApp

budgets:
  monthly_tokens: 5000000
  daily_tokens: 150000
  per_request: 8192

thresholds:
  warning: 80
  optimize: 90
  block: 100

fallback:
  enabled: true
  model: gpt-4.1-mini
```

---

## Technology Stack

| Layer         | Technology                |
| ------------- | ------------------------- |
| Language      | Python                    |
| SDK           | OpenAI                    |
| Tokenization  | tiktoken                  |
| Configuration | YAML                      |
| Dashboard     | Chart.js                  |
| CLI           | Python Terminal Framework |
| Analytics     | Local Processing          |
| Integration   | Graphify Runtime Hooks    |

---

## Use Cases

### AI Startups

Prevent runaway inference costs during rapid experimentation.

### Engineering Teams

Track token consumption across services and environments.

### Enterprises

Enforce governance policies and spending limits.

### Open Source Projects

Gain visibility into model usage without external observability platforms.

---

## Roadmap

* Multi-provider support
* Anthropic integration
* Gemini integration
* Ollama integration
* Team dashboards
* Usage alerts
* Slack notifications
* Cost anomaly detection
* OpenTelemetry support
* Kubernetes deployment mode

---

## License

MIT License

---

<p align="center">
Built for developers who want visibility, governance, and control over AI spending.
</p>
