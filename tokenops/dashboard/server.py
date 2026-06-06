import http.server
import socketserver
import json
import webbrowser
import time
import threading
from pathlib import Path

from tokenops.tracking.aggregator import read_records, get_aggregated_by_provider_model, get_totals_for_timeframe
from tokenops.budgets.config import load_config
from tokenops.forecasting.engine import generate_forecast
from tokenops.optimization.recommender import get_recommendations

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging output to keep console tidy
        pass
        
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            html_path = Path(__file__).parent / "index.html"
            try:
                content = html_path.read_text(encoding="utf-8")
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.wfile.write(f"<h3>Error loading index.html: {e}</h3>".encode("utf-8"))
                
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            data = self.get_dashboard_data()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            
    def get_dashboard_data(self) -> dict:
        config = load_config()
        records = read_records()
        forecast = generate_forecast()
        recs_data = get_recommendations(records)
        
        monthly_limit = config.get("budgets", {}).get("monthly_tokens", 5000000)
        daily_limit = config.get("budgets", {}).get("daily_tokens", 150000)
        
        monthly_usage = get_totals_for_timeframe(current_month_only=True)
        daily_usage = get_totals_for_timeframe(current_day_only=True)
        
        monthly_percent = (monthly_usage / monthly_limit) * 100 if monthly_limit > 0 else 0.0
        daily_percent = (daily_usage / daily_limit) * 100 if daily_limit > 0 else 0.0
        
        provider_stats = {}
        model_stats = {}
        daily_trend_stats = {}
        total_spend = 0.0
        from tokenops.cli.main import estimate_cost
        
        for r in records:
            # 1. Provider breakdown
            prov = r.get("provider", "unknown")
            provider_stats[prov] = provider_stats.get(prov, 0) + r.get("total_tokens", 0)
            
            # 2. Model breakdown
            model = r.get("model", "unknown")
            model_stats[model] = model_stats.get(model, 0) + r.get("total_tokens", 0)
            
            # 3. Daily trend
            ts = r.get("timestamp", "")
            if ts and len(ts) >= 10:
                date = ts[:10]
                daily_trend_stats[date] = daily_trend_stats.get(date, 0) + r.get("total_tokens", 0)
                
            # 4. Total Spend Calculation
            total_spend += estimate_cost(
                prov,
                model,
                r.get("input_tokens", 0),
                r.get("output_tokens", 0)
            )
                
        sorted_dates = sorted(daily_trend_stats.keys())
        trend_values = [daily_trend_stats[d] for d in sorted_dates]
        
        recent = []
        for r in reversed(records[-15:]):
            recent.append({
                "timestamp": r.get("timestamp", ""),
                "provider": r.get("provider", ""),
                "model": r.get("model", ""),
                "input_tokens": r.get("input_tokens", 0),
                "output_tokens": r.get("output_tokens", 0),
                "total_tokens": r.get("total_tokens", 0)
            })
            
        return {
            "project_name": config.get("project_name", "MyProject"),
            "total_spend": round(total_spend, 4),
            "monthly": {
                "usage": monthly_usage,
                "limit": monthly_limit,
                "percent": round(monthly_percent, 1)
            },
            "daily": {
                "usage": daily_usage,
                "limit": daily_limit,
                "percent": round(daily_percent, 1)
            },
            "forecast": forecast,
            "optimization": {
                "savings_percent": recs_data["estimated_savings_percent"],
                "recommendations": recs_data["recommendations"]
            },
            "charts": {
                "providers": {
                    "labels": list(provider_stats.keys()),
                    "values": list(provider_stats.values())
                },
                "models": {
                    "labels": list(model_stats.keys()),
                    "values": list(model_stats.values())
                },
                "daily_trend": {
                    "labels": sorted_dates[-10:],
                    "values": trend_values[-10:]
                }
            },
            "recent_calls": recent
        }

def start_server(port: int = 5000):
    handler = DashboardHandler
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}"
            print(f"\n[tokenops] Dashboard active at {url}")
            print("[tokenops] Press Ctrl+C to stop the dashboard server.")
            
            # Launch browser automatically
            def open_browser():
                time.sleep(0.5)
                webbrowser.open(url)
            threading.Thread(target=open_browser, daemon=True).start()
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n[tokenops] Stopping dashboard server...")
    except OSError as e:
        print(f"[tokenops] Could not start server on port {port}: {e}")
