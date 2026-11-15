# Tasks to the final report (due Mon 11/16, night)

## Final sprint, Sun 11/15 to Mon 11/16

Configuration: decision 007. Rules: CLAUDE.md, "Final sprint rules". Only the owner changes a row's Status.
Need something from someone else? Add a row to **Requests** at the bottom and message them in the group chat,
because their Claude session will not see it until they pull.

### Timeline (ET)

| When | Milestone |
|---|---|
| Sun 6:00pm | Ari and Jay have pulled, pushed any local work, and signed 007 (A1, J1) |
| Sun 9:00pm | Ari pushes the final-config rerun (A4). This unblocks P4, J4 |
| Sun 10:30pm | Palmer's reruns (P3, P4), Jay's noarb check (J4), Ari's tables (A5, A6) pushed |
| Sun 11:00pm | Palmer writes `docs/reports/final/numbers.md` (P5) and tags `results-final` (P6). Code and results frozen |
| Mon 1:00pm | Every section draft pushed to `docs/reports/final/sections/` |
| Mon 1:00 to 8:00pm | Palmer assembles and edits for one voice. Ari and Jay review their sections in the assembled draft by 6pm |
| Mon 9:00pm | Submit (buffer before the deadline) |

### Palmer (coordination, data, sections 3, 8, appendix, final edit)

| ID | Task | Done when | Due | Status |
|---|---|---|---|---|
| P1 | Push the setup commit: decision 007, this sprint table, CLAUDE.md sprint rules, `docs/reports/final/sections/README.md` | on `main` | Sun 5pm | done 11/15, `6e9c565` |
| P2 | Message Ari and Jay: pull, push local work, read and sign 007 | both signed in 007 | Sun 6pm | done 11/15: Ari `5bc03a1`, Jay `4504289` |
| P3 | `src/decomposition.py` -> `results/decomposition.md` (old TASK 7, moved from Ari). Split the CUT90 and HIKE90 index change into belief change, roll-down on ordinary days, bracket rolls and announcement resets, as in `docs/log/palmer.md` 11/12, on the final index from 2023-02-02, with the Milestone 1 sample as a comparison row. Imports `index/` read-only. Start on current code, rerun after A4 | table committed after A4 | Sun 10:30pm | done 11/15, rerun on the final configuration at `fb94863` (`results/decomposition.md`) |
| P4 | After A4: rerun `src/settlement_check.py`, `src/reset_check.py` (dealer break-even, by-direction reset), `src/leg_liquidity.py`. Commit `results/*.md`. Check they agree with `index/results/` | committed | Sun 10:30pm | done 11/15, all four scripts rerun at `fb94863` and agree exactly with `index/results/`: settlement_check "proposed" = robustness row "Ari's 11/12 fallback", "base" = "11/12 configuration" (trades, rate-move RMSE, max no-move error, mean cost, 4 indices); reset_check by direction = `futures_error_by_direction.csv`; its mean costs = `futures_costs_pooled.csv` |
| P5 | `docs/reports/final/numbers.md`: every number the report cites, one line each, with source file. Replaces the "Headline numbers" list in the outline | committed | Sun 11pm | done 11/15: `docs/reports/final/numbers.md`, 172 numbers with source file and commit, from `src/report_numbers.py` at `fb94863`/`8baff80`. Keys match every `{{numbers.md: key}}` in `theory.md` and sections 1, 4, 5. Checked `index/README.md` (agrees), `docs/theory.md` (all keys resolve; qualitative claims hold on the final run), `docs/spec.md` (R6). Outline headline list replaced |
| P6 | Tag `results-final` once A4, A5, A6, J4, P3, P4 are done. Update the README status table | tag pushed | Sun 11pm | open |
| P7 | Sections 3, 8, 9 (appendix: reproduction commands at the tag) | drafts in `sections/` | Mon 1pm | open |
| P8 | Assemble, edit for one voice, check every number against `numbers.md`, submit | submitted | Mon 9pm | open |
| P9 | Optional: Bloomberg ZQ history into `raw/rates/zq/` and rerun `src/` on Palmer's Mac. Only if the data is in hand by Sun 8pm; otherwise section 8 states the limit | | Sun 8pm | optional |

### Ari (index, backtest, sections 2, 6, 7)

| ID | Task | Done when | Due | Status |
|---|---|---|---|---|
| A1 | Read 007. Ari decides; add the "Accepted by" line (or write objections in `docs/log/ari.md` and message Palmer). Push alone | pushed | Sun 6pm | done 11/15 16:42, `5bc03a1` |
| A2 | `index/legs.py`: rule `final` = `src` plus wide-book mid (logic in `src/settlement_check.py::wide_mid_days`: source is trade, bid > 0, ask < 1, quote_age <= 3 -> value = mid, source `wide_mid`). Default in `build.py` and `futures.py`; keep `src` and `m1` for robustness. Tests | tests pass | Sun 7:30pm | done 11/15, rule `final` = `wide_mid_days` exactly |
| A3 | `index/futures.py`: spec section 4 expiry calendar (reference: `src/settlement_check.py::expiries_no_decision`; must move 5 of 44 expiries) and spec section 5 fallback (3 of 5, extend back to 10 days but not past a decision date, defer, backstop). Robustness rows listed in 007. Tests for each fallback branch (old TASK 18) | tests pass | Sun 8:30pm | done 11/15, spec calendar and fallback, 20 index tests |
| A4 | Rerun `build.py`, `futures.py`, `figures.py` (add a final CUT90/HIKE90 series figure if section 2 uses one). Update `index/README.md` results and its "For the spec" list. Log entry with the new headline numbers. **Push, then message Palmer and Jay** | pushed | Sun 9pm | done 11/15, pushed; README, log and figures updated |
| A5 | Hedge error by direction of the rate move (cut, hike) for all four indices, from `futures.py` (old TASK 21; break-even itself comes from P4) | in `index/results/` | Sun 10:30pm | done 11/15, `index/results/futures_error_by_direction.csv` |
| A6 | Event study (old TASK 22, promised in Milestone I): CUT90/HIKE90 change on each FOMC decision day from Feb 2023, by decision (cut, hold, hike), next to `futures_rate_move_events.csv`. `index/results/event_study.md` | pushed | Sun 10:30pm | done 11/15, `index/results/event_study.md` |
| A7 | Sections 2, 6, 7 | drafts in `sections/` | Mon 1pm | open |

### Jay (spec, theory, sections 1, 4, 5)

| ID | Task | Done when | Due | Status |
|---|---|---|---|---|
| J1 | Read 007. Jay decides; add the "Accepted by" line (or write objections in `docs/log/jay.md` and message Palmer). Push alone | pushed | Sun 6pm | done 11/15 16:5x, signed with two notes (see 007 and R1) |
| J2 | `docs/spec.md` to final: section 5 source hierarchy per 007 (book under the rule, wide-book mid, 3-day carry; composite removed, 006 point 3); close the composite [open] item; section 4 justified by definition, remove "the RMSE should fall"; collision counts per 007 (cite 5 of 44); rewrite section 10; status line to final | pushed | Sun 8pm | done 11/15 17:4x. Also added the decision-date stop to the 5.2 extension (see R1). No [open] items remain |
| J3 | `docs/theory.md` (old TASKS 9, 14, 20): static hedge exact iff no target-range change before expiry, with proof; fair value as the fixed-weight blend minus a bounded settlement discount; reset adjustment F_adj = F0 - p_dir x G and why it fits CUT but overstates HIKE (`docs/notes/reset_adjustment.md`); continuity between announcements. Numbers as `{{numbers.md}}` placeholders until the tag | draft pushed | Sun 9:30pm | done 11/15 17:4x, all empirical numbers are `{{numbers.md: key}}` placeholders |
| J4 | After A4: rerun `theory/noarb.py`; update `theory/README.md` only if a number moved | pushed | Sun 10:30pm | done 11/15: reran `theory/noarb.py` at `fb94863`, every number reproduces, `theory/README.md` unchanged |
| J5 | Fill `theory.md` placeholders from `numbers.md` | pushed | Mon 10am | done 11/15: 52 placeholders filled in `theory.md` and sections 1, 4, 5 from `numbers.md`. All 26 keys resolved, none missing |
| J6 | Sections 1, 4, 5 | drafts in `sections/` | Mon 1pm | drafts done 11/15 with final numbers in place. Monday is a read-through, not a rewrite |

### Requests (between people)

| # | From | To | Request | Status |
|---|---|---|---|---|
| R1 | Ari | Jay | 007 F1. `docs/spec.md` section 5: describe the wide-book mid as the code does. It replaces the last-trade price on a book that is two-sided, quoted within 3 days and wider than 10c (`src/settlement_check.py::wide_mid_days`, A2). A wide book with no trade in 3 days still has no price (108 of 7,192 index-leg days from 2023-02-02). 007's wording ("any two-sided book") is broader than the code | closed 11/15 (Jay): spec 5.1 step 2 now matches `wide_mid_days` (book two-sided, quoted within 3 days, wider than 10c, trade within 3 days) |
| R2 | Ari | Jay | 007 F2. Spec section 5 rounds S to the nearest 0.25; 007 and A3 do not, so the backtest does not round. Drop the rounding or say it is untested (it would add up to $0.125 of hedge error) | closed 11/15 (Ari): the backtest now rounds S to 0.25 as the spec says; error before rounding kept |
| R3 | Ari | Jay | 007 F3. Spec section 5 says the 10-day extension never reaches a decision "because section 4 keeps decisions out of the window". Not so: 11 of 45 final-calendar expiries have a decision exactly 9 days before expiry, the first day the extension can reach. The backtest counts the decision day (its close is after the announcement) and never goes earlier, so the guard never binds. Please fix the reasoning | closed 11/15 (Ari): the spec now gives the day-after-decision stop; the backtest follows it (changes 0 settlements) |
| R4 | Ari | Jay | 007 F4. The tail fill is part of the 007 rule but not of spec section 5's source hierarchy ("carried forward up to three days", "no fourth branch"). 437 of 7,192 index-leg days from 2023-02-02 carry a pinned price beyond 3 days. Please add it as a branch | closed 11/15 (Jay): tail fill added as spec 5.1 step 5; "never older than three days" now excepts it |
| R5 | Ari | Palmer | 007 F5. The final expiry calendar has 45 expiries, not 44: 2026-10-30 moves back to 2026-10-23, inside the data (your `settlement_check.py` already has 45). "5 of 44 move" is still right for the old calendar. `numbers.md` should give 45 for the final sample | closed 11/15 (Palmer): `numbers.md` gives `sample_expiries` = 45 and `expiries_moved_old_calendar` = 5 of 44 |
| R6 | Palmer | Jay | P5 check of `docs/spec.md` (at `8b1ce08`) against `numbers.md`. Numbers only, no rule change. (a) Section 4: "The report cites 5 of 44". The final backtest has 45 expiries (`sample_expiries`); 5 of 44 is the old-calendar move count (`expiries_moved_old_calendar`), plus 2026-10-30 moving to 2026-10-23. (b) 5.2 opening: "about one CUT90 settlement in five" has fewer than five valid days. Final run: 23% of CUT90 trades (`share_settle_not_full_cut90`), 35 of 178 settlements across the four indices (`settle_full` 143 of 178). (c) 5.2 paragraph: "11 of the 44 expiries" is 11 of 45 on the final calendar (checked: the only decision within reach of the extension is exactly 9 days before expiry). (d) Last paragraph of the spec: the R1-to-Ari note is out of date. The deferral test exists (`index/tests/test_futures.py::test_settle_spec_extension_stops_at_a_decision`), and R1 in this table is Ari's request to you. (e) Replace each "pre-freeze" citation with its key, e.g. 9% to 24% is `drop_trade_lt3_cut90`. (f) The 10% to 130% carry is now `discount_implied_carry`, sourced from `theory/README.md` prose only. Fine as is, or add it to `noarb_summary.md`. Checked and fine: the RMSE direction in section 4 (rises for CUT90 and CUT60, falls for HIKE90 and HIKE60 on the final run) and the ladder numbers in section 7 | closed 11/15 (Jay): 45 expiries, 23% and 35 of 178, 11 of 45, R1 note removed, citations by `numbers.md` key |

---

## History: tasks from 11/12 (frozen; decision 007 and the sprint table above supersede the open rows)


(Original note: freeze Sunday 10pm. Moved to 11pm by the sprint table.)

| # | Owner | Task | Status | Due |
|---|---|---|---|---|
| 1 | Ari, Jay | Accept or amend decisions 002, 003, 004 | Jay done 11/12 (003, 004 accepted; 002 conclusion accepted, reasoning superseded by decision 005). Ari still to sign | Fri 11/13 |
| 2 | Palmer | `src/costs.py`: `cost(price, days_to_meeting, kind, side)` from Kalshi spread + fee schedule | closed 11/12: not needed. `index/futures.py` already prices spread + taker fee per leg; fee schedule confirmed (TASK 16) | Fri 11/13 |
| 3 | Palmer | `src/composite.py`: combined Kalshi/Polymarket settlement price per meeting and day | closed 11/12 (Palmer): no composite in settlement, robustness row only. Reasons in decision 006 point 3 | Sat 11/14 |
| 4 | Palmer | Far-leg liquidity table: 90-day vs 60-day horizon (spread, share of days traded, stale share) | done 11/12, `results/leg_liquidity.md` (`src/leg_liquidity.py`). Far leg: 90d 113 days out, 5c median spread, traded 30% of days, 12% stale; 60d 83 days, 3c, 39%, 9% | Sat 11/14 |
| 5 | Ari | `index/build.py`: CUT90/HIKE90 on the `src/` panel, output per decision 003; compare to `index_m1` | done 11/12 (`index/README.md`; reproduces `index_m1` exactly under its rule) | Sat 11/14 |
| 6 | Ari | Futures fair value from the static hedge, and futures backtest vs hedge with costs (tracking, hedge cost, capital) for 90d and 60d | done 11/12, results in `index/README.md`; rerun if decision 002 changes | Sun 11/15 |
| 7 | Ari | Return decomposition table (belief change, roll-down, announcement resets), see `docs/log/palmer.md` 11/12 | open | Sun 11/15 |
| 8 | Jay | `docs/spec.md`: final contract terms (start from Milestone 1 report section 5) | draft done 11/12, `docs/spec.md`; [open] items listed in section 10 | Sat 11/14 |
| 9 | Jay | `docs/theory.md`: pricing proposition (fair value = fixed-weight blend of two contracts, minus settlement discount), when the static hedge is exact, continuity (report section 6) | open | Sun 11/15 |
| 10 | Jay | Settlement discount estimate and the ladder no-arbitrage check | done 11/12, `theory/README.md`. Ladder is arbitrage-free at executable prices (12 of 11,179 days). Settlement discount is NOT identifiable at these spreads: bound it, do not estimate it | Sun 11/15 |
| 11 | all | Own report section in own words: product definition first, then index formula, backtest method, metrics with expectations, results | open | Mon 11/16 |
| 12 | Palmer | Edit full report for one voice, submit | open | Mon 11/16 |
| 13 | Jay | Spec: the expiry rule lets an FOMC decision fall inside the 5-day settlement window (6 of 55 expiries since Mar 2022, Wednesday decision before Friday expiry). Consider "no decision inside the window" (`index/README.md`, For the spec) | done 11/12, `docs/spec.md` section 4: step back one week until the window is clear. 5 of 44 expiries move, collisions go to 0 | Sat 11/14 |
| 14 | Jay | Theory: static-hedge fair value is exact only if the rate does not change before expiry; a move breaks it with a predictable sign (dealer gains when the Fed moves in the index's direction). Fair value for longer futures needs a reset adjustment | open | Sun 11/15 |
| 15 | Palmer | Decision 002 input: under the src rule every day where rebuilt CUT90 differs from Milestone 1 by more than 5pp (28 days) uses a trade-branch leg (last trade on a book wider than 10c), up to 29pp. Also 18% of futures trades have a settlement day without a valid index value. Worth weighing before the rule becomes the settlement rule | done 11/12, decision 006 and `results/settlement_rule_check.md` | Fri 11/13 |
| 16 | Palmer | `src/costs.py` (task 2): `index/futures.py` already prices each hedge leg off the standing bid/ask and the 0.07 taker rate, so the futures results do not wait on it. If `series_fees.csv` shows a different FED/KXFED rate or multiplier, tell Ari | done 11/12: live Kalshi /series: FED quadratic, KXFED quadratic_with_maker_fees, fee_multiplier 1 on both. 0.07 taker is right; KXFED also charges 0.0175 maker | Fri 11/13 |
| 17 | Ari, Jay | Reconcile the expiry collision count: `index/README.md` says 6 of 55 since Mar 2022, `theory/noarb.py` says 7 of 58 over Mar 2022 to Dec 2026 and 5 of 44 over the backtest sample. Same rule, different month windows | Palmer 11/12: same rule, different windows. 6 of 55 Mar 2022 to Sep 2026, 5 of 44 backtest, 7 of 58 to Dec 2026 (decision 006). Ari/Jay: confirm and close | Fri 11/13 |
| 18 | Ari | Rerun `index/futures.py` on the `docs/spec.md` section 4 expiry calendar and the section 5 settlement fallback. 5 of 44 expiry dates move, and they are exactly the trades with a decision inside the window, so the rate-move RMSE should fall | open | Sat 11/14 |
| 19 | Palmer, Ari | Decision 005 point 3: should the settlement index drop the trade branch? Your TASK 15 note says all 28 large-difference days come from a stale trade on a book wider than 10c. Settling on that is a dispute waiting to happen | Palmer 11/12: decision 006. Agree on not settling on wide-book trades, but price them at the book mid instead of dropping them (dropping: CUT90 settlements with < 3 valid days 9% -> 24%). Ari, Jay: accept or amend | Fri 11/13 |
| 20 | Jay | TASK 14 input: `docs/notes/reset_adjustment.md`. The reset is one-sided (dealer +$24 when the Fed moves the index's way, -$2 against) and an ex-ante correction F_adj = F0 - p_dir x G from the entry-day ladder fits CUT (predicted gain 22.3 vs 24.6 realized) but overstates HIKE. Also: moving expiries does not lower the rate-move RMSE for CUT (decision 006), so justify spec section 4 by definition, not hedge error | open | Sun 11/15 |
| 21 | Ari | Results section: add the dealer break-even (`results/reset_adjustment.md` section 4: CUT90 mean net -$4.40, net negative on 90% of trades, cost when no rate change $7.97) and the by-direction hedge error table | open | Sun 11/15 |
| 22 | Ari | Milestone I promised an FOMC event study. Frame `futures_rate_move_events.csv` plus the by-direction table as that, or add index moves on decision days | open | Sun 11/15 |
| 23 | Palmer | Once 006 is accepted: add the wide-mid branch to `src/stale.py`, rerun `src/` outputs, tell Ari to rerun with TASK 18 | open | Sat 11/14 |
| 24 | all | Check `docs/reports/final/outline.md` (section owners, figures, Niusha's feedback checklist) and edit your row | open | Sat 11/14 |
