#!/usr/bin/env python3
"""
Fetch NCAA Tournament bracket from ESPN after Selection Sunday.
Generates matchups.json mapping pick IDs to real matchups.

Usage:
    python3 scripts/fetch_bracket.py              # Fetch and generate matchups
    python3 scripts/fetch_bracket.py --dry-run     # Preview without writing
"""

import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
MATCHUPS_FILE = ROOT / "matchups.json"

# ESPN bracket endpoint
ESPN_BRACKET = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# Regions in standard bracket order
REGIONS = ["East", "West", "South", "Midwest"]

# Standard bracket matchups by seed for each region
# R64: 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15
SEED_MATCHUPS = [
    (1, 16), (8, 9), (5, 12), (4, 13),
    (6, 11), (3, 14), (7, 10), (2, 15),
]


def fetch_tournament_teams():
    """
    Fetch tournament field from ESPN.
    Returns dict of {region: [{seed, team_name, team_short}, ...]}
    """
    # ESPN doesn't have a clean bracket API, so we scrape from scoreboard
    # after games are scheduled. Alternative: parse the selection show data.

    # Try fetching tournament schedule
    url = f"{ESPN_BRACKET}?groups=100&dates=20260318-20260321&limit=50"
    try:
        req = Request(url, headers={"User-Agent": "BracketLeague/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            events = data.get("events", [])
    except (URLError, json.JSONDecodeError) as e:
        print(f"⚠️  Error fetching bracket: {e}", file=sys.stderr)
        return None

    if not events:
        print("No tournament games found yet. Bracket may not be published.")
        return None

    # Parse teams by region
    regions = {}
    for event in events:
        comps = event.get("competitions", [{}])[0]
        notes = comps.get("notes", [])

        # Extract region from notes
        region = None
        for note in notes:
            headline = note.get("headline", "")
            for r in REGIONS:
                if r.lower() in headline.lower():
                    region = r
                    break
            if region:
                break

        if not region:
            continue

        if region not in regions:
            regions[region] = []

        for c in comps.get("competitors", []):
            team = {
                "seed": c.get("curatedRank", {}).get("current", 0),
                "name": c.get("team", {}).get("shortDisplayName", ""),
                "full_name": c.get("team", {}).get("displayName", ""),
                "team_id": c.get("team", {}).get("id", ""),
            }
            # Avoid duplicates
            if not any(t["name"] == team["name"] for t in regions[region]):
                regions[region].append(team)

    return regions


def generate_matchups(regions):
    """
    Generate matchups.json from tournament field.
    Maps pick IDs to matchups based on standard bracket structure.
    """
    matchups = {}
    pick_counter = {"R64": 0, "R32": 0, "S16": 0, "E8": 0, "F4": 0}

    for region_idx, region_name in enumerate(REGIONS):
        teams = regions.get(region_name, [])
        if not teams:
            print(f"⚠️  No teams found for {region_name} region")
            continue

        # Sort by seed
        teams_by_seed = {t["seed"]: t for t in teams}

        # Generate R64 matchups for this region (8 games per region)
        for seed_high, seed_low in SEED_MATCHUPS:
            pick_counter["R64"] += 1
            pick_id = f"R64_{pick_counter['R64']}"

            high_team = teams_by_seed.get(seed_high, {"name": f"TBD-{seed_high}", "full_name": f"TBD Seed {seed_high}"})
            low_team = teams_by_seed.get(seed_low, {"name": f"TBD-{seed_low}", "full_name": f"TBD Seed {seed_low}"})

            matchups[pick_id] = {
                "region": region_name,
                "round": "R64",
                "higher_seed": high_team["name"],
                "higher_seed_full": high_team.get("full_name", high_team["name"]),
                "higher_seed_num": seed_high,
                "lower_seed": low_team["name"],
                "lower_seed_full": low_team.get("full_name", low_team["name"]),
                "lower_seed_num": seed_low,
                "matchup": f"{seed_high}-{high_team['name']} vs {seed_low}-{low_team['name']}",
            }

        # R32: winners of adjacent R64 games play each other
        # R64_1 winner vs R64_2 winner, R64_3 vs R64_4, etc.
        r64_start = (region_idx * 8) + 1
        for i in range(4):
            pick_counter["R32"] += 1
            pick_id = f"R32_{pick_counter['R32']}"
            game_a = f"R64_{r64_start + i*2}"
            game_b = f"R64_{r64_start + i*2 + 1}"
            matchups[pick_id] = {
                "region": region_name,
                "round": "R32",
                "feeds_from": [game_a, game_b],
                "matchup": f"Winner of {game_a} vs Winner of {game_b}",
            }

        # S16: winners of adjacent R32 games
        r32_start = (region_idx * 4) + 1
        for i in range(2):
            pick_counter["S16"] += 1
            pick_id = f"S16_{pick_counter['S16']}"
            game_a = f"R32_{r32_start + i*2}"
            game_b = f"R32_{r32_start + i*2 + 1}"
            matchups[pick_id] = {
                "region": region_name,
                "round": "S16",
                "feeds_from": [game_a, game_b],
                "matchup": f"Winner of {game_a} vs Winner of {game_b}",
            }

        # E8: winners of S16 games in this region
        s16_start = (region_idx * 2) + 1
        pick_counter["E8"] += 1
        pick_id = f"E8_{pick_counter['E8']}"
        matchups[pick_id] = {
            "region": region_name,
            "round": "E8",
            "feeds_from": [f"S16_{s16_start}", f"S16_{s16_start + 1}"],
            "matchup": f"{region_name} Regional Final",
        }

    # F4: Region winners play each other
    # Standard: East vs West, South vs Midwest (may vary by year)
    matchups["F4_1"] = {
        "round": "F4",
        "feeds_from": ["E8_1", "E8_2"],
        "matchup": f"{REGIONS[0]} champion vs {REGIONS[1]} champion",
    }
    matchups["F4_2"] = {
        "round": "F4",
        "feeds_from": ["E8_3", "E8_4"],
        "matchup": f"{REGIONS[2]} champion vs {REGIONS[3]} champion",
    }

    # Championship
    matchups["CHAMP"] = {
        "round": "CHAMP",
        "feeds_from": ["F4_1", "F4_2"],
        "matchup": "National Championship",
    }

    return matchups


def extract_valid_teams(matchups):
    """Extract list of valid team names from matchups for validator."""
    teams = set()
    for pick_id, m in matchups.items():
        if "higher_seed" in m:
            teams.add(m["higher_seed"])
        if "lower_seed" in m:
            teams.add(m["lower_seed"])
    return sorted(teams)


def main():
    dry_run = "--dry-run" in sys.argv

    print("🏀 Fetching NCAA Tournament bracket from ESPN...")
    regions = fetch_tournament_teams()

    if not regions:
        print("\n⚠️  Bracket not available yet. Run again after Selection Sunday (March 15, 2026).")
        sys.exit(0)

    print(f"\nFound {sum(len(t) for t in regions.values())} teams across {len(regions)} regions:")
    for region, teams in regions.items():
        print(f"  {region}: {len(teams)} teams")
        for t in sorted(teams, key=lambda x: x["seed"]):
            print(f"    ({t['seed']}) {t['name']}")

    matchups = generate_matchups(regions)
    valid_teams = extract_valid_teams(matchups)

    if dry_run:
        print(f"\n📋 Generated {len(matchups)} matchups")
        print(f"🏫 {len(valid_teams)} valid team names")
        for pick_id in sorted(matchups.keys()):
            m = matchups[pick_id]
            print(f"  {pick_id}: {m['matchup']}")
    else:
        MATCHUPS_FILE.write_text(json.dumps(matchups, indent=2) + "\n")
        print(f"\n✅ Written {len(matchups)} matchups to matchups.json")
        print(f"🏫 {len(valid_teams)} valid team names")

        # Also write valid teams list
        teams_file = ROOT / "valid-teams.json"
        teams_file.write_text(json.dumps(valid_teams, indent=2) + "\n")
        print(f"✅ Written valid team list to valid-teams.json")


if __name__ == "__main__":
    main()
