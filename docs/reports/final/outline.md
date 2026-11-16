# Final report outline (Palmer; final at the results freeze, 11/15)

Due Mon 11/16, night. Results freeze Sun 11/15, 11pm (tag `results-final`; sprint table in `docs/TASKS.md`).
Configuration: decision 007. Each person writes their own sections in their own words in
`docs/reports/final/sections/` (owners in its README), and Palmer edits the whole report for one voice on
Monday. This file is the shared checklist, not report text. Owners: ask Palmer through the Requests table to
change a row here.

Update 11/15: cite `docs/reports/final/numbers.md` only.

## Feedback on Milestone 1 that every section must answer (Niusha, 11/11)
1. Say what the product is before anything else. Section 1 does this in one paragraph.
2. Define the index up front, once, with a formula and a worked example (section 2).
3. Explain announcement days, and don't exclude them silently (decision 004; sections 2 and 7).
4. For every backtest, state the method and the metrics, and what we expect each metric to show, before
   giving results (section 6).
5. Write in plain sentences: no em dashes, no filler, every term defined once.

## Sections

| # | Section | Owner | Content | Sources | Figures and tables |
|---|---|---|---|---|---|
| 1 | The product | Jay | One paragraph: a fully collateralized future paying $100 x CUT90, who would use it (hedging the timing of Fed cuts), and why a future instead of the spot index (it prices the roll-down) | `docs/spec.md`, Palmer log 11/12 | none |
| 2 | The index | Ari | Definition of U_t, C_m, H_m, w, CUT_H, HIKE_H; worked example (2024-01-11, `ex_index_*`); the series; announcement-day resets with the 2024-12-18 example (`ex_reset_*`) | decision 003, `index/README.md`, `index/results/worked_examples.md` | M1 fig1 (ladder), fig2 (term structure), `index/results/fig_index_series.png` (final rule) |
| 3 | Data and price rule | Palmer | Kalshi ladder; stale rule (decisions 002, 005, 006); Kalshi vs Polymarket agreement as the robustness check on venue; fed funds futures comparison (5 meetings from 2026-01-02 only); leg liquidity at 60 vs 90 days | `README.md` findings, `results/summary.md`, `results/settlement_rule_check.md`, `results/leg_liquidity.md` | liquidity table; venue agreement table |
| 4 | Contract specification | Jay | Payoff, collateral, expiry (spec section 4: no decision in the settlement window), 5-day settlement and fallback, settlement price rule (decisions 005, 006), settlement discount bounded, not estimated (TASK 10) | `docs/spec.md` | spec table |
| 5 | Pricing | Jay | Static hedge; F0 exact before the next meeting; the reset digital and F_adj = F0 - p_dir x G; continuity between announcements; ladder no-arbitrage check (12 of 11,179 days) | `docs/theory.md`, `theory/README.md`, `docs/notes/reset_adjustment.md`, `docs/notes/futures_pricing.md` | none, or one diagram |
| 6 | Backtest method and metrics | Ari | Sample (45 expiries, 7 leads, 4 indices, 1,188 trades), trade construction, each metric defined with its expected value (hedge error 0 without a rate change; cost mostly the far leg; basis rising with lead) | `index/README.md` | none |
| 7 | Results | Ari | Fair value and basis (roll-down priced in); hedge error by case and by direction of the move; cost and the far-leg share; capital; dealer break-even; return decomposition; worked trade (expiry 2024-12-27, `ex_trade_*`); event study; robustness rows; reset correction (R7: cross-reference section 5.2) | `index/results/futures_backtest.md`, `index/results/event_study.md`, `index/results/worked_examples.md`, `results/reset_adjustment.md`, `results/decomposition.md` | fig_hedge_error, fig_hedge_cost; 3 or 4 compact tables |
| 8 | Limitations | Palmer | Data end 2026-10-26; fed funds futures cover 5 meetings from 2026 only (P9 skipped); execution at the last book with no depth; fee rate held constant; overlapping trades; the HIKE reset estimate; the index is often missing the day before a decision (3-day rule; Palmer log 11/15) | all logs, `results/decomposition.md` | none |
| | References, Appendix (reproduction commands, data files) | Palmer | | `README.md` run blocks | |

## Promised in the Milestone I update (graders compare plan with delivery)
- [x] Ari: rerun with fees, capital, and an event study around FOMC meetings (A6, `index/results/event_study.md`).
- [x] Jay: settlement discount (TASK 10: not identifiable at these spreads, so bound it), ladder no-arbitrage check
      (TASK 10), settlement and collateral terms (TASK 8, `docs/spec.md`).
- [x] Return decomposition explaining the 274-point gap (P3, `results/decomposition.md`; the Milestone 1 method row
      reproduces it exactly, `rolldown_total_m1`, `portfolio_pnl_m1`).
- [x] Palmer: Polymarket, spread, fee and volume data, Kalshi vs Polymarket, and Kalshi vs fed funds futures at
      the meeting level (`kz_mae_p_hold`). ZQ covers only 5 meetings from 2026-01-02, so section 3 says so and
      section 8 lists it as a limit.

## Headline numbers
Replaced by `docs/reports/final/numbers.md` (P5, generated by `src/report_numbers.py` from the committed result
files). The pre-007 list that stood here is withdrawn: on the final configuration there are 45 expiries and 1,188
trades, CUT90 hedge cost is $7.76 and the CUT90 rate-move RMSE is $26.11. Cite keys from `numbers.md` only.
