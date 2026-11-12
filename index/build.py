"""CUT/HIKE constant-maturity index (decision 003) on the data-layer price rule, any horizon.

  U_t      upper bound after every decision announced on or before day t (realized_upper_bound.csv)
  C_m(t)   1 - Y_m(U_t - 0.25, t)   probability the upper bound after meeting m is below U_t
  H_m(t)   Y_m(U_t, t)              probability it is above U_t
  T        t + H days; m1 = last meeting with t < decision <= T; m2 = first meeting after T
  w        (d2 - T) / (d2 - d1), weight on m1
  CUT_H    w C_m1 + (1 - w) C_m2;   HIKE_H the same with H_m
At the zero lower bound (U_t <= 0.25) a cut is impossible and C = 0, as in Milestone 1.

Outputs
  processed/index_daily.csv       H = 90, src rule, decision-003 columns:
                                  date, ub, m1, m2, d1, d2, w, C1, C2, H1, H2, CUT90, HIKE90, any_stale,
                                  announcement, source  (+ per-leg price sources)
  processed/index_daily_h60.csv   same for H = 60 (columns CUT60, HIKE60)
  index/results/index_vs_m1.csv   rebuilt CUT90/HIKE90 vs the frozen Milestone 1 index
Run: cd index && python build.py
"""
from __future__ import annotations

import bisect
import datetime as dt

import numpy as np
import pandas as pd

import legs

PROCESSED = legs.ROOT / "processed"
RESULTS = legs.ROOT / "index" / "results"
SAMPLE_START = dt.date(2023, 2, 2)     # decision 002: main sample from the Feb 2023 meeting
EXT_START = dt.date(2022, 3, 17)       # Milestone 1 main sample (first day off the zero lower bound)
FRESH = {"quote", "bound", "trade"}    # src-rule sources that use a fresh price


def ub_at(d: dt.date) -> float:
    p = legs.rate_path()
    i = bisect.bisect_right(list(p["decision_date"]), d)
    return 0.25 if i == 0 else float(p["ub_after"].iloc[i - 1])


def bracket(d: dt.date, horizon: int):
    """(m1, m2, w) for target d + horizon, with m1 strictly after d; None if no bracketing pair."""
    meets = legs.fomc_dates()
    tgt = d + dt.timedelta(days=horizon)
    i = bisect.bisect_right(meets, tgt)
    if i == 0 or i >= len(meets) or meets[i - 1] <= d:
        return None
    m1, m2 = meets[i - 1], meets[i]
    return m1, m2, (m2 - tgt).days / (m2 - m1).days


def cut_strike(u: float) -> float:
    return round(u - 0.25, 4)


def hike_strike(u: float) -> float:
    return round(u, 4)


def leg(book: legs.Book, m, k, d, kind: str, u: float):
    """(probability, source) of a net cut (kind='C') or hike ('H') by meeting m, strike k, day d."""
    if kind == "C" and u <= 0.25:
        return 0.0, "zlb"
    r = book.get(m, k, d)
    if r is None:
        return np.nan, "missing"
    y, src = r[0], r[3]
    return (1 - y if kind == "C" else y), src


def build_index(rule: str = "src", horizon: int = 90, start: dt.date | None = None,
                end: dt.date | None = None, book: legs.Book | None = None) -> pd.DataFrame:
    book = book or legs.book(rule)
    start = start or dt.date(2021, 7, 2)
    end = end or legs.data_end()
    ann = set(legs.fomc_dates())
    ids = legs.meeting_ids()
    rows = []
    for d in pd.date_range(start, end, freq="D").date:
        br = bracket(d, horizon)
        if br is None:
            continue
        m1, m2, w = br
        u = ub_at(d)
        r = {"date": d, "ub": u, "m1": ids[m1], "m2": ids[m2], "d1": m1, "d2": m2, "w": w}
        for kind, k in (("C", cut_strike(u)), ("H", hike_strike(u))):
            for j, m in (("1", m1), ("2", m2)):
                r[f"{kind}{j}"], r[f"{kind}{j}_src"] = leg(book, m, k, d, kind, u)
        rows.append(r)
    ix = pd.DataFrame(rows)
    cut, hike = f"CUT{horizon}", f"HIKE{horizon}"
    ix[cut] = ix["w"] * ix["C1"] + (1 - ix["w"]) * ix["C2"]
    ix[hike] = ix["w"] * ix["H1"] + (1 - ix["w"]) * ix["H2"]
    good = FRESH | {"zlb"} if rule == "src" else {"quote", "zlb"}
    srcs = ix[["C1_src", "C2_src", "H1_src", "H2_src"]]
    ix["any_stale"] = ~srcs.isin(good).all(axis=1)
    ix["announcement"] = ix["date"].isin(ann)
    ix["source"] = "kalshi"
    ix["rule"] = rule
    return ix


def compare_to_m1(ix: pd.DataFrame, start=SAMPLE_START) -> pd.DataFrame:
    m1 = pd.read_csv(legs.M1 / "data" / "index_daily.csv", parse_dates=["date"])
    m1["date"] = m1["date"].dt.date
    x = ix.merge(m1[["date", "CUT90", "HIKE90"]], on="date", suffixes=("", "_m1"))
    rows = []
    for lab, s in (("from 2022-03-17", EXT_START), ("from 2023-02-02", start)):
        y = x[x["date"] >= s]
        for col in ("CUT90", "HIKE90"):
            both = y[[col, f"{col}_m1"]].dropna()
            d = both[col] - both[f"{col}_m1"]
            rows.append({"sample": lab, "index": col, "days": len(y),
                         "coverage_rebuilt": y[col].notna().mean(), "coverage_m1": y[f"{col}_m1"].notna().mean(),
                         "days_both": len(both), "corr_level": both[col].corr(both[f"{col}_m1"]),
                         "mean_diff_pp": 100 * d.mean(), "mae_pp": 100 * d.abs().mean(),
                         "max_abs_diff_pp": 100 * d.abs().max()})
    return pd.DataFrame(rows)


def main():
    PROCESSED.mkdir(exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    ix90 = build_index("src", 90)
    ix90.to_csv(PROCESSED / "index_daily.csv", index=False)
    ix60 = build_index("src", 60)
    ix60.to_csv(PROCESSED / "index_daily_h60.csv", index=False)
    cmp_ = compare_to_m1(ix90)
    cmp_.to_csv(RESULTS / "index_vs_m1.csv", index=False)
    print(cmp_.round(4).to_string(index=False))
    for ix, h in ((ix90, 90), (ix60, 60)):
        s = ix[ix["date"] >= SAMPLE_START]
        print(f"H={h}: {len(s)} days from {SAMPLE_START}, CUT coverage {s[f'CUT{h}'].notna().mean():.3f}, "
              f"HIKE coverage {s[f'HIKE{h}'].notna().mean():.3f}, any_stale {s['any_stale'].mean():.3f}")


if __name__ == "__main__":
    main()
