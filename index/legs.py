"""Daily prices for every Kalshi ladder contract, from the committed Milestone 1 pull.

Inputs (committed, nothing is re-pulled):
  index_m1/data/kalshi_markets.csv          660 FED/KXFED contracts "upper bound above K after meeting m"
  index_m1/raw/kalshi/candles{,_live}/*.csv daily candles (same columns src/pull_kalshi.py writes)
  index_m1/data/kalshi_daily.parquet        only used to find the last complete day of the pull
  index_m1/data/realized_upper_bound.csv    upper bound after each meeting, from settled ladders
  index_m1/data/fomc_calendar.csv           scheduled decision dates

Two price rules, so the final tables can show what the cleaning rule changes (decision 002):
  "src"  Palmer's data-layer rule (src/stale.py): quote -> bound -> trade -> stale, N = 3 days,
         S = $0.10, tick-floor bound on, plus the tail fill used for aggregation. Proposed for the final
         report in decision 002.
  "m1"   the Milestone 1 rule (index_m1/build_index.py): mid if spread <= $0.10, else missing; last mid
         carried forward up to 10 days.
Execution always uses the standing Kalshi book (last observed bid/ask), whatever the index rule.
"""
from __future__ import annotations

import datetime as dt
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import panel as P  # noqa: E402  (Palmer's data layer: strike_eff, fee constants)
import stale  # noqa: E402
from config import KALSHI_TAKER_RATE, KALSHI_TICK_BOUND, STALE_MAX_SPREAD, STALE_N_DAYS  # noqa: E402

M1 = ROOT / "index_m1"
M1_MAXFILL, M1_MAXSPREAD = 10, 0.10


# ---------------------------------------------------------------- calendar and rate path
@lru_cache(maxsize=None)
def fomc_dates() -> tuple:
    cal = pd.read_csv(M1 / "data" / "fomc_calendar.csv", parse_dates=["decision_date"])
    return tuple(sorted(cal["decision_date"].dt.date))


@lru_cache(maxsize=None)
def meeting_ids() -> dict:
    cal = pd.read_csv(M1 / "data" / "fomc_calendar.csv", parse_dates=["decision_date"])
    return dict(zip(cal["decision_date"].dt.date, cal["meeting_id"]))


@lru_cache(maxsize=None)
def rate_path() -> pd.DataFrame:
    """Upper bound after each decision (inferred from settled ladders in Milestone 1)."""
    p = pd.read_csv(M1 / "data" / "realized_upper_bound.csv", parse_dates=["decision_date"])
    p["decision_date"] = p["decision_date"].dt.date
    return p.sort_values("decision_date").reset_index(drop=True)


@lru_cache(maxsize=None)
def data_end() -> dt.date:
    """Last complete day in the pull (the pull day's own candle is still forming)."""
    d = pd.read_parquet(M1 / "data" / "kalshi_daily.parquet", columns=["date", "partial_day"])
    return pd.to_datetime(d.loc[~d["partial_day"], "date"]).max().date()


# ---------------------------------------------------------------- contracts
@lru_cache(maxsize=None)
def markets() -> pd.DataFrame:
    mk = pd.read_csv(M1 / "data" / "kalshi_markets.csv", parse_dates=["decision_date"])
    mk = mk.dropna(subset=["decision_date", "strike"]).copy()
    mk["meeting"] = mk["decision_date"].dt.date
    # every subtitle is ">K%": strike type "greater" on the 25bp grid, normalized as in src/panel.py
    mk["strike_eff"] = [P.strike_eff(s, "greater") for s in mk["strike"]]
    return mk


def _candles(ticker: str) -> pd.DataFrame:
    for d in ("candles", "candles_live"):
        f = M1 / "raw" / "kalshi" / d / f"{ticker}.csv"
        if f.exists():
            return pd.read_csv(f)
    return pd.DataFrame()


@lru_cache(maxsize=None)
def contract_days(rule: str = "src", n_days: int = STALE_N_DAYS, max_spread: float = STALE_MAX_SPREAD,
                  tick_bound: bool = KALSHI_TICK_BOUND) -> pd.DataFrame:
    """One row per contract-day up to the day before its meeting: index price (`value`, YES side, NaN if
    unusable under `rule`), standing yes bid/ask, quote age, and the price source."""
    end_all = data_end()
    out = []
    for m in markets().itertuples(index=False):
        c = _candles(m.market_ticker)
        if c.empty:
            continue
        end = min(m.meeting - dt.timedelta(days=1), end_all)
        d = stale.kalshi_daily(c, end=end)
        if d.empty:
            continue
        d = d[d.index <= end]
        if d.empty:
            continue
        r = stale.apply_kalshi_rule(d, n_days, max_spread, tick_bound)
        if rule == "src":
            val = stale.tail_filled(r["price"], r["last_usable"], r["bid"], r["ask"])
            src = np.where(r["price"].notna(), r["source"], np.where(val.notna(), "tailfill", "stale"))
        elif rule == "m1":
            # Milestone 1: mid of a quote with spread <= 0.10 on days a candle printed, carried <= 10 days
            ok = (r["quote_age"] == 0) & (r["ask"] - r["bid"] <= M1_MAXSPREAD + 1e-9)
            mid = ((r["bid"] + r["ask"]) / 2).where(ok)
            val = mid.ffill(limit=M1_MAXFILL)
            src = np.where(mid.notna(), "quote", np.where(val.notna(), "carried", "stale"))
        else:
            raise ValueError(rule)
        out.append(pd.DataFrame({
            "date": r.index, "ticker": m.market_ticker, "series": m.series, "meeting": m.meeting,
            "strike": m.strike_eff, "value": val.to_numpy(float), "source": src,
            "bid": r["bid"].to_numpy(float), "ask": r["ask"].to_numpy(float),
            "quote_age": r["quote_age"].to_numpy(float), "volume": r["volume"].to_numpy(float),
            "result_yes": m.result_yes}))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- lookup
class Book:
    """(meeting, strike) -> {date: (yes_value, yes_bid, yes_ask, source, quote_age)}."""

    def __init__(self, cd: pd.DataFrame, taker_rate: float = KALSHI_TAKER_RATE):
        self.data = {}
        for (m, s), g in cd.groupby(["meeting", "strike"]):
            self.data[(m, round(float(s), 4))] = dict(zip(
                g["date"], zip(g["value"].to_numpy(float), g["bid"].to_numpy(float), g["ask"].to_numpy(float),
                               g["source"], g["quote_age"].to_numpy(float))))
        self.taker_rate = taker_rate

    def get(self, m, k, d):
        return self.data.get((m, round(float(k), 4)), {}).get(d)


@lru_cache(maxsize=None)
def book(rule: str = "src") -> Book:
    return Book(contract_days(rule))
