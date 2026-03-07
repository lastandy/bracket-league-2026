#!/usr/bin/env python3
"""
Fetch NCAA Tournament results from ESPN API.
Writes results to results/{round}.json for scoring.

Usage:
    python3 scripts/fetch_results.py              # Fetch all completed games
    python3 scripts/fetch_results.py --dry-run     # Show what would be written
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
MATCHUPS_FILE = ROOT / "matchups.json"

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# NCAA tournament group ID
NCAA_GROUP = 100

# Tournament dates (2026) — fetch each day
# First Four: Mar 18-19
# R64: Mar 20-21
# R32: Mar 22-23
# S16: Mar 27-28
# E8: Mar 29-30  (adjusted — typically Thu-Fri for S16, Sat-Sun for E8)
# F4: Apr 5
# CHAMP: Apr 7
TOURNAMENT_DATES = []
# Generate all dates from Mar 18 to Apr 8, 2026
_start = datetime(2026, 3, 18)
_end = datetime(2026, 4, 8)
_d = _start
while _d <= _end:
    TOURNAMENT_DATES.append(_d.strftime("%Y%m%d"))
    _d += timedelta(days=1)

# Map ESPN notes/round descriptions to our round IDs
ROUND_MAP = {
    "1st round": "R64",
    "first round": "R64",
    "2nd round": "R32",
    "second round": "R32",
    "sweet 16": "S16",
    "sweet sixteen": "S16",
    "elite 8": "E8",
    "elite eight": "E8",
    "regional semifinal": "S16",
    "regional final": "E8",
    "national semifinal": "F4",
    "final four": "F4",
    "semifinal": "F4",
    "national championship": "CHAMP",
    "championship": "CHAMP",
}


def fetch_espn(date_str):
    """Fetch ESPN scoreboard for a given date (YYYYMMDD). Returns events list."""
    url = f"{ESPN_BASE}?groups={NCAA_GROUP}&dates={date_str}&limit=50"
    try:
        req = Request(url, headers={"User-Agent": "BracketLeague/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("events", [])
    except (URLError, json.JSONDecodeError) as e:
        print(f"  ⚠️  Error fetching {date_str}: {e}", file=sys.stderr)
        return []


def parse_round(event):
    """Extract round from ESPN event notes."""
    comps = event.get("competitions", [{}])[0]
    notes = comps.get("notes", [])
    for note in notes:
        headline = note.get("headline", "").lower()
        for key, round_id in ROUND_MAP.items():
            if key in headline:
                return round_id
    return None


def parse_game(event):
    """Parse a completed ESPN event into a game result."""
    comps = event.get("competitions", [{}])[0]
    status = comps.get("status", {}).get("type", {}).get("name", "")

    if status != "STATUS_FINAL":
        return None

    competitors = comps.get("competitors", [])
    if len(competitors) != 2:
        return None

    winner = None
    loser = None
    for c in competitors:
        team_data = {
            "name": c.get("team", {}).get("shortDisplayName", ""),
            "full_name": c.get("team", {}).get("displayName", ""),
            "seed": c.get("curatedRank", {}).get("current", 0),
            "score": int(c.get("score", 0)),
        }
        if c.get("winner", False):
            winner = team_data
        else:
            loser = team_data

    if not winner or not loser:
        # Determine by score
        t1, t2 = competitors
        s1 = int(t1.get("score", 0))
        s2 = int(t2.get("score", 0))
        if s1 > s2:
            winner_c, loser_c = t1, t2
        else:
            winner_c, loser_c = t2, t1
        winner = {
            "name": winner_c.get("team", {}).get("shortDisplayName", ""),
            "full_name": winner_c.get("team", {}).get("displayName", ""),
            "seed": winner_c.get("curatedRank", {}).get("current", 0),
            "score": int(winner_c.get("score", 0)),
        }
        loser = {
            "name": loser_c.get("team", {}).get("shortDisplayName", ""),
            "full_name": loser_c.get("team", {}).get("displayName", ""),
            "seed": loser_c.get("curatedRank", {}).get("current", 0),
            "score": int(loser_c.get("score", 0)),
        }

    round_id = parse_round(event)

    return {
        "winner": winner["name"],
        "winner_full": winner["full_name"],
        "seed": winner["seed"],
        "winner_score": winner["score"],
        "loser": loser["name"],
        "loser_full": loser["full_name"],
        "loser_seed": loser["seed"],
        "loser_score": loser["score"],
        "round": round_id,
        "espn_id": event.get("id", ""),
    }


def load_matchups():
    """Load matchups.json to map games to pick IDs."""
    if not MATCHUPS_FILE.exists():
        return None
    return json.loads(MATCHUPS_FILE.read_text())


def match_game_to_pick(game, matchups, existing_results):
    """Match a game result to a pick ID using matchups.json."""
    if not matchups:
        return None

    round_id = game["round"]
    if not round_id:
        return None

    winner = game["winner"]
    loser = game["loser"]

    for pick_id, matchup in matchups.items():
        if not pick_id.startswith(round_id):
            continue

        # Check if this pick is already resolved
        if pick_id in existing_results:
            continue

        # Match by team names (either team in the matchup)
        matchup_teams = [
            matchup.get("higher_seed", ""),
            matchup.get("lower_seed", ""),
            matchup.get("team_a", ""),
            matchup.get("team_b", ""),
        ]
        matchup_teams = [t for t in matchup_teams if t]

        if winner in matchup_teams or loser in matchup_teams:
            return pick_id

    return None


def fetch_all_results(dry_run=False):
    """Fetch all tournament results and write to results/ directory."""
    RESULTS_DIR.mkdir(exist_ok=True)
    matchups = load_matchups()

    # Load existing results
    all_results = {}
    for round_file in RESULTS_DIR.glob("*.json"):
        if round_file.stem in ("summary", "raw"):
            continue
        existing = json.loads(round_file.read_text())
        all_results.update(existing)

    new_games = []
    raw_games = []

    for date_str in TOURNAMENT_DATES:
        events = fetch_espn(date_str)
        if not events:
            continue

        for event in events:
            game = parse_game(event)
            if not game:
                continue

            # Skip if we already have this ESPN game
            if any(g.get("espn_id") == game["espn_id"] for g in raw_games):
                continue

            raw_games.append(game)

            if matchups:
                pick_id = match_game_to_pick(game, matchups, all_results)
                if pick_id and pick_id not in all_results:
                    all_results[pick_id] = {
                        "winner": game["winner"],
                        "seed": game["seed"],
                        "score": f"{game['winner_score']}-{game['loser_score']}",
                    }
                    new_games.append((pick_id, game))

    # Group results by round and write
    round_results = {}
    for pick_id, result in all_results.items():
        round_id = pick_id.split("_")[0] if "_" in pick_id else pick_id
        if round_id not in round_results:
            round_results[round_id] = {}
        round_results[round_id][pick_id] = result

    if dry_run:
        print(f"📊 Found {len(raw_games)} completed tournament games")
        print(f"📋 {len(all_results)} matched to pick IDs")
        print(f"🆕 {len(new_games)} new results")
        for pick_id, game in new_games:
            print(f"  {pick_id}: ({game['seed']}) {game['winner']} {game['winner_score']}-{game['loser_score']} {game['loser']}")
    else:
        for round_id, results in round_results.items():
            round_file = RESULTS_DIR / f"{round_id}.json"
            round_file.write_text(json.dumps(results, indent=2) + "\n")
            print(f"  ✅ {round_file.name}: {len(results)} games")

    # Always write raw games for reference
    raw_file = RESULTS_DIR / "raw.json"
    if not dry_run:
        raw_file.write_text(json.dumps(raw_games, indent=2) + "\n")

    return len(new_games), len(all_results), len(raw_games)


def main():
    dry_run = "--dry-run" in sys.argv

    print("🏀 Fetching NCAA Tournament results from ESPN...")
    new, total, raw = fetch_all_results(dry_run)

    if not dry_run:
        print(f"\n📊 {raw} games fetched, {total} matched, {new} new")
        if new > 0:
            print("Run 'python3 scripts/score.py' to update standings")


if __name__ == "__main__":
    main()
