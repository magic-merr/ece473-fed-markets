# 4. Contract specification

Owner: Jay. Full terms: `docs/spec.md`. Configuration: decision 007. Numbers: `docs/reports/final/numbers.md`; the counts in this section come from `theory/noarb.py`, which reads only frozen Milestone 1 data.

## 4.1 Terms

| Term | Value |
|---|---|
| Underlying | CUT90, the 90-day constant-maturity net-cut probability (section 2) |
| Quotation | Index points, 0 to 100, in increments of 0.25 |
| Contract size | $1 per index point, so $100 maximum payout |
| Settlement | Cash, in USD |
| Settlement value `S` | Mean of the daily index over the settlement window, rounded to 0.25 (4.3) |
| Expiry | Monthly (4.2) |
| Listed contracts | The three nearest monthly expiries |
| Collateral | Full. The buyer posts `F`, the seller posts `100 - F`, both held to settlement |
| Margin calls | None, and no default risk (4.5) |

## 4.2 Expiry

Expiry is the last Friday of the calendar month, moved one week earlier, repeatedly if needed, until no FOMC
decision falls inside the settlement window or on the first business day after expiry.

The rule follows from the definition of the index rather than from any empirical result. The index is measured
against the target range in effect on the day. A decision inside the settlement window changes that range
part-way through the window, so the mean in 4.3 would average index values measured against two different
ranges. Those are not the same quantity and no contract should settle on their average.

Our Milestone 1 draft moved expiry only when a decision fell within one business day of it. That rule never
fires for the case it was written for: decisions are announced on a Wednesday, a Wednesday decision and a
Friday expiry are two business days apart, and the five-day window beginning on the preceding Monday still
contains the decision. Over the 44 expiries in the backtest sample, the old rule leaves a decision inside the
settlement window at 5 of them and the rule above at none, moving five expiry dates back by one week. The same
rule gives 6 of 55 over March 2022 to September 2026 and 7 of 58 through December 2026; these are one rule
over three month ranges, and we cite the backtest sample.

Moving those five expiries does not reduce hedge error, and we do not claim it does. The rate-move RMSE rises
for CUT and falls for HIKE (section 7), because the moved trades had partial resets and shifting the expiry
changes which entries see a full one. The rule is justified by what the index measures, not by its effect on
the backtest.

## 4.3 Settlement and the fallback when days are missing

The settlement window is the five calendar days ending on expiry, and `S` is the mean of the valid daily index
values in it. A day is valid when both index legs have a price under the rule in 4.4.

About one CUT90 settlement in five has fewer than five valid days, so the fallback is part of the contract
rather than an edge case:

1. If at least three of the five days are valid, `S` is their mean.
2. Otherwise extend the window backwards one day at a time until three values are available.
3. The extension stops at whichever comes first, a total window of ten calendar days or the day after the most
   recent FOMC decision. It never crosses a decision date, for the reason in 4.2.
4. If three values are not available when the extension stops, settlement defers to the next business day that
   produces a valid index value, and settles at that value.
5. A backstop settles at the last valid value before expiry if nothing appears within ten business days. It
   does not fire in our sample.

The stop in step 3 binds in practice. In 11 of the 44 expiries a decision falls exactly nine days before
expiry, inside a ten-day extension: March and September of every year, plus December 2024 and June 2025.

## 4.4 What price settles a leg

A leg takes the first of these that applies:

1. The standing two-sided Kalshi book, priced at the mid when it is no wider than ten cents, or at the bound
   midpoint when one side is pinned.
2. If the book is two-sided and quoted within three days but wider than ten cents, the mid of that book.
3. The last trade, only when the book is not two-sided.
4. Any of the above carried forward, up to three days old.

If none applies the day is not valid. There is no fifth branch, so the contract never settles on a price more
than three days old.

Step 2 is the one term we changed on evidence rather than on principle. Our first proposal was to refuse a
wide book outright, on the ground that a last trade inside a book fifteen to thirty-five cents wide should not
settle a contract. Refusing them turned out to cost too much: the share of CUT90 settlements with fewer than
three valid days rises from 9% to 24%, so one settlement in four would need the extension in 4.3. Pricing a
wide two-sided book at its mid keeps the day and is also a better price. Across index-leg days that used a
last trade on a two-sided book, the median book was twenty-five cents wide and the last trade sat a median
9.5 cents from the mid; where a tight quote followed within three days, the mid was closer to it 57% of the
time (section 3).

We do not use a combined Kalshi and Polymarket price to settle. Polymarket publishes no historical order
books, so its freshness cannot be tested against the three-day rule, and it lists outcome buckets rather than
the ladder strikes the index reads. Its agreement with Kalshi is reported in section 3 as a check on the
venue, not used in the contract.

## 4.5 Collateral, and the settlement discount

Full collateral makes the contract free of counterparty risk without a margin system: the two postings always
sum to the maximum payout, so neither side can owe more than it has already posted. This is the construction
Kalshi and Polymarket use for a complete set, in which a dollar of collateral splits into a YES and a NO that
always sum to a dollar. The price of that safety is the time value of the locked collateral, which is small
next to trading cost, about $1.04 per contract at a ninety-day lead against
$7.76 of round-trip hedging (section 7).

Prediction-market prices are not quite probabilities, because a contract paying a dollar at resolution trades
at roughly its probability times a discount for the collateral locked until then. We promised in Milestone I
to estimate that discount. We can report that it is **not identifiable in this data**, and why. A discount
predicts an asymmetry, with a near-certain winner trading below a dollar and a near-certain loser near zero.
In our data both sides are off by the same amount at every horizon, 3 cents at a
week and 6 cents past 150 days, and the implied annualized carry reaches triple
digits, which no financing rate does. What that gap measures is residual uncertainty plus the one-cent tick.
We therefore bound the discount rather than estimating it, and section 5 shows that the pricing argument does
not need it.
