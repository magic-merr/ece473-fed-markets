# Contract specification: the CUT90 future

Owner: Jay. Covers TASK 8 and TASK 13.
Status: draft for the final report. Terms marked **[open]** still need a decision.

This file defines the product. The index it settles on is defined in decision 003. The price rule that
feeds the index is decision 002 as amended by decision 005. Where this file and the Milestone 1 report
section 5 disagree, this file is current and the change is listed in section 9.

## 1. What the product is

The CUT90 future is a cash-settled, fully collateralized futures contract on the probability that the
Federal Reserve's target range is lower in 90 days than it is today. One contract pays $1 for each index
point at settlement, so a contract settling at an index value of 42.75 pays $42.75 and the maximum payout
is $100.

The contract exists because the exposure it provides cannot be held directly. Kalshi lists a separate
market for each FOMC meeting, and every one of them expires. Anyone who wants a standing 90-day view has
to hold two meeting contracts and rebalance them daily as the 90-day point moves between meetings. The
Milestone 1 backtest measured what that costs: the replicating portfolio gave up 26.2 basis points a day
to the slope of the term structure, which is 399 index points over the sample, and it had to be re-struck
every time the Fed moved the target range. A dealer who sells this future hedges it with two contracts
bought once and held to expiry, with no daily rebalancing (section 8). The contract turns a position that
has to be managed every day into one that does not.

Two users:

- A **buyer** who wants 90-day exposure to Fed cuts without running a roll. A fund hedging a floating-rate
  liability, or anyone with a view on the pace rather than the timing of cuts.
- A **dealer** who sells the future and hedges it statically in the meeting contracts, earning the spread
  between the futures price and the hedge cost.

HIKE90 is the same contract on the probability of a higher range. CUT60 and HIKE60 are the same at a
60-day horizon and are reported as a comparison, not listed as products.

## 2. Underlying

The settlement index is CUT90 as defined in decision 003 and implemented in `index/build.py`. In words:
`U_t` is the upper bound of the target range in effect on day `t`. For meeting `m`, `C_m(t)` is the
probability that the upper bound after `m` is below `U_t`, taken as one minus the YES price of meeting
`m`'s "above `U_t` minus 0.25" contract. With `T = t + 90` days, `m1` is the last meeting on or before `T`
and `m2` the first meeting after `T`, and `w = (date of m2 - T) / (date of m2 - date of m1)`. Then
`CUT90(t) = w C_m1(t) + (1 - w) C_m2(t)`, reported in index points, which are percentage points times one.

The index is measured against today's target range, so it re-anchors when the Fed moves. That reset is a
property of the product and is reported, not excluded (decision 004). Section 8 states what it does and
does not do to a hedged position.

## 3. Contract terms

| Term | Value |
|---|---|
| Underlying | CUT90, the 90-day constant-maturity net-cut probability (decision 003) |
| Quotation | Index points, 0 to 100, in increments of 0.25 |
| Contract size | $1 per index point, so $100 maximum payout |
| Settlement | Cash, in USD |
| Settlement value `S` | Mean of the daily index over the settlement window (section 5), rounded to 0.25 |
| Expiry | Monthly, by the calendar in section 4 |
| Listed contracts | The three nearest monthly expiries |
| Collateral | Full. The buyer posts `F`, the seller posts `100 - F`, both held until settlement |
| Margin calls | None. There is no variation margin and no default risk (section 6) |
| Position limits | **[open]** not needed for the report; a live venue would set one |
| Trading hours | Continuous while the index inputs trade |

## 4. Expiry calendar

**Expiry is the last Friday of the calendar month, moved one week earlier, repeatedly if needed, until no
FOMC decision falls inside the settlement window or on the first business day after expiry.**

This replaces the Milestone 1 draft rule, which moved expiry only when a decision fell within one business
day of it. That rule does not do what it was written to do. FOMC decisions are announced on a Wednesday at
2:00pm. A Wednesday decision and a Friday expiry are two business days apart, so the old rule never fires,
while the five-calendar-day settlement window starting on the preceding Monday still contains the
decision. Settlement would then average index values measured against two different target ranges, which
are not the same quantity.

Checked against the FOMC calendar in `index_m1/data/fomc_calendar.csv`:

| Window | Expiries | Collisions, old rule | Collisions, new rule | Expiry dates that move |
|---|---|---|---|---|
| Feb 2023 to Sep 2026 (the futures backtest sample) | 44 | 5 | 0 | 5 |
| Mar 2022 to Dec 2026 | 58 | 7 | 0 | 7 |

The five expiries that move in the backtest sample are 2023-07, 2025-01, 2025-10, 2026-01 and 2026-07, each
back by one week. Stepping back one week never creates a new collision in this window, because scheduled
meetings are at least five weeks apart.

Ari's `index/README.md` counts 6 collisions over a slightly different window. The two counts need
reconciling before the results are frozen; it is a question of which months are in the sample, not of the
rule. See TASK 17.

## 5. Settlement

**Settlement window.** The five calendar days ending on expiry, expiry included.

**Settlement value.** `S` is the mean of the valid daily index values in the window, rounded to the nearest
0.25.

**Valid.** A daily index value is valid when both legs, `C_m1` and `C_m2`, have a price under the rule in
decision 002 as amended by decision 005. A day on which either leg has no price produces no index value and
is not valid.

**Fallback, in order.** This is the part the Milestone 1 draft left unspecified, and it matters: 18% of the
trades in Ari's backtest had at least one settlement day without a valid index value (TASK 15).

1. Take the mean of the valid days in the window. If at least three of the five are valid, that is `S`.
2. If fewer than three are valid, extend the window backwards one calendar day at a time, to a maximum
   total length of ten calendar days, until three valid values are available. Take the mean of those three.
3. If three valid values are not available within ten days, settlement is deferred. The contract settles on
   the next business day that produces a valid index value, at that single value.
4. If no valid value appears within ten business days of expiry, the contract settles at the last valid
   index value before expiry. **[open]** This last branch is a backstop that never fires in our sample. A
   live venue would instead settle to a committee determination.

The extension in step 2 never reaches back past a decision date, because section 4 keeps decisions out of
the window and meetings are at least five weeks apart.

**Source hierarchy for a leg's price.** A leg takes the first of these that is available on the day:

1. The Kalshi two-sided book for that meeting and strike, under the decision 002 rule.
2. The composite Kalshi and Polymarket price for the same event, once `src/composite.py` exists (TASK 3).
   **[open]** whether the composite is in the settlement rule or only a robustness row. It should be in the
   rule only if Palmer's table shows it adds valid days without adding noise.
3. The last price from 1 or 2, carried forward up to three days, which is the `N = 3` freshness test in
   decision 002.

If none is available the leg has no price and the day is not valid, which sends settlement to the fallback
above. There is no fourth branch. The contract never settles on a price nobody could have traded on.

## 6. Collateral

The contract is fully collateralized and there is no margin call. At trade price `F`, the buyer posts `F`
and the seller posts `100 - F`. The two amounts always sum to $100, which is the largest payout the
contract can make, so neither side can owe more than it has already posted and neither side can default.
This is the same construction as a Kalshi or Polymarket complete set, where $1 of collateral splits into a
YES and a NO that always sum to $1.

The cost of that safety is the time value of the locked collateral. Ari measures it at $0.07 per contract
at a 7-day lead and $1.04 at 90 days, at an illustrative 4% a year, against $5 to $8 of trading cost over
the same trade. Collateral is not what makes this product expensive.

**[open]** On-chain version. The Milestone 1 report sketched a stablecoin escrow with an oracle posting the
index. Nothing in this spec depends on it. If the final report keeps it, it belongs in `theory.md` as a
variant, with the oracle being the same index computation reported by whoever runs it.

## 7. Index inputs and no-arbitrage

The index reads one strike per meeting, at `U_t - 0.25`, which is near the money. It never reads a deep
tail. This matters for decision 005, and it also means the index inherits whatever the ladder does at that
strike.

The ladder is sound enough to settle on. Across 11,179 meeting-days from March 2022, prices that are
executable are almost always monotone in the strike, which is what no-arbitrage requires, since
"upper bound above K" must be weakly decreasing in K:

| Test | Violations | Share |
|---|---|---|
| Mid prices non-monotone in strike | 2,846 of 11,179 | 25.5% |
| Executable violation, a bid at a higher strike above an ask at a lower strike | 12 of 11,179 | 0.11% |

The twelve executable violations have a maximum credit of $0.09 and the largest is a single day in May
2022. The mid-price figure is much larger because a mid is not a tradable price when the book is one-sided,
which is common in this ladder. Reported in `theory/README.md`; the script is `theory/noarb.py`.

## 8. What the contract does not remove

A buyer of this future is not holding a riskless position, and the dealer's static hedge is not always
exact. Ari's backtest is precise about when it breaks, and this is the most important limit to state in the
report.

The hedge is exact when the target range does not change between the trade and expiry. A meeting at which
the Fed holds does not break it, because the index strike only moves when the rate moves. Ari measures a
root mean squared hedge error of $0.16 per $100 contract across CUT90 trades with no rate change, against
$23.5 when the Fed moved, with a worst case of $54.8.

The reason is mechanical. The hedge holds contracts struck at the old `U`. After a move the index switches
to a strike one notch away, and the two stop being the same quantity. The sign is predictable: the dealer
gains when the Fed moves in the index's direction.

Two consequences for the product:

- Short-dated contracts are close to exactly hedgeable. Across CUT90 trades, the share with no meeting
  before expiry is 88% at a 7-day lead and 0% from 45 days on.
- A contract listed more than about six weeks before expiry carries rate-change risk that the static hedge
  does not cover. Pricing that is TASK 14 and belongs in `theory.md`. This spec lists only the three
  nearest monthly expiries for that reason.

## 9. Changes from the Milestone 1 draft

| Term | Milestone 1 report section 5 | Here | Why |
|---|---|---|---|
| Expiry adjustment | Move one week if within one business day of a decision | Move one week, repeatedly, until no decision is in the settlement window or on the next business day | The old rule never fires for a Wednesday decision and a Friday expiry, section 4 |
| Missing settlement days | Drop from the mean, no minimum | At least three of five valid, then a defined extension and deferral | 18% of trades hit a missing settlement day, TASK 15 |
| Leg price source | Not stated | Explicit three-step hierarchy, section 5 | Settlement cannot rest on an untraded price |
| Quotation increment | Not stated | 0.25 index points | The ladder prices in whole cents, and the index is a weighted average of two of them |
| Listed expiries | Not stated | The three nearest months | Beyond that the static hedge does not hold, section 8 |

## 10. What this spec still needs

- The **[open]** items above, chiefly whether the composite price enters the settlement rule.
- Reconciliation of the expiry collision count with `index/README.md` (TASK 17).
- A rerun of `index/futures.py` on the section 4 expiry calendar and the section 5 fallback (TASK 18).
  Five of 44 expiry dates move, and those five are exactly the trades where a decision currently sits
  inside the settlement window, so the rate-move RMSE should fall. That is a result worth reporting, not a
  correction to hide.
