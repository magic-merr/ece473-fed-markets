# Final report outline (draft 11/12, Palmer)

Due Mon 11/16, night. Results freeze Sun 11/15, 10pm. Each person writes their own sections in their own words
(CLAUDE.md rule 6), and Palmer edits the whole report for one voice on Monday. Edit the owner, source and
figure columns here if your plan differs. This file is the shared checklist, not report text.

## Feedback on Milestone 1 that every section must answer (Niusha, 11/11)
1. Say what the product is before anything else. Section 1 does this in one paragraph.
2. Define the index up front, once, with a formula and a worked example (section 2).
3. Explain announcement days, and don't exclude them silently (decision 004; sections 2 and 7).
4. For every backtest, state the method and the metrics, and what we expect each metric to show, before
   giving results (section 6).
5. Write in plain sentences: no em dashes, no filler, every term defined once.

## Sections

| # | Section | Owner | Content | Sources | Figures and tables |
|---|---|---|---|---|---|
| 1 | The product | Jay | One paragraph: a fully collateralized future paying $100 x CUT90, who would use it (hedging the timing of Fed cuts), and why a future instead of the spot index (it prices the roll-down) | `docs/spec.md`, Palmer log 11/12 | none |
| 2 | The index | Ari | Definition of U_t, C_m, H_m, w, CUT_H, HIKE_H; worked example; the series; announcement-day resets | decision 003, `index/README.md` | M1 fig1 (ladder), fig2 (term structure), fig3 (index: rebuild on the final rule?) |
| 3 | Data and price rule | Palmer | Kalshi ladder; stale rule (decisions 002, 005, 006); Kalshi vs Polymarket agreement as the robustness check on venue; fed funds futures and Atlanta Fed MPT comparison; leg liquidity at 60 vs 90 days | `README.md` findings, `results/summary.md`, `results/settlement_rule_check.md`, `results/leg_liquidity.md` | liquidity table; venue agreement table |
| 4 | Contract specification | Jay | Payoff, collateral, expiry (spec section 4: no decision in the settlement window), 5-day settlement and fallback, settlement price rule (decisions 005, 006), settlement discount bounded, not estimated (TASK 10) | `docs/spec.md` | spec table |
| 5 | Pricing | Jay | Static hedge; F0 exact before the next meeting; the reset digital and F_adj = F0 - p_dir x G; continuity between announcements; ladder no-arbitrage check (12 of 11,179 days) | `docs/theory.md`, `theory/README.md`, `docs/notes/reset_adjustment.md`, `docs/notes/futures_pricing.md` | none, or one diagram |
| 6 | Backtest method and metrics | Ari | Sample (44 expiries, 7 leads, 4 indices), trade construction, each metric defined with its expected value (hedge error 0 without a rate change; cost mostly the far leg; basis rising with lead) | `index/README.md` | none |
| 7 | Results | Ari | Fair value and basis (roll-down priced in); hedge error by case and by direction of the move; cost and the far-leg share; capital; dealer break-even; return decomposition (TASK 7); robustness rows | `index/results/futures_backtest.md`, `results/reset_adjustment.md` | fig_hedge_error, fig_hedge_cost; 3 or 4 compact tables |
| 8 | Limitations | Palmer | Data end 2026-10-26; Yahoo ZQ coverage; execution at the last book with no depth; fee rate held constant; overlapping trades; the HIKE reset estimate | all logs | none |
| | References, Appendix (reproduction commands, data files) | Palmer | | `README.md` run blocks | |

## Promised in the Milestone I update (graders compare plan with delivery)
- [ ] Ari: rerun with fees (done), capital (done), event study around FOMC meetings. Proposal: frame
      `futures_rate_move_events.csv` and the reset table as the event study, or add index moves on decision days.
- [x] Jay: settlement discount (TASK 10: not identifiable at these spreads, so bound it), ladder no-arbitrage check
      (TASK 10), settlement and collateral terms (TASK 8, `docs/spec.md`).
- [ ] Return decomposition explaining the 274-point gap (in Palmer's 11/12 log; Ari reruns it as TASK 7).
- [ ] Palmer: Polymarket (done), spread, fee and volume data (done), Kalshi vs Polymarket (done), index vs fed
      funds futures. ZQ is meeting-level only and covers Oct 2026 onward; say so in section 3 and point to the
      meeting-level comparison and MPT.

## Headline numbers to keep consistent across sections
Check these against the repo files before citing them. If decision 006 is accepted and Ari reruns on the spec
calendar (TASK 18), they move slightly.
- 44 monthly expiries, Feb 2023 to Sep 2026; 1,152 trades across CUT90, HIKE90, CUT60, HIKE60.
- Hedge error is 0 with no rate change (max $1.31). When the Fed moves, the RMSE is $23.5 (CUT90).
- Round-trip hedge cost: CUT90 $7.56, CUT60 $5.61, HIKE90 $7.26, HIKE60 $6.05.
- Basis F0 minus spot, CUT90: $1.8 at 7 days, $8.2 at 30, $16.3 at 90.
- Dealer gain when the Fed moves in the index's direction: about $24 (90-day) and $34 (60-day). Against it: $1 to $3.
- Kalshi vs Polymarket: mean absolute P(hold) gap 2.1pp, correlation of expected change 0.995.
