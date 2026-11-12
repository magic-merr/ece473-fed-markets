# Tasks to the final report (due Mon 11/16, night)

Freeze results Sunday 11/15, 10pm. Monday is writing and editing only.

| # | Owner | Task | Status | Due |
|---|---|---|---|---|
| 1 | Ari, Jay | Accept or amend decisions 002, 003, 004 | open | Fri 11/13 |
| 2 | Palmer | `src/costs.py`: `cost(price, days_to_meeting, kind, side)` from Kalshi spread + fee schedule | open | Fri 11/13 |
| 3 | Palmer | `src/composite.py`: combined Kalshi/Polymarket settlement price per meeting and day | open | Sat 11/14 |
| 4 | Palmer | Far-leg liquidity table: 90-day vs 60-day horizon (spread, share of days traded, stale share) | open | Sat 11/14 |
| 5 | Ari | `index/build.py`: CUT90/HIKE90 on the `src/` panel, output per decision 003; compare to `index_m1` | done 11/12 (`index/README.md`; reproduces `index_m1` exactly under its rule) | Sat 11/14 |
| 6 | Ari | Futures fair value from the static hedge, and futures backtest vs hedge with costs (tracking, hedge cost, capital) for 90d and 60d | done 11/12, results in `index/README.md`; rerun if decision 002 changes | Sun 11/15 |
| 7 | Ari | Return decomposition table (belief change, roll-down, announcement resets), see `docs/log/palmer.md` 11/12 | open | Sun 11/15 |
| 8 | Jay | `docs/spec.md`: final contract terms (start from Milestone 1 report section 5) | open | Sat 11/14 |
| 9 | Jay | `docs/theory.md`: pricing proposition (fair value = fixed-weight blend of two contracts, minus settlement discount), when the static hedge is exact, continuity (report section 6) | open | Sun 11/15 |
| 10 | Jay | Settlement discount estimate and the ladder no-arbitrage check | open | Sun 11/15 |
| 11 | all | Own report section in own words: product definition first, then index formula, backtest method, metrics with expectations, results | open | Mon 11/16 |
| 12 | Palmer | Edit full report for one voice, submit | open | Mon 11/16 |
| 13 | Jay | Spec: the expiry rule lets an FOMC decision fall inside the 5-day settlement window (6 of 55 expiries since Mar 2022, Wednesday decision before Friday expiry). Consider "no decision inside the window" (`index/README.md`, For the spec) | open | Sat 11/14 |
| 14 | Jay | Theory: static-hedge fair value is exact only if the rate does not change before expiry; a move breaks it with a predictable sign (dealer gains when the Fed moves in the index's direction). Fair value for longer futures needs a reset adjustment | open | Sun 11/15 |
| 15 | Palmer | Decision 002 input: under the src rule every day where rebuilt CUT90 differs from Milestone 1 by more than 5pp (28 days) uses a trade-branch leg (last trade on a book wider than 10c), up to 29pp. Also 18% of futures trades have a settlement day without a valid index value. Worth weighing before the rule becomes the settlement rule | open | Fri 11/13 |
| 16 | Palmer | `src/costs.py` (task 2): `index/futures.py` already prices each hedge leg off the standing bid/ask and the 0.07 taker rate, so the futures results do not wait on it. If `series_fees.csv` shows a different FED/KXFED rate or multiplier, tell Ari | open | Fri 11/13 |
