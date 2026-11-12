# Reset adjustment to fair value, and dealer break-even

Status: working note from Palmer, 11/12. For Jay (TASK 14, the theory section) and Ari (the futures results).
Numbers: `src/reset_check.py` -> `results/reset_adjustment.md`, run on Ari's main backtest. Units are dollars per
$100 contract.

## 1. The reset is one-sided
When the Fed changes the rate before expiry, the index moves to the new strike and the hedge keeps the old one.
Which way the Fed moves decides almost everything:

| | Fed moves in the index's direction | Fed moves against it | No change |
|---|---|---|---|
| CUT90 dealer gain, mean (trades) | +23.75 (41) | -2.61 (29) | -0.01 (217) |
| HIKE90 dealer gain, mean (trades) | +24.35 (29) | -2.00 (37) | 0.00 (217) |

Why, for CUT (HIKE is the mirror image). Each hedge leg is "at least one net cut by meeting m". After a cut that
leg is worth about 1. The index, re-anchored at the new bound, now asks for "a further cut", which is worth
P(2 cuts) / P(1 cut). So the dealer gains about 1 - P(2 cuts)/P(1 cut) per unit. After a hike the old strike is two
steps away and worth almost nothing, so the dealer loses only a little. The dealer is effectively long a digital
on "the Fed moves my way before expiry", and F0 does not charge for it.

## 2. An ex-ante correction from the ladder
Everything below is observable on the entry day t:

- p_dir = P(at least one step in the index's direction by the last meeting before expiry). For CUT this is
  1 - Y_k(U - 0.25); for HIKE it is Y_k(U); k is the last meeting before expiry.
- G = the sum over hedge tranches of q x (1 - P_two(m) / P_one(m)): what the dealer gains if that move happens.
- F_adj = F0 - p_dir x G.

The correction ignores moves against the index and assumes the old legs go to 1, so it is an upper bound.

How well it does (`results/reset_adjustment.md`, sections 2 and 3):
- **p_dir is well calibrated.** The mean is 0.16 for CUT90, and the realized share of trades with a cut before
  expiry is 0.14. For HIKE90 it is 0.12 vs 0.12.
- **CUT: G is about right.** Predicted G is 22.3 and the realized gain 24.6 for CUT90 (28.2 vs 33.4 for CUT60).
  By lead, the mean correction tracks the dealer's mean gain closely up to 60 days (CUT90: 0.64 vs 0.56 at
  7 days, 3.74 vs 3.17 at 30, 5.67 vs 4.45 at 60) and overshoots at 90 (9.97 vs 5.66).
- **HIKE: G is too large** (39.5 predicted vs 24.4 realized for HIKE90), and the correlation across trades is
  about zero. After the 2023 hikes the market priced further hikes more than the entry-day ladder ratio implied.
- **Effect on the buyer.** For CUT90, the buyer's mean loss falls from 8.54 at F0 to 4.44 at F_adj, and the RMS
  P&L falls from 20.5 to 17.7. The remaining loss is belief change (cuts kept arriving later than priced), not
  construction. For HIKE the correction overshoots: the buyer goes from about 0 to +4.85.

Suggested statement for `docs/theory.md`: F0 is the exact no-arbitrage price for a future that expires before
the next FOMC meeting. For longer futures, the seller's hedge is long a digital on a move in the index's
direction, so fair value is F0 minus that digital's value, and p_dir x G is a first-order estimate of it from
the ladder. Report it for CUT, and for HIKE as an upper bound.

## 3. Dealer break-even
Net = dealer gain minus round-trip hedge cost, before the dealer charges any futures spread:

| | Mean gain | Mean hedge cost | Mean net | Share of trades net negative | Cost when no rate change |
|---|---|---|---|---|---|
| CUT90 | 3.16 | 7.56 | -4.40 | 90% | 7.97 |
| CUT60 | 4.90 | 5.61 | -0.71 | 87% | 5.83 |
| HIKE90 | 2.23 | 7.26 | -5.02 | 90% | 6.84 |
| HIKE60 | 3.11 | 6.05 | -2.95 | 90% | 5.73 |

Reading: the mean gain is the reset digital paying off in a sample with many cuts. A market maker cannot count on
it, and it loses on 9 of 10 trades. So the edge a dealer needs is roughly the hedge cost itself: about $7 to $8
per CUT90 contract round trip, or $3.5 to $4 a side. Per dollar of payoff that is 7.6 cents, against a 2.7 cent round
trip on a Kalshi contract within a week of its meeting and 8.8 cents beyond 90 days (`results/summary.md`): the
future inherits the far leg's illiquidity. This is the strongest argument for
the 60-day version (cost $5.6) or for letting the dealer hedge with maker orders.
