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
| `index/` | CUT90/HIKE90 on the decision 007 price rule, futures fair value, futures backtest, event study | Ari |
| `docs/spec.md`, `docs/theory.md`, `theory/` | Contract terms, pricing argument, proofs, no-arbitrage checks | Jay |
| `results/*.md`, `src/` scripts that import `index/` read-only | Settlement-rule check, reset adjustment and break-even, leg liquidity, return decomposition | Palmer |
| `docs/TASKS.md`, `docs/reports/final/outline.md`, `numbers.md`, `README.md`, `CLAUDE.md` | Coordination | Palmer |
| `docs/reports/final/sections/` | One file per report section, owner in `sections/README.md` | per file |
| `docs/reports/milestone*/` | Submitted reports | frozen |
| `docs/notes/` | Working notes, not final text | all |
| `docs/log/<name>.md` | Each person's session log | that person |

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

## Final sprint rules (Sun 11/15 to Mon 11/16). These add to the rules above.
1. **The GitHub repo, branch `main`, is the only source of truth.** Not chat history, not claude.ai project
   files, not another person's Claude. If what you were told in chat disagrees with the repo, follow the repo
   and say so in your log.
2. **Know who you work for.** Start every session by stating the person's name and their rows in
   `docs/TASKS.md`. Commit with that person's `[name]` prefix only. Never edit another person's files, never
   change the Status of their rows, never add an "Accepted by" line for them.
3. **Decision 007 is the final configuration** and overrides the Status lines still printed in 002 to 006.
   Anything not in 007 stays as it is. A change needs a new decision that the other two accept.
4. **Only the owner regenerates a results folder**: `index/results/` (Ari), `results/` (Palmer),
   `theory/results/` (Jay). Palmer's `src/` scripts import `index/` read-only and never write into it.
5. **Before every push:** `python -m pytest tests index/tests -q` passes; `git status` shows only your own
   files; stage explicit paths (no `git add -A` or `git add .`); `git pull --rebase`; never force-push; stay on
   `main`.
6. **New decision files:** pull, take the next free number, push that file on its own right away so nobody
   else takes the number.
7. **Report numbers come only from `docs/reports/final/numbers.md`** once it exists (P5). Before that, cite the
   result file and mark the number "pre-freeze".
8. **After the tag `results-final`, code and result files are frozen.** A real bug fix needs a new decision, a
   rerun by the owner and a new tag `results-final-2`. Monday is writing only.
9. **Cross-person requests** go in the Requests table in `docs/TASKS.md`, and the human messages the other
   person, since their Claude only sees it after a pull.
10. **End every session** with a log entry (template below) that lists the numbers you produced and what is
    left, then push.

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
