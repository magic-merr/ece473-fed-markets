# Milestone II Update: Constant-Maturity Event Futures

ECE 473 | Palmer Mann, Jay Crowther, Ariel Perczek (submitted Nov 12, 2026; copied from the Claude doc)

## Recap

For reference, our project is a futures contract that pays $100 multiplied by CUT90 (our index that tracks the probability of a Fed cut within the next 90 days). Our aim, put simply, is to make a trader's life easier. Today, a trader has to roll Kalshi contracts by hand every six weeks instead of holding just one fixed position. Since "day 90" usually falls between two FOMC meetings, we take a weighted average of Kalshi's prices for those two meetings, favoring whichever is closer to day 90.

In Milestone 1, a portfolio built to track the index lost 274 points while the index rose 9 points. We hypothesized a few reasons then, and Jay has since figured out why. The market usually priced a cut as more likely at the later meeting, so the index drifts up as its weight shifts toward it, and no holder of the contracts earns that drift. A futures price builds that drift in up front, which is the main case for our product over the spot index.

## Planned vs. actual progress

**Palmer (data).** *Planned:* add Polymarket, collect spreads, fees and volume, and compare Kalshi with Polymarket and the index with fed funds futures. *Done:* all but a full futures comparison. Kalshi and Polymarket price Fed decisions almost identically (about 2 points apart on average), so the venue does not drive our results. Free fed funds futures data only covers contracts still listed (from October 2026), where they agree with both within about 3 points; for earlier years we use the Atlanta Fed's market probability tracker. He also found the weak link in our blend: the later meeting trades on only 30% of days.

**Ari (index and backtest).** *Planned:* rerun the backtest with fees, estimate capital needs, and run an event study around FOMC meetings. *Done:* all three, built around one question: can someone who sells our future hedge it? The natural hedge is to buy the two Kalshi contracts behind the index and hold them to expiry. Across 44 monthly expirations (2023 to 2026, about 1,150 trades), it matches the future exactly whenever the Fed leaves rates unchanged before expiry. When the Fed moves, it misses by about $23 per $100 contract, usually in the seller's favor; this is our event study. The real obstacle is cost: about $7.50 per round trip in spreads and fees, mostly on the later meeting, with the seller tying up nearly the full $100.

**Jay (spec and theory).** *Planned:* explain the 274-point gap, estimate the settlement discount, check the strike ladder for arbitrage, and finalize the contract terms. *Done:* all but the discount. The ladder allows a tradable arbitrage on only 12 of about 11,000 meeting-days, so it is a sound basis for settlement. The discount is too small to separate from noise at current spreads, so we will bound it instead. The spec also fixes our expiry rule, which let an FOMC decision fall inside the settlement window on 5 of 44 expiries.

## Are the final results ready?

Almost. The data, index and backtest are done, and the main findings will not change. Before we freeze results on Sunday, November 15:

1. **Settlement price (Palmer, Ari):** when a book is wide on a settlement day, use its midpoint instead of the noisier last trade, then rerun the backtest on the new expiry calendar.
2. **Pricing argument (Jay):** why the hedge sets the futures price, plus a correction for rate changes before expiry that the backtest shows can be read off Kalshi prices.
3. **Return breakdown (Ari):** the 274-point explanation, redone on the final index.

Monday, November 16 is for the final report and presentation.

---
Sources for every number: `README.md` findings, `results/leg_liquidity.md`, `index/results/futures_backtest.md`,
`theory/results/noarb_summary.md`, `docs/spec.md` section 4.
