# 004: Announcement days stay in the sample
Status: proposed
Date / who: 2026-11-12, Palmer

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
