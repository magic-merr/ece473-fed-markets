# ECE 473: Constant-Maturity Event Futures

Palmer Mann, Jay Crowther, Ariel Perczek. Start with `CLAUDE.md` (repo map, owners, working rules),
then `docs/decisions/`, `docs/TASKS.md` and `docs/log/`.

**Product.** A fully collateralized futures contract that pays $100 x CUT90 at expiry. CUT90 is the
market's probability of a net Fed cut within the next 90 days, built by blending the Kalshi ladder
contracts for the two FOMC meetings around the 90-day mark (like the VIX blends two option expiries).
HIKE90 is the same for hikes. Definition: `docs/decisions/003-index-definition-and-interface.md`.

| Part | Folder | Status |
|---|---|---|
| Milestone 1: index, tracking backtest, draft contract | `index_m1/`, `docs/reports/milestone1/` | frozen; `cd index_m1 && python build_index.py && python make_figures.py` rebuilds every Milestone 1 number |
| Data layer: Kalshi / Polymarket / futures, stale rule, fees, liquidity | `src/`, `tests/`, `results/summary.md` | this README below |
| Final: index on the `src/` panel, futures pricing and backtest | `index/`, `docs/spec.md`, `docs/theory.md` | in progress, see `docs/TASKS.md` |

The two parts currently use different cleaning rules and sample starts; decision 002 settles which one
the final report uses.

---

# Data layer: Fed decision markets vs fed funds futures

Daily, meeting-level comparison of what Kalshi, Polymarket and the futures market price for each
FOMC decision, Feb 2023 onward, with a stale-price rule so thin markets don't pollute the comparison.

## Run

```bash
pip install -r requirements.txt
cd src
python pull_kalshi.py        # Kalshi markets, fee schedule, daily candles (bid/ask/trade/volume/OI)
python pull_polymarket.py    # Polymarket Fed decision markets: hourly prices, trades, fees
python pull_rates.py         # NY Fed EFFR + target range + SOFR, Yahoo ZQ futures, Atlanta Fed MPT
python panel.py              # build processed/panel.csv (one row per meeting x day x venue)
python compare.py            # results/*.csv + results/summary.md
python figures.py            # results/fig_*.png
python -m pytest ../tests    # unit + synthetic end-to-end tests
```

Pulls are cached: settled markets are not re-downloaded unless `--refresh` is passed.
Hosts used (all public, no keys): `api.elections.kalshi.com`, `gamma-api.polymarket.com`,
`clob.polymarket.com`, `data-api.polymarket.com`, `markets.newyorkfed.org`, `query1.finance.yahoo.com`,
`www.atlantafed.org`.

## What each venue contributes

| Venue | Markets | Price | Spread | Volume | Fees |
|---|---|---|---|---|---|
| Kalshi | `FED`/`KXFED` ladder ("upper bound above X%"), `FEDDECISION`/`KXFEDDECISION` (cut/hold/hike) | daily candle mid or last trade | yes, daily bid/ask | yes, daily + OI | series `fee_type` and `fee_multiplier`: taker 0.07·P(1−P), maker 0.0175·P(1−P) on maker-fee series, rounded up to the cent per order |
| Polymarket | "Fed decision in <month>?" buckets | CLOB price series (mid if spread ≤ 10c, else last trade) | live markets only (no historical books) | trade prints | taker only: 0.05·p(1−p) (Economics rate) on fee-enabled markets from 2026-03-30 (the Apr 2026 meeting onward), zero otherwise. The CLOB `base_fee` = 1000 is a flag, not the rate |
| Fed funds futures | ZQ contracts Yahoo still lists (Nov 2026 onward) | daily close | n/a | daily | n/a |
| Atlanta Fed MPT | SOFR-options-implied distribution of the 3-month average rate, quarterly windows | daily | n/a | n/a | n/a |

**Probability objects.**
- Bucket markets (Kalshi decision, Polymarket) give P(cut), P(hold), P(hike) directly, normalized by the sum of the bucket prices.
- The Kalshi ladder gives P(cut) = 1 − P(U > U₀ − 25bp) and P(hike) = P(U > U₀). This is only used for the next meeting, where U₀ (the current bound) is known.
- Whether the ladder references the upper or the lower bound is checked against every settled ladder market (`infer_ladder_offset`).
- Futures use the CME FedWatch method (`src/fedwatch.py`). Contract M prices the average EFFR in month M. The post-meeting rate comes from the next month's contract when that month has no meeting, and from the meeting-month contract otherwise. The expected change is then split between the two adjacent 25bp outcomes.

**Futures coverage caveat.** Yahoo drops expired ZQ contracts, so exact futures probabilities exist only for meetings priced by contracts that are still listed. That means the Oct 2026 meeting (resolved, from mid-Sep 2026) and Dec 2026 onward (live). For 2023–Sep 2026 the benchmark is the Atlanta Fed MPT. It describes the 3-month average SOFR over quarterly windows, not individual meetings, so it is compared to the Kalshi-implied expected rate path (`compare.mpt_compare`). It is not compared meeting by meeting. Dropping a Bloomberg ZQ export into `raw/rates/zq/` (same columns: `contract_month,date,close,volume`) upgrades the futures benchmark to every meeting with no code changes.

## Stale-price rule

All prices are taken as of the end of the ET day. A meeting is compared only on days strictly before its decision date, because the 2pm statement lands inside that day's candle and futures settlement.

Parameters: **N = 3 days**, **S = $0.10** (`src/config.py`). The sensitivity grid N ∈ {1, 3, 7} × S ∈ {0.05, 0.10, 0.20} is reported in `results/stale_rule_sensitivity.csv`.

**Kalshi**, per contract and day:
1. **Quote.** If the book is two-sided (bid > 0, ask < $1; Kalshi has quoted sub-cent ticks since 2025), the spread is ≤ S, and the quote changed within N days, use the **mid**.
2. **Bound.** Otherwise, if the book is pinned at the price boundary (no bid and ask ≤ 3¢, or no ask and bid ≥ 97¢) and it traded or was quoted within N days, use the **midpoint of the bounded interval** (ask/2 or (1+bid)/2). With a 1¢ tick, a tail "trading at 1¢" only means "worth ≤ 1¢". The toggle is `config.KALSHI_TICK_BOUND`, and results with it off are in the sensitivity table.
3. **Trade.** Otherwise, if a trade printed within N days, use the **last trade**.
4. **Stale.** Otherwise, the contract is not used that day.

Kalshi only emits a candle when something changes, so the latest candle's bid/ask is the standing quote and its date is the quote's last update.

**Polymarket.** The price series already applies the same mid-or-last-trade logic with S = 10c. Historical books aren't published, though, so quote freshness can't be verified. A Polymarket price is used only if the market **traded within N days**.

**Futures.** Use the latest close within N days.

**Aggregating contracts into one probability.** Far tails rarely trade, so two kinds of stale tail contract keep a value:
- one whose last usable price was ≤ 3c or ≥ 97c keeps that price;
- a Kalshi tail with a one-sided book pinned near zero or one (no bid and ask ≤ 3c, or no ask and bid ≥ 97c) is filled at the midpoint of that bound.

Any other stale input drops the venue for that meeting-day. `price_source_shares.csv` reports how often each branch fired.

## Findings (run of 2026-11-12, default rule N = 3, S = $0.10)

Sample: 40 FOMC meetings Feb 2023–Dec 2027 on Kalshi (31 resolved), 33 on Polymarket (29 resolved; usable prices for 28), futures for 5 (Oct 2026 resolved, Dec 2026–Apr 2027 live). Every settled Kalshi and Polymarket contract resolves consistently with the NY Fed target range (29/29 meetings on each venue, 346/346 Kalshi ladder markets).

- **Kalshi and Polymarket price the same thing almost identically.** Over 1,923 shared meeting-days, the mean absolute gap in P(hold) is 2.1pp and the expected-change correlation is 0.995. Within a week of the meeting, the P(hold) gap is 1.2pp and no day differs by more than 5pp. Disagreement grows with horizon: beyond 90 days, 25% of days differ by more than 5pp.
- **Kalshi's 1¢ tick floor biases its tails up.** Before 2025, Kalshi's long-shot buckets sat at "no bid / ask 1¢" and traded at 1¢, which is an upper bound and not a price. Valuing those books at the bound midpoint (the BOUND branch) cuts the Kalshi–Polymarket P(hold) bias from −1.2pp to −0.5pp and the 1-day Kalshi Brier score from 0.011 to 0.009. Without it, Kalshi looks systematically less confident than Polymarket on the eve of every meeting.
- **Accuracy is a tie.** On the 20–24 meetings both venues covered, Brier scores are 0.009 vs 0.007 (1 day), 0.028 vs 0.028 (7 days), 0.038 vs 0.036 (14 days) and 0.156 vs 0.152 (30 days), Kalshi vs Polymarket. The differences are well inside what 20–24 meetings can resolve.
- **Futures agree near the meeting and lean further out.** On Oct 2026 and the live meetings, futures-implied P(hold) is within about 2–3pp of the prediction markets inside 30 days. Beyond 90 days, futures put about 14pp more on a move: the two-point FedWatch split forces the expected change onto adjacent outcomes, and futures carry a term premium. Only one resolved meeting has futures coverage, so futures Brier scores are not meaningful.
- **Atlanta Fed MPT path.** On 275 days where the Kalshi ladder fully covers an MPT window, the Kalshi-implied 3-month average SOFR is 3bp below MPT for the nearest window (MAE 5.4bp, correlation 0.995).
- **Kalshi liquidity and costs.**
  - Decision contracts within a week of the meeting: median spread 1¢, taker fee 0.5¢, round trip (spread + 2 taker fees) 2.7¢, traded on 99% of days.
  - Beyond 90 days: median spread 6¢, round trip 8.8¢, traded on 23% of days.
  - Taker fees run about 3–5% of the contract price. Polymarket charged no fees on Fed markets before the Apr 2026 meeting, and 0.05·p(1−p) after.
- **Cross-venue gaps are mostly inside costs.** The same bucket on both venues differs by a median 0.4¢ (≤ 7 days) to 2¢ (> 90 days). The gap exceeds even a lower-bound trading cost plus 2¢ on only 2–3% of days within 90 days of a meeting, and on 14% beyond that.
- **Stale rule.**
  - Within a week of a meeting, 31% of Kalshi contract-days are stale: mostly far ladder strikes and tail buckets that haven't moved in weeks. On Polymarket, 14% are stale (no trade in 3 days).
  - Varying N from 1 to 7 days and S from 5¢ to 20¢ changes coverage (2,802–5,149 Kalshi meeting-days) but barely moves the comparison: the Kalshi–Polymarket P(hold) MAE stays at 1.9–2.2pp and Brier scores within ±0.002.

## Outputs

- `processed/panel.csv`: meeting, date, venue, p_cut, p_hold, p_hike, exp_change_bps, days_to_meeting. Venues: `kalshi` (the decision series when available, otherwise the ladder; `kalshi_source` records which), `kalshi_decision`, `kalshi_ladder`, `polymarket`, `zq`.
- `processed/kalshi_contract_daily.csv`: bid, ask, spread, mid, last trade, volume, OI, rule branch (quote / bound / trade / stale), taker/maker fee per contract and the rounded 1-lot fee.
- `processed/poly_contract_daily.csv`, `processed/outcomes.csv`, and `processed/kalshi_level_path.csv`. The level path is E[upper bound] from the Kalshi ladder's survival curve. The usable strikes must bracket the distribution (≥ 0.97 at the bottom, ≤ 0.03 at the top), and stale middle strikes are linearly interpolated (`n_interpolated`).
- `results/`:
  - `pairwise_agreement.csv`: MAE and bias in P(hold) and P(cut), RMSE of expected change, by horizon.
  - `accuracy_brier.csv`: three-outcome Brier score at 1/7/14/30/60 days, on each venue's own sample and on the common Kalshi∩Polymarket sample.
  - `kalshi_liquidity.csv`: spread, fees, round-trip cost, share of days traded, OI, by horizon.
  - `gap_vs_cost.csv`: Kalshi vs Polymarket gap on the same bucket versus a lower bound on the cost of trading it.
  - `mpt_path.csv`, `coverage.csv`, `summary.md`, `fig_*.png`.

## Known limits

- Yahoo rate-limits the shared cloud IP (HTTP 429). On this run the ZQ closes (Nov 2026–May 2027 contracts, from Jan 2026) were fetched through a browser and checked against per-contract row counts and checksums. Run `pull_rates.py` from your own machine to refresh them.

- Polymarket trades come from Data API v2 (`/v2/trades`, cursor pagination). v1 was retired. Full history is pulled; any market that stopped early is listed in `raw/polymarket/trades_truncated.csv` (none on the last run).
- Polymarket buckets are filtered to plain decision outcomes. Dissent-count side markets and meta markets are dropped, and when a meeting has two events the one with the most volume is kept (`raw/polymarket/markets_all.csv` keeps everything).
- Kalshi listed two events for a few meetings (e.g. FEDDECISION-24JAN and -24JAN31). The one with the most volume is kept.
- Kalshi fees use the current series schedule for every date. Polymarket fees are zero before 2026-03-30 and on markets not flagged fee-enabled.
- The cross-venue cost bound treats Polymarket's (unobserved) historical spread as zero, so it understates the true cost.
