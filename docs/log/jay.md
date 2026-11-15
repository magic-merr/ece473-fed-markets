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

## 2026-11-15 17:45  main
Did: J1, J2, J3, J6. J4 and J5 are blocked on other people (see below).
- J1: signed decision 007 as written, pushed alone (`4504289`), with two notes recorded in 007 and Request R1.
- J2: `docs/spec.md` to final on the 007 configuration. Section 5 now carries the four-step source hierarchy
  (book, wide-book mid, last trade only on a one-sided book, 3-day carry), the composite is out (006 point 3),
  and the [open] items are closed. Section 4 is justified by definition and no longer predicts a fall in hedge
  error. Section 10 rewritten: nothing in the spec is open.
- J3: `docs/theory.md` written. Proposition 1 (static replication) with proof, the two corollaries, the reset
  digital and `F_adj`, continuity, the settlement discount, the ladder check. Every empirical number is a
  `{{numbers.md: key}}` placeholder.
- J6: drafts of sections 1, 4 and 5 in `docs/reports/final/sections/`.
- Reran `theory/noarb.py`; all four checks reproduce exactly. 47 tests pass.

Results (numbers worth keeping):
- **Two errors of mine from 11/12, both now fixed.** (a) Spec section 10 predicted the rate-move RMSE would
  fall when expiries move. Decision 006 measured it rising for CUT90 and CUT60 and falling for HIKE90 and
  HIKE60. The expiry rule is right, my argument for it was not; it is now justified by definition only.
  (b) Spec section 5 claimed the settlement-window extension could never reach back past a decision date.
  False: in 11 of the 44 expiries a decision falls exactly 9 days before expiry (March and September every
  year, plus 2024-12 and 2025-06), inside a 10-day extension. The rule in 007 and A3 already said "not past a
  decision date", so only my justification was wrong. Section 5.2 now states it as an explicit stop condition
  and says settlement defers when it binds. That is Request R1 for Ari.
- The settlement discount does not enter the pricing argument at all. Proposition 1 never reads a price as a
  probability; it uses only that settlement is a fixed-weight combination of traded contracts and that the
  hedge holds the same contracts and sells them on the same days the index reads them. A discount factor
  carried on every price appears identically on both sides and cancels. So the fact that D is not identifiable
  (TASK 10) costs the pricing argument nothing. This closes item 2 of `docs/notes/futures_pricing.md`, which
  assumed F needed a carry adjustment that Jay would estimate.
- Corollary 1.2 derives the roll-down term analytically: between announcements `dw/dt = -1/(date b - date a)`,
  so the index drifts by the cut-curve slope across the bracketing meetings divided by the gap between them.
  A holder of the two meeting contracts earns none of it. That is the Milestone 1 gap, and `F0` already
  contains it, which is the product's reason to exist.
- `theory/noarb.py` unchanged and rerun: 12 executable ladder violations of 11,179 meeting-days, max credit
  $0.09; expiry collisions 5 of 44, 6 of 55, 7 of 58, all zero under the spec rule.

Open issues:
- J4 blocked on A4, but it should be a no-op: `theory/noarb.py` reads only `index_m1/` frozen data and the
  FOMC calendar, neither of which A4 touches. I will rerun it to confirm once A4 lands.
- J5 blocked on P5. Placeholder keys used in `theory.md` and sections 1, 4, 5, for Palmer to match in
  `numbers.md`: `rolldown_bp_per_day`, `rolldown_total_m1`, `index_change_m1`, `cut90_rmse_held`,
  `cut90_rmse_no_meeting`, `basis_cut90_7d`, `basis_cut90_30d`, `basis_cut90_90d`, `hedge_cost_cut90`,
  `capital_cost_90d`, `cut90_gain_with_move`, `cut90_gain_against_move`, `p_dir_cut90_mean`,
  `p_dir_cut90_realized`, `G_cut90_predicted`, `G_cut90_realized`, `G_hike90_predicted`, `G_hike90_realized`,
  `buyer_loss_F0_cut90`, `buyer_loss_Fadj_cut90`, `discount_gap_1week`, `discount_gap_150day`, `ladder_days`,
  `ladder_violations_tradable`, `ladder_violations_mid`, `ladder_worst_credit`.
- R1 for Ari: the decision-date stop binds in 11 of 44 expiries, so A3 needs a test on the deferral branch.
- Sections 1, 4 and 5 cite section 7 for the backtest numbers. If A4 moves the headline figures, the
  placeholders handle it, but the sentences around them that say "rises" or "is close" need one read-through
  after the freeze.

Next: J4 once Ari messages that A4 is pushed, then J5 from `numbers.md`, then a review pass on sections 1, 4
and 5 Monday morning.

## 2026-11-15 18:00  main
Did:
- J4: reran `theory/noarb.py` at `fb94863`. Every number reproduces; `theory/README.md` unchanged.
- `docs/spec.md`: closed R1, R4 and R6. Section 5.1 now states the rule exactly as the code applies it (wide-book
  mid only where a trade printed within 3 days; last trade also when the book has not been quoted in 3 days;
  tail fill as step 5). Numbers updated to the final run (45 expiries, 11 of 45, 23% of CUT90 trades and 35 of
  178 settlements below five valid days) and cited by `numbers.md` key. Edits drafted by Palmer's session from
  the code and `numbers.md`; reviewed and applied by Jay.
Checked before applying, rather than taking the patch on trust:
- `src/stale.py` line 72 and 80: the trade branch does require `trade_age <= 3`, so R1's wording is right that
  the wide-book mid only replaces a price where a trade printed within three days.
- `stale.tail_filled`: it fills only where `price` is NaN, so the tail fill really is a last resort and belongs
  at step 5 rather than earlier in the hierarchy.
- Recomputed the final calendar independently: 45 expiries, first 2023-02-24, last 2026-10-23, and 11 of them
  have a decision inside a 10-day extension, every one at exactly 9 days. Matches R5 and R6.
- `theory/noarb.py` rerun at this commit: output byte-identical, so J4 is a confirmation and `theory/README.md`
  needed no change.

Results (numbers worth keeping): none new.
Open issues: none on the spec. 48 `{{numbers.md: key}}` placeholders remain in `theory.md` (23) and sections 1,
4 and 5 (5, 5, 15); `docs/spec.md` has none left.
Next: J5 (fill the placeholders), then review Monday.
