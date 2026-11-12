# Milestone I Update: Constant Maturity Event Futures

ECE473 | Palmer Mann, Jay Crowther, Ariel Perczek  (submitted Oct 30, 2026; copied from the Claude doc)

## 1. Planned vs. Actual Progress

**Palmer (data).** *Planned:* pull all Kalshi Fed funds contracts since 2021 and matching Polymarket
markets, build the FOMC calendar, and assemble a clean daily dataset. *Done:* full Kalshi panel (41
meetings, 660 contracts, 110,885 contract-days), FED/KXFED tickers merged into one series, FOMC calendar
built, and cleaning rules set. Polymarket moved to Milestone II.

**Ari (index and backtest).** *Planned:* build the 90-day constant-maturity index and run a first
mid-price tracking backtest. *Done:* built CUT90 (95.8% coverage) and added HIKE90. Outside announcement
days, the tracking portfolio has 0.99 correlation and 0.32pp daily tracking error with the index; the
remaining gap is a mechanical roll term of about 26 bp/day.

**Jay (futures spec and theory).** *Planned:* draft the futures specification and start the continuity
proof. *Done:* drafted a fully collateralized contract ($100 max, 5-day average settlement) and wrote a
proof sketch that the index is continuous between announcements, which the daily data supports.

**Challenges.** About 35% of index observations use a stale price for at least one contract. One unit of
the tracking portfolio lost 274 probability points while the index rose 9, and we have not yet explained
the gap.

## 2. Remaining Work for Milestone II (11/12)

- **Palmer:** pull Polymarket data; collect spread, fee, and volume data; compare Kalshi with Polymarket
  and the index with fed funds futures.
- **Ari:** rerun the backtest with fees; estimate capital requirements; run an event study around FOMC
  meetings.
- **Jay:** estimate the settlement discount and decompose returns to explain the 274-point gap; check
  strike ladders for no-arbitrage violations; finalize settlement and collateral terms.

## 3. Refinements to Our Plan

- **Sample start:** main sample begins March 17, 2022, since a cut was impossible at a 0.25% upper bound.
  Robustness sample starts February 2, 2023.
- **HIKE90 added:** a cut-only index carries little information during hiking periods.
- **Decomposition:** returns will now separate the mechanical roll term from settlement-discount drift.
- **Polymarket** moved to Milestone II. Responsibilities are otherwise unchanged.

Note (11/12): the update says 110,885 contract-days; the panel and report say 100,885. 100,885 is correct.
