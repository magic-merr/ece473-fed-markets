# ECE 473: Constant-Maturity Event Futures

Team: Palmer Mann (data), Ariel Perczek (index and backtest), Jay Crowther (futures spec and theory).
Final report due Monday 2026-11-16, night.

## What the project is
The product is a fully collateralized futures contract that settles on **CUT90**, a 90-day
constant-maturity probability of a net Fed cut built from the Kalshi strike ladder. HIKE90 is the same
for hikes. Everything else in this repo exists to build, test or price that contract.

## Repo map
| Path | What | Owner |
|---|---|---|
| `index_m1/` | Milestone 1 index, tracking backtest, figures and data. **Frozen baseline**: do not edit, it reproduces the Milestone 1 report exactly. | Ari |
| `src/`, `tests/` | Data layer: Kalshi/Polymarket/futures pulls, 4-branch stale rule, cross-venue comparison, fees and liquidity | Palmer |
| `index/` (to create) | CUT90/HIKE90 rebuilt on the `src/` panel, futures fair value, futures backtest | Ari |
| `docs/spec.md`, `docs/theory.md` (to create) | Contract terms, pricing argument, proofs | Jay |
| `docs/reports/` | Submitted reports (Milestone 1 report and update) | all |
| `docs/notes/` | Working notes, not final text | all |

## Rules for every session (human or Claude)
1. **Start:** `git pull --rebase`. Then read this file, every file in `docs/decisions/`, `docs/TASKS.md`,
   and the latest entry in each file in `docs/log/`.
2. **Only edit files you own** (table above). Need a change in someone else's file? Add a row to
   `docs/TASKS.md` assigned to them.
3. **Shared parameters change only through a decision file.** Stale rule, horizon, sample start, index
   definition, file interfaces. New file `docs/decisions/NNN-short-name.md` using the template below.
   Never edit an accepted decision; write a new one that supersedes it.
4. **End:** append an entry to your own `docs/log/<name>.md`, commit with a `[name]` prefix
   (e.g. `[ari] rebuild CUT90 on src panel`), `git pull --rebase`, push.
5. Raw and processed data are gitignored (`raw/*`, `processed/`, `results/*.csv`). Rebuild them with the
   scripts; commit only code, small result tables and figures that a report cites.
6. Writing for the reports: plain sentences, define every term once, no em dashes, no filler. Each
   person writes their own section.

## Decision template
```
# NNN: <title>
Status: proposed | accepted | superseded by NNN
Date / who:
Decision:
Why:
Alternatives considered:
Files affected:
```

## Log entry template
```
## YYYY-MM-DD HH:MM  <branch or main>
Did:
Results (numbers worth keeping):
Open issues:
Next:
```
