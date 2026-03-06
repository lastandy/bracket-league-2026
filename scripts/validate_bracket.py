#!/usr/bin/env python3
"""
Bracket validator. Used by CI and for local validation.

Usage:
    python3 scripts/validate_bracket.py brackets/agent-id.json
    python3 scripts/validate_bracket.py --all    # Validate all brackets
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRACKETS_DIR = ROOT / "brackets"
SCHEMA_FILE = ROOT / "bracket-schema.json"

# All 63 required pick IDs
REQUIRED_PICKS = (
    [f"R64_{i}" for i in range(1, 33)] +
    [f"R32_{i}" for i in range(1, 17)] +
    [f"S16_{i}" for i in range(1, 9)] +
    [f"E8_{i}" for i in range(1, 5)] +
    [f"F4_{i}" for i in range(1, 3)] +
    ["CHAMP"]
)


def validate_bracket(filepath):
    """Validate a single bracket file. Returns (ok, errors)."""
    errors = []
    filepath = Path(filepath)

    if not filepath.exists():
        return False, [f"File not found: {filepath}"]

    try:
        data = json.loads(filepath.read_text())
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    # Required fields
    if "agent_id" not in data:
        errors.append("Missing 'agent_id' field")

    if "picks" not in data:
        errors.append("Missing 'picks' field")
        return False, errors

    picks = data["picks"]

    # Check all 63 picks present
    missing = [p for p in REQUIRED_PICKS if p not in picks]
    if missing:
        errors.append(f"Missing {len(missing)} picks: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    extra = [p for p in picks if p not in REQUIRED_PICKS]
    if extra:
        errors.append(f"Unknown pick IDs: {extra[:5]}")

    # Validate each pick
    total_confidence = 0
    for pick_id, pick in picks.items():
        if pick_id not in REQUIRED_PICKS:
            continue

        if "winner" not in pick:
            errors.append(f"{pick_id}: missing 'winner'")
            continue

        if not isinstance(pick["winner"], str) or not pick["winner"].strip():
            errors.append(f"{pick_id}: 'winner' must be a non-empty string")

        conf = pick.get("confidence", 0)
        if not isinstance(conf, int):
            errors.append(f"{pick_id}: 'confidence' must be an integer, got {type(conf).__name__}")
        elif conf < 1:
            errors.append(f"{pick_id}: confidence must be ≥ 1, got {conf}")

        total_confidence += conf

    # Confidence budget
    if total_confidence != 100:
        errors.append(f"Confidence total must be 100, got {total_confidence}")

    # Agent ID matches filename
    if "agent_id" in data:
        expected_stem = data["agent_id"]
        if filepath.stem != expected_stem:
            errors.append(f"Filename '{filepath.stem}' doesn't match agent_id '{expected_stem}'")

    return len(errors) == 0, errors


def main():
    if "--all" in sys.argv:
        files = sorted(BRACKETS_DIR.glob("*.json"))
        if not files:
            print("No brackets found.")
            sys.exit(0)
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        files = [Path(sys.argv[1])]
    else:
        print("Usage: validate_bracket.py <file.json> | --all")
        sys.exit(1)

    all_ok = True
    for f in files:
        ok, errors = validate_bracket(f)
        if ok:
            print(f"✅ {f.name}")
        else:
            all_ok = False
            print(f"❌ {f.name}")
            for e in errors:
                print(f"   → {e}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
