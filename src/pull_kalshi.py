"""Pull Kalshi Fed markets: market metadata, series fee schedules, and daily candles (bid/ask/trade/volume/OI).

Outputs
  raw/kalshi/series_fees.csv           one row per series: fee_type, fee_multiplier
  raw/kalshi/markets.csv               one row per market (both live and historical tiers)
  raw/kalshi/candles/{TICKER}.csv      daily candles, same columns as the existing project files

Kalshi splits data into live and historical tiers (GET /historical/cutoff); markets that settled before
the cutoff, and their candles, are only served by the /historical/* endpoints. Both are queried.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

import pandas as pd

from config import (KALSHI_API, KALSHI_CANDLES, KALSHI_DECISION_SERIES, KALSHI_LEVEL_SERIES, KALSHI_RAW,
                    MONTHS, SAMPLE_START, meeting_for_month)
from http_util import get

CANDLE_COLS = ["end_period_ts", "yes_bid_close", "yes_ask_close", "price_close", "price_mean", "volume",
               "open_interest"]
EVENT_RE = re.compile(r"^(?:KX)?FED(?:DECISION)?-(\d{2})([A-Z]{3})")


def meeting_from_event(event_ticker: str):
    m = EVENT_RE.match(event_ticker or "")
    if not m:
        return None
    year, mon = 2000 + int(m.group(1)), m.group(2)
    if mon not in MONTHS:
        return None
    return meeting_for_month(year, MONTHS.index(mon) + 1)


def _ts(x):
    if x in (None, ""):
        return None
    return int(pd.Timestamp(x).timestamp())


def _dollar(d: dict | None, key: str):
    """Kalshi price formats: live tier `close_dollars` ("0.8600"); historical tier `close` as a dollar
    string ("0.9800"); legacy `close` as integer cents (98)."""
    if not d:
        return None
    v = d.get(f"{key}_dollars")
    if v not in (None, ""):
        return float(v)
    v = d.get(key)
    if v in (None, ""):
        return None
    return float(v) if isinstance(v, str) else float(v) / 100.0


def _num(c: dict, key: str):
    v = c.get(f"{key}_fp", c.get(key))
    return None if v in (None, "") else float(v)


def parse_candle(c: dict) -> dict:
    return {
        "end_period_ts": int(c["end_period_ts"]),
        "yes_bid_close": _dollar(c.get("yes_bid"), "close"),
        "yes_ask_close": _dollar(c.get("yes_ask"), "close"),
        "price_close": _dollar(c.get("price"), "close"),
        "price_mean": _dollar(c.get("price"), "mean"),
        "volume": _num(c, "volume") or 0.0,
        "open_interest": _num(c, "open_interest"),
    }


def paginate(path: str, params: dict, key: str) -> list[dict]:
    out, cursor = [], None
    while True:
        p = dict(params, limit=1000)
        if cursor:
            p["cursor"] = cursor
        j = get(KALSHI_API + path, p)
        if not j:
            break
        out.extend(j.get(key) or [])
        cursor = j.get("cursor")
        if not cursor:
            break
    return out


def pull_series_fees(series: list[str]) -> pd.DataFrame:
    rows = []
    for s in series:
        j = get(f"{KALSHI_API}/series/{s}")
        if not j or "series" not in j:
            print(f"  series {s}: not found", file=sys.stderr)
            continue
        se = j["series"]
        rows.append({"series": s, "title": se.get("title"), "fee_type": se.get("fee_type"),
                     "fee_multiplier": se.get("fee_multiplier"), "last_updated_ts": se.get("last_updated_ts")})
    return pd.DataFrame(rows)


def pull_markets(series: list[str]) -> pd.DataFrame:
    rows = []
    for s in series:
        live = paginate("/markets", {"series_ticker": s}, "markets")
        hist = paginate("/historical/markets", {"series_ticker": s}, "markets")
        print(f"  {s}: {len(live)} live-tier markets, {len(hist)} historical-tier markets")
        for tier, ms in (("live", live), ("historical", hist)):
            for m in ms:
                meet = meeting_from_event(m.get("event_ticker", ""))
                rows.append({
                    "series": s, "tier": tier, "ticker": m["ticker"], "event_ticker": m.get("event_ticker"),
                    "meeting": meet, "status": m.get("status"), "result": m.get("result"),
                    "open_time": m.get("open_time"), "close_time": m.get("close_time"),
                    "strike_type": m.get("strike_type"), "floor_strike": m.get("floor_strike"),
                    "cap_strike": m.get("cap_strike"), "yes_sub_title": m.get("yes_sub_title"),
                    "subtitle": m.get("subtitle"), "title": m.get("title"),
                    "volume": m.get("volume_fp", m.get("volume")),
                    "open_interest": m.get("open_interest_fp", m.get("open_interest")),
                })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # A market can appear in both tiers around the cutoff: keep the historical copy (it is final).
    df = df.sort_values("tier").drop_duplicates("ticker", keep="first")
    df = df[df["meeting"].notna() & (pd.to_datetime(df["meeting"]) >= pd.Timestamp(SAMPLE_START))]
    return df.reset_index(drop=True)


def pull_candles(m: pd.Series, refresh: bool) -> int:
    path = KALSHI_CANDLES / f"{m.ticker}.csv"
    settled = m.status in ("settled", "finalized", "determined") or m.tier == "historical"
    if path.exists() and settled and not refresh:
        return -1
    start = _ts(m.open_time) or int(pd.Timestamp(SAMPLE_START).timestamp())
    end = min(_ts(m.close_time) or 2**31, int(dt.datetime.now(dt.timezone.utc).timestamp()))
    if m.tier == "historical":
        url = f"{KALSHI_API}/historical/markets/{m.ticker}/candlesticks"
    else:
        url = f"{KALSHI_API}/series/{m.series}/markets/{m.ticker}/candlesticks"
    rows, step = [], 4000 * 86400  # stay under the per-request candle cap
    for a in range(start, end + 1, step):
        j = get(url, {"start_ts": a, "end_ts": min(a + step, end + 86400), "period_interval": 1440})
        for c in (j or {}).get("candlesticks") or []:
            rows.append(parse_candle(c))
    df = pd.DataFrame(rows, columns=CANDLE_COLS).drop_duplicates("end_period_ts").sort_values("end_period_ts")
    df.to_csv(path, index=False, float_format="%.4f")
    return len(df)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-pull candles even for settled markets")
    ap.add_argument("--series", nargs="*", default=KALSHI_LEVEL_SERIES + KALSHI_DECISION_SERIES)
    a = ap.parse_args(argv)
    KALSHI_CANDLES.mkdir(parents=True, exist_ok=True)

    cutoff = get(f"{KALSHI_API}/historical/cutoff")
    print("historical cutoff:", cutoff)
    fees = pull_series_fees(a.series)
    fees.to_csv(KALSHI_RAW / "series_fees.csv", index=False)
    print(fees.to_string(index=False))

    mk = pull_markets(a.series)
    mk.to_csv(KALSHI_RAW / "markets.csv", index=False)
    print(f"{len(mk)} markets across {mk['meeting'].nunique() if len(mk) else 0} meetings")

    n_new = 0
    for i, m in enumerate(mk.itertuples(index=False), 1):
        n = pull_candles(m, a.refresh)
        n_new += n >= 0
        if i % 50 == 0:
            print(f"  candles {i}/{len(mk)}")
    print(f"candles written for {n_new} markets (cached: {len(mk) - n_new})")


if __name__ == "__main__":
    main()
