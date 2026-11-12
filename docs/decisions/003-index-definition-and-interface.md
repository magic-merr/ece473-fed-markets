# 003: Index definition and the file interface between data, index and futures code
Status: accepted (definition unchanged from Milestone 1); interface proposed
Date / who: 2026-11-12, Palmer

Definition (as implemented in `index_m1/build_index.py`, Milestone 1 report section 3):
- U_t = upper bound in effect at t. Y_m(K, t) = YES price of meeting m's "upper bound above K" contract.
- C_m(t) = 1 - Y_m(U_t - 0.25, t) (net cut by meeting m); H_m(t) = Y_m(U_t, t) (net hike by meeting m).
- T = t + 90 days; m1 = last meeting with decision <= T; m2 = first meeting after T.
- w_t = (d2 - T) / (d2 - d1). CUT90 = w C_m1 + (1 - w) C_m2. HIKE90 the same with H.
- Cuts are measured relative to today's rate, so the index resets when the Fed moves (announcement-day
  jumps are part of the product, see 004).

Interface (proposed): the rebuilt index writes `processed/index_daily.csv` with the same columns as
`index_m1/data/index_daily.csv`:
`date, ub, m1, m2, d1, d2, w, C1, C2, H1, H2, CUT90, HIKE90, any_stale, announcement`
plus `source` (`kalshi` | `composite`). Contract prices per day come from
`processed/kalshi_contract_daily.csv` (Palmer). Trading costs come from a function in `src/costs.py`:
`cost(price, days_to_meeting, kind, side) -> dollars per contract` (Palmer). Futures code (Ari) depends
only on these three.

Why: lets Palmer, Ari and Jay work in parallel without waiting on each other's internals.
Files affected: `index/`, `src/costs.py`, `src/composite.py`.
