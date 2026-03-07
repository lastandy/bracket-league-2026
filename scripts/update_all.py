#!/usr/bin/env python3
"""
Full pipeline: fetch results → score → update leaderboard → commit & push.
Designed to run via cron during the tournament.

Usage:
    python3 scripts/update_all.py              # Full pipeline
    python3 scripts/update_all.py --no-push    # Update locally, don't push
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd=None):
    """Run a command, return (success, output)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or ROOT
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output.strip()


def main():
    no_push = "--no-push" in sys.argv

    print("=" * 60)
    print("🏀 Bracket League 2026 — Update Pipeline")
    print("=" * 60)

    # 1. Fetch results
    print("\n📡 Step 1: Fetching results from ESPN...")
    ok, output = run("python3 scripts/fetch_results.py")
    print(output)
    if not ok:
        print("⚠️  Results fetch had issues, continuing anyway...")

    # 2. Score
    print("\n📊 Step 2: Running scorer...")
    ok, output = run("python3 scripts/score.py")
    print(output)
    if not ok:
        print("⚠️  Scoring had issues")
        return

    # 3. Update leaderboard
    print("\n📋 Step 3: Updating README leaderboard...")
    ok, output = run("python3 scripts/update_leaderboard.py")
    print(output)

    # 4. Git commit & push
    ok, status = run("git status --porcelain")
    if not status.strip():
        print("\n✅ No changes to commit")
        return

    print(f"\n📝 Step 4: Committing changes...")
    run("git add results/ scores/ README.md")
    ok, output = run('git commit -m "🏀 Update: results + leaderboard"')
    print(output)

    if no_push:
        print("\n⏸️  Skipping push (--no-push)")
    else:
        print("\n🚀 Step 5: Pushing to GitHub...")
        ok, output = run("git push")
        if ok:
            print("✅ Pushed to GitHub")
        else:
            print(f"❌ Push failed: {output}")


if __name__ == "__main__":
    main()
