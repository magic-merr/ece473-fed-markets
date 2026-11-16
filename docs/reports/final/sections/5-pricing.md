# 5. Pricing

Owner: Jay. Full argument and proof: `docs/theory.md`. Numbers: `docs/reports/final/numbers.md`.

## 5.1 Fair value from a static hedge

Write `U_t` for the upper bound of the target range set by the most recent decision announced on or before
day `t`, since the daily close falls after the 2:00pm announcement, and `C_m(t)` for the price of the
cut leg at meeting `m`, which is one minus the price of meeting `m`'s contract "the upper bound after `m` is
above `U_t` minus 0.25". The index on day `t` is `I(t) = w(t) C_a(t) + (1 - w(t)) C_b(t)`, where `a` and `b`
are the meetings bracketing the day ninety days ahead and `w` is the interpolation weight (section 2). The
contract settles at `S`, the mean of `I` over the five days ending at expiry.

**If the target range does not change between the trade date and expiry, the future is exactly replicable by
a portfolio bought once and held.** FOMC meeting dates are published years ahead, so for each settlement day
the bracketing meetings and the weight are known on the trade date. If the range does not change, the strike
is known too. The settlement value is then a fixed-weight combination of contracts that already trade, with
weights and strikes fixed on the trade date, and

    F0 = (1/5) sum over the five settlement days d of [ w(d) C_a(d) + (1 - w(d)) C_b(d) ]

evaluated at trade-date prices. A dealer short the future buys, for each settlement day, `20 w(d)` contracts
of the nearer meeting and `20 (1 - w(d))` of the later one, and sells each day's tranche at that day's close.
That pays `100` times the mean of the index over those five days, which is the contract's payout before `S`
is rounded to the nearest 0.25. Any other price allows a riskless profit. Rounding and the missing-day
fallback are the only reasons the replication is not exact to the cent: with a full window and no rate change
the error is zero before rounding and at most $0.12 after. The proof is in `docs/theory.md` section 2.

Two things follow.

**The exact condition is no rate change, not no meeting.** A meeting at which the Fed holds leaves the range
and therefore the strike unchanged, so the hedge still works. Our Milestone 1 note expected exactness only
when no meeting fell before expiry, which is too narrow. The backtest confirms the sharper condition: trades
with a meeting that held have the same near-zero hedge error as trades with no meeting at all,
$0.20 against $0.22 per contract (section 7).

**The future prices the roll-down that the spot index cannot deliver.** Between announcements the strike is
fixed and the ninety-day point advances one day per day, so the weight moves mechanically from the nearer
meeting to the later one at a rate of one over the gap between them. Differentiating the index splits its
change into that mechanical term, which depends only on the slope of the cut curve and the gap between
meetings, and the change in the two contract prices, which is news. A holder of the two meeting contracts
earns only the news term, because their holdings do not re-weight, and this is the gap our Milestone 1
backtest measured. The future has no such gap, because `F0` is the cost today of the contracts the index will
hold at expiry, at the weights it will hold them. The roll-down is already in the price, and it shows up as a
basis over the spot index that grows with the lead: $1.61,
$8.20 and $17.28 at 7, 30 and 90 days (section 7).

## 5.2 What a rate change does, and how to charge for it

When the Fed moves the range before expiry, the hedge holds contracts struck at the old upper bound while the
index re-anchors to the new one, and the two stop being the same claim.

Suppose the Fed cuts one notch. The hedge leg at the old strike is now worth about one. The index, re-anchored,
asks for a further cut, which is worth about the price of two cuts divided by the price of one. The dealer's
gain per unit held at meeting `m` is therefore about `1 - P_two(m) / P_one(m)`, which is positive. After a
hike instead, the old strike is two notches away and nearly worthless, so the dealer loses only a little. The
dealer is long a digital on the Fed moving in the index's direction, and `F0` does not charge for it. The
backtest shows that asymmetry: a mean gain of $25.27 when the Fed moves in the
index's direction against -$2.51 when it moves the other way (section 7).

Everything needed to price that digital in advance is on the ladder on the trade date. Let `p_dir` be the
price of at least one step in the index's direction by the last meeting before expiry, and let `G` be the sum
over hedge tranches of the tranche size times `1 - P_two / P_one`. Then

    F_adj = F0 - p_dir x G

This is an upper bound on the correction rather than an estimate of it, because it ignores moves against the
index and assumes the old legs go to exactly one.

It works for CUT and overstates for HIKE. The direction probability is well calibrated for both: for CUT90 a
mean of 0.15 against a realized 0.13. For CUT90
the gain term is close, $22.71 predicted against
$26.40 realized. The formula is built to overstate the correction, so it is worth saying that for CUT it
does not: the predicted gain lands a little below the realized one. Applying it cuts the buyer's mean loss
from $8.63 to $4.92. For HIKE90 the gain term is
too large, $37.24 against $20.01, and its
correlation with the realized gain across trades is near zero. The reason is that the ratio of two hikes to
one hike is read off the entry-day ladder and assumed stable. It is not, and it misses in both directions.
The aggregate overstatement comes from the May 2023 and September 2026 hikes, where the market priced a
further hike far more richly once the move happened than the entry-day ratio implied, so the re-anchored
index was worth more than the formula assumed and the dealer's real gain was smaller. At the March and July
2023 hikes it understated the gain instead. The errors are large and of both signs, which is why the
correlation is near zero rather than merely weak. We report `F_adj` as fair value for CUT and as an upper
bound for HIKE.

What is left after the correction is belief change rather than construction. In this sample cuts kept arriving
later than priced, which is a fact about 2023 to 2026 and not a property of the contract.

## 5.3 Continuity, and why announcement days stay in

The index is continuous on any stretch with no rate change, because the weight and the two contract prices all
move continuously. It jumps when the range changes, because the strike moves one notch, and it does not jump
at a meeting that holds. Those jumps are where the hedge fails and where the product's residual risk lives.
Dropping them from the sample would remove the only days on which the dealer's digital pays, so they stay in
and are shown as their own row (section 7). The same fact is why no decision may fall inside the settlement
window and why the window extension stops at a decision date (section 4).

## 5.4 The pricing argument does not need the settlement discount

The replication argument never reads a price as a probability. It uses only that the settlement value is a
fixed-weight combination of traded contracts and that the hedge holds those same contracts and sells them on
the same days the index reads them. If every price carries a collateral discount, it carries it identically on
both sides and cancels. The discount matters only for reading the index as a probability of a cut, which
nothing in the contract requires. That is fortunate, because section 4.5 shows it is not identifiable in this
data.

## 5.5 The ladder is consistent enough to settle on

Replication needs the ladder to be internally consistent, since the price of "the upper bound is above `K`"
must fall as `K` rises. Across 11,179 meeting-days from March 2022,
12 (0.11%) admit an executable violation, meaning a bid at a higher strike
above an ask at a lower strike, with a largest available credit of $0.09. Mid
prices look much worse at 25.5%, but a mid is not a tradable price when the
book is one-sided, which is common in this ladder, and the executable test is the one that matters.
