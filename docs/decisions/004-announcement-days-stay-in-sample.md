# 004: Announcement days stay in the sample
Status: proposed
Date / who: 2026-11-12, Palmer
Accepted by: Jay 2026-11-12, no changes. The expiry rule referred to below is rewritten in `docs/spec.md`
section 4, because the Milestone 1 version never fires for a Wednesday decision before a Friday expiry.
That strengthens this decision rather than replacing it: keeping decisions out of the settlement window
limits settlement risk, and the index still re-anchors on the path, which is what this decision is about.

Decision: Report every backtest statistic on all days, with announcement days shown as a separate row,
never silently excluded.

Why: Niusha asked why we made an exception. The answer is mechanical: C_m is measured against today's
upper bound, so when the Fed moves the reference strike shifts and the index re-anchors even if beliefs
about later meetings are unchanged. That reset is how the product behaves, and settlement risk around
resolution is one of the evaluation criteria, so it belongs in the results. In Milestone 1, the 32
announcement days (15 with a rate change) carry most of the tracking error (2.04pp daily TE with them,
0.32pp without).

Alternatives considered: change the futures expiry rule so no contract settles within a day of an FOMC
decision (already in the Milestone 1 draft spec). Keep that too; it limits settlement risk but does not
remove the reset from the index path.
