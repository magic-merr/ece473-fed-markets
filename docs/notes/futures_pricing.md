# Working notes: how the CUT90 future is priced and hedged

Status: notes from 11/12 planning, for Jay to turn into `docs/theory.md` and Ari to test in `index/`.

## The contract (Milestone 1 draft, report section 5)
Pays $1 per index point at expiry: $100 x CUT90, averaged over the 5 days ending at expiry. Fully
collateralized: at trade price F the long locks F and the short locks 100 - F, so no margin calls and no
default. Monthly expiry, moved off FOMC days.

## Fair value from a static hedge
At expiry date E the index will be

    CUT90_E = w_E C_a(E) + (1 - w_E) C_b(E)

where a and b are the meetings that bracket E + 90 days. Meeting dates are known today, so **a, b and w_E
are all known today**. If no FOMC meeting falls between today and E, the rate U_E = U_today, so the
strike U - 0.25 is also known today. Then the future pays a fixed mix of two contracts that already trade,
and

    F_today = w_E C_a(today) + (1 - w_E) C_b(today)          (before the settlement discount)

Hedge: a dealer short the future buys w_E of meeting a's cut position and 1 - w_E of meeting b's, holds to
expiry, sells. No daily rebalancing. This is why a future fixes the problem in the Milestone 1 backtest:
tracking the spot index needs daily rebalancing and gives up the roll-down (26bp/day on average), while
the future's price already embeds the roll-down because it is the forward value of the index.

Example: expiry in 30 days, meetings at 105 and 150 days. E + 90 = day 120,
w_E = (150 - 120)/(150 - 105) = 2/3. F = 2/3 C(105-day meeting) + 1/3 C(150-day meeting).

## Where it stops being exact (what to measure)
1. **A meeting before expiry.** If the Fed meets between today and E, U_E is unknown, so the strike the
   index will use is unknown. The hedge must be re-struck after that meeting. Risk and cost concentrate
   there. Futures that expire before the next meeting are exactly hedgeable; longer ones are not.
2. **Settlement discount.** Prices are about probability x D(tau) (Gebele and Matthes 2026), so contract
   prices drift up as tau shrinks even with no news. F needs a small carry adjustment; Jay estimates D.
3. **5-day averaging.** Settlement averages 5 daily values with slightly different weights. Still linear
   in contract prices, so the hedge is the average of 5 static hedges.
4. **Liquidity.** Meeting b is always more than 90 days out: median spread 6c, trades on about 23% of days
   (`results/summary.md`, Kalshi liquidity). Hedge cost is mostly that leg. Compare with a 60-day index.

## HIKE90
Identical with H_m = Y_m(U, t). Note CUT90 + HIKE90 <= 1 at every date. A HIKE90 - CUT90 spread contract is
a simple "Fed direction" product if we want one more design.

## Return decomposition (feeds task 7)
Index change = holder P&L + roll-down + announcement resets. Milestone 1 numbers in `docs/log/palmer.md`
(11/12): holder -274, roll-down +399, resets -127, bracket rolls +11, index +9 (CUT90, from 2022-03-17).
