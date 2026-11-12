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

## 2026-11-12 19:45  main
Did:
- Decision 006 (`src/settlement_check.py`, `results/settlement_rule_check.md`): answers Jay's 005 point 3
  (TASK 19). Agree that wide-book last trades should not settle; propose the wide-book mid instead of dropping
  those days. Also reconciles TASK 17 and checks the spec section 4 expiry rule against Ari's backtest.
- Reset adjustment and dealer break-even (`src/reset_check.py`, `results/reset_adjustment.md`,
  `docs/notes/reset_adjustment.md`), input for Jay's TASK 14 and Ari's results.
- TASK 4 leg liquidity (`src/leg_liquidity.py`, `results/leg_liquidity.md`).
- TASK 16 fee check against live Kalshi /series. TASKS 2 and 3 closed. Final report outline in
  `docs/reports/final/outline.md`.
- None of Ari's or Jay's files changed. All three scripts import Ari's `index/` code read-only.
Results (numbers worth keeping):
- Trade-branch legs on two-sided books (from Feb 2023): 7,011 leg-days, median spread 25c, median gap to mid
  9.5c. The mid predicts the next tight quote better (MAE 8.4c vs 9.9c, closer 57% of the time).
- Dropping trade-branch days from settlement: CUT90 windows with < 5 valid days 21% -> 45%, < 3 valid 9% -> 24%.
  Wide-book mid: no change in coverage, S moves on 21% of CUT90 trades by at most $3.28.
- Spec expiry rule: the rate-move RMSE rises for CUT90 (23.5 -> 26.2) and falls for HIKE90 (18.0 -> 16.5).
- Reset: dealer gains +$23.75 (CUT90) when the Fed moves the index's way and -$2.61 against. The ex-ante
  p_dir x G fits CUT (22.3 predicted vs 24.6 realized gain) and overstates HIKE (39.5 vs 24.4).
- Dealer break-even before any futures spread: CUT90 mean net -$4.40, negative on 90% of trades.
- Far leg: 90d is 113 days out, 5c median spread, traded on 30% of days, 12% stale. 60d: 83 days, 3c, 39%, 9%.
- Fees: FED quadratic and KXFED quadratic_with_maker_fees, multiplier 1 on both.
Open issues:
- 006 needs Ari and Jay. If accepted: TASK 23 (stale.py), then Ari's rerun with TASK 18.
Next: my report sections 3 and 8; edit on Monday.
