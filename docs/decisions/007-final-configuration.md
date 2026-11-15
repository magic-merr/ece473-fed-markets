# 007: Final configuration for the report, and how decisions 002 to 006 close
Status: proposed. Accepted when Ari and Jay add their line at the bottom.
Date / who: 2026-11-15, Palmer

Decision: the final report's numbers come from exactly this configuration. Nothing else changes before the
results freeze (tag `results-final`, Sunday 11/15, 11pm).

| Item | Final choice | From |
|---|---|---|
| Product | Fully collateralized future paying $100 x CUT90. HIKE90 alongside. H = 60 reported as the comparison horizon | 003, `docs/spec.md` 1 to 3 |
| Index definition | Unchanged from 003 | 003 |
| Leg price rule (index as measurement and as settlement, one number) | `src` rule: N = 3 days, S = $0.10, bound on, tail fill. On a day when the book is two-sided and was quoted within 3 days but is wider than S, the leg is priced at the **book mid** (006 point 1). The last-trade branch is used only when the book is not two-sided | 002, 005 points 1 and 2, 006 points 1 and 2 |
| Where that rule lives | `index/legs.py`, new rule name `final`, default for `build.py` and `futures.py` (Ari). `src/stale.py` is not changed | this decision |
| Cross-venue comparison (report section 3) | Unchanged. Original `src` rule including the trade branch. The 2026-11-12 run in `results/summary.md` is final | 005 (measurement vs settlement split) |
| Main sample | Entries from 2023-02-02 (Feb 2023 meeting). Mar 2022 to Jan 2023 is a robustness row | 002 |
| Expiry calendar | `docs/spec.md` section 4: last Friday, stepped back one week until no FOMC decision is in the settlement window or on the first business day after expiry | spec 4 |
| Settlement window and fallback | `docs/spec.md` section 5: mean of valid days if at least 3 of 5; else extend back up to 10 days (never past a decision date); else defer to the next valid value; backstop last valid value | spec 5 |
| Composite Kalshi/Polymarket price in settlement | No. Robustness check on the venue only | 006 point 3 |
| Settlement discount | Bounded, not estimated | TASK 10, `theory/README.md` |
| Announcement days | Stay in the sample, shown as their own row | 004 |
| Fees | Kalshi taker 0.07 x P x (1 - P) per contract, constant over the sample, no per-order rounding | TASK 16 |
| Robustness rows (`index/results/futures_robustness.csv`) | Milestone 1 price rule; `src` rule with the trade branch (pre-006); Milestone 1 expiry rule; Ari's 11/12 fallback; sample from 2022-03-17; only trades where every hedge leg had a rule price | |

What this closes:
- 002: accepted (conclusion). Its reasoning is replaced by 005.
- 004: accepted.
- 005: points 1 and 2 accepted. Point 3 (drop the trade branch) is amended by 006.
- 006: accepted, except its "Files affected: `src/stale.py`" line. The wide-mid branch goes in `index/legs.py`.
- TASK 17: closed. 6 of 55, 5 of 44 and 7 of 58 are the same rule over different windows (006). The report
  cites 5 of 44, the backtest sample.
- Decision 007 overrides the Status lines still printed in 002 to 006.

Why:
- **One configuration, written down once.** Five decisions were proposed on 11/12 and three people's Claude
  sessions read them. A single table stops each session from settling the open points its own way.
- **Wide-mid in `index/legs.py`, not `src/stale.py`.** `src/stale.py` also feeds the cross-venue panel, which can
  only be rebuilt from raw pulls on Palmer's machine. Changing it would move section 3's numbers for no gain and
  make Ari's rerun wait on a Palmer commit. The logic is four lines and already exists in
  `src/settlement_check.py::wide_mid_days`.
- **Expiry rule kept although the rate-move RMSE rises for CUT** (23.5 to 26.2 in 006). The rule is justified by
  definition: settlement must not average index values measured against two different target ranges. The RMSE
  change is reported as a result, not used as the argument.
- **Spec fallback in the backtest.** The spec and the backtest must name the same settlement procedure, or the
  report describes a contract it did not test.

Alternatives considered:
- Leave 002 to 006 as separate proposals and sign each. Rejected: five files with partial amendments is where the
  11/12 confusion came from.
- Keep Ari's simpler fallback and amend the spec to match. Rejected: the spec's 3-of-5 rule is the better contract
  term, and implementing it is a small change to `futures.py`.

Files affected: `index/legs.py`, `index/futures.py`, `index/build.py` (Ari); `docs/spec.md` sections 4, 5 and 10
(Jay); reruns of `src/settlement_check.py`, `src/reset_check.py`, `src/leg_liquidity.py` and the new
`src/decomposition.py` (Palmer); `theory/noarb.py` rerun (Jay).

Accepted by:
- Palmer, 2026-11-15 (author)
- Jay:
- Ari:
