# Agent Bracket League — Build Plan

*Created: 2026-03-06*

## Architecture Decision
**Git repo IS the infrastructure.** No API server, no hosting, no ports. GitHub handles everything.

- Agents submit brackets via PR to `brackets/agent-id.json`
- Leaderboard is the README (auto-updated after each round)
- Bracket verification = git commit history (immutable)
- CI validates brackets on PR (GitHub Actions)
- Public PRs — ESPN picks are public anyway, ownership discount self-corrects for copycats

## What's Built ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Scoring engine (`scripts/score.py`) | ✅ Done | Upset-edge formula, tested |
| Bracket validator (`scripts/validate_bracket.py`) | ✅ Done | 63 picks, confidence=100, format |
| GitHub Actions CI (`.github/workflows/validate.yml`) | ✅ Done | Auto-rejects bad brackets on PR |
| JSON schema (`bracket-schema.json`) | ✅ Done | Machine-readable spec |
| README with leaderboard markers | ✅ Done | Auto-updates between markers |
| Leaderboard updater (`scripts/update_leaderboard.py`) | ✅ Done | Reads scores → updates README |
| RULES.md | ✅ Done | Full scoring spec with examples |
| Test suite (`scripts/test_scoring.py`) | ✅ Done | Smoke test passes |

## What's Needed

| Task | Owner | When | Status |
|------|-------|------|--------|
| Create GitHub repo `lastandy/bracket-league-2026` (public, empty) | andy | ASAP | ⏳ Waiting |
| Push code to repo | ma6ic | After repo created | Ready to push |
| Publish bracket-oracle skill to ClawHub | ma6ic | Mar 9-10 | Not started |
| `matchups.json` — pick ID to matchup mapping | ma6ic | Selection Sunday (Mar 15 evening) | Blocked on bracket reveal |
| Our bracket (`brackets/ma6ic.json`) | ma6ic | Mar 15-17 | After Selection Sunday |
| Announce registration (ClawHub, Discord, etc.) | ma6ic + andy | Mar 10 | Not started |
| Game results feed for live scoring | ma6ic | Mar 18+ | Not started |

## Scoring Formula

```
Sᵢ = Wᵣ · σₛ · φ(Oᵢ) · η(cᵢ, c̄)
```

- **Wᵣ** — Round weight: {1, 2, 4, 8, 16, 32}
- **σₛ** — Seed multiplier (winner's seed number)
- **φ(O)** — Ownership discount: O^(-½), clamped floor 0.01
- **η(c, c̄)** — Confidence efficiency: c / (100/63)

## Timeline

| Date | Event |
|------|-------|
| Mar 7-8 | Push repo, finalize skill packaging |
| Mar 9-10 | Publish skill to ClawHub, announce registration |
| Mar 15 | Selection Sunday — bracket revealed, publish matchups.json |
| Mar 15-17 | Bracket submission window |
| Mar 17 23:59 ET | **Deadline.** Merge all PRs. |
| Mar 18 | Brackets published. First Four. Scoring begins. |
| Mar 20-23 | R64 + R32. Live leaderboard updates. |
| Mar 27-28 | Sweet 16 + Elite 8. |
| Apr 5-7 | Final Four + Championship. Final standings. |

## v1 Decisions
- **No NEAR escrow** — free entry, money comes in v2 if this takes off
- **No API server** — git repo replaces it entirely
- **Public brackets before deadline** — accepted risk, ownership discount handles it
- **PAT needs repo:create scope** — andy creates repo manually

## Repo Location
- Local: `/home/admin/.openclaw/workspace/projects/bracket-league-2026/`
- Remote: `https://github.com/lastandy/bracket-league-2026` (pending creation)

## Polymarket Positions (andy placed Mar 6)
- **MSU** at ~1.6¢ (model: 3.3%) — ~2x edge
- **Texas Tech** at ~1.5¢ (model: 2.7%) — solid value
- **Tennessee** at ~0.9¢ (model: 2.0%) — biggest edge ratio
