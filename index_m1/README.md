# ECE473 Milestone 1 data (Kalshi + FOMC calendar)

Pulled 2026-10-27 from the public Kalshi API. Polymarket is metadata only so far (see open items).

## data/
- `fomc_calendar.csv`: every scheduled FOMC meeting Jul 2021 to Jan 2028. `decision_ts_utc` = 2:00pm ET statement time. Matches Kalshi's own event dates for all 41 dated events. Nov 2021 meeting has no Kalshi contract.
- `kalshi_markets.csv`: one row per contract (660). Strike ladder "upper bound above X%" (series FED until Dec 2025, KXFED after). `result_yes` is the settled outcome.
- `kalshi_daily.csv` / `.parquet`: one row per contract per day (100,885 rows, 2021-07-02 to 2026-10-27).

## kalshi_daily columns
| column | meaning |
|---|---|
| date | ET calendar day the candle covers (Kalshi daily candles close at 00:00 ET) |
| candle_end_utc | raw candle close time |
| meeting_id, decision_date | FOMC meeting the contract settles on |
| market_ticker, strike | contract and its strike (pays 1 if upper bound > strike) |
| yes_bid, yes_ask | best bid/ask at candle close, in dollars |
| mid, spread | (bid+ask)/2 and ask-bid; raw, not filtered |
| two_sided | False when bid is 0 or ask is 1, i.e. mid is not a real quote |
| last_price, vwap_day | last trade and volume-weighted mean trade price that day (blank if no trades) |
| volume, open_interest | contracts traded that day, open interest at close |
| days_to_decision, tau_years | time to the 2pm ET announcement |
| post_decision | candle closes after the announcement (410 rows) |
| partial_day | today's candle, still forming |
| result_yes | settlement (blank for live contracts) |

## raw/ and scripts
- `raw/kalshi/`: API metadata dumps and per-contract daily candles; `raw/polymarket/decision_events.json`: 24 Polymarket "Fed decision" events (May 2024 onward) with token IDs.
- `build_dataset.py` rebuilds `data/` from `raw/`. `fetch_kalshi.py` / `fetch_polymarket.py` re-pull everything from scratch (stdlib Python, run from any normal internet connection).
