# 006: Settle on the mid of a wide book, not a last trade, and do not drop those days
Status: proposed (amends 005 point 3; needs Jay and Ari). Answers TASK 19 and closes TASKS 15 and 17.
Date / who: 2026-11-12, Palmer

Evidence: `src/settlement_check.py` -> `results/settlement_rule_check.md`. It reruns Ari's `index/futures.py`
with the hedge, costs and sample unchanged and varies only the settlement rule. It uses Ari's settlement
fallback, not the 3-of-5 fallback in `docs/spec.md` section 5. The shares of windows with fewer than 3 valid
days are reported so the two can be compared.

Decision (proposed):
1. **Agree with 005 point 3 that a last trade on a wide book must not settle the contract.** Amend how: on a
   day when a leg's book is two-sided and was quoted within 3 days but is wider than 10c, the settlement index
   prices that leg at the **mid of the standing book** instead of dropping it. The trade branch is then used
   only when the book is not two-sided. QUOTE, BOUND and the 3-day carry are unchanged. In `docs/spec.md`
   section 5's source hierarchy this is a new step 1b, between the decision 002 book and the carry.
2. **Use the same rule for the index as a measurement**, so there is still one number (002's own argument).
   The trade-branch index stays as one robustness row.
3. **No composite Kalshi/Polymarket price in the settlement rule** (the spec section 5 [open] item, TASK 3).
   Polymarket publishes no historical order books, so its freshness cannot be checked against the 3-day test,
   and it lists outcome buckets, not the ladder strikes the index reads. Its agreement with Kalshi (mean
   absolute P(hold) gap 2.1pp, expected-change correlation 0.995, `results/summary.md`) goes in the report as a robustness
   check on the venue. TASK 3 is closed without `src/composite.py`.

Why:
- **Dropping trade-branch days costs a lot of settlement days.** For CUT90, the share of settlements with
  fewer than 5 valid days rises from 21% to 45%, and with fewer than 3 valid days from 9% to 24%. Under the
  spec's fallback, one CUT90 settlement in four would then need the window extension. For HIKE90 it is
  10% to 17%, and 14 more trades get no settlement at all under Ari's fallback.
- **The wide-book mid is a better price than the last trade.** From Feb 2023, 7,011 index-leg days use the
  trade branch on a two-sided book. The median spread is 25c and the last trade sits a median 9.5c from the mid.
  On 2,616 of them, a tight quote follows within 1 to 3 days. The mid is closer to that quote 57% of the time
  (mean error 8.4c vs 9.9c; 90th percentile 20c vs 24c).
- **It keeps coverage and the hedge.** It changes settlement on 21% of CUT90 trades by at most $3.28
  (HIKE90: 17%, at most $6.33). No trades are lost, the share of settlements using fewer than 5 days stays at
  21%, and the hedge is still exact when the rate does not move (max error $0.67). Mean CUT90 hedge cost goes
  from $7.56 to $7.67.
- **Caveat for the report.** Against the frozen Milestone 1 index, the wide-mid rule has more days with a gap
  above 5pp (CUT90: 45 vs 28 of 1,708). Milestone 1 is not ground truth on those days: it carried mids forward
  up to 10 days, and these are exactly the days when the book had widened.

Related findings for 005 and the spec section 4 expiry rule (no change proposed):
- **TASK 17, reconciled.** The same rule gives 6 of 55 collisions for Mar 2022 to Sep 2026 (Ari's window,
  ending at the data), 5 of 44 for the backtest sample, and 7 of 58 through Dec 2026 (Jay's window, which adds
  the Oct 2026 expiry). The 6 dates since Mar 2022: 2022-07-29, 2023-07-28, 2025-01-31, 2025-10-31,
  2026-01-30, 2026-07-31.
- **The rate-move RMSE does not fall when expiries move** (spec section 10 and TASK 18 expect it to).
  It rises for CUT90 (23.5 to 26.2) and CUT60 (33.7 to 36.7), and falls for HIKE90 (18.0 to 16.5) and HIKE60
  (22.9 to 20.1). Across all trades, CUT90 goes from 11.6 to 12.3 and HIKE90 from 8.7 to 7.5. The trades with a
  decision inside the window had partial resets, and moving the expiry shifts which entries see a full one.
  The rule is still right, because settlement should not average two definitions of the index. Justify it
  that way, not by hedge error.

Alternatives considered:
(a) 005 point 3 as written (drop the trade branch for settlement). The cost is above.
(b) Clip the last trade to the standing bid and ask. Rejected: it changes almost nothing, because the large
    gaps are trades inside books 15 to 35c wide, not trades outside them.
(c) Keep the 002 rule for settlement. Rejected for the reason 005 gives.

Files affected: `src/stale.py` (Palmer, once accepted: a wide-mid branch); `index/legs.py` and a rerun of
`index/futures.py` together with TASK 18 (Ari); `docs/spec.md` section 5 source hierarchy and the [open]
composite item (Jay).
