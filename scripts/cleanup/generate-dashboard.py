#!/usr/bin/env python3
"""Generate cleanup progress dashboard."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict


def load_backlog() -> Dict:
    """Load cleanup backlog."""
    backlog_path = Path("reports/cleanup/backlog.json")
    if not backlog_path.exists():
        # Create sample backlog if it doesn't exist
        return {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "version": "1.0",
                "total_items": 0,
            },
            "items": [],
            "summary": {
                "by_status": {
                    "completed": 0,
                    "in_progress": 0,
                    "todo": 0,
                    "blocked": 0,
                },
                "by_risk": {"low": 0, "medium": 0, "high": 0},
            },
        }

    with open(backlog_path) as f:
        return json.load(f)


def calculate_velocity(backlog: Dict) -> Dict[str, float]:
    """Calculate velocity metrics."""
    items = backlog.get("items", [])

    completed_items = [
        item
        for item in items
        if item.get("status") == "completed" and item.get("completed")
    ]

    if not completed_items:
        return {"items_per_day": 0.0, "avg_hours_per_item": 0.0}

    # Calculate time spans
    dates = []
    total_hours = 0

    for item in completed_items:
        if item.get("started") and item.get("completed"):
            start = datetime.fromisoformat(item["started"])
            end = datetime.fromisoformat(item["completed"])
            dates.append(end)
            hours = (end - start).total_seconds() / 3600
            total_hours += hours

    if len(dates) < 2:
        return {
            "items_per_day": len(completed_items),
            "avg_hours_per_item": (
                total_hours / len(completed_items) if completed_items else 0
            ),
        }

    # Calculate velocity
    first_date = min(dates)
    last_date = max(dates)
    days = (last_date - first_date).days + 1

    return {
        "items_per_day": len(completed_items) / days if days > 0 else 0,
        "avg_hours_per_item": total_hours / len(completed_items),
    }


def generate_html_dashboard(backlog: Dict, velocity: Dict) -> str:
    """Generate HTML dashboard."""
    summary = backlog.get("summary", {})
    status = summary.get("by_status", {})
    risk = summary.get("by_risk", {})

    total = backlog["metadata"]["total_items"]
    completed = status.get("completed", 0)
    in_progress = status.get("in_progress", 0)
    blocked = status.get("blocked", 0)
    todo = status.get("todo", total - completed - in_progress - blocked)

    progress_pct = (completed / total * 100) if total > 0 else 0

    # Calculate ETA
    remaining = total - completed
    items_per_day = velocity.get("items_per_day", 0)
    eta_days = remaining / items_per_day if items_per_day > 0 else 0

    # Recent items
    recent_items = [
        item for item in backlog.get("items", []) if item.get("status") == "completed"
    ][-5:]

    recent_html = ""
    for item in reversed(recent_items):
        recent_html += f"""
        <tr>
            <td>{item.get("id", "N/A")}</td>
            <td>{item.get("title", "N/A")}</td>
            <td><span class="badge risk-{item.get("risk", "low")}">{item.get("risk", "low").upper()}</span></td>
            <td>{item.get("completed", "N/A")[:10]}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Legacy Cleanup Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .timestamp {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 30px;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .metric {{
            padding: 25px;
            border-radius: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
        }}

        .metric.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}

        .metric.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}

        .metric.info {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}

        .metric h2 {{
            font-size: 48px;
            margin-bottom: 10px;
            font-weight: 300;
        }}

        .metric p {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.9;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}

        .progress-bar {{
            width: 100%;
            height: 40px;
            background: #ecf0f1;
            border-radius: 20px;
            overflow: hidden;
            margin-bottom: 10px;
            position: relative;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db 0%, #2ecc71 100%);
            width: {progress_pct}%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 15px;
            color: white;
            font-weight: bold;
        }}

        .risk-breakdown {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }}

        .risk-item {{
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}

        .risk-low {{
            background: #d5f4e6;
            color: #27ae60;
        }}

        .risk-medium {{
            background: #fff4e6;
            color: #f39c12;
        }}

        .risk-high {{
            background: #fadbd8;
            color: #e74c3c;
        }}

        .risk-item h3 {{
            font-size: 32px;
            margin-bottom: 5px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}

        th {{
            background: #34495e;
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}

        .velocity {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
        }}

        .velocity-item {{
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}

        .velocity-item .label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}

        .velocity-item .value {{
            font-size: 28px;
            color: #2c3e50;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Legacy Cleanup Dashboard</h1>
        <p class="timestamp">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

        <div class="metrics">
            <div class="metric">
                <h2>{total}</h2>
                <p>Total Items</p>
            </div>
            <div class="metric success">
                <h2>{completed}</h2>
                <p>Completed</p>
            </div>
            <div class="metric warning">
                <h2>{in_progress}</h2>
                <p>In Progress</p>
            </div>
            <div class="metric info">
                <h2>{todo}</h2>
                <p>Remaining</p>
            </div>
        </div>

        <div class="section">
            <h2>Overall Progress: {progress_pct:.1f}%</h2>
            <div class="progress-bar">
                <div class="progress-fill">{progress_pct:.1f}%</div>
            </div>
            <p style="color: #7f8c8d; margin-top: 10px;">
                {completed} of {total} items completed
            </p>
        </div>

        <div class="section">
            <h2>Items by Risk Level</h2>
            <div class="risk-breakdown">
                <div class="risk-item risk-low">
                    <h3>{risk.get("low", 0)}</h3>
                    <p>Low Risk</p>
                </div>
                <div class="risk-item risk-medium">
                    <h3>{risk.get("medium", 0)}</h3>
                    <p>Medium Risk</p>
                </div>
                <div class="risk-item risk-high">
                    <h3>{risk.get("high", 0)}</h3>
                    <p>High Risk</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Velocity Metrics</h2>
            <div class="velocity">
                <div class="velocity-item">
                    <div class="label">Items per Day</div>
                    <div class="value">{velocity.get("items_per_day", 0):.1f}</div>
                </div>
                <div class="velocity-item">
                    <div class="label">Avg Hours per Item</div>
                    <div class="value">{velocity.get("avg_hours_per_item", 0):.1f}</div>
                </div>
            </div>
            {f'<p style="margin-top: 15px; color: #7f8c8d;">Estimated completion: {eta_days:.1f} days</p>' if eta_days > 0 else ''}
        </div>

        {f'''<div class="section">
            <h2>Recently Completed</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Risk</th>
                        <th>Completed</th>
                    </tr>
                </thead>
                <tbody>
                    {recent_html}
                </tbody>
            </table>
        </div>''' if recent_items else ''}
    </div>
</body>
</html>
"""

    return html


def main():
    """Generate dashboard."""
    print("Generating cleanup dashboard...")

    # Load data
    backlog = load_backlog()
    velocity = calculate_velocity(backlog)

    # Generate HTML
    html = generate_html_dashboard(backlog, velocity)

    # Save dashboard
    output_path = Path("reports/cleanup/dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"✓ Dashboard generated: {output_path}")
    print(f"  Open file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
