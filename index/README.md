# index/: CUT/HIKE index, futures fair value and the futures-vs-hedge backtest

Owner: Ari. Configuration: decision 007 (final). Numbers below are pre-freeze until `results-final`; the report
cites `docs/reports/final/numbers.md` only. Everything runs from data already in the repo (`index_m1/raw`,
`index_m1/data`). Nothing is pulled.

```bash
cd index
python build.py      # index -> processed/index_daily.csv (H=90), processed/index_daily_h60.csv, results/index_vs_m1.csv
python futures.py    # backtest -> results/futures_*.csv, results/futures_backtest.md, processed/futures_trades.csv
python figures.py    # results/fig_hedge_error.png, results/fig_hedge_cost.png, results/fig_index_series.png
python event_study.py  # results/event_study.md (run after futures.py)
python -m pytest tests -q
```

| File | What it does |
|---|---|
| `legs.py` | Daily price of every Kalshi ladder contract from the committed candles, under three rules: `final` (decision 007, the default), `src` (Palmer's rule with the trade branch, pre-006) and `m1` (Milestone 1). |
| `build.py` | CUT_H and HIKE_H for any horizon H, written in the decision 003 format. |
| `futures.py` | Expiry calendar, settlement procedure, static hedge, hedge error, trading cost, capital, fair value, robustness rows. |
| `figures.py` | The three figures. |
| `event_study.py` | Index change on each FOMC decision day, by decision, next to the futures hedge errors. |
| `tests/test_futures.py` | 22 tests: hand-calculated synthetic cases, every settlement fallback branch, the `final` rule against `src/settlement_check.py::wide_mid_days`, the spec calendar against `expiries_no_decision`, exact reproduction of the Milestone 1 index and of the 11/12 tables (`tests/ref_1112/`), and an independent recomputation of real trades. |

## Definitions

**Index** (decision 003). U_t is the upper bound of the Fed's target range after every decision announced on or
before day t. C_m(t) is the probability that the upper bound after meeting m is below U_t: one minus the YES price
of meeting m's "above U_t - 0.25" contract. H_m(t) is the YES price of the "above U_t" contract. With
T = t + H days, m1 is the last meeting on or before T and m2 the first meeting after T, and
w = (date of m2 - T) / (date of m2 - date of m1). Then CUT_H = w C_m1 + (1 - w) C_m2, and HIKE_H is the same with H_m.
H = 90 is the product. H = 60 is the comparison.

**Price rule** `final` (decision 007), applied to each leg each day in this order. (1) Quote: the mid of a
two-sided book quoted within 3 days and no wider than 10 cents. (2) Bound: a one-sided book pinned at the boundary
(no bid and an ask of at most 3 cents, or no ask and a bid of at least 97 cents) that traded or was quoted within
3 days is priced at the midpoint of the interval it bounds. (3) Wide-book mid: a two-sided book quoted within 3
days but wider than 10 cents is priced at its mid (decision 006). (4) Trade: the last trade within 3 days, used only
when the book is not two-sided. (5) Tail fill: with none of these, a last usable price of at most 3 cents or at
least 97 cents is carried forward, as is the bound midpoint of a book still pinned at a tail. Otherwise the leg has
no price and the index has no value that day. Steps 1, 2, 4 and 5 are Palmer's `src/stale.py`; step 3 replaces
step 4 exactly as `src/settlement_check.py::wide_mid_days` does.

**Future** (decision 007, `docs/spec.md` sections 3 to 5). It pays $1 per index point, so $100 times the settlement
value S. It is fully collateralized: at price F the buyer posts F and the seller posts 100 - F. Expiry is the last
Friday of each month, moved back one week at a time until no FOMC decision falls in the settlement window or on the
first business day after expiry. The settlement window is the five calendar days ending on expiry. S is the mean of
the valid index values in the window if at least three are valid. Otherwise the window extends back, one day at a
time and to ten days in total, until three valid values are found, never before the last decision (the decision day
counts, because its index is the close after the announcement). Otherwise settlement is deferred to the next
business day with a valid value, up to ten business days, and after that it is the last valid value before expiry.
The backtest does not round S (Request R2).

**Static hedge** (`docs/notes/futures_pricing.md`). The dealer who sells the future on day t buys, for each of
the five settlement days d, 20 x w(d) contracts of meeting m1(d) and 20 x (1 - w(d)) of meeting m2(d), all at
today's strike. It sells day d's share at the close of day d. If day d has no valid index value, that share is sold
on the next valid day in the window, or else on the day the settlement value is known (expiry, or the deferred
day). Meeting dates are known in advance, so the meetings and weights are known on day t. **Fair value** F0 is the
cost of this hedge at the index's own prices on day t.

**Measures**, in dollars per $100 contract (equal to index points):
- *Hedge error* = hedge proceeds minus settlement, both at the index's prices. Positive means the dealer gains.
- *Hedge effectiveness* = 1 - sum(error^2) / sum(futures P&L^2), where futures P&L = S - F0.
- *Trading cost* = the spread paid relative to the index's price for each leg, plus the Kalshi taker fee
  0.07 x P x (1 - P) per contract at the execution price. The dealer buys at the ask and sells at the bid of the
  side it holds. A cut leg is a NO contract, so its ask is 1 - (YES bid).
- *Capital* = the dealer's 100 - F0 of futures collateral plus the hedge purchase. The buyer's capital is F0.

**Sample.** 45 monthly expiries from 2023-02-24 to 2026-10-23, entries from 2023-02-02 (decision 007). There are
seven entry leads: 7, 14, 21, 30, 45, 60 and 90 calendar days before expiry. That gives 1,188 trades across CUT90,
HIKE90, CUT60 and HIKE60. The old calendar had 44 expiries over the same months; the spec calendar moves 5 of them
back a week and adds 2026-10-23 (2026-10-30 moved back into the data). Trades with leads above about 30 days overlap
across expiries, so they are not independent.

## Results (pre-freeze)

**1. The hedge matches the future exactly unless the Fed changes the rate before expiry.** At the index's own
prices, every trade whose settlement used the full five-day window and had no rate change before expiry has an
error of exactly zero. A meeting at which the Fed holds does not break the hedge, because the strike only moves when
the rate moves. The only other nonzero errors without a rate change come from settlement fallbacks (fewer than five
valid days), at most $3.11 (HIKE60, extended window).

| Index | No meeting before expiry: RMSE ($) | Fed held: RMSE ($) | Fed moved: RMSE ($) | Fed moved: worst ($) | Effectiveness, all trades |
|---|---|---|---|---|---|
| CUT90 | 0.20 (128) | 0.16 (102) | 26.1 (65) | 56.2 | 0.66 |
| CUT60 | 0.15 (128) | 0.10 (102) | 36.4 (66) | 74.3 | 0.53 |
| HIKE90 | 0.23 (119) | 0.30 (104) | 14.9 (73) | 50.6 | 0.73 |
| HIKE60 | 0.51 (126) | 0.01 (102) | 19.5 (73) | 62.9 | 0.52 |

The settlement fallback was needed on few expiries, and the backstop never fired:

| Index | Expiries | Full window | 3 or 4 valid days | Extended | Deferred | Backstop |
|---|---|---|---|---|---|---|
| CUT90 | 44 | 34 | 5 | 3 | 2 | 0 |
| CUT60 | 44 | 38 | 3 | 2 | 1 | 0 |
| HIKE90 | 45 | 33 | 6 | 1 | 5 | 0 |
| HIKE60 | 45 | 38 | 3 | 3 | 1 | 0 |

**2. A rate change breaks the hedge, and the sign is predictable.** After a move, the index re-anchors to the new
upper bound, but the hedge still holds contracts struck at the old one. Example: a CUT90 future expiring
2024-12-27, sold on 2024-11-27 for $88.61. The hedge is strike 4.50, "upper bound below 4.75%", in the Mar and May
2025 meetings. The Fed cut to 4.50% on 2024-12-18, so the index switched to "below 4.50%" and settled at $42.75.
The hedge, still "below 4.75%", was worth $93.81. The dealer gained $51.06 relative to the future. When the Fed
moves in the index's direction (a cut for CUT, a hike for HIKE) the dealer gains; when it moves the other way the
dealer loses, by less. How often this happens depends on the lead. Across CUT90 trades, the share with no meeting
before expiry is 100% at 7 days, 75% at 14, 53% at 30 and 0% from 45 days on.

**3. Most of the trading cost comes from the later contract, but not all of it.** Mean round trip (spread plus
taker fees) per $100 contract. The far leg holds about half the contracts but costs 1.3 to 2.1 times more per
contract. The 60-day CUT index costs about a quarter less to hedge than the 90-day one, because both legs are closer
to their meetings.

| Index | Total | Spread | Fees | Near leg | Far leg | Far share of cost | Far share of contracts | Per contract, near / far |
|---|---|---|---|---|---|---|---|---|
| CUT90 | 7.76 | 5.93 | 1.82 | 3.35 | 4.41 | 57% | 49% | 6.3c / 9.5c |
| CUT60 | 5.71 | 4.16 | 1.55 | 2.40 | 3.31 | 58% | 53% | 4.4c / 7.1c |
| HIKE90 | 7.93 | 6.73 | 1.20 | 3.77 | 4.16 | 52% | 50% | 6.6c / 8.7c |
| HIKE60 | 6.10 | 5.05 | 1.05 | 2.07 | 4.03 | 66% | 53% | 3.9c / 8.1c |

**4. Capital is $102.74 to $107.22 per contract for the dealer, and small next to trading cost.** The dealer posts
100 - F0 and pays about F0 plus entry costs for the hedge, so a hedged seller ties up roughly the full $100 for the
life of the trade. At an illustrative 4% a year that is $0.07 at a 7-day lead, $0.33 to $0.34 at 30 days and $1.03 to
$1.06 at 90 days, against $5.07 to $10.24 of mean trading cost by index and lead. The buyer ties up only F0: $39.87 to $60.28 on average for
CUT90, depending on the lead.

**5. The futures price builds in the roll-down that the spot index shows.** F0 sits above spot CUT90, and the gap
grows with the lead: $1.61 at 7 days, $8.20 at 30 and $17.28 at 90. In this sample a buyer of the CUT90 future lost
about that gap on average ($0.35 gained at 7 days, $7.83 and $19.73 lost at 30 and 90), because cuts kept arriving
later than priced. For HIKE90 the gap is close to zero ($0.25, $0.30, -$0.05).

**6. The sign of the hedge error follows the direction of the move** (`results/futures_error_by_direction.csv`).
When the Fed moves in the index's direction, the dealer gained on every trade. When it moves the other way, the
dealer loses a little. No trade in the sample spans moves in both directions.

| Index | Move | Relative to the index | Trades | Mean error ($) | Range ($) | Share where the dealer gains |
|---|---|---|---|---|---|---|
| CUT90 | cut | with | 39 | 25.25 | 0.17 to 56.21 | 100% |
| CUT90 | hike | against | 26 | -2.55 | -6.28 to 0.47 | 4% |
| CUT60 | cut | with | 40 | 36.28 | 2.03 to 74.30 | 100% |
| CUT60 | hike | against | 26 | -1.45 | -3.59 to 0.38 | 23% |
| HIKE90 | cut | against | 47 | -2.07 | -8.65 to 0.97 | 15% |
| HIKE90 | hike | with | 26 | 20.05 | 3.42 to 50.61 | 100% |
| HIKE60 | cut | against | 47 | -1.36 | -12.70 to 0.46 | 28% |
| HIKE60 | hike | with | 26 | 28.51 | 2.42 to 62.93 | 100% |

**7. Event study: on a decision day the index falls when the Fed moves in its direction** (`results/event_study.md`).
CUT90 and HIKE90 at the close of each of the 29 decision days from 2023-02-02, minus the close of the day before
(the nearest valid day within 3 days if either is missing). The final rule has no value around several cut days,
because the books for those meetings went stale, so the Milestone 1 rule is shown beside it. In brackets: decisions
with a value.

| Decision | Decisions | CUT90 mean change (pp), final rule | CUT90, Milestone 1 rule | HIKE90 mean change (pp), final rule | HIKE90, Milestone 1 rule |
|---|---|---|---|---|---|
| cut | 6 | -26.99 (3) | -23.76 (6) | no value | 1.04 (5) |
| hold | 19 | -0.31 (18) | 0.77 (17) | -0.50 (17) | 0.25 (18) |
| hike | 4 | 1.75 (3) | 5.69 (3) | -37.62 (4) | -45.97 (3) |

## Robustness (`results/futures_robustness.csv`)

The last row reruns the 11/12 configuration and reproduces the committed 11/12 tables exactly
(`tests/test_futures.py::test_1112_configuration_reproduces_the_1112_tables`).

| Variant | CUT90 RMSE when the Fed moved | CUT90 mean cost | HIKE90 RMSE when the Fed moved | HIKE90 mean cost | Trades (CUT90 / HIKE90) |
|---|---|---|---|---|---|
| Main: decision 007 (final rule, spec calendar, spec fallback, from 2023-02-02) | 26.1 | 7.76 | 14.9 | 7.93 | 295 / 296 |
| Only trades where every hedge leg had a rule price | 19.5 | 7.87 | 18.0 | 7.82 | 206 / 201 |
| Milestone 1 price rule | 26.3 | 7.51 | 16.2 | 7.27 | 304 / 296 |
| src rule with the trade branch (pre-006) | 26.2 | 7.75 | 15.0 | 7.45 | 295 / 296 |
| Milestone 1 expiry rule | 23.4 | 7.67 | 16.9 | 7.78 | 287 / 289 |
| Ari's 11/12 fallback | 26.1 | 7.75 | 16.3 | 7.71 | 295 / 290 |
| Sample from 2022-03-17 | 21.2 | 7.01 | 13.5 | 7.23 | 356 / 355 |
| 11/12 configuration (src rule, Milestone 1 calendar, 11/12 fallback): reproduces the 11/12 tables | 23.5 | 7.56 | 18.0 | 7.26 | 287 / 283 |

## Choices and limits to know before citing the numbers

- **Hedge legs without a rule price.** In 27% of trades, at least one hedge leg had no price under the `final` rule
  on its trade day, usually the far leg or the old strike after a move. The dealer still holds such a leg, so for
  hedge legs only it is valued at the standing book's mid, or at the midpoint of a one-sided book within 15 cents of
  0 or 1. A leg with no bid in that zone is sold at 0, which is conservative. The index itself is untouched. Without
  those trades (robustness row 2) the CUT90 rate-move RMSE is lower and the costs are about the same.
- **Execution** uses the last observed Kalshi book. Depending on the index and lead, 15 to 74% of leg executions
  (median 31%) use a book that last changed more than 3 days earlier (`share_legs_old_book`). Candles have no depth,
  so top-of-book size is assumed to be enough.
- **Fees** use the 0.07 taker rate for every date, without per-order rounding (decision 007; rounding adds at most 1
  cent per order). Maker fees would be lower but need passive fills.
- **No interest** is credited on locked collateral. The settlement discount is bounded, not estimated (decision 007).
- **Data end:** the Milestone 1 pull runs through 2026-10-26, so the last expiry is 2026-10-23.

## Index on the final rule vs Milestone 1 (`results/index_vs_m1.csv`)

With the Milestone 1 rule, `build.py` reproduces `index_m1/data/index_daily.csv` exactly: all 1,943 days, every
leg, the same missing days. With the `final` rule, from 2023-02-02, CUT90 has a level correlation of 0.995 with
Milestone 1 and a mean absolute gap of 0.59pp, but coverage falls from 96.0% to 87.5% of days, because a price must
be at most 3 days old instead of 10. On 45 of the 1,708 days where both versions have a value (from Jul 2021), the
gap exceeds 5pp, up to 39pp. Every one of those days has a leg priced at a wide-book mid (44) or a last trade on a
one-sided book (1). Milestone 1 is not ground truth on those days: it carried a mid forward up to 10 days, and these
are the days when the book had widened (decision 006).

## For the spec and the theory (Jay)

1. The static-hedge fair value is exact only for futures that settle before the next change in the target range.
   For longer futures, F0 is the "no rate change" price. Dealers selling CUT90 futures at F0 gained $3.11 on
   average before trading costs, and $14.13 on trades with a rate change, mostly those spanning a cut.
2. The spec calendar leaves no decision in any settlement window (the old rule left 5 of 44). It raises the CUT90
   rate-move RMSE from 23.4 to 26.1 and lowers HIKE90's from 16.9 to 14.9 (robustness rows 1 and 5). Report this as a
   result; the rule is justified by definition (decision 007).
3. The spec fallback settles every expiry. Across the four indices, 143 of 178 expiry settlements used the full
   window, 17 used three or four valid days, 9 the extension and 9 the deferral; the backstop never fired.
4. Requests R1 to R4 in `docs/TASKS.md`: describe the wide-book mid as the code does, drop or flag the 0.25
   rounding, fix the reasoning about the extension and decision dates, and add the tail fill to the source hierarchy.
