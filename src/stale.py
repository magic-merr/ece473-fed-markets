"""Daily price construction and the stale-price rule.

Everything is observed as of the END of an ET calendar day D (after the 2pm ET FOMC statement on a
meeting day, so comparisons use only days strictly before the decision date).

Stale-price rule (defaults in config: N = 3 days, S = 0.10)
------------------------------------------------------------
For contract c on day D, define
    last_trade(D)  = most recent day <= D with traded volume > 0, and its last trade price
    quote(D)       = latest yes bid / yes ask as of D (Kalshi candles are emitted only when something
                     changes, so the last candle's bid/ask is the standing quote), and the day it last changed
    two_sided      = bid > 0 and ask < 1 (Kalshi has quoted sub-cent ticks since 2025)
Kalshi
    1. QUOTE: if two_sided and (ask - bid) <= S and the quote changed within N days -> use the mid.
    2. BOUND: else if the book is pinned at the price boundary (no bid and ask <= 3c, or no ask and
              bid >= 97c) and it traded or was quoted within N days -> midpoint of the bounded interval
              (ask/2 or (1+bid)/2). With a 1c tick the last trade sits on the bound, so a tail that "trades
              at 1c" is really "<= 1c". Toggle: config.KALSHI_TICK_BOUND.
    3. TRADE: else if a trade printed within N days                                -> use the last trade.
    4. STALE: otherwise the price is not used (NaN).
Polymarket
    The CLOB price series is already "mid if spread <= 0.10, else last trade" (Polymarket's display rule),
    but historical books are not published, so quote age cannot be verified. A Polymarket price is used
    only if the market traded within N days; otherwise STALE.
Tail fill (used only when aggregating buckets/ladders into one probability)
    A stale contract whose last usable price was <= 0.03 or >= 0.97 keeps that price, since far tails
    rarely trade and dropping them would discard otherwise-good days. On Kalshi, a one-sided book pinned
    at a tail (no bid and ask <= 0.03, or no ask and bid >= 0.97) is filled with the midpoint of the
    bounded interval (ask/2, or (1+bid)/2). Any other stale input makes the aggregated probability NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ET = "America/New_York"
TAIL = 0.03


def kalshi_daily(c: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """Expand sparse daily candles to one row per ET day with carry-forward state."""
    if c.empty:
        return pd.DataFrame()
    c = c.copy()
    # A daily candle ending at ~00:00 ET on day D+1 covers day D. Kalshi steps boundaries by 24h, so
    # around DST changes the end can land at 23:00 or 01:00 ET; shifting back 12h is robust to both.
    c["date"] = (pd.to_datetime(c["end_period_ts"], unit="s", utc=True).dt.tz_convert(ET)
                 - pd.Timedelta(hours=12)).dt.date
    c = c.groupby("date").last()
    idx = pd.date_range(start or min(c.index), end or max(c.index), freq="D").date
    d = pd.DataFrame(index=pd.Index(idx, name="date"))
    d["volume"] = c["volume"].reindex(idx).fillna(0.0)
    d["bid"] = c["yes_bid_close"].reindex(idx).ffill()
    d["ask"] = c["yes_ask_close"].reindex(idx).ffill()
    d["oi"] = c["open_interest"].reindex(idx).ffill()
    upd = pd.Series(pd.to_datetime(c.index), index=c.index).reindex(idx).ffill()
    d["quote_age"] = (pd.to_datetime(pd.Series(idx, index=idx)) - upd).dt.days
    traded = c[c["volume"] > 0]
    lt = traded["price_close"].reindex(idx).ffill()
    ltd = pd.Series(pd.to_datetime(traded.index), index=traded.index).reindex(idx).ffill()
    d["last_trade"] = lt
    d["trade_age"] = (pd.to_datetime(pd.Series(idx, index=idx)) - ltd).dt.days
    return d


def apply_kalshi_rule(d: pd.DataFrame, n_days: int, max_spread: float, tick_bound: bool = True) -> pd.DataFrame:
    d = d.copy()
    two_sided = (d["bid"] > 0) & (d["ask"] < 1)   # Kalshi quotes sub-cent ticks since 2025
    d["spread"] = np.where(two_sided, d["ask"] - d["bid"], np.nan)
    d["mid"] = np.where(two_sided, (d["ask"] + d["bid"]) / 2, np.nan)
    quote_ok = two_sided & (d["spread"] <= max_spread + 1e-9) & (d["quote_age"] <= n_days)
    trade_ok = d["trade_age"] <= n_days
    fresh = (d["quote_age"] <= n_days) | trade_ok
    pin_lo = (d["bid"].fillna(0) <= 0) & (d["ask"] <= TAIL) & fresh
    pin_hi = (d["ask"].fillna(1) >= 1) & (d["bid"] >= 1 - TAIL) & fresh
    bound_ok = (pin_lo | pin_hi) & tick_bound
    bound_px = np.where(pin_lo, d["ask"] / 2, (1 + d["bid"]) / 2)
    d["price"] = np.where(quote_ok, d["mid"], np.where(bound_ok, bound_px,
                          np.where(trade_ok, d["last_trade"], np.nan)))
    d["source"] = np.where(quote_ok, "quote", np.where(bound_ok, "bound", np.where(trade_ok, "trade", "stale")))
    # last price that was ever usable, for the tail-fill exception
    d["last_usable"] = pd.Series(d["price"].values, index=d.index).ffill()
    return d


def poly_daily(prices: pd.DataFrame, trades: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()
    p = prices.copy()
    p["date"] = pd.to_datetime(p["t"], unit="s", utc=True).dt.tz_convert(ET).dt.date
    p = p.sort_values("t").groupby("date")["p"].last()
    idx = pd.date_range(start or min(p.index), end or max(p.index), freq="D").date
    d = pd.DataFrame(index=pd.Index(idx, name="date"))
    d["display"] = p.reindex(idx).ffill()
    if trades is not None and not trades.empty:
        t = trades.copy()
        t["date"] = pd.to_datetime(t["ts"], unit="s", utc=True).dt.tz_convert(ET).dt.date
        g = t.sort_values("ts").groupby("date")
        vol = g["size"].sum()
        d["volume"] = vol.reindex(idx).fillna(0.0)
        d["notional"] = (t.assign(n=t["size"] * t["yes_price"]).groupby("date")["n"].sum()
                         .reindex(idx).fillna(0.0))
        d["last_trade"] = g["yes_price"].last().reindex(idx).ffill()
        ltd = pd.Series(pd.to_datetime(vol.index), index=vol.index).reindex(idx).ffill()
        d["trade_age"] = (pd.to_datetime(pd.Series(idx, index=idx)) - ltd).dt.days
    else:
        d["volume"], d["notional"], d["last_trade"], d["trade_age"] = 0.0, 0.0, np.nan, np.nan
    return d


def apply_poly_rule(d: pd.DataFrame, n_days: int) -> pd.DataFrame:
    d = d.copy()
    ok = d["trade_age"] <= n_days
    d["price"] = np.where(ok, d["display"], np.nan)
    d["source"] = np.where(ok, "trade", "stale")
    d["last_usable"] = pd.Series(d["price"].values, index=d.index).ffill()
    return d


def tail_filled(price: pd.Series, last_usable: pd.Series, bid: pd.Series | None = None,
                ask: pd.Series | None = None) -> pd.Series:
    fill = last_usable.where((last_usable <= TAIL) | (last_usable >= 1 - TAIL))
    out = price.fillna(fill)
    if bid is not None and ask is not None:
        # one-sided book pinned at a tail: no bid and ask <= 3c (or no ask and bid >= 97c) bounds the price
        lo = ((bid.fillna(0) <= 0) & (ask <= TAIL)).fillna(False)
        hi = ((ask.fillna(1) >= 1) & (bid >= 1 - TAIL)).fillna(False)
        out = out.fillna(pd.Series(np.where(lo, ask / 2, np.where(hi, (1 + bid) / 2, np.nan)), index=out.index))
    return out
