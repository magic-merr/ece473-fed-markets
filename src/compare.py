"""Comparison tables: venue agreement, accuracy, Kalshi liquidity/fees, cross-venue gaps vs costs,
stale-rule sensitivity, and the Atlanta Fed MPT rate-path comparison.

Writes results/*.csv and results/summary.md.
"""
from __future__ import annotations

import datetime as dt
import itertools

import numpy as np
import pandas as pd

from config import (FOMC_DATES, PROCESSED, RATES_RAW, RESULTS, STALE_MAX_SPREAD, STALE_N_DAYS,
                    STALE_SENSITIVITY_N, STALE_SENSITIVITY_SPREAD)
import panel as P

HBINS = [0, 7, 30, 90, 10_000]
HLABELS = ["1-7d", "8-30d", "31-90d", ">90d"]
MAIN = ["kalshi", "polymarket", "zq"]


def hbucket(days):
    return pd.cut(days, HBINS, labels=HLABELS, right=True)


def load():
    pn = pd.read_csv(PROCESSED / "panel.csv", parse_dates=["meeting", "date"])
    pn["meeting"], pn["date"] = pn["meeting"].dt.date, pn["date"].dt.date
    oc = pd.read_csv(PROCESSED / "outcomes.csv", parse_dates=["meeting"])
    oc["meeting"] = oc["meeting"].dt.date
    kc = pd.read_csv(PROCESSED / "kalshi_contract_daily.csv", parse_dates=["meeting", "date"], low_memory=False)
    pc_path = PROCESSED / "poly_contract_daily.csv"
    pc = pd.read_csv(pc_path, parse_dates=["meeting", "date"]) if pc_path.stat().st_size > 5 else pd.DataFrame()
    for d in (kc, pc):
        if len(d):
            d["meeting"], d["date"] = d["meeting"].dt.date, d["date"].dt.date
    return pn, oc, kc, pc


# ------------------------------------------------------------------ agreement
def pairwise(pn: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a, b in itertools.combinations(MAIN, 2):
        x = pn[pn.venue == a].merge(pn[pn.venue == b], on=["meeting", "date"], suffixes=("_a", "_b"))
        if x.empty:
            continue
        x["h"] = hbucket(x["days_to_meeting_a"])
        for h, g in list(x.groupby("h", observed=True)) + [("all", x)]:
            d_hold = g["p_hold_a"] - g["p_hold_b"]
            d_cut = g["p_cut_a"] - g["p_cut_b"]
            d_exp = g["exp_change_bps_a"] - g["exp_change_bps_b"]
            rows.append({"pair": f"{a} - {b}", "horizon": h, "days": len(g), "meetings": g["meeting"].nunique(),
                         "mean_diff_p_hold": d_hold.mean(), "mae_p_hold": d_hold.abs().mean(),
                         "mean_diff_p_cut": d_cut.mean(), "mae_p_cut": d_cut.abs().mean(),
                         "rmse_exp_change_bps": np.sqrt((d_exp ** 2).mean()),
                         "corr_exp_change": g["exp_change_bps_a"].corr(g["exp_change_bps_b"]),
                         "share_abs_gap_gt_5pp": (np.maximum(d_hold.abs(), d_cut.abs()) > 0.05).mean()})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ accuracy
def accuracy(pn: pd.DataFrame, oc: pd.DataFrame, horizons=(1, 7, 14, 30, 60), slack=3) -> pd.DataFrame:
    o = oc.set_index("meeting")
    rows = []
    obs = {}
    for v in MAIN:
        g = pn[pn.venue == v]
        for h in horizons:
            for m in o.index:
                cut = m - dt.timedelta(days=h)
                s = g[(g.meeting == m) & (g.date <= cut) & (g.date >= cut - dt.timedelta(days=slack))]
                if len(s):
                    r = s.sort_values("date").iloc[-1]
                    dec = o.loc[m, "decision"]
                    y = {"cut": (1, 0, 0), "hold": (0, 1, 0), "hike": (0, 0, 1)}[dec]
                    p = (r.p_cut, r.p_hold, r.p_hike)
                    obs[(v, h, m)] = (sum((pi - yi) ** 2 for pi, yi in zip(p, y)), p[["cut", "hold", "hike"].index(dec)])
    for h in horizons:
        common = set.intersection(*[{m for (v, hh, m) in obs if v == vv and hh == h} for vv in ("kalshi", "polymarket")])
        for v in MAIN:
            own = [obs[k] for k in obs if k[0] == v and k[1] == h]
            com = [obs[(v, h, m)] for m in common if (v, h, m) in obs]
            rows.append({"venue": v, "horizon_days": h, "meetings": len(own),
                         "brier": np.mean([b for b, _ in own]) if own else np.nan,
                         "mean_p_realized": np.mean([p for _, p in own]) if own else np.nan,
                         "meetings_common_kalshi_poly": len(com),
                         "brier_common": np.mean([b for b, _ in com]) if com else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Kalshi liquidity & fees
def kalshi_liquidity(kc: pd.DataFrame) -> pd.DataFrame:
    k = kc[kc["price"].notna()].copy()
    k["days_to_meeting"] = (pd.to_datetime(k["meeting"]) - pd.to_datetime(k["date"])).dt.days
    k["h"] = hbucket(k["days_to_meeting"])
    live = k[(k["price"] >= 0.05) & (k["price"] <= 0.95)]   # contracts that carry information
    rows = []
    for (kind, h), g in live.groupby(["kind", "h"], observed=True):
        rows.append({"kind": kind, "horizon": h, "contract_days": len(g),
                     "median_spread": g["spread"].median(), "p90_spread": g["spread"].quantile(0.9),
                     "median_taker_fee": g["fee_taker"].median(), "median_maker_fee": g["fee_maker"].median(),
                     "median_round_trip_taker": (g["spread"] + 2 * g["fee_taker"]).median(),
                     "fee_pct_of_price": (g["fee_taker"] / g["price"]).median(),
                     "share_days_traded": (g["volume"] > 0).mean(),
                     "median_volume_when_traded": g.loc[g["volume"] > 0, "volume"].median(),
                     "median_oi": g["oi"].median()})
    by_meeting = (kc.groupby(["meeting", "kind"])
                  .agg(total_volume=("volume", "sum"), max_oi=("oi", "max"), contracts=("ticker", "nunique"))
                  .reset_index())
    by_meeting.to_csv(RESULTS / "kalshi_volume_by_meeting.csv", index=False)
    return pd.DataFrame(rows)


def source_shares(kc: pd.DataFrame, pc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, d in (("kalshi", kc), ("polymarket", pc)):
        if d is None or d.empty:
            continue
        d = d.assign(h=hbucket((pd.to_datetime(d["meeting"]) - pd.to_datetime(d["date"])).dt.days))
        for h, g in list(d.groupby("h", observed=True)) + [("all", d)]:
            s = g["source"].value_counts(normalize=True)
            rows.append({"venue": name, "horizon": h, "contract_days": len(g),
                         "share_quote": s.get("quote", 0.0), "share_bound": s.get("bound", 0.0),
                         "share_trade": s.get("trade", 0.0),
                         "share_stale": s.get("stale", 0.0)})
    return pd.DataFrame(rows)


def sensitivity(oc_all: pd.DataFrame) -> pd.DataFrame:
    """Re-run the panel over the stale-rule grid (and once with the Kalshi tick-bound branch off)."""
    rows = []
    grid = [(n, sp, True) for n, sp in itertools.product(STALE_SENSITIVITY_N, STALE_SENSITIVITY_SPREAD)]
    grid.append((STALE_N_DAYS, STALE_MAX_SPREAD, False))
    for n, sp, tb in grid:
        pn, kc, pc, oc, _ = P.build(n, sp, write=False, tick_bound=tb)
        def add(metric, n_obs, value):
            rows.append({"N_days": n, "max_spread": sp, "tick_bound": tb, "metric": metric, "n": n_obs,
                         "value": value})
        for v in MAIN:
            g = pn[pn.venue == v]
            add(f"{v}_meeting_days", g["meeting"].nunique(), len(g))
        add("kalshi_contract_days_usable", len(kc), int(kc["price"].notna().sum()))
        k = pn[pn.venue == "kalshi"].merge(pn[pn.venue == "polymarket"], on=["meeting", "date"])
        add("kalshi_vs_poly_mae_p_hold", len(k), (k["p_hold_x"] - k["p_hold_y"]).abs().mean())
        add("kalshi_vs_poly_mean_diff_p_hold", len(k), (k["p_hold_x"] - k["p_hold_y"]).mean())
        acc = accuracy(pn, oc_all, horizons=(1, 7, 30)).set_index(["venue", "horizon_days"])
        for h in (1, 7, 30):
            for v in ("kalshi", "polymarket"):
                add(f"{v}_brier_common_{h}d", acc.loc[(v, h), "meetings_common_kalshi_poly"],
                    acc.loc[(v, h), "brier_common"])
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ cross-venue gap vs costs
def gap_vs_cost(kc: pd.DataFrame, pc: pd.DataFrame) -> pd.DataFrame:
    if pc is None or pc.empty:
        return pd.DataFrame()
    k = kc[(kc["kind"] == "decision") & kc["price"].notna()][
        ["meeting", "date", "bps", "price", "spread", "fee_taker", "source"]]
    p = pc[pc["price"].notna()][["meeting", "date", "bps", "price", "fee_taker"]]
    x = k.merge(p, on=["meeting", "date", "bps"], suffixes=("_k", "_p"))
    if x.empty:
        return x
    x["gap"] = (x["price_k"] - x["price_p"]).abs()
    # Lower bound on the cost of trading the gap: cross half the Kalshi spread, pay both taker fees.
    # Polymarket's historical spread is unobserved, so it is set to 0 here (cost is understated).
    x["cost_lb"] = x["spread"].fillna(0) / 2 + x["fee_taker_k"] + x["fee_taker_p"]
    x["excess"] = x["gap"] - x["cost_lb"]
    x["days_to_meeting"] = (pd.to_datetime(x["meeting"]) - pd.to_datetime(x["date"])).dt.days
    return x


# ------------------------------------------------------------------ Atlanta Fed MPT path comparison
def mpt_compare(pn_effr=None) -> pd.DataFrame:
    path = RATES_RAW / "mpt.csv"
    lvl_path = PROCESSED / "kalshi_level_path.csv"
    if not path.exists() or not lvl_path.exists():
        return pd.DataFrame()
    mpt = pd.read_csv(path, parse_dates=["date", "reference_start"])
    mpt = mpt[mpt["field"].str.strip() == "Rate: mean"]
    lvl = pd.read_csv(lvl_path, parse_dates=["meeting", "date"])
    lvl["meeting"], lvl["date"] = lvl["meeting"].dt.date, lvl["date"].dt.date
    effr = P.load_effr()
    sofr = pd.read_csv(RATES_RAW / "sofr.csv", parse_dates=["date"]).assign(date=lambda d: d["date"].dt.date)
    sofr = sofr.set_index("date")["rate"]
    mid = (effr["target_lo"] + effr["target_hi"]) / 2
    spread = (sofr - mid.reindex(sofr.index)).dropna()
    by_date = {d: g.set_index("meeting")["exp_upper"] for d, g in lvl.groupby("date")}
    rows = []
    for r in mpt.itertuples(index=False):
        t, ws = r.date.date(), r.reference_start.date()
        we = (pd.Timestamp(ws) + pd.DateOffset(months=3)).date()
        if t not in by_date or ws <= t:
            continue
        exp = by_date[t]
        meets = [m for m in FOMC_DATES if t < m < we]
        if any(m not in exp.index for m in meets):
            continue
        cur_mid = P.asof(mid, t)
        days = pd.date_range(ws, we - dt.timedelta(days=1), freq="D").date
        lvl_day = []
        for dd in days:
            eff = [m for m in meets if m + dt.timedelta(days=1) <= dd]
            lvl_day.append(exp[eff[-1]] - 0.125 if eff else cur_mid)
        sp = spread[spread.index < t].tail(20).mean()
        k_mean = 100 * (np.mean(lvl_day) + sp)
        rows.append({"date": t, "reference_start": ws, "mpt_mean_bps": float(r.value), "kalshi_mean_bps": k_mean,
                     "diff_bps": k_mean - float(r.value), "meetings_in_window": len(meets),
                     "sofr_minus_mid_bps": 100 * sp})
    out = pd.DataFrame(rows)
    if len(out):
        out["window_rank"] = out.groupby("date")["reference_start"].rank(method="dense").astype(int)
    return out


# ------------------------------------------------------------------ main
def fmt(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".3f") if len(df) else "_no rows_"


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    pn, oc, kc, pc = load()
    tabs = {
        "pairwise_agreement": pairwise(pn),
        "accuracy_brier": accuracy(pn, oc),
        "kalshi_liquidity": kalshi_liquidity(kc),
        "price_source_shares": source_shares(kc, pc),
        "stale_rule_sensitivity": sensitivity(oc),
    }
    g = gap_vs_cost(kc, pc)
    g.to_csv(RESULTS / "gap_vs_cost_daily.csv", index=False)
    if len(g):
        g["h"] = hbucket(g["days_to_meeting"])
        tabs["gap_vs_cost"] = (g.groupby("h", observed=True)
                               .agg(days=("gap", "size"), median_gap=("gap", "median"),
                                    median_cost_lb=("cost_lb", "median"),
                                    share_gap_gt_cost=("excess", lambda s: (s > 0).mean()),
                                    share_gap_gt_cost_plus_2c=("excess", lambda s: (s > 0.02).mean()))
                               .reset_index())
    mp = mpt_compare()
    mp.to_csv(RESULTS / "mpt_path_daily.csv", index=False)
    if len(mp):
        tabs["mpt_path"] = (mp.groupby("window_rank")
                            .agg(days=("diff_bps", "size"), mean_diff_bps=("diff_bps", "mean"),
                                 mae_bps=("diff_bps", lambda s: s.abs().mean()),
                                 corr=("diff_bps", lambda s: mp.loc[s.index, "kalshi_mean_bps"]
                                       .corr(mp.loc[s.index, "mpt_mean_bps"])))
                            .reset_index())
    for k, v in tabs.items():
        v.to_csv(RESULTS / f"{k}.csv", index=False)
    cover = (pn.groupby("venue").agg(meeting_days=("date", "size"), meetings=("meeting", "nunique"),
                                     first=("date", "min"), last=("date", "max")).reset_index())
    cover.to_csv(RESULTS / "coverage.csv", index=False)
    with open(RESULTS / "summary.md", "w") as f:
        f.write(f"# Fed decision markets: Kalshi vs Polymarket vs fed funds futures\n\n"
                f"Stale rule: N = {STALE_N_DAYS} days, max spread = {STALE_MAX_SPREAD:.2f}. "
                f"Generated {dt.date.today()}.\n\n## Coverage\n\n{fmt(cover)}\n\n"
                f"## Outcomes\n\n{fmt(oc)}\n\n")
        for k, v in tabs.items():
            f.write(f"## {k.replace('_', ' ').title()}\n\n{fmt(v)}\n\n")
    print(open(RESULTS / "summary.md").read()[:4000])


if __name__ == "__main__":
    main()
