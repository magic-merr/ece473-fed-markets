# Jay's log

(Append entries using the template in CLAUDE.md. Newest at the bottom.)

## 2026-11-12 18:20  main
Did:
- TASK 1. Accepted 003 and 004 unchanged. Accepted 002's conclusion but wrote decision 005 to replace its
  reasoning, and proposed that the index which *settles* the contract drop the trade branch. Needs Palmer
  and Ari (TASK 19).
- TASK 10 and TASK 13. New `theory/` folder: `noarb.py` runs four checks off repo data, writes
  `theory/results/noarb_summary.md`. Findings in `theory/README.md`.
- TASK 8. Wrote `docs/spec.md`, the full contract spec, with the expiry rule and the settlement fallback
  rewritten.

Results (numbers worth keeping):
- Ladder is arbitrage-free where it counts: of 11,179 meeting-days from Mar 2022, 12 (0.11%) allow a bid at
  a higher strike above an ask at a lower strike, max credit $0.09. Mid prices are non-monotone on 25.5% of
  days, but a mid is not tradable on a one-sided book. The index can settle a contract.
- Decision 002's tail argument does not hold for this index. CUT90 reads one near-the-money strike per
  meeting. Pinned 1c/99c share is 40.4% (near leg) in Mar 2022 to Jan 2023 and 0.7% from Feb 2023, zero in
  2024 to 2026. On the 186 pinned days the BOUND price equals the Milestone 1 mid to four decimals, because
  (1+bid)/2 is (bid+ask)/2 when the ask is pinned at 1. The branch is a no-op here. It is still a real fix
  for Palmer's whole-ladder work, which does read far strikes.
- Settlement discount is not identifiable at these spreads. A discount predicts asymmetry: near-certain
  winners below $1, near-certain losers near $0. Both sides are off by the same amount at every horizon
  (3c at a week, 6c past 150 days), and the implied annualized carry is 10 to 130%. So it is residual
  uncertainty plus the tick floor. `theory.md` should bound the discount, not estimate it. This revises
  `docs/notes/futures_pricing.md` item 2.
- Expiry rule. The Milestone 1 rule never fires for a Wednesday decision before a Friday expiry, because
  they are two business days apart while the five-day window still spans the decision. Collisions: 5 of 44
  expiries in the backtest sample, 7 of 58 over Mar 2022 to Dec 2026. The spec rule (step back one week
  until the window is clear) gives 0 in both, moving 5 expiry dates.

Open issues:
- Ari still has to sign 002/003/004 (TASK 1), and decision 005 point 3 needs both of them (TASK 19).
- TASK 17: my expiry collision count and Ari's differ because the month windows differ, not the rule.
- TASK 18: `index/futures.py` should be rerun on the spec's expiry calendar and settlement fallback. The
  five expiries that move are exactly the ones with a decision inside the window, so the rate-move RMSE
  should fall. That is a result to report, not a correction to bury.
- `docs/spec.md` section 10 lists the terms still marked [open]. The one that matters is whether the
  composite price enters the settlement rule, which waits on Palmer's TASK 3.

Next: TASK 9 (`docs/theory.md`), then TASK 14.
