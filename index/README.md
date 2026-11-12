# index/: CUT/HIKE index, futures fair value and the futures-vs-hedge backtest

Owner: Ari. Covers TASKS 5 (index on the data-layer rule) and 6 (futures fair value and backtest).
Everything here runs from data already in the repo (`index_m1/raw`, `index_m1/data`). Nothing is pulled.

```bash
cd index
python build.py      # index -> processed/index_daily.csv (H=90), processed/index_daily_h60.csv, results/index_vs_m1.csv
python futures.py    # backtest -> results/futures_*.csv, results/futures_backtest.md, processed/futures_trades.csv
python figures.py    # results/fig_hedge_error.png, results/fig_hedge_cost.png
python -m pytest tests -q
```

| File | What it does |
|---|---|
| `legs.py` | Daily price of every Kalshi ladder contract from the committed candles. Two price rules: `src` (Palmer's quote, bound, trade, stale rule from `src/stale.py`, N = 3 days, S = $0.10; decision 002) and `m1` (the Milestone 1 rule). |
| `build.py` | CUT_H and HIKE_H for any horizon H, written in the decision 003 format. |
| `futures.py` | Expiry calendar, static hedge, hedge error, trading cost, capital, fair value, robustness. |
| `figures.py` | The two figures below. |
| `tests/test_futures.py` | 11 tests: hand-calculated synthetic cases, exact reproduction of the Milestone 1 index, and an independent recomputation of real trades. |

## Definitions

**Index** (decision 003). U_t is the upper bound of the Fed's target range after every decision announced on or
before day t. C_m(t) is the probability that the upper bound after meeting m is below U_t: one minus the YES price
of meeting m's "above U_t - 0.25" contract. H_m(t) is the YES price of the "above U_t" contract. With
T = t + H days, m1 is the last meeting on or before T and m2 the first meeting after T, and
w = (date of m2 - T) / (date of m2 - date of m1). Then CUT_H = w C_m1 + (1 - w) C_m2, and HIKE_H is the same with H_m.
H = 90 is the product. H = 60 is the comparison.

**Future** (Milestone 1 report, section 5). It pays $1 per index point, so $100 times the settlement value S. It is
fully collateralized: at price F the buyer posts F and the seller posts 100 - F. Expiry is the last Friday of each
month, moved one week earlier if it falls within one business day of an FOMC decision. S is the mean of the daily
index over the five calendar days ending on expiry. Days without a valid index value drop out of the mean. If all
five are missing, settlement waits for the next valid value.

**Static hedge** (`docs/notes/futures_pricing.md`). The dealer who sells the future on day t buys, for each of
the five settlement days d, 20 x w(d) contracts of meeting m1(d) and 20 x (1 - w(d)) of meeting m2(d), all at
today's strike. It sells day d's share at the close of day d. Meeting dates are known in advance, so the meetings
and weights are known on day t. This usually means two contracts, and three when the settlement window straddles a
switch of the bracketing pair. **Fair value** F0 is the cost of this hedge at the index's own prices on day t.

**Measures**, in dollars per $100 contract (equal to index points):
- *Hedge error* = hedge proceeds minus settlement, both at the index's prices. Positive means the dealer gains.
- *Hedge effectiveness* = 1 - sum(error^2) / sum(futures P&L^2), where futures P&L = S - F0.
- *Trading cost* = the spread paid relative to the index's price for each leg, plus the Kalshi taker fee
  0.07 x P x (1 - P) per contract at the execution price. The dealer buys at the ask and sells at the bid of the
  side it holds. A cut leg is a NO contract, so its ask is 1 - (YES bid).
- *Capital* = the dealer's 100 - F0 of futures collateral plus the hedge purchase. The buyer's capital is F0.

**Sample.** 44 monthly expiries from Feb 2023 to Sep 2026, entries from 2023-02-02 (decision 002). There are seven
entry leads: 7, 14, 21, 30, 45, 60 and 90 calendar days before expiry. That gives 1,152 trades across CUT90,
HIKE90, CUT60 and HIKE60. Trades with leads above about 30 days overlap across expiries, so they are not
independent.

## Results

**1. The hedge matches the future exactly unless the Fed changes the rate before expiry.** At the index's own
prices, every trade with no rate change before expiry has an error of exactly zero, unless a settlement day had no
valid index value. Those fallback cases have errors of at most $1.31. A meeting at which the Fed holds does not
break the hedge, because the strike only moves when the rate moves. The expectation "near exact when no meeting
falls before expiry" is therefore too narrow. The condition is no rate *change*.

| Index | No meeting before expiry: RMSE ($) | Fed held: RMSE ($) | Fed moved: RMSE ($) | Fed moved: worst ($) | Effectiveness, all trades |
|---|---|---|---|---|---|
| CUT90 | 0.16 (104 trades) | 0.16 (113) | 23.5 (70) | 54.8 | 0.68 |
| CUT60 | 0.12 (104) | 0.04 (113) | 33.7 (71) | 74.3 | 0.56 |
| HIKE90 | 0.23 (106) | 0.17 (111) | 18.0 (66) | 51.1 | 0.55 |
| HIKE60 | 0.09 (107) | 0.17 (112) | 22.9 (75) | 63.4 | 0.30 |

**2. A rate change breaks the hedge, and the sign is predictable.** After a move, the index re-anchors to the new
upper bound, but the hedge still holds contracts struck at the old one. Example: a CUT90 future expiring
2024-12-27, sold on 2024-11-27 for $88.61. The hedge is strike 4.50, "upper bound below 4.75%", in the Mar and May
2025 meetings. The Fed cut to 4.50% on 2024-12-18, so the index switched to "below 4.50%" and settled at $42.75.
The hedge, still "below 4.75%", was worth about $93. The dealer gained $51 relative to the future. When the Fed
moves in the index's direction (a cut for CUT, a hike for HIKE) the dealer gains. When it moves the other way the
dealer loses, by less, because the index is small then. How often this happens depends on the lead. Across CUT90
trades, the share with no meeting before expiry is 88% at 7 days, 63% at 14, 40% at 30 and 0% from 45 days on.

**3. Most of the trading cost comes from the later contract, but it is not the whole cost.** The mean round trip
(spread plus taker fees) per $100 contract is shown below. The far leg holds about half the contracts but costs 1.3
to 2.0 times more per contract. Shortening the horizon to 60 days cuts the CUT cost by about a quarter, because
both legs are closer to their meetings.

| Index | Total | Spread | Fees | Near leg | Far leg | Far share of cost | Far share of contracts | Per contract, near / far |
|---|---|---|---|---|---|---|---|---|
| CUT90 | 7.56 | 5.71 | 1.85 | 3.42 | 4.14 | 55% | 48% | 6.2c / 9.9c |
| CUT60 | 5.61 | 4.05 | 1.56 | 2.30 | 3.32 | 59% | 53% | 4.3c / 6.8c |
| HIKE90 | 7.26 | 6.06 | 1.20 | 3.54 | 3.71 | 51% | 49% | 6.4c / 8.4c |
| HIKE60 | 6.05 | 5.03 | 1.02 | 2.06 | 3.99 | 66% | 53% | 3.9c / 7.7c |

**4. Capital is about $103 to $105 per contract for the dealer, and small next to trading cost.** The dealer posts
100 - F0 and pays about F0 plus entry costs for the hedge. So a hedged seller ties up roughly the full $100 for the
life of the trade. At an illustrative 4% a year, that is $0.07 at a 7-day lead, $0.33 at 30 days and $1.04 at
90 days, against $5 to $8 of trading cost. The buyer ties up only F0: $41 to $60 on average for CUT90, depending on
the lead.

**5. The futures price builds in the roll-down that the spot index shows.** F0 sits above the spot index, and the
gap grows with the lead. For CUT90 the mean gap is $1.8 at 7 days, $8.2 at 30 and $16.3 at 90. In this sample a
buyer of the future lost about that gap on average (-$0.1, -$8.6, -$19.5), because cuts kept arriving later than
priced. This is the futures-side view of the Milestone 1 roll-down in `docs/log/palmer.md`.

## Robustness (`results/futures_robustness.csv`)

| Variant | CUT90 RMSE when the Fed moved | CUT90 mean cost | CUT90 far share |
|---|---|---|---|
| Main: src rule, from 2023-02-02 | 23.5 | 7.56 | 55% |
| Only trades where every hedge leg had a rule price | 17.5 | 7.68 | 54% |
| Milestone 1 price rule | 24.2 | 7.52 | 53% |
| src rule, from 2022-03-17 | 19.3 | 6.82 | 55% |

## Choices and limits to know before citing the numbers

- **Hedge legs without a rule price.** In 21% of trades, at least one hedge leg had no usable price under the
  3-day rule, usually the far leg or the old strike after a move. Dropping those trades would have removed more
  than half of the rate-move trades. The dealer still holds such a leg, so for hedge legs only it is valued at the
  standing book's mid, or at the midpoint of a one-sided book within 15 cents of 0 or 1 (Palmer's bound logic,
  widened from 3 cents). A leg with no bid in that zone is sold at 0, which is conservative. The index itself is
  untouched. Under the Milestone 1 rule, which needs almost none of these marks, the results are the same.
- **Execution** uses the last observed Kalshi book. Depending on the index and lead, 12 to 81% of leg executions
  (median 31%) use a book that last changed more than 3 days earlier (`share_legs_old_book`). Candles have no depth, so top-of-book size is assumed to be enough.
- **Fees** use the 0.07 taker rate for every date, as `src/` does, without per-order rounding (the large-order
  limit; rounding adds at most 1 cent per order). Maker fees would be lower but need passive fills.
- **No interest** is credited on locked collateral. Kalshi pays interest on open positions since Oct 2024 and the
  draft escrow does not. That is Jay's settlement-discount item (TASK 10).
- **Data end:** the Milestone 1 pull runs through 2026-10-26, so the last expiry is 2026-09-25.

## Index on the data-layer rule vs Milestone 1 (TASK 5, `results/index_vs_m1.csv`)

With the Milestone 1 rule, `build.py` reproduces `index_m1/data/index_daily.csv` exactly: all 1,943 days, every
leg, the same missing days. With the decision 002 rule, from 2023-02-02, CUT90 has a level correlation of 0.997
with Milestone 1 and a mean absolute gap of 0.49pp, but coverage falls from 96% to 88%, because a quote must be at
most 3 days old instead of 10. On 28 of the 1,708 days where both versions have a value (from Jul 2021), the gap exceeds 5pp. Every one of these days has a leg priced by the rule's
trade branch: when a book is wider than 10 cents, the last trade sets the price, and a single stale or extreme
print (for example a 1-cent trade) can move CUT90 by up to 29pp.

## For the spec and the theory (Jay)

1. The static-hedge fair value is exact only for futures that expire before the next rate change. For longer
   futures, F0 is the "no rate change" price. In this sample, dealers selling CUT futures at F0 gained on
   average before trading costs ($3.12 per CUT90 contract across all trades, $12.83 when the Fed moved), so the true fair value needs an
   adjustment for the reset.
2. The expiry rule allows an FOMC decision inside the five-day settlement window. That happens on 6 of 55 monthly
   expiries since Mar 2022: a Wednesday decision before a Friday expiry. A rule of "no decision inside the
   settlement window" would close this.
3. Under the decision 002 rule, 18% of trades had at least one settlement day without a valid index value, and 45
   had none in the whole window and waited. Trade-branch outliers (above) also reach settlement. Both bear on
   which price rule the contract names.
