# 005: Keep decision 002's conclusion, replace its reasoning, and separate the settlement rule from the index rule
Status: proposed (needs Palmer and Ari). Supersedes the "Why" of 002, not its decision.
Date / who: 2026-11-12, Jay

Decision:
1. Accept decision 002's conclusion. The index uses the `src/` rule (N = 3, S = $0.10) and the main sample
   starts with the Feb 2023 meeting.
2. Strike the tail-correction argument from 002's reasoning. It does not hold for this index, see below.
   The reasons that do hold are: one product needs one price rule, the `src/` rule is documented and has a
   sensitivity grid, and a three-day freshness test is the right standard for a price that settles a
   contract.
3. **New, needs agreement:** the index that *settles the future* uses the quote and bound branches and the
   three-day carry-forward, but not the trade branch. A settlement price should not be a last trade on a
   book wider than ten cents. Everything else about the rule is unchanged. This is written into
   `docs/spec.md` section 5 as the source hierarchy.

Why:

**The tail argument does not apply to this index.** Decision 002 justifies the `src/` rule by saying CUT90
sat near 2% through 2022, which is the 1c / 99c regime the BOUND branch corrects. Both halves fail for the
legs the index actually reads.

CUT90 reads exactly one strike per meeting, at `U_t - 0.25`, which is near the money. Share of CUT90 leg
days in the pinned-tail regime, from `theory/noarb.py` and the Milestone 1 panel:

| Period | Near leg | Far leg |
|---|---|---|
| Mar 2022 to Jan 2023 | 40.4% | 14.3% |
| Feb 2023 to Oct 2026 | 0.7% | 0.0% |

By year the pinned share is 30.2% in 2022, 1.5% in 2023 and 0.0% in 2024, 2025 and 2026. So the regime the
BOUND branch addresses is almost entirely inside the period 002 proposes to drop from the main sample.

Worse, on the 186 leg days that are pinned, the BOUND price and the Milestone 1 mid are the same number to
four decimal places. When the ask is pinned at 1, the bound midpoint `(1 + bid) / 2` is arithmetically
identical to the mid `(bid + ask) / 2`. The branch is a no-op for this index in every period.

The BOUND branch is a real fix for Palmer's cross-venue work, which aggregates the whole ladder and gives
weight to far strikes. CUT90 never reads a far strike, so the finding does not transfer. Nothing is wrong
with the branch. The argument for adopting it here was just the wrong argument.

**What switching rules actually does is cut coverage, and that is the thing to weigh.** The `src/` rule
requires a quote or trade within three days. Milestone 1 carried a quote forward up to ten days with no
freshness test. The Milestone 1 robustness table has index coverage at 0.890 for a five-day fill against
0.958 at ten days, so a three-day test lands below 0.89. For a research index that is a cost. For a
settlement price it is the correct trade: a contract should not settle on a quote nobody has refreshed in
a week.

**Why the trade branch should not settle the contract.** Palmer's TASK 15 note reports that every one of
the 28 days where the rebuilt index differs from Milestone 1 by more than 5 points uses a trade-branch leg,
a last trade on a book wider than ten cents, with differences up to 29 points. A 29-point move in a
settlement price sourced from a single stale print on a wide book is the kind of input that invites a
dispute, and on a live venue, manipulation. The same price is fine for measuring what the market thought,
which is what the comparison work needs. So the two uses should take different branches of the same rule
rather than two different rules.

This splits one number into two and both should be reported: the index as a measurement, which keeps the
trade branch, and the index as a settlement price, which does not.

Alternatives considered:
- Keep 002 exactly as written. Rejected: the stated reason is checkable and does not survive the check, and
  Niusha reads these.
- Use the Milestone 1 rule for settlement, since it needs almost no marks. Rejected: ten-day stale quotes
  are worse for settlement than three-day ones, and we would be back to two definitions of the price.
- Extend `src/` back to 2022 so the main sample covers the tail regime. Still worth doing if time allows,
  as 002 says, but it is not what decides this.

Files affected: `docs/spec.md` (section 5 and section 7), `index/legs.py` would need a settlement variant
(Ari), `theory/noarb.py` and `theory/README.md` (evidence, Jay). If point 3 is accepted, `index/futures.py`
needs a rerun, which is TASK 18.
