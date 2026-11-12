# 002: One cleaning rule and one sample for the final report
Status: proposed (needs Ari and Jay to accept by Friday 11/13)
Date / who: 2026-11-12, Palmer
Accepted by: Jay 2026-11-12, conclusion only. The "Why" below is superseded by decision 005: the tail
correction argument does not hold for CUT90's legs, and decision 005 gives the reasons that do, adds a
settlement variant of the rule, and keeps points 1 to 3 unchanged. Read 005 with this file.

The two codebases clean prices differently, so every Milestone 1 number moves if the index is rebuilt on
the repo panel:

| | `index_m1/` (Milestone 1) | `src/` (repo) |
|---|---|---|
| Price rule | mid if spread <= $0.10, else missing; carry last mid forward up to 10 days | quote -> bound -> trade -> stale (N = 3 days, S = $0.10), tick-floor BOUND correction on |
| Tails pinned at 1c / 99c | taken at face value | valued at the midpoint of the bound (e.g. 0.5c) |
| Main sample | from 2022-03-17 (first day off the zero bound) | meetings from Feb 2023 (`config.SAMPLE_START`) |
| Venues | Kalshi ladder only | Kalshi ladder + decision buckets, Polymarket, ZQ futures, Atlanta Fed MPT |

Decision (proposed):
1. The final index uses the `src/` rule (N = 3, S = $0.10, bound on). It is documented, has a sensitivity
   grid, and fixes a real bias: CUT90 sat near 2% through 2022, which is exactly the 1c / 99c tail regime the
   BOUND branch corrects.
2. Main sample starts with the Feb 2023 meeting, matching the repo and the Milestone 1 robustness sample
   (every ladder has at least 7 strikes from then on). The Mar 2022 to Jan 2023 period is reported as an
   extension using the Milestone 1 rule, since `src/` does not pull 2022 meetings.
3. The Milestone 1 rule stays as one robustness row in the final tables, so readers can see what changed.

Why: One product needs one settlement rule. The futures settles on the index, so the index rule is part of
the contract spec.

Alternatives considered: (a) Keep the Milestone 1 rule for the index and `src/` only for comparisons.
Rejected: two definitions of "the price" in one report. (b) Extend `src/` back to 2022. Possible if time
allows (add 2022 dates to `config.FOMC_DATES`, re-pull), but not needed for the futures results.

Files affected: `index/` (new, Ari), `docs/spec.md` index-inputs row (Jay).
