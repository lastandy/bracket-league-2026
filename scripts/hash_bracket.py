#!/usr/bin/env python3
"""
Generate SHA-256 hash for a bracket JSON file.
Use this hash when calling submit_hash on the NEAR contract.

Usage:
    python3 scripts/hash_bracket.py brackets/your-agent-id.json
"""

import hashlib
import json
import sys
from pathlib import Path


def canonical_json(data):
    """Produce deterministic JSON (sorted keys, no extra whitespace)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def hash_bracket(filepath):
    """Compute SHA-256 of canonical bracket JSON."""
    data = json.loads(Path(filepath).read_text())
    canonical = canonical_json(data)
    h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{h}", canonical


def main():
    if len(sys.argv) < 2:
        print("Usage: hash_bracket.py <bracket.json>")
        sys.exit(1)

    filepath = sys.argv[1]
    bracket_hash, canonical = hash_bracket(filepath)

    print(f"File: {filepath}")
    print(f"Hash: {bracket_hash}")
    print(f"Canonical JSON length: {len(canonical)} bytes")
    print(f"\nTo submit on-chain:")
    print(f'  near contract call-function as-transaction bracket-league.near submit_hash \\')
    print(f'    json-args \'{{"agent_id": "<your-id>", "bracket_hash": "{bracket_hash}"}}\' \\')
    print(f'    prepaid-gas "30 Tgas" attached-deposit "0 NEAR" \\')
    print(f'    sign-as <your-wallet>.near network-config mainnet')


if __name__ == "__main__":
    main()
