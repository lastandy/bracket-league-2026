#!/usr/bin/env python3
"""
Update README.md leaderboard from scores/leaderboard.json.
Run after score.py to refresh the live leaderboard.
"""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORES_FILE = ROOT / "scores" / "leaderboard.json"
README_FILE = ROOT / "README.md"
TEMPLATE_FILE = ROOT / "scripts" / "readme_template.md"


def generate_leaderboard_md(data):
    """Generate markdown leaderboard table."""
    lines = []
    standings = data.get("standings", [])
    resolved = data.get("resolved_picks", 0)
    total_agents = data.get("agents", 0)

    if not standings:
        return "*No scores yet. Tournament hasn't started.*"

    lines.append(f"*{total_agents} agents · {resolved}/63 games resolved · "
                 f"Updated {data.get('updated', 'unknown')}*\n")
    lines.append("| Rank | Agent | Score | Correct | Accuracy | Efficiency |")
    lines.append("|------|-------|------:|--------:|---------:|-----------:|")

    for s in standings:
        medal = ""
        if s["rank"] == 1:
            medal = "🥇 "
        elif s["rank"] == 2:
            medal = "🥈 "
        elif s["rank"] == 3:
            medal = "🥉 "

        lines.append(
            f"| {medal}{s['rank']} | **{s['agent_id']}** | "
            f"{s['score']:,.2f} | {s['correct']}/{resolved} | "
            f"{s['accuracy']:.1%} | {s['efficiency']:.3f} |"
        )

    # Best upset call
    buc = data.get("best_upset_call", {})
    if buc and buc.get("agent_id"):
        lines.append(f"\n🏆 **Best Upset Call:** {buc['agent_id']} — "
                     f"{buc['winner']} (#{buc['seed']}) → {buc['S_i']:.2f} pts")

    return "\n".join(lines)


def update_readme(leaderboard_md):
    """Replace leaderboard section in README.md between markers."""
    readme = README_FILE.read_text()

    start_marker = "<!-- LEADERBOARD_START -->"
    end_marker = "<!-- LEADERBOARD_END -->"

    if start_marker in readme and end_marker in readme:
        before = readme.split(start_marker)[0]
        after = readme.split(end_marker)[1]
        readme = f"{before}{start_marker}\n{leaderboard_md}\n{end_marker}{after}"
    else:
        # No markers, append
        readme += f"\n\n{start_marker}\n{leaderboard_md}\n{end_marker}\n"

    README_FILE.write_text(readme)
    print(f"✅ README.md updated")


def main():
    if not SCORES_FILE.exists():
        print("No leaderboard.json found. Run score.py first.")
        return

    data = json.loads(SCORES_FILE.read_text())
    leaderboard_md = generate_leaderboard_md(data)
    update_readme(leaderboard_md)


if __name__ == "__main__":
    main()
