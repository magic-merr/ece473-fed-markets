# Milestone II Update: Constant-Maturity Event Futures

ECE 473 | Palmer Mann, Jay Crowther, Ariel Perczek (submitted Nov 12, 2026; copied from the Claude doc)

## Recap

For reference, our project is a futures contract that pays $100 multiplied by CUT90 (our index that tracks the probability of a Fed cut within the next 90 days). Our aim, put simply, is to make a trader's life easier. Today, a trader has to roll Kalshi contracts by hand every six weeks instead of holding just one fixed position. Since "day 90" usually falls between two FOMC meetings, we take a weighted average of Kalshi's prices for those two meetings, favoring whichever is closer to day 90.

In Milestone 1, a portfolio built to track the index lost 274 points while the index rose 9 points. We hypothesized a few reasons then, and Jay has since figured out why: the market usually priced a cut as more likely at the later meeting, so the index drifts up as its weight shifts toward it, and no holder of the contracts earns that drift. A futures price builds that drift in up front, which is the main case for our product.

## Progress since Milestone 1

We finished most of what we planned.

On the data side, Palmer added Polymarket, which prices Fed decisions almost identically to Kalshi (about 2 points apart on average), so our choice of venue does not drive the results. The fed funds futures comparison is only partial: free data covers contracts listed from October 2026, so for earlier years we compare against the Atlanta Fed's market probability tracker instead.

Ari then tested whether someone who sells our future can hedge it by buying the two Kalshi contracts behind the index and holding them to expiry. Across 44 monthly expirations from 2023 to 2026, the hedge is exact whenever the Fed leaves rates unchanged. When the Fed moves, it misses by about $23 per $100 contract, usually in the seller's favor, and that rate-change analysis became our event study. Once fees are included, the real obstacle is cost: about $7.50 per round trip, mostly on the later meeting, which Palmer found trades on only 30% of days. The seller also ties up nearly the full $100 in collateral.

Jay showed the contract can settle cleanly: the Kalshi ladder allows a tradable arbitrage on only 12 of about 11,000 meeting-days. He also wrote the full contract spec, including an expiry rule that keeps FOMC decisions out of the settlement window. The settlement discount proved too small to measure at current spreads, so we will bound it instead.

## Are the final results ready?

Almost. The main findings will not change. Before we freeze results on Sunday, November 15, Palmer and Ari will settle how to price a wide order book on settlement days and rerun the backtest on the new expiry calendar, Jay will write up the pricing argument, and Ari will redo the 274-point breakdown on the final index. Monday is for the final report and presentation.

---
Sources for every number: `README.md` findings, `results/leg_liquidity.md`, `index/results/futures_backtest.md`,
`theory/results/noarb_summary.md`, `docs/spec.md` section 4.
