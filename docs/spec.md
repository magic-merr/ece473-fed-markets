# Contract specification: the CUT90 future

Owner: Jay. Status: final, on the decision 007 configuration.

This file defines the product. The index it settles on is defined in decision 003. The price rule that feeds
the index is decision 002, with its reasoning in 005 and its wide-book branch in 006, all closed by decision
007. Where this file and the Milestone 1 report section 5 disagree, this file is current, and section 9 lists
every change.

Numbers produced by the backtest are cited by result file and marked pre-freeze until
`docs/reports/final/numbers.md` exists (CLAUDE.md sprint rule 7). The counts in sections 4 and 7 come from
`theory/noarb.py`, which reads only the frozen Milestone 1 data and does not move with the rerun.

## 1. What the product is

The CUT90 future is a cash-settled, fully collateralized futures contract on the probability that the Federal
Reserve's target range is lower in 90 days than it is today. One contract pays $1 for each index point at
settlement, so a contract settling at an index value of 42.75 pays $42.75, and the maximum payout is $100.

The contract exists because the exposure it provides cannot be held directly. Kalshi lists a separate market
for each FOMC meeting, and every one of them expires. Anyone who wants a standing 90-day view has to hold two
meeting contracts and rebalance them daily as the 90-day point moves between meetings. The Milestone 1
backtest measured what that costs: the replicating portfolio gave up the slope of the term structure every
day, about 26 basis points, and it had to be re-struck every time the Fed moved the target range
(`docs/reports/milestone1/`, and the decomposition in `results/decomposition.md`).

A dealer who sells this future does not run that roll. The future pays a fixed mix of two contracts that
already trade, in weights that are known on the trade date, so the dealer buys them once and holds them to
expiry. Section 8 states the one condition under which that hedge stops being exact. The argument is in
`docs/theory.md`.

Two users:

- A **buyer** who wants 90-day exposure to Fed cuts without running a roll: a fund hedging a floating-rate
  liability, or anyone with a view on the pace of cuts rather than the timing of one meeting.
- A **dealer** who sells the future and hedges it statically in the meeting contracts, earning the spread
  between the futures price and the hedge cost.

HIKE90 is the same contract on the probability of a higher range. CUT60 and HIKE60 are the same at a 60-day
horizon and are reported as a comparison, not listed as products.

## 2. Underlying

The settlement index is CUT90 as defined in decision 003 and implemented in `index/build.py`. In words:
`U_t` is the upper bound of the target range in effect on day `t`. For meeting `m`, `C_m(t)` is the
probability that the upper bound after `m` is below `U_t`, taken as one minus the YES price of meeting `m`'s
"above `U_t` minus 0.25" contract. With `T = t + 90` days, `m1` is the last meeting on or before `T` and `m2`
the first meeting after `T`, and `w = (date of m2 - T) / (date of m2 - date of m1)`. Then
`CUT90(t) = w C_m1(t) + (1 - w) C_m2(t)`, in index points, which are percentage points.

The index is measured against today's target range, so it re-anchors when the Fed moves. That reset is a
property of the product. It is reported, never excluded (decision 004), it is the reason the static hedge has
a limit (section 8), and it is priced in `docs/theory.md`.

## 3. Contract terms

| Term | Value |
|---|---|
| Underlying | CUT90, the 90-day constant-maturity net-cut probability (decision 003) |
| Quotation | Index points, 0 to 100, in increments of 0.25 |
| Contract size | $1 per index point, so $100 maximum payout |
| Settlement | Cash, in USD |
| Settlement value `S` | Mean of the daily index over the settlement window (section 5), rounded to 0.25 |
| Expiry | Monthly, by the calendar in section 4 |
| Listed contracts | The three nearest monthly expiries (section 8) |
| Collateral | Full. The buyer posts `F`, the seller posts `100 - F`, both held until settlement |
| Margin calls | None. There is no variation margin and no default risk (section 6) |
| Trading hours | Continuous while the index inputs trade |
| Position limits | Not specified. A live venue would set one; nothing in this report depends on it |

## 4. Expiry calendar

**Expiry is the last Friday of the calendar month, moved one week earlier, repeatedly if needed, until no
FOMC decision falls inside the settlement window or on the first business day after expiry.**

The rule is justified by definition, not by hedge error. The index is measured against the target range in
effect on the day. A decision inside the settlement window changes that range part-way through, so the mean in
section 5 would average index values measured against two different ranges. Those are not the same quantity,
and no contract should settle on their average.

This replaces the Milestone 1 draft rule, which moved expiry only when a decision fell within one business day
of it. That rule never fires for the case it was written for. FOMC decisions are announced on a Wednesday at
2:00pm, a Wednesday decision and a Friday expiry are two business days apart, and the five-calendar-day
settlement window starting on the preceding Monday still contains the decision.

Checked against `index_m1/data/fomc_calendar.csv` by `theory/noarb.py`:

| Window | Expiries | Collisions, Milestone 1 rule | Collisions, this rule |
|---|---|---|---|
| Feb 2023 to Sep 2026, the backtest sample | 44 | 5 | 0 |
| Mar 2022 to Sep 2026, Ari's window | 55 | 6 | 0 |
| Mar 2022 to Dec 2026 | 58 | 7 | 0 |

The three counts are the same rule over different month ranges, which closes TASK 17 (decision 006, decision
007). **The report cites 5 of 44**, the backtest sample. Those five expiries are 2023-07, 2025-01, 2025-10,
2026-01 and 2026-07, each moved back one week. Stepping back one week never creates a new collision in this
window, because scheduled meetings are at least five weeks apart.

Moving those five expiries does not reduce hedge error, and the report should not claim it does. Decision 006
measured the rate-move RMSE rising for CUT90 and CUT60 and falling for HIKE90 and HIKE60 (pre-freeze,
`results/settlement_rule_check.md`). The reason is that the moved trades had partial resets, and shifting the
expiry changes which entries see a full one. That is a result to report in section 7, not an argument for or
against this rule.

## 5. Settlement

**Settlement window.** The five calendar days ending on expiry, expiry included.

**Settlement value.** `S` is the mean of the valid daily index values in the window, rounded to the nearest
0.25.

**Valid.** A daily index value is valid when both legs, `C_m1` and `C_m2`, have a price under the hierarchy
below. A day on which either leg has no price produces no index value and is not valid.

### 5.1 Source hierarchy for a leg's price

A leg takes the first of these that applies on the day. This is the decision 007 rule, which is decision 002
with the wide-book branch from decision 006.

1. **Book.** The standing two-sided Kalshi book for that meeting and strike, priced under the decision 002
   rule: the mid when the book is no wider than $0.10, and the bound midpoint when one side is pinned at 0 or
   1.
2. **Wide book.** The book is two-sided and was quoted within three days but is wider than $0.10. The leg is
   priced at the **mid of the standing book**. This is decision 006 point 1. It replaces decision 005 point 3,
   which would have dropped these days: dropping them raises the share of CUT90 settlements with fewer than
   three valid days from 9% to 24%, so one settlement in four would need the extension below (pre-freeze,
   `results/settlement_rule_check.md`).
3. **Last trade.** Used only when the book is not two-sided.
4. **Carry forward.** The last price from 1 to 3, up to three days old. This is the `N = 3` freshness test in
   decision 002.

If none applies, the leg has no price, the day is not valid, and settlement goes to the fallback below. There
is no fifth branch. The contract never settles on a price older than three days.

There is **no composite Kalshi and Polymarket price** in the settlement rule (decision 006 point 3). Polymarket
publishes no historical order books, so its freshness cannot be tested against the three-day rule, and it lists
outcome buckets rather than the ladder strikes the index reads. Its agreement with Kalshi is reported in
section 3 of the report as a robustness check on the venue. This closes the open item carried in the 11/12
draft of this file.

### 5.2 Fallback when the window has too few valid days

This matters: about one CUT90 settlement in five has fewer than five valid days even under the rule above
(pre-freeze, `results/settlement_rule_check.md`).

1. If at least three of the five days are valid, `S` is the mean of the valid days.
2. Otherwise extend the window backwards one calendar day at a time until three valid values are available,
   subject to both stop conditions below.
3. **Stop conditions on the extension.** The extension stops at whichever comes first: a total window length of
   ten calendar days, or the day after the most recent FOMC decision. The extension never crosses a decision
   date, for the reason in section 4: index values on the two sides of a decision are measured against
   different target ranges and must not be averaged.
4. If three valid values are not available when the extension stops, settlement is deferred. The contract
   settles on the next business day that produces a valid index value, at that single value.
5. If no valid value appears within ten business days of expiry, the contract settles at the last valid index
   value before expiry. This backstop does not fire in our sample. A live venue would instead settle by
   committee determination.

The decision-date stop in step 3 is a real constraint, not a formality. In 11 of the 44 expiries in the
backtest sample a decision falls exactly nine days before expiry, inside a ten-day extension: March and
September of every year, plus December 2024 and June 2025. In those months the extension can reach back only
to the day after the decision, so it may stop short of three valid days and settlement defers under step 4.
An earlier draft of this file asserted that the extension could never reach a decision date. That assertion
was wrong. The rule in decision 007 and in TASK A3 already carried the guard; only this file's justification
was at fault.

## 6. Collateral

The contract is fully collateralized and there is no margin call. At trade price `F`, the buyer posts `F` and
the seller posts `100 - F`. The two amounts always sum to $100, the largest payout the contract can make, so
neither side can owe more than it has already posted and neither side can default. This is the construction
Kalshi and Polymarket use for a complete set, where $1 of collateral splits into a YES and a NO that always
sum to $1.

The cost of that safety is the time value of the locked collateral, and it is small next to trading cost: on
the order of a dollar per contract at a 90-day lead against five to eight dollars of round-trip hedge cost
(pre-freeze, `index/results/futures_backtest.md`, result 4). Collateral is not what makes this product
expensive. The far hedge leg is.

## 7. Index inputs and no-arbitrage

The index reads one strike per meeting, at `U_t - 0.25`, which is near the money. It never reads a deep tail.
Two consequences, both from `theory/noarb.py`:

**The ladder is sound enough to settle on.** Across 11,179 meeting-days from March 2022, prices that are
executable are almost always monotone in the strike, which is what no-arbitrage requires, since "upper bound
above K" must be weakly decreasing in K:

| Test | Violations | Share |
|---|---|---|
| Mid prices non-monotone in strike | 2,846 of 11,179 | 25.5% |
| Executable, a bid at a higher strike above an ask at a lower strike | 12 of 11,179 | 0.11% |

The twelve executable violations have a maximum credit of $0.09. The mid-price figure is much larger because a
mid is not a tradable price when the book is one-sided, which is common in this ladder.

**The settlement discount is bounded, not estimated** (decision 007, TASK 10). A discount `D(tau) < 1` on a
contract paying $1 at settlement predicts an asymmetry: a near-certain winner trades below $1 and a
near-certain loser trades near $0. In this data both sides are off by the same amount at every horizon, about
3 cents at a week and 6 cents past 150 days, and the implied annualized carry runs from 10% to 130%. That is
residual uncertainty plus the one-cent tick, not a financing rate. Any true discount is smaller than that
figure, which is in turn smaller than the round-trip hedge cost. `docs/theory.md` carries it as a bounded term.

## 8. What the contract does not remove

A buyer of this future is not holding a riskless position, and the dealer's static hedge is not always exact.

**The hedge is exact when the target range does not change between the trade and expiry.** A meeting at which
the Fed holds does not break it, because the index strike moves only when the rate moves. The Milestone 1
planning note expected exactness to require "no meeting before expiry". That is too narrow, and Ari's backtest
shows the correct condition is no rate change: trades with a meeting that held have the same near-zero error as
trades with no meeting at all (pre-freeze, `index/results/futures_backtest.md`, result 1).

The failure is mechanical. The hedge holds contracts struck at the old `U`. After a move the index switches to
a strike one notch away, and the two stop being the same quantity. The sign is predictable: the dealer gains
when the Fed moves in the index's direction and loses less when it moves against, because the index is small
then. `docs/theory.md` prices this as a digital on a move in the index's direction, and gives the ex-ante
correction `F_adj = F0 - p_dir x G`.

Two consequences for the product:

- Short-dated contracts are close to exactly hedgeable. The share of CUT90 trades with no meeting before expiry
  falls with the lead and reaches zero from 45 days on (pre-freeze,
  `index/results/futures_backtest.md`, result 2).
- A contract listed more than about six weeks before expiry carries rate-change risk the static hedge does not
  cover, and the buyer pays for it in the basis. This is why section 3 lists only the three nearest monthly
  expiries.

## 9. Changes from the Milestone 1 draft

| Term | Milestone 1 report section 5 | Here | Why |
|---|---|---|---|
| Expiry adjustment | Move one week if within one business day of a decision | Move one week, repeatedly, until no decision is in the settlement window or on the next business day | The old rule never fires for a Wednesday decision before a Friday expiry. Section 4 |
| Missing settlement days | Drop from the mean, no minimum | Three of five valid, then a bounded extension, then deferral | About one CUT90 settlement in five has fewer than five valid days. Section 5.2 |
| Extension across a decision | Not considered | Explicit stop at the day after a decision | Index values on the two sides of a decision are not the same quantity. Section 5.2 |
| Leg price source | Not stated | Four-step hierarchy, with a wide two-sided book priced at the mid | Decisions 002, 005, 006, 007. Section 5.1 |
| Composite venue price | Raised as an option | Not used in settlement | Decision 006 point 3. Section 5.1 |
| Quotation increment | Not stated | 0.25 index points | The ladder prices in whole cents and the index is a weighted average of two of them |
| Listed expiries | Not stated | The three nearest months | Beyond that the static hedge does not hold. Section 8 |
| Settlement discount | Assumed estimable, after Gebele and Matthes | Bounded, not estimated | Not identifiable at these spreads. Section 7 |

## 10. Status of open items

Every term in this file is now fixed by decision 007. Nothing in the specification is open.

Two things sit outside it and belong to other sections of the report:

- The on-chain variant sketched in the Milestone 1 report, a stablecoin escrow with an oracle posting the
  index, is not part of this specification. Nothing here depends on it. If the final report keeps it, it goes
  in `docs/theory.md` as a variant, where the oracle is the same index computation reported by whoever runs
  the venue.
- Position limits, listing fees and venue rules are not specified, because no result in the report depends on
  them.

One request is outstanding: **R1** in `docs/TASKS.md` asks Ari to test the deferral branch in section 5.2
step 4, since the decision-date stop binds in 11 of the 44 expiries.
