# Ari's log

(Append entries using the template in CLAUDE.md. Newest at the bottom.)

## 2026-11-12 17:45  main
Did:
- Built `index/` (TASKS 5 and 6), using only data already in the repo (`index_m1/raw`, `index_m1/data`): `legs.py`
  applies Palmer's `src/stale.py` rule (decision 002) to the committed candles, `build.py` builds CUT/HIKE for
  H = 90 and 60 in the decision 003 format, `futures.py` runs the futures-vs-static-hedge backtest under the
  Milestone 1 draft contract terms, `figures.py` makes two figures, 11 tests.
- Under the Milestone 1 price rule `build.py` reproduces `index_m1/data/index_daily.csv` exactly (1,943 days).
Results (numbers worth keeping), 44 monthly expiries Feb 2023 to Sep 2026, 1,152 trades, $ per $100 contract:
- Hedge error is exactly 0 when the rate does not change before expiry (meetings where the Fed holds included),
  apart from settlement days without an index value (max $1.31). When the Fed moves: RMSE $23.5 (CUT90),
  $33.7 (CUT60), worst $74; the dealer gains when the move is in the index's direction.
- Round-trip hedge cost: CUT90 $7.56, CUT60 $5.61, HIKE90 $7.26, HIKE60 $6.05. Far leg: 51 to 66% of cost with
  about half the contracts; 1.3 to 2.0 times the near leg's cost per contract.
- Dealer capital about $103 to $105 per contract for the life of the trade ($0.07 to $1.04 at 4% a year).
- Futures price above spot CUT90 by $1.8 (7-day lead), $8.2 (30), $16.3 (90): the roll-down is priced in.
Open issues:
- Decision 002 is still proposed; results use it. Rerun `python futures.py` if it changes.
- TASKS 13 to 16 added for Jay and Palmer.
Next: TASK 7 (return decomposition on the src-rule index), then my report section.

## 2026-11-15 16:51  main
Did:
- A1: read decision 007 and signed it (`5bc03a1`, pushed alone). Wrote notes F1 to F5 (spec wording and reporting,
  none changes the configuration) as Requests R1 to R5 (`734ca07`).
- A2: `index/legs.py` rule `final` = `src` plus the wide-book mid, identical to `src/settlement_check.py::wide_mid_days`
  (same rows, sources and values, checked at zero tolerance). Default in `build.py` and `futures.py`.
- A3: `index/futures.py` spec section 4 calendar (identical to `expiries_no_decision`; moves 5 of the old 44
  expiries back one week and adds 2026-10-23) and spec section 5 settlement (3 of 5, extension to 10 days not before
  the last decision, deferral up to 10 business days, backstop). Hedge shares on days without a valid index value
  are sold on the next valid window day, else on the day settlement is known (causal). Low-level defaults of
  `expiries()` and `hedge_trade()` stay at the 11/12 behaviour so Palmer's read-only imports keep their meaning;
  `run()` and `main()` use the 007 configuration. Robustness rows per 007 plus the 11/12 configuration, which
  reproduces all 1,152 trades and every committed 11/12 table exactly (`tests/ref_1112/`). 20 index tests.
- A4: reran `build.py`, `futures.py`, `figures.py`; new `fig_index_series.png`; rewrote `index/README.md`.
Results (numbers worth keeping, pre-freeze; $ per $100 contract):
- Sample: 45 monthly expiries 2023-02-24 to 2026-10-23, 7 leads, 1,188 trades. No decision in any settlement window.
- Hedge error exactly 0 with a full window and no rate change, including meetings where the Fed holds. Fallback
  windows without a rate change: at most $3.11 (HIKE60). Rate move RMSE: CUT90 26.1, CUT60 36.4, HIKE90 14.9,
  HIKE60 19.5; worst $74.3. Hedge effectiveness, all trades: CUT90 0.66, CUT60 0.53, HIKE90 0.73, HIKE60 0.52.
- Round-trip hedge cost: CUT90 $7.76, CUT60 $5.71, HIKE90 $7.93, HIKE60 $6.10. Far leg 52 to 66% of cost with 49 to
  53% of the contracts; 1.3 to 2.1 times the near leg per contract.
- Dealer capital $102.74 to $107.22 per contract; $0.07 (7-day lead) to $1.06 (90-day) at 4% a year.
- Basis F0 minus spot CUT90: $1.61 (7 days), $8.20 (30), $17.28 (90). HIKE90 about 0.
- Settlement: 143 of 178 expiry settlements full window, 17 three or four days, 9 extended, 9 deferred, 0 backstop.
- Final index vs Milestone 1 from 2023-02-02: CUT90 correlation 0.995, MAE 0.59pp, coverage 87.5% vs 96.0%;
  45 of 1,708 days differ by more than 5pp (max 39pp), all on wide-book-mid or trade legs.
- Robustness, CUT90 rate-move RMSE: 26.1 main, 19.5 rule-priced legs only, 26.3 Milestone 1 rule, 26.2 src rule,
  23.4 Milestone 1 calendar, 26.1 11/12 fallback, 21.2 from 2022-03-17, 23.5 in the 11/12 configuration.
Open issues:
- Requests R1 to R4 (Jay, spec wording) and R5 (Palmer, numbers.md: 45 expiries) are open.
Next: A5 (hedge error by direction of the move), A6 (event study), by 10:30pm. A7 on Monday.

## 2026-11-15 16:58  main
Did:
- A5: `futures.py` classifies each rate-move trade by the direction of the change (`move_direction`) and writes
  `index/results/futures_error_by_direction.csv` plus a section in `futures_backtest.md`. No A4 table changed.
- A6: new `index/event_study.py` -> `index/results/event_study.md`, `event_study.csv`, `event_study_summary.csv`:
  CUT90 and HIKE90 change on each FOMC decision day from 2023-02-02 (29 decisions: 6 cuts, 19 holds, 4 hikes), by
  decision, next to the mean futures hedge error of trades whose only rate change was that decision. The final rule
  has no value around several cut days (stale books), so the Milestone 1 rule is shown beside it.
- 22 index tests. README results 6 and 7 added.
Results (numbers worth keeping, pre-freeze):
- Hedge error by direction ($ per $100). With the index's direction the dealer gains on every trade: mean CUT90
  25.25, CUT60 36.28, HIKE90 20.05, HIKE60 28.51. Against it: mean CUT90 -2.55, CUT60 -1.45, HIKE90 -2.07,
  HIKE60 -1.36; worst -12.70 (HIKE60). No trade spans moves in both directions.
- Event study, mean change on the decision day (pp). Cuts: CUT90 -26.99 on the final rule (3 of 6 with a value),
  -23.76 on the Milestone 1 rule (6 of 6). Hikes: HIKE90 -37.62 (4 of 4) and -45.97 (3 of 4). Holds: CUT90 -0.31,
  HIKE90 -0.50 (final rule). Largest single move: CUT90 -50.01 on 2024-12-18.
Open issues:
- Requests R1 to R5 still open. A7 (sections 2, 6, 7) on Monday from numbers.md only.
Next: stop code changes before Palmer's 11pm tag; A7 Monday.

## 2026-11-15 17:08  main
Did:
- Aligned the backtest with Jay's final `docs/spec.md` section 5 (pushed 8b1ce08), Ari's call: S rounded to the
  nearest 0.25 (halves up), and the extension stops at the day after the most recent decision (decision day not
  used). `processed/futures_trades.csv` keeps `S_unrounded` and `err_mid_unrounded`. Tests updated (22 index tests).
- Ari's call on Requests R1 and R4 (spec 5.1 vs decision 007: wide-book wording, tail fill): keep the code, which
  follows 007 and A2 and is what Palmer's scripts use; Jay aligns the spec text.
Results (numbers worth keeping, pre-freeze; these replace the 16:51 and 16:59 entries where they differ):
- The decision-day stop changes 0 of 1,188 settlements.
- Rounding: hedge error exactly 0 before rounding with a full window and no rate change, at most $0.12 after.
  Fallback windows without a rate change: at most $3.11 before rounding, $3.01 after. Rate-move RMSE unchanged at
  one decimal (CUT90 26.1, CUT60 36.4, HIKE90 14.9, HIKE60 19.5); worst $74.35 (CUT60).
- CUT90 dealer mean error $3.13 over all trades, $14.16 with a rate change. Direction, mean error with the index's
  direction: CUT90 25.27, CUT60 36.28, HIKE90 20.01, HIKE60 28.55; against: -2.51, -1.46, -2.08, -1.34.
- CUT90 buyer P&L: +$0.33 (7 days), -$7.85 (30), -$19.75 (90). Costs, capital, basis and the event study unchanged.
Open issues:
- R1 and R4 for Jay. R2 and R3 closed by this change. R5 accepted by Palmer.
Next: no more code changes before the 11pm tag unless Palmer or Jay find a problem. A7 on Monday.

