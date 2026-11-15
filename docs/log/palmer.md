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

## 2026-11-15 16:45  main
Did:
- Final sprint setup. Decision 007 (final configuration; closes 002 to 006 and TASK 17 once Ari and Jay sign).
  Sprint table at the top of `docs/TASKS.md` (IDs P, A, J; old table kept below as history). CLAUDE.md
  "Final sprint rules" and an updated repo map. `docs/reports/final/sections/README.md` (one file per section).
- Checked a clean clone: `index/build.py`, `index/futures.py`, `theory/noarb.py` and both test suites run
  (30 + 11 tests pass); `futures.py` reproduces the committed 11/12 tables exactly.
Results (numbers worth keeping): none new.
Open issues:
- Old TASK 7 (return decomposition) moves from Ari to Palmer (P3) to take load off the critical path.
- 007 puts the wide-mid branch in `index/legs.py`, not `src/stale.py`, so the cross-venue results do not move
  and Ari's rerun does not wait on a Palmer commit.
Next: P2 (get 007 signed), P3, then P4 after Ari's A4 push.

## 2026-11-15 17:00  main
Working for Palmer (rows P1 to P9). Claude session.
Did:
- P1 and P2 marked done (setup commit `6e9c565`; 007 signed by Ari `5bc03a1` and Jay `4504289`). R5 accepted:
  the final calendar has 45 expiries (the 5 old-calendar moves plus 2026-10-30 to 2026-10-23, inside the data).
- P3: `src/decomposition.py`, `tests/test_decomposition.py` (6 tests), pre-A4 `results/decomposition.md` (`5b6bb71`).
- P4 prep (`683689e`): `src/index_rule.py` picks `final` once `index/legs.py` has it, so `decomposition.py`,
  `leg_liquidity.py`, `reset_check.py` and `settlement_check.py` rerun unchanged after A4. `reset_check.py` now
  takes trades from `index/futures.py::run()` in-process, so nothing of Palmer's needs `futures.py` to write into
  `index/results/`. `settlement_check.py` keeps its own copy of the Milestone 1 calendar for its base variant.
  Pre-A4 reruns reproduce the committed 11/12 tables exactly. Dry run with a stand-in `final` rule in a scratch
  copy: all four scripts and the tests pass.
Results (numbers worth keeping, pre-A4, `src` rule, from 2023-02-02, index points):
- CUT90: index change +3.4 = belief change -300.4 + roll-down +407.3 + bracket rolls +13.4 + announcement
  resets -116.9 (of which the 10 rate-change days -127.2). HIKE90: -0.6 = +65.9 + 67.2 + 3.4 - 137.1.
- Ordinary days: gap -33.4bp a day, equal to minus the term-structure slope (an exact identity, tested).
- Milestone 1 method reproduces the 11/12 table exactly: CUT90 1,599 day pairs, index +9.4, portfolio -274.3,
  gap -283.7 (and `index_m1/data/backtest_*.csv` day by day, tested).
Open issues:
- Method change from 11/12, for the report: the Milestone 1 tracking backtest used one-day pairs. Under the 3-day
  rule the index has no value on the day before 5 of the 10 rate changes since Feb 2023 (CUT90 and HIKE90 each),
  often because a near leg with 2 to 5% weight is stale, so one-day pairs drop most resets (CUT90 resets -42
  instead of -117). The decomposition therefore chains consecutive days that have an index value, holding the
  weights fixed in between, and marks a held leg as `index/futures.py` marks a hedge leg when the rule has no
  price. No interval is dropped. Section 8 should mention the missing pre-decision days.
- The chained CUT90 index change is +3.43 in all four configurations because the endpoints coincide (CUT90 is
  0.025 on both 2022-03-16 and 2023-02-01); the telescoping test confirms it is not a bug.
Next: P4 after Ari's A4 push (rerun all four scripts, compare with `index/results/`), P5 `numbers.md`, P6 tag.

## 2026-11-15 17:45  main
Working for Palmer (rows P1 to P9). Claude session.
Did:
- P3 and P4 done at Ari's final state `fb94863` (`8baff80`). All four scripts rerun on decision 007 and agree
  exactly with `index/results/`: `settlement_check` "proposed" equals the robustness row "Ari's 11/12 fallback" and
  "base" equals "11/12 configuration" (trades, rate-move RMSE, max no-move error, mean cost, all four indices);
  `reset_check` by direction equals `futures_error_by_direction.csv`; its mean costs equal `futures_costs_pooled.csv`.
  Fixed a header bug in `decomposition.md` (it named the last loop configuration, `m1`, as the main rule).
- P5 done (`55ef1fa`): `docs/reports/final/numbers.md`, 172 numbers, generated by `src/report_numbers.py` from the
  committed source files only, each with source file and commit. Keys match all of Jay's placeholders. Checked
  `index/README.md` (agrees), `docs/theory.md` (keys resolve; "G tracks to 60 days, overshoots at 90" holds:
  $5.97 vs $5.19 at 60, $10.03 vs $7.19 at 90), `docs/spec.md` (R6 to Jay, numbers only). R5 closed. Outline's
  pre-007 headline list replaced by a pointer to `numbers.md`.
- Before Ari's `fb94863`: checked whether counting the decision day in the settlement extension (his first A3)
  or not (Jay's spec 5.2) matters. 0 of 180 settlements change. Ari then aligned the code to the spec.
Results (numbers worth keeping, decision 007, all in `numbers.md`):
- 45 expiries, 1,188 trades. CUT90: rate-move RMSE $26.11, cost $7.76, basis $1.61 / $8.20 / $17.28 (7/30/90 days).
- Break-even before any futures spread: CUT90 -$4.60 (negative on 91% of trades), HIKE90 -$6.54, CUT60 -$0.91,
  HIKE60 -$3.87. CUT90 cost with no rate change $7.86.
- Reset: CUT90 G predicted $22.71 vs realized $26.40; HIKE90 $37.24 vs $20.01. CUT90 buyer loss $8.63 at F0,
  $4.92 at F_adj.
- Decomposition, final rule from 2023-02-02: CUT90 +3.4 = belief -289.9 + roll-down +396.4 + bracket rolls +13.3
  + resets -116.4 (rate-change days -126.8). Roll-down 32.5bp a day (Milestone 1 configuration: 26.0).
Open issues:
- P6 (tag `results-final`) waits on J4. A4, A5, A6, P3, P4 are done.
- Spec text Requests R1, R4 (Ari to Jay) and R6 (Palmer to Jay) are open. They are docs, not tag blockers.
Next: P6 once J4 shows done, with the README status table. P7 and P8 Monday.

## 2026-11-15 17:55  main
Did:
- P6: all six preconditions done (A4, A5, A6 Ari; J4 Jay `facdec1`; P3, P4). Since the P4 rerun (`8baff80`) the only
  code change is `src/report_numbers.py`; regenerating `numbers.md` changes only its header hash. README status table
  updated (`1e72257`), 58 tests pass. Annotated tag `results-final` created on `1e72257`, but this Claude session
  cannot push tags: `git push` of the tag is cut off and the GitHub API returns 403 ("write access to this API path
  is not permitted through this proxy"). Palmer pushes the tag from his Mac. Code and results count as frozen
  from `1e72257` on.
- Jay applied the spec patch (`facdec1`, J4 done, R1, R4, R6 closed) and did J5 himself (`fab8bef`).
- R7 to Ari (from Jay): section 7 sentence that F_adj does not bind for CUT90 (G predicted $22.71 vs realized $26.40).
Results (numbers worth keeping): none new; all in `numbers.md`.
Open issues: tag push (Palmer, from his Mac).
Next: Monday. P7 sections 3, 8, 9 by 1pm, P8 assemble, edit, check every number against `numbers.md`, submit by 9pm.
