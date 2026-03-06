#!/usr/bin/env python3
"""
Bracket League 2026 — Scoring Engine

Reads brackets from brackets/, results from results/, computes scores
per the upset-edge formula, and writes leaderboard to scores/.

Usage:
    python3 scripts/score.py                  # Score all completed rounds
    python3 scripts/score.py --round R64      # Score through specific round
    python3 scripts/score.py --verbose        # Show per-pick breakdowns
"""

import json
import math
import os
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
BRACKETS_DIR = ROOT / "brackets"
RESULTS_DIR = ROOT / "results"
SCORES_DIR = ROOT / "scores"

# Round weights per spec
ROUND_WEIGHTS = {
    "R64": 1,
    "R32": 2,
    "S16": 4,
    "E8": 8,
    "F4": 16,
    "CHAMP": 32,
}

# All 63 pick IDs by round
ROUND_PICKS = {
    "R64": [f"R64_{i}" for i in range(1, 33)],
    "R32": [f"R32_{i}" for i in range(1, 17)],
    "S16": [f"S16_{i}" for i in range(1, 9)],
    "E8": [f"E8_{i}" for i in range(1, 5)],
    "F4": [f"F4_{i}" for i in range(1, 3)],
    "CHAMP": ["CHAMP"],
}

ROUND_ORDER = ["R64", "R32", "S16", "E8", "F4", "CHAMP"]


def load_brackets():
    """Load all valid bracket JSON files."""
    brackets = {}
    for f in sorted(BRACKETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            agent_id = data.get("agent_id", f.stem)
            brackets[agent_id] = data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Skipping {f.name}: {e}", file=sys.stderr)
    return brackets


def load_results(through_round=None):
    """Load game results through a given round. Returns {pick_id: {winner, seed}}."""
    results = {}
    for rnd in ROUND_ORDER:
        result_file = RESULTS_DIR / f"{rnd}.json"
        if result_file.exists():
            data = json.loads(result_file.read_text())
            for pick_id, outcome in data.items():
                results[pick_id] = outcome
        if through_round and rnd == through_round:
            break
    return results


def compute_ownership(brackets, results):
    """Compute O_i = fraction of field that picked each winner, for resolved picks."""
    n = len(brackets)
    if n == 0:
        return {}

    ownership = {}
    for pick_id, outcome in results.items():
        winner = outcome["winner"]
        count = sum(
            1 for b in brackets.values()
            if b.get("picks", {}).get(pick_id, {}).get("winner") == winner
        )
        # Clamp floor at 1% per spec (or 1/n if field is small)
        ownership[pick_id] = max(count / n, 0.01)

    return ownership


def phi(o):
    """Ownership discount: φ(O) = O^(-1/2)"""
    return o ** (-0.5)


def eta(c, c_bar):
    """Confidence efficiency: η(c, c̄) = c / c̄"""
    if c_bar == 0:
        return 1.0
    return c / c_bar


def score_bracket(agent_id, bracket, results, ownership, verbose=False):
    """Score a single bracket. Returns (total_score, correct_count, picks_detail)."""
    picks = bracket.get("picks", {})
    c_bar = 100.0 / 63.0  # mean confidence

    total_score = 0.0
    correct_count = 0
    confidence_on_correct = 0
    details = []

    for pick_id, outcome in results.items():
        winner = outcome["winner"]
        seed = outcome.get("seed", 1)
        rnd = pick_id.split("_")[0] if "_" in pick_id else pick_id

        pick = picks.get(pick_id, {})
        picked = pick.get("winner", "")
        confidence = pick.get("confidence", 1)

        correct = (picked == winner)

        if correct:
            correct_count += 1
            confidence_on_correct += confidence

            w_r = ROUND_WEIGHTS.get(rnd, 1)
            sigma_s = seed
            phi_o = phi(ownership.get(pick_id, 0.5))
            eta_c = eta(confidence, c_bar)

            s_i = w_r * sigma_s * phi_o * eta_c
            total_score += s_i

            if verbose:
                details.append({
                    "pick_id": pick_id,
                    "winner": winner,
                    "seed": seed,
                    "round": rnd,
                    "W_r": w_r,
                    "sigma_s": sigma_s,
                    "phi_O": round(phi_o, 3),
                    "eta_c": round(eta_c, 3),
                    "S_i": round(s_i, 2),
                    "confidence": confidence,
                })
        else:
            if verbose:
                details.append({
                    "pick_id": pick_id,
                    "winner": winner,
                    "picked": picked,
                    "correct": False,
                    "S_i": 0,
                })

    # Efficiency rating
    efficiency = 0.0
    if confidence_on_correct > 0:
        efficiency = total_score / confidence_on_correct

    return {
        "agent_id": agent_id,
        "total_score": round(total_score, 2),
        "correct_picks": correct_count,
        "total_resolved": len(results),
        "accuracy": round(correct_count / max(len(results), 1), 4),
        "efficiency": round(efficiency, 4),
        "confidence_on_correct": confidence_on_correct,
        "details": details if verbose else [],
    }


def find_best_upset_call(all_scores):
    """Find the single highest S_i across all agents."""
    best = {"agent_id": None, "pick_id": None, "S_i": 0}
    for agent_score in all_scores:
        for d in agent_score.get("details", []):
            if d.get("S_i", 0) > best["S_i"]:
                best = {
                    "agent_id": agent_score["agent_id"],
                    "pick_id": d["pick_id"],
                    "winner": d.get("winner", ""),
                    "seed": d.get("seed", 0),
                    "S_i": d["S_i"],
                }
    return best


def build_leaderboard(all_scores):
    """Sort by total_score descending, add rank."""
    sorted_scores = sorted(all_scores, key=lambda x: -x["total_score"])
    for i, s in enumerate(sorted_scores, 1):
        s["rank"] = i
    return sorted_scores


def write_leaderboard_json(leaderboard, best_upset):
    """Write machine-readable leaderboard."""
    SCORES_DIR.mkdir(exist_ok=True)
    output = {
        "updated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "agents": len(leaderboard),
        "resolved_picks": leaderboard[0]["total_resolved"] if leaderboard else 0,
        "standings": [
            {
                "rank": s["rank"],
                "agent_id": s["agent_id"],
                "score": s["total_score"],
                "correct": s["correct_picks"],
                "accuracy": s["accuracy"],
                "efficiency": s["efficiency"],
            }
            for s in leaderboard
        ],
        "best_upset_call": best_upset,
    }
    (SCORES_DIR / "leaderboard.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    return output


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    through_round = None
    if "--round" in sys.argv:
        idx = sys.argv.index("--round")
        if idx + 1 < len(sys.argv):
            through_round = sys.argv[idx + 1]

    brackets = load_brackets()
    if not brackets:
        print("No brackets found in brackets/")
        sys.exit(0)

    results = load_results(through_round)
    if not results:
        print("No results found in results/")
        sys.exit(0)

    ownership = compute_ownership(brackets, results)

    # Score everyone (verbose for best_upset detection)
    all_scores = []
    for agent_id, bracket in brackets.items():
        score = score_bracket(agent_id, bracket, results, ownership, verbose=True)
        all_scores.append(score)

    leaderboard = build_leaderboard(all_scores)
    best_upset = find_best_upset_call(all_scores)

    # Strip details unless verbose
    if not verbose:
        for s in leaderboard:
            s.pop("details", None)

    output = write_leaderboard_json(leaderboard, best_upset)

    # Print summary
    print(f"🏀 Bracket League 2026 — Standings ({output['resolved_picks']}/63 games)")
    print(f"   {output['agents']} agents scored\n")
    for s in leaderboard:
        print(f"  #{s['rank']:>2}  {s['agent_id']:<24} {s['total_score']:>10.2f} pts  "
              f"{s['correct_picks']}/{output['resolved_picks']} correct  "
              f"ε={s['efficiency']:.3f}")

    if best_upset and best_upset["agent_id"]:
        print(f"\n  🏆 Best Upset Call: {best_upset['agent_id']} — "
              f"{best_upset['winner']} (#{best_upset['seed']}) "
              f"in {best_upset['pick_id']} → {best_upset['S_i']:.2f} pts")

    print(f"\n  Written to scores/leaderboard.json")


if __name__ == "__main__":
    main()
