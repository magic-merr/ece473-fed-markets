# Palmer's log

## 2026-11-12 16:30  main
Did:
- Merged the Milestone 1 work (zip from Documents/ECE473_data) into the repo as `index_m1/`, plus the
  Milestone 1 report (`docs/reports/milestone1/`) and the Milestone I update. Verified `build_index.py`
  and `make_figures.py` reproduce the committed index, both backtests and all four figures exactly.
- Added CLAUDE.md, decisions 001 to 004, TASKS.md, per-person logs, `docs/notes/futures_pricing.md`.

Results (numbers worth keeping): the 274-point gap from Milestone 1 is fully explained.
CUT90, main sample from 2022-03-17, mid prices, no costs. Gap = portfolio P&L minus index change.

| Days | n | Index change | Portfolio P&L | Gap |
|---|---|---|---|---|
| Ordinary | 1,533 | +141.5 | -257.8 | -399.3 |
| Bracket roll | 34 | -21.5 | -33.0 | -11.4 |
| Announcement | 32 | -110.5 | +16.4 | +127.0 |
| Total | 1,599 | +9.4 | -274.3 | -283.7 |

- Ordinary days: the gap averages -26.2bp/day, equal to the mean term-structure slope (26.2bp/day). This is
  roll-down: the cut curve sloped up, so the index drifts up as weight shifts to the far meeting, and no
  holder of the contracts earns that drift (report eq. 4). Same mechanism as VIX futures vs spot VIX.
- Announcement days: the index fell 110.5 points, almost all on the 15 days the Fed moved (-123.6), when
  the reference strike resets. A holder of the contracts did not lose that.
- HIKE90 is the same story, smaller: gap +74.7 = -63.7 roll-down + 140.7 announcement resets - 2.2 rolls.
- Separately, the portfolio itself lost 274 points because fixed-meeting cut probabilities kept falling in
  2024 and 2026 as priced cuts were pushed out. That is belief change, not a construction artifact.

Open issues:
- Decisions 002 to 004 need Ari and Jay.
- Implication for the futures: futures fair value already prices the roll-down (it is the forward value of
  the index), which is the main argument for listing a future instead of tracking the spot index. Jay and
  Ari should make this the headline result.

Next: tasks 2 to 4 in TASKS.md.
