# 1. The product

Owner: Jay. Source: `docs/spec.md` sections 1 and 3. Numbers: `docs/reports/final/numbers.md`.

We specify, price and test a **constant-maturity event future**: a cash-settled, fully collateralized futures
contract that pays one dollar for every point of CUT90, a 90-day constant-maturity probability that the
Federal Reserve's target range is lower than it is today. A contract settling at 42.75 pays $42.75, and the
most it can pay is $100. At a trade price `F` the buyer posts `F` and the seller posts `100 - F`, so the two
sides together always hold the largest payout the contract can make and neither can default. HIKE90 is the
same contract on the probability of a higher range, and we report 60-day versions of both as a comparison.

The contract exists because the exposure it offers cannot be held directly. Kalshi lists a separate market for
each FOMC meeting, and every one of those markets expires. Anyone who wants a standing 90-day view has to hold
two meeting contracts and rebalance them every day as the 90-day point moves between meetings. Our Milestone 1
backtest measured what that costs. The replicating portfolio gave up the slope of the cut curve every day, an
average of 26.0 basis points, which accumulated to
399.3 index points over the sample while the index itself moved
+9.4 (`results/decomposition.md`). The portfolio also had to be re-struck every
time the Fed moved the range. The future removes both chores from the buyer. Because the meeting dates are
published years ahead, the mix of meeting contracts the index will hold at expiry is known on the trade date,
so a dealer selling the future buys that mix once and holds it to expiry with no daily rebalancing. Section 5
proves this and states the one condition under which it stops being exact.

Two people would use it. A buyer who wants ninety-day exposure to the pace of Fed cuts, such as a fund hedging
a floating-rate liability, gets it in one position instead of a daily roll. A dealer who sells it hedges it
statically in the meeting contracts and earns the difference between the futures price and the hedge cost.
Section 7 reports what that difference has to be. Round-trip hedging costs $7.76 per contract, and on trades
where the Fed did not move at all the dealer needs $7.86. Across every trade the shortfall is smaller,
$4.60, because the dealer's gains when the Fed does move pay back part of the cost. The spread a market
maker needs therefore sits between those two figures depending on how often the Fed moves.

The rest of the report is about that contract. Section 2 defines the index it settles on, section 3 the data
and the price rule behind the index, section 4 the contract terms, section 5 the pricing argument, sections 6
and 7 the backtest and its results, and section 8 the limits.
