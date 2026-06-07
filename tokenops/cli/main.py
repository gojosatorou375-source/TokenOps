import argparse
import sys
from pathlib import Path

from tokenops.budgets.config import load_config
from tokenops.tracking.aggregator import get_aggregated_by_provider_model, get_totals_for_timeframe, read_records
from tokenops.reporting.formatter import format_table, get_progress_bar
from tokenops.forecasting.engine import generate_forecast
from tokenops.optimization.recommender import get_recommendations

# Per-million-token rates (input, output)
PRICING = {
    "openai": (0.40, 1.60),
    "anthropic": (3.00, 15.00),
    "claude": (3.00, 15.00),
    "gemini": (0.50, 3.00),
    "deepseek": (0.14, 0.28),
    "kimi": (0.74, 4.66),
    "ollama": (0.00, 0.00),
    "bedrock": (0.80, 3.20),
}

def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimates cost in USD based on rates mapping."""
    prov = provider.lower()
    mdl = model.lower()
    rate = (0.50, 2.00) # Default fallback
    
    for key, val in PRICING.items():
        if key in prov or key in mdl:
            rate = val
            break
    return (input_tokens / 1_000_000) * rate[0] + (output_tokens / 1_000_000) * rate[1]

def cmd_init():
    """Scaffolds tokenops.yaml if it does not exist."""
    config_file = Path.cwd() / "tokenops.yaml"
    if config_file.exists():
        print(f"[tokenops] tokenops.yaml already exists at {config_file}")
        return
        
    default_config = """project_name: MyProject

# Global token budgets
budgets:
  monthly_tokens: 5000000
  daily_tokens: 150000
  per_request: 8192

# Graduated threshold actions
thresholds:
  warning: 80
  optimize: 90
  block: 100

# Fallback model settings
fallback:
  enabled: true
  model: gpt-4.1-mini

# Active tracking status per provider
providers:
  openai: true
  anthropic: true
  gemini: false
  graphify: true

# CI/CD validation rules
ci:
  max_prompt_growth: 20
"""
    try:
        config_file.write_text(default_config, encoding="utf-8")
        print(f"[tokenops] Scaffolded default configuration file at {config_file}")
    except Exception as e:
        print(f"[tokenops] Error writing config file: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_report():
    """Aggregates and formats a table of token spend."""
    agg = get_aggregated_by_provider_model()
    if not agg:
        print("[tokenops] No usage logs found. Run some calls or populate logs first.")
        return
        
    headers = ["Provider", "Model", "Input Tokens", "Output Tokens", "Total Tokens", "Est. Cost ($)"]
    rows = []
    
    total_in = 0
    total_out = 0
    total_tot = 0
    total_cost = 0.0
    
    for (prov, mod), stats in sorted(agg.items()):
        in_t = stats["input_tokens"]
        out_t = stats["output_tokens"]
        tot_t = stats["total_tokens"]
        cost = estimate_cost(prov, mod, in_t, out_t)
        
        total_in += in_t
        total_out += out_t
        total_tot += tot_t
        total_cost += cost
        
        rows.append([
            prov,
            mod,
            f"{in_t:,}",
            f"{out_t:,}",
            f"{tot_t:,}",
            f"${cost:.4f}"
        ])
        
    rows.append([
        "TOTAL",
        "-",
        f"{total_in:,}",
        f"{total_out:,}",
        f"{total_tot:,}",
        f"${total_cost:.4f}"
    ])
    
    print("\nTokenOps Usage Report")
    print("=====================")
    print(format_table(headers, rows))

def cmd_check():
    """Compares current usage against budgets. Exits 1 if exceeded."""
    config = load_config()
    budgets = config.get("budgets", {})
    
    daily_limit = budgets.get("daily_tokens", 150000)
    monthly_limit = budgets.get("monthly_tokens", 5000000)
    
    daily_usage = get_totals_for_timeframe(current_day_only=True)
    monthly_usage = get_totals_for_timeframe(current_month_only=True)
    
    exceeded = False
    print("\nAI Budget Status Check")
    print("----------------------")
    
    if daily_limit > 0:
        percent = (daily_usage / daily_limit) * 100
        print(f"Daily Budget:   {daily_usage:,} / {daily_limit:,} tokens")
        print(get_progress_bar(percent))
        if percent >= 100:
            print("[!] Daily token budget exceeded!")
            exceeded = True
            
    if monthly_limit > 0:
        percent = (monthly_usage / monthly_limit) * 100
        print(f"Monthly Budget: {monthly_usage:,} / {monthly_limit:,} tokens")
        print(get_progress_bar(percent))
        if percent >= 100:
            print("[!] Monthly token budget exceeded!")
            exceeded = True
            
    if exceeded:
        sys.exit(1)
    else:
        print("\n[ok] All token budgets within limits.")
        sys.exit(0)

def cmd_forecast():
    """Generates and displays burn rates and exhaust forecasts."""
    forecast = generate_forecast()
    
    print("\nAI Token Burn Rate & Spend Forecast")
    print("===================================")
    print(f"Current Month Usage:   {forecast['current_month_usage']:,} tokens")
    print(f"Estimated Daily Burn:  {forecast['daily_burn_rate']:,} tokens/day")
    print(f"Projected Month-End:   {forecast['projected_monthly_usage']:,} tokens")
    print(f"Monthly Budget Limit:  {forecast['monthly_limit']:,} tokens")
    
    if forecast["overrun_percent"] > 0:
        print(f"\n[!] WARNING: Budget overrun of {forecast['overrun_percent']}% expected.")
        print(f"[!] Estimated Budget Exhaustion Date: {forecast['exhaustion_date']}")
    else:
        print("\n[ok] Spending is on track. No budget overrun predicted.")

def cmd_optimize():
    """Audits recent prompts for token reduction advice."""
    records = read_records()
    analysis = get_recommendations(records)
    
    print("\nAI Prompt Efficiency Optimization")
    print("=================================")
    print(f"Evaluated token volume: {analysis['total_tokens_evaluated']:,} tokens")
    print(f"Estimated potential savings: {analysis['estimated_savings_percent']}%")
    print()
    
    recs = analysis["recommendations"]
    if not recs:
        print("No efficiency issues detected in recent prompts. Good job!")
        return
        
    for idx, rec in enumerate(recs, start=1):
        print(f"{idx}. [{rec['category']}] (Est. Saving: {rec['potential_savings']}%)")
        print(f"   Issue:      {rec['description']}")
        print(f"   Suggestion: {rec['suggestion']}\n")

def cmd_dashboard(port=5000):
    """Starts local dashboard server."""
    try:
        from tokenops.dashboard.server import start_server
        start_server(port=port)
    except Exception as e:
        print(f"[tokenops] Error starting dashboard: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_shell():
    """Starts a beautiful interactive terminal for TokenOps cost governance."""
    import os
    print("\n" + "=" * 60)
    print(r"""
████████╗ ██████╗ ██╗  ██╗███████╗███╗   ██╗ ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔═══██╗██║ ██╔╝██╔════╝████╗  ██║██╔═══██╗██╔══██╗██╔════╝
   ██║   ██║   ██║█████╔╝ █████╗  ██╔██╗ ██║██║   ██║██████╔╝███████╗
   ██║   ██║   ██║██╔═██╗ ██╔══╝  ██║╚██╗██║██║   ██║██╔═══╝ ╚════██║
   ██║   ╚██████╔╝██║  ██╗███████╗██║ ╚████║╚██████╔╝██║     ███████║
   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚══════╝
    """)
    print("=" * 60)
    print("\nTips for getting started:")
    print("1. Type /help to view all available commands.")
    print("2. Run '/run <prompt>' to test a guarded LLM request.")
    print("3. Enter '/patch' to test the Graphify integration bridge.")
    
    while True:
        try:
            line = input("\ntokenops > ").strip()
            if not line:
                continue
                
            if not line.startswith("/"):
                print("Commands must start with a slash '/'. Type '/help' for a list of commands.")
                continue
                
            parts = line.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == "/exit" or cmd == "/quit":
                print("Goodbye!")
                break
            elif cmd == "/help":
                print("\nAvailable Commands:")
                print("  /report     - Print token spending report table")
                print("  /check      - Verify current usage against budgets")
                print("  /forecast   - Project monthly spending and exhaustion dates")
                print("  /optimize   - Audit recent prompts for cost reduction suggestions")
                print("  /patch      - Activate Graphify patch and run simulated extraction")
                print("  /run <msg>  - Send a prompt to GuardedOpenAI (simulated if api key missing)")
                print("  /dashboard  - Start the local web visualization dashboard")
                print("  /exit       - Close the interactive session")
            elif cmd == "/report":
                cmd_report()
            elif cmd == "/check":
                try:
                    cmd_check()
                except SystemExit:
                    pass
            elif cmd == "/forecast":
                cmd_forecast()
            elif cmd == "/optimize":
                cmd_optimize()
            elif cmd == "/patch":
                from tokenops import patch_graphify
                patch_graphify()
                print("[patch] Graphify patch activated at runtime.")
                print("[patch] Simulating patched Graphify call...")
                try:
                    import graphify.llm
                    res = graphify.llm.extract_files_direct(
                        files=[Path("demo.py")],
                        backend="openai"
                    )
                    print(f"[patch] Success! Intercepted {res['input_tokens'] + res['output_tokens']} tokens.")
                except Exception as e:
                    print(f"[patch] Failed to simulate Graphify extraction: {e}")
            elif cmd == "/run":
                if not args:
                    print("Error: /run command requires a prompt message. Example: /run Tell me a story.")
                    continue
                
                from tokenops.optimization.analyzer import analyze_prompt_content
                from tokenops.optimization.refiner import refine_prompt
                
                issues = analyze_prompt_content(system_prompt="", user_prompt=args)
                run_prompt = args
                
                if issues:
                    print("\n[!] PROMPT INEFFICIENCY DETECTED:")
                    for idx, issue in enumerate(issues, start=1):
                        print(f"  {idx}. [{issue['category']}] (Est. Saving: {issue['potential_savings']}%):")
                        print(f"     Issue:      {issue['description']}")
                        print(f"     Suggestion: {issue['suggestion']}")
                    
                    if any(issue['category'] == "Redundant Instructions" for issue in issues):
                        refined_prompt, removed_phrases = refine_prompt(args)
                        print(f"\nRefinement Suggestion:")
                        print(f"  Original:  \"{args}\"")
                        print(f"  Optimized: \"{refined_prompt}\"")
                        print(f"  Removed:   {', '.join([repr(x) for x in removed_phrases])}")
                        
                        try:
                            choice = input("\nOptimize prompt before running? (y/n) [y]: ").strip().lower()
                        except (KeyboardInterrupt, EOFError):
                            choice = "n"
                            
                        if choice in ("", "y", "yes"):
                            run_prompt = refined_prompt
                            print(f"[run] Running optimized prompt...")
                        else:
                            print(f"[run] Running original prompt...")
                    else:
                        print()
                
                from tokenops import GuardedOpenAI
                api_key = os.environ.get("OPENAI_API_KEY", "mock-key")
                
                if api_key == "mock-key":
                    print("[run] No OPENAI_API_KEY detected in environment. Running simulation...")
                    prompt_tok = len(run_prompt) // 4 + 5
                    comp_tok = 50
                    from tokenops.tracking.recorder import record_usage
                    from tokenops.budgets.enforcer import check_budget
                    try:
                        check_budget("openai", estimated_tokens=prompt_tok)
                        print(f"[run] Response: Mocked response content for request: '{run_prompt}'")
                        record_usage("openai", "gpt-4.1-mini", prompt_tok, comp_tok, [{"role": "user", "content": run_prompt}])
                        print(f"[run] Telemetry recorded: {prompt_tok} input, {comp_tok} output tokens.")
                    except Exception as e:
                        print(f"[run] Request blocked: {e}")
                else:
                    print(f"[run] Sending request to OpenAI using your API key...")
                    client = GuardedOpenAI()
                    try:
                        resp = client.chat.completions.create(
                            model="gpt-4.1-mini",
                            messages=[{"role": "user", "content": run_prompt}]
                        )
                        print(f"[run] Response: {resp.choices[0].message.content}")
                    except Exception as e:
                        print(f"[run] Error during execution: {e}")
            elif cmd == "/dashboard":
                cmd_dashboard()
            else:
                print(f"Unknown command '{cmd}'. Type '/help' for assistance.")
        except KeyboardInterrupt:
            print("\nUse '/exit' to quit the interactive session.")
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description="TokenOps LLM Cost Governance CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("init", help="Scaffold default tokenops.yaml")
    subparsers.add_parser("report", help="Print token spending report table")
    subparsers.add_parser("check", help="Verify current usage against budgets (exit 1 if exceeded)")
    subparsers.add_parser("forecast", help="Project spending and budget exhaustion date")
    subparsers.add_parser("optimize", help="Audit recent prompts for recommendations")
    
    dash_parser = subparsers.add_parser("dashboard", help="Start the local visualization dashboard")
    dash_parser.add_argument("--port", type=int, default=5000, help="Local server port (default: 5000)")
    
    args = parser.parse_args()
    
    if args.command == "init":
        cmd_init()
    elif args.command == "report":
        cmd_report()
    elif args.command == "check":
        cmd_check()
    elif args.command == "forecast":
        cmd_forecast()
    elif args.command == "optimize":
        cmd_optimize()
    elif args.command == "dashboard":
        cmd_dashboard(args.port)
    else:
        cmd_shell()

if __name__ == "__main__":
    main()
