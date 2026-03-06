#!/usr/bin/env python3
"""Quick smoke test for the scoring engine."""

import json
import tempfile
import shutil
from pathlib import Path

# Create temp structure
tmp = Path(tempfile.mkdtemp())
(tmp / "brackets").mkdir()
(tmp / "results").mkdir()
(tmp / "scores").mkdir()

# Two test brackets
bracket_a = {
    "agent_id": "agent-chalk",
    "picks": {},
    "confidence_total": 100,
}
bracket_b = {
    "agent_id": "agent-upset",
    "picks": {},
    "confidence_total": 100,
}

# Fill R64 picks (32 games)
# Agent A picks all 1-seeds (chalk), agent B picks some upsets
for i in range(1, 33):
    bracket_a["picks"][f"R64_{i}"] = {"winner": f"Team{(i-1)//2 * 2 + 1}", "confidence": 1}
    bracket_b["picks"][f"R64_{i}"] = {"winner": f"Team{(i-1)//2 * 2 + 1}", "confidence": 1}

# R32 through CHAMP (fill with placeholders)
for i in range(1, 17):
    bracket_a["picks"][f"R32_{i}"] = {"winner": f"Team{i}", "confidence": 1}
    bracket_b["picks"][f"R32_{i}"] = {"winner": f"Team{i}", "confidence": 1}
for i in range(1, 9):
    bracket_a["picks"][f"S16_{i}"] = {"winner": f"Team{i}", "confidence": 1}
    bracket_b["picks"][f"S16_{i}"] = {"winner": f"Team{i}", "confidence": 1}
for i in range(1, 5):
    bracket_a["picks"][f"E8_{i}"] = {"winner": f"Team{i}", "confidence": 1}
    bracket_b["picks"][f"E8_{i}"] = {"winner": f"Team{i}", "confidence": 1}
bracket_a["picks"]["F4_1"] = {"winner": "Team1", "confidence": 1}
bracket_a["picks"]["F4_2"] = {"winner": "Team2", "confidence": 1}
bracket_b["picks"]["F4_1"] = {"winner": "Team1", "confidence": 1}
bracket_b["picks"]["F4_2"] = {"winner": "Team2", "confidence": 1}
bracket_a["picks"]["CHAMP"] = {"winner": "Team1", "confidence": 1}
bracket_b["picks"]["CHAMP"] = {"winner": "Team1", "confidence": 1}

# Make agent-upset pick a 12-seed upset in R64_5 with high confidence
bracket_b["picks"]["R64_5"] = {"winner": "Cinderella", "confidence": 20}
# Rebalance: reduce elsewhere
surplus = 19  # added 19 extra to R64_5
adjusted = 0
for pid in bracket_b["picks"]:
    if pid != "R64_5" and adjusted < surplus:
        # Can't go below 1, skip ones already at 1
        pass
# Simpler: just set all others to 1, total = 62*1 + 20 = 82, need 100
# Set a few others higher
bracket_b["picks"]["CHAMP"]["confidence"] = 10  # +9
bracket_b["picks"]["F4_1"]["confidence"] = 5    # +4
bracket_b["picks"]["R32_1"]["confidence"] = 5   # +4
# Now: 59*1 + 20 + 10 + 5 + 5 = 99... need 1 more
bracket_b["picks"]["R64_1"]["confidence"] = 2   # +1 = 100

# Verify totals
total_a = sum(p["confidence"] for p in bracket_a["picks"].values())
total_b = sum(p["confidence"] for p in bracket_b["picks"].values())
assert total_a == 63, f"A: {total_a}"  # all 1s = 63, need to fix
# A has 63 picks * 1 = 63 confidence, not 100. Fix:
# Distribute remaining 37 across picks
extra = 100 - 63
for i in range(1, extra + 1):
    pid = f"R64_{(i % 32) + 1}"
    bracket_a["picks"][pid]["confidence"] += 1

total_a = sum(p["confidence"] for p in bracket_a["picks"].values())
total_b = sum(p["confidence"] for p in bracket_b["picks"].values())
print(f"Confidence totals: A={total_a}, B={total_b}")
assert total_a == 100, f"A confidence: {total_a}"
assert total_b == 100, f"B confidence: {total_b}"

(tmp / "brackets" / "agent-chalk.json").write_text(json.dumps(bracket_a, indent=2))
(tmp / "brackets" / "agent-upset.json").write_text(json.dumps(bracket_b, indent=2))

# Results: R64 only, Cinderella wins game 5 (12-seed upset)
results = {}
for i in range(1, 33):
    if i == 5:
        results[f"R64_{i}"] = {"winner": "Cinderella", "seed": 12}
    else:
        results[f"R64_{i}"] = {"winner": f"Team{(i-1)//2 * 2 + 1}", "seed": 1}

(tmp / "results" / "R64.json").write_text(json.dumps(results, indent=2))

# Monkey-patch ROOT and run scorer
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score
score.ROOT = tmp
score.BRACKETS_DIR = tmp / "brackets"
score.RESULTS_DIR = tmp / "results"
score.SCORES_DIR = tmp / "scores"

score.main()

# Cleanup
shutil.rmtree(tmp)
print("\n✅ Scoring engine test passed!")
