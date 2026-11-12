"""Build the daily meeting-level probability panel across venues.

Outputs (processed/)
  kalshi_contract_daily.csv   one row per Kalshi contract-day: bid, ask, spread, mid, last trade, volume, OI,
                              rule source (quote / trade / stale), usable price, taker & maker fee at the price
  poly_contract_daily.csv     one row per Polymarket bucket-day: display price, trades, volume, rule source, fee
  outcomes.csv                realized decision per meeting (from NY Fed target range)
  panel.csv                   one row per (meeting, date, venue): p_cut, p_hold, p_hike, exp_change_bps
                              venues: kalshi_decision, kalshi_ladder, kalshi (decision if available else
                              ladder), polymarket, zq (FedWatch method on Yahoo futures)
  kalshi_level_path.csv       E[upper bound after meeting] from the Kalshi ladder, any horizon (for MPT)
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

import fedwatch
from config import (KALSHI_TICK_BOUND, FOMC_DATES, KALSHI_CANDLES, KALSHI_DECISION_SERIES, KALSHI_MAKER_RATE, KALSHI_RAW,
                    KALSHI_TAKER_RATE, POLY_FALLBACK_TAKER_RATE, POLY_FEE_START, POLY_RAW, PROCESSED,
                    RATES_RAW, STALE_MAX_SPREAD, STALE_N_DAYS)
from pull_polymarket import parse_bucket
from stale import (apply_kalshi_rule, apply_poly_rule, kalshi_daily, poly_daily, tail_filled)

TODAY = dt.date.today()


# ---------------------------------------------------------------- helpers
def kalshi_bucket(ticker: str, sub: str | None):
    """Decision bucket from the market subtitle ('Cut 25bps', 'Hike >25bps', 'Hike 0bps', 'No change'),
    which is authoritative; ticker suffixes are inconsistent across years (C26, C>25, TC25, even C24 for
    'Cut >25bps'). 'More than k' -> magnitude k+25, open-ended. Ticker is only a fallback."""
    s = (sub or "").lower()
    if re.search(r"\bno (cut|change|hike|move)|\bhold\b|unchanged|maintain", s):
        return 0, False
    g = re.search(r"(cut|hike)\s*(>)?\s*(\d+)", s)
    if g:
        sign, k = (-1 if g.group(1) == "cut" else 1), int(g.group(3))
        if k == 0:
            return 0, False
        return (sign * (k + 25), True) if g.group(2) else (sign * k, False)
    if s:
        b = parse_bucket(s)
        if b is not None:
            return b
    m = re.search(r"-(T)?(H|C)(>)?(\d+)$", ticker or "")
    if m:
        above, sign, k = bool(m.group(1) or m.group(3)), (1 if m.group(2) == "H" else -1), int(m.group(4))
        if k == 0:
            return 0, False
        if above:
            return sign * (k + 25), True
        if k % 25 == 0:
            return sign * k, False
        return sign * (k // 25 + 1) * 25, True
    return None


def dedupe_events(mk: pd.DataFrame) -> pd.DataFrame:
    """Kalshi occasionally listed two events for one meeting (e.g. FEDDECISION-24JAN and -24JAN31).
    Keep, per meeting and market type, the event with the most volume."""
    mk = mk.copy()
    mk["kind"] = np.where(mk["series"].isin(KALSHI_DECISION_SERIES), "decision", "level")
    vol = (mk.assign(v=pd.to_numeric(mk["volume"], errors="coerce").fillna(0))
           .groupby(["kind", "meeting", "event_ticker"])["v"].sum().reset_index())
    keep = vol.sort_values("v").drop_duplicates(["kind", "meeting"], keep="last")[["kind", "meeting", "event_ticker"]]
    return mk.merge(keep, on=["kind", "meeting", "event_ticker"]).drop(columns="kind")


def kalshi_fee_rates(fees: pd.DataFrame) -> dict[str, tuple[float, float]]:
    out = {}
    for r in fees.itertuples(index=False):
        mult = float(r.fee_multiplier) if pd.notna(r.fee_multiplier) else 1.0
        maker = KALSHI_MAKER_RATE if "maker" in str(r.fee_type) else 0.0
        out[r.series] = (KALSHI_TAKER_RATE * mult, maker * mult)
    return out


def strike_eff(s, stype):
    """Normalize a Kalshi strike to an equivalent 'upper > g' statement on the 25 bp grid."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return np.nan
    s = float(s)
    if str(stype) == "greater_or_equal":
        return math.ceil(round(s / 0.25, 6)) * 0.25 - 0.25
    return math.floor(round(s / 0.25, 6)) * 0.25


def strike_from(m):
    """floor_strike is blank on some older markets; fall back to the ticker suffix (-T4.00 = 'above 4.00%')."""
    if pd.notna(m.floor_strike):
        return m.floor_strike, m.strike_type
    t = re.search(r"-T(\d+(?:\.\d+)?)$", m.ticker or "")
    return (float(t.group(1)), "greater") if t else (np.nan, None)


def infer_ladder_offset(kc: pd.DataFrame, oc: pd.DataFrame) -> float:
    """Kalshi level markets reference either the upper or the lower bound of the target range.
    Pick the one that reproduces every settled result: 0.0 = upper bound, -0.25 = lower bound."""
    lv = kc[(kc["kind"] == "level") & kc["result"].isin(["yes", "no"])].drop_duplicates("ticker")
    lv = lv.merge(oc[["meeting", "post_upper"]], on="meeting")
    if lv.empty:
        return 0.0
    score = {}
    for off in (0.0, -0.25):
        pred = np.where(lv["post_upper"] + off > lv["strike"] + 1e-9, "yes", "no")
        score[off] = (pred == lv["result"]).mean()
    best = max(score, key=score.get)
    print(f"ladder reference check: upper-bound match {score[0.0]:.1%}, lower-bound match {score[-0.25]:.1%}"
          f" ({len(lv)} settled level markets)")
    return best


def ceil_cent(x):
    return np.ceil(np.round(x * 100, 9)) / 100


def load_effr() -> pd.DataFrame:
    e = pd.read_csv(RATES_RAW / "effr.csv", parse_dates=["date"])
    e["date"] = e["date"].dt.date
    return e.sort_values("date").set_index("date")


def asof(series: pd.Series, d: dt.date, strict: bool = False):
    s = series[series.index < d] if strict else series[series.index <= d]
    return s.iloc[-1] if len(s) else np.nan


def outcomes(effr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for m in FOMC_DATES:
        if m >= TODAY or m < effr.index.min():
            continue
        pre = asof(effr["target_hi"], m)
        after = effr[effr.index > m]
        if after.empty:
            continue
        post = after["target_hi"].iloc[0]
        ch = int(round((post - pre) * 100))
        rows.append({"meeting": m, "pre_upper": pre, "post_upper": post, "change_bps": ch,
                     "decision": "cut" if ch < 0 else ("hike" if ch > 0 else "hold")})
    return pd.DataFrame(rows)


def next_meeting(d: dt.date):
    return next((m for m in FOMC_DATES if m > d), None)


# ---------------------------------------------------------------- Kalshi
def kalshi_contracts(n_days: int, max_spread: float, tick_bound: bool = KALSHI_TICK_BOUND) -> pd.DataFrame:
    mk = pd.read_csv(KALSHI_RAW / "markets.csv", parse_dates=["meeting"])
    mk["meeting"] = mk["meeting"].dt.date
    mk = dedupe_events(mk)
    fees = kalshi_fee_rates(pd.read_csv(KALSHI_RAW / "series_fees.csv"))
    out = []
    for m in mk.itertuples(index=False):
        f = KALSHI_CANDLES / f"{m.ticker}.csv"
        if not f.exists():
            continue
        c = pd.read_csv(f)
        if c.empty:
            continue
        end = min(m.meeting - dt.timedelta(days=1), TODAY)
        d = kalshi_daily(c, end=end)
        if d.empty:
            continue
        d = d[d.index <= end]
        d = apply_kalshi_rule(d, n_days, max_spread, tick_bound)
        is_dec = m.series in KALSHI_DECISION_SERIES
        b = kalshi_bucket(m.ticker, m.yes_sub_title) if is_dec else None
        taker, maker = fees.get(m.series, (KALSHI_TAKER_RATE, 0.0))
        d = d.reset_index().assign(
            ticker=m.ticker, series=m.series, kind="decision" if is_dec else "level", meeting=m.meeting,
            strike=np.nan if is_dec else strike_eff(*strike_from(m)), strike_type=m.strike_type,
            result=m.result,
            bps=b[0] if b else np.nan, open_ended=b[1] if b else np.nan)
        p = d["price"]
        d["fee_taker"] = taker * p * (1 - p)                 # per contract, exact
        d["fee_maker"] = maker * p * (1 - p)
        d["fee_taker_1lot"] = ceil_cent(taker * p * (1 - p))  # what one contract actually pays (rounded up)
        out.append(d)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def aggregate_buckets(df: pd.DataFrame, venue: str) -> pd.DataFrame:
    """Bucket markets (cut/hold/hike) -> one probability vector per meeting-day."""
    rows = []
    for (meet, date), g in df.dropna(subset=["bps"]).groupby(["meeting", "date"]):
        px = tail_filled(g["price"], g["last_usable"], g.get("bid"), g.get("ask"))
        if px.isna().any() or not (g["bps"] == 0).any():
            continue
        bps = g["bps"].astype(float)
        tot = px.sum()
        if tot <= 0:
            continue
        rows.append({"meeting": meet, "date": date, "venue": venue,
                     "p_cut": px[bps < 0].sum() / tot, "p_hold": px[bps == 0].sum() / tot,
                     "p_hike": px[bps > 0].sum() / tot, "exp_change_bps": (px * bps).sum() / tot,
                     "sum_raw": tot, "n_contracts": len(g),
                     "n_stale_filled": int(g["price"].isna().sum())})
    return pd.DataFrame(rows)


def ladder(df: pd.DataFrame, effr: pd.DataFrame, offset: float = 0.0):
    """Threshold ladder 'upper bound > s' -> decision probs (next meeting only) and E[upper] (any horizon)."""
    dec_rows, lvl_rows = [], []
    lv = df[(df["kind"] == "level") & df["strike"].notna()]
    for (meet, date), g in lv.groupby(["meeting", "date"]):
        g = g.sort_values("strike")
        px = tail_filled(g["price"], g["last_usable"], g["bid"], g["ask"])
        s = g["strike"].to_numpy(float)
        ok = px.notna().to_numpy()
        # E[upper] from the survival curve P(U > s). The usable strikes must bracket the distribution
        # (lowest usable >= 0.97, highest usable <= 0.03); stale strikes in between are interpolated.
        su, pu = s[ok], px.to_numpy(float)[ok]
        if len(su) >= 3 and pu[0] >= 0.97 and pu[-1] <= 0.03:
            pu = np.minimum.accumulate(pu)                          # enforce monotone survival
            grid = np.arange(su[0], su[-1] + 1e-9, 0.25)
            surv = np.interp(grid, su, pu)
            lvl_rows.append({"meeting": meet, "date": date, "exp_upper": grid[0] - offset + 0.25 * surv.sum(),
                             "n_strikes": len(grid), "n_interpolated": len(grid) - len(su)})
        if next_meeting(date) != meet:
            continue
        u0 = asof(effr["target_hi"], date) + offset   # current level of the referenced bound
        if not np.isfinite(u0):
            continue

        def surv_at(k):
            j = np.where(np.abs(s - k) < 0.02)[0]
            return px.iloc[j[0]] if len(j) else np.nan
        p_gt_lo, p_gt_u0 = surv_at(u0 - 0.25), surv_at(u0)
        if not (np.isfinite(p_gt_lo) and np.isfinite(p_gt_u0)):
            continue
        p_gt_u0 = min(p_gt_u0, p_gt_lo)
        p_gt_hi = surv_at(u0 + 0.25)
        p_lt_lo = surv_at(u0 - 0.50)
        exp_ch = 25 * (p_gt_u0 + (p_gt_hi if np.isfinite(p_gt_hi) else 0)
                       - (1 - p_gt_lo) - ((1 - p_lt_lo) if np.isfinite(p_lt_lo) else 0))
        dec_rows.append({"meeting": meet, "date": date, "venue": "kalshi_ladder", "p_cut": 1 - p_gt_lo,
                         "p_hold": p_gt_lo - p_gt_u0, "p_hike": p_gt_u0, "exp_change_bps": exp_ch,
                         "sum_raw": 1.0, "n_contracts": len(g), "n_stale_filled": int(g["price"].isna().sum())})
    return pd.DataFrame(dec_rows), pd.DataFrame(lvl_rows)


# ---------------------------------------------------------------- Polymarket
def poly_contracts(n_days: int) -> pd.DataFrame:
    p = POLY_RAW / "markets.csv"
    if not p.exists():
        return pd.DataFrame()
    mk = pd.read_csv(p, parse_dates=["meeting"], dtype={"yes_token": str, "no_token": str})
    mk["meeting"] = mk["meeting"].dt.date
    fees = pd.read_csv(POLY_RAW / "fees.csv", dtype={"yes_token": str}) if (POLY_RAW / "fees.csv").exists() else None
    out = []
    for m in mk.itertuples(index=False):
        pf, tf = POLY_RAW / "prices" / f"{m.condition_id}.csv", POLY_RAW / "trades" / f"{m.condition_id}.csv"
        if not pf.exists():
            continue
        pr = pd.read_csv(pf)
        tr = pd.read_csv(tf) if tf.exists() else pd.DataFrame()
        if pr.empty:
            continue
        end = min(m.meeting - dt.timedelta(days=1), TODAY)
        d = poly_daily(pr, tr, end=end)
        d = apply_poly_rule(d[d.index <= end], n_days).reset_index()
        # Fee = C x feeRate x p(1-p), taker only (Polymarket fee docs). The CLOB /fee-rate `base_fee`
        # (1000 on fee-enabled markets) is a flag, not the rate; Fed decisions are Economics: 0.05.
        fe = getattr(m, "fees_enabled", None)
        enabled = bool(fe) if fe is not None and pd.notna(fe) else False
        if fees is not None:
            fr = fees.loc[fees["condition_id"] == m.condition_id, "fee_rate_raw"]
            enabled = enabled or (len(fr) > 0 and pd.notna(fr.iloc[0]) and float(fr.iloc[0]) > 0)
        rate = POLY_FALLBACK_TAKER_RATE if enabled else 0.0
        on = pd.to_datetime(d["date"]).dt.date >= POLY_FEE_START
        d["fee_taker"] = np.where(on, rate * d["price"] * (1 - d["price"]), 0.0)
        d = d.assign(condition_id=m.condition_id, meeting=m.meeting, bps=m.bps, open_ended=m.open_ended,
                     label=m.label)
        out.append(d)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


# ---------------------------------------------------------------- ZQ
def zq_panel(effr: pd.DataFrame, n_days: int) -> pd.DataFrame:
    zdir = RATES_RAW / "zq"
    files = sorted(zdir.glob("ZQ*.csv")) if zdir.exists() else []
    if not files:
        return pd.DataFrame()
    fut = {}
    for f in files:
        z = pd.read_csv(f, parse_dates=["date", "contract_month"])
        cm = z["contract_month"].iloc[0].date()
        fut[cm] = z.assign(date=z["date"].dt.date).set_index("date")["close"]
    all_dates = sorted(set().union(*[s.index for s in fut.values()]))
    rows = []
    for d in all_dates:
        # EFFR for day d is published on d+1, so the latest known print is for a day < d. If an FOMC
        # decision has taken effect since that print (or was announced on d itself, before the futures
        # close), shift the print by the change in the target range.
        known = effr[effr.index < d]
        if known.empty or not np.isfinite(known["rate"].iloc[-1]):
            continue
        after = effr[effr.index > d]
        tgt_now = after["target_hi"].iloc[0] if len(after) else asof(effr["target_hi"], d)
        e = known["rate"].iloc[-1] + (tgt_now - known["target_hi"].iloc[-1])
        quotes = {}
        for cm, s in fut.items():
            v = s[(s.index <= d) & (s.index >= d - dt.timedelta(days=n_days))]
            if len(v):
                quotes[cm] = float(v.iloc[-1])
        for meet, (r0, r1) in fedwatch.meeting_rates(d, e, quotes).items():
            pr = fedwatch.decision_probs((r1 - r0) * 100)
            rows.append({"meeting": meet, "date": d, "venue": "zq", **pr, "sum_raw": 1.0,
                         "zq_r0": r0, "zq_r1": r1})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main
def build(n_days: int = STALE_N_DAYS, max_spread: float = STALE_MAX_SPREAD, write: bool = True,
          tick_bound: bool = KALSHI_TICK_BOUND):
    effr = load_effr()
    kc = kalshi_contracts(n_days, max_spread, tick_bound)
    pc = poly_contracts(n_days)
    parts = []
    k_dec = aggregate_buckets(kc[kc["kind"] == "decision"], "kalshi_decision") if len(kc) else pd.DataFrame()
    oc = outcomes(effr)
    offset = infer_ladder_offset(kc, oc) if len(kc) else 0.0
    k_lad, k_lvl = ladder(kc, effr, offset) if len(kc) else (pd.DataFrame(), pd.DataFrame())
    parts += [k_dec, k_lad]
    if len(k_dec) or len(k_lad):
        comb = pd.concat([k_dec, k_lad]).sort_values("venue")      # 'kalshi_decision' < 'kalshi_ladder'
        comb = comb.drop_duplicates(["meeting", "date"], keep="first").assign(
            kalshi_source=lambda x: x["venue"], venue="kalshi")
        parts.append(comb)
    if len(pc):
        parts.append(aggregate_buckets(pc, "polymarket"))
    zq = zq_panel(effr, n_days)
    parts.append(zq)
    panel = pd.concat([p for p in parts if len(p)], ignore_index=True)
    panel["days_to_meeting"] = (pd.to_datetime(panel["meeting"]) - pd.to_datetime(panel["date"])).dt.days
    if write:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        kc.to_csv(PROCESSED / "kalshi_contract_daily.csv", index=False)
        pc.to_csv(PROCESSED / "poly_contract_daily.csv", index=False)
        oc.to_csv(PROCESSED / "outcomes.csv", index=False)
        panel.to_csv(PROCESSED / "panel.csv", index=False)
        k_lvl.to_csv(PROCESSED / "kalshi_level_path.csv", index=False)
    return panel, kc, pc, oc, k_lvl


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-days", type=int, default=STALE_N_DAYS)
    ap.add_argument("--max-spread", type=float, default=STALE_MAX_SPREAD)
    a = ap.parse_args(argv)
    panel, kc, pc, oc, lvl = build(a.n_days, a.max_spread)
    print(panel.groupby("venue").agg(rows=("date", "size"), meetings=("meeting", "nunique")).to_string())


if __name__ == "__main__":
    main()
