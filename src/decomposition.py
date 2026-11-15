"""Return decomposition of CUT90 and HIKE90 (sprint row P3, old TASK 7). Palmer.

Question: how much of the daily index change could a holder of the underlying Kalshi contracts actually earn,
and where does the rest come from? Method as in `docs/log/palmer.md` 11/12 (Milestone 1 tracking backtest,
`index_m1/build_index.py::backtest`):

  On each pair of consecutive calendar days (t0, t1) where the index has a value on both days:
    portfolio P&L  hold w(t0) of meeting m1(t0) and 1 - w(t0) of m2(t0), at the strike in effect on t0, from
                   t0 to t1, priced at the index's own leg prices. This is the change in fixed-meeting,
                   fixed-strike probabilities: the belief change.
    index change   I(t1) - I(t0)
    gap            portfolio P&L - index change

  Each day pair is one of three types:
    announcement   t1 is an FOMC decision day. If the Fed moved, the reference strike resets.
    bracket roll   otherwise, m1 or m2 changes between t0 and t1 (T = t + H passes a meeting).
    ordinary       neither. Here the gap is exactly minus the term-structure slope
                   (C_m2 - C_m1) / (d2 - d1) at t1: the weight shifts one day toward the far meeting, and
                   no holder of the contracts earns that drift (roll-down).

  So the index change splits into four parts that add up exactly:
    index change = belief change - roll-down gap - bracket-roll gap - announcement gap

Configurations (rule x sample). The main row uses the decision 007 price rule ("final" in index/legs.py)
from 2023-02-02. Until Ari's A4 push adds that rule, the script falls back to "src" and says so in the
output. The Milestone 1 rule from 2022-03-17 reproduces `index_m1/data/backtest_*.csv` exactly
(tests/test_decomposition.py), which is the comparison row.

Imports index/ read-only and writes only into results/.
Run: cd src && python decomposition.py [--rule final|src|m1]  ->  results/decomposition.md (+ .csv)
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "index"))  # appended: src/figures.py and index/figures.py share a name

import build  # noqa: E402
import futures as F  # noqa: E402  (mark(): how the backtest values a held leg)
import legs  # noqa: E402
from index_rule import main_rule, pre_a4_note  # noqa: E402

OUT = ROOT / "results"
HORIZON = 90
KINDS = (("CUT", "C"), ("HIKE", "H"))


final_rule = main_rule  # 'final' once index/legs.py has it (decision 007, Ari's A2), else 'src'


def _held_value(bk, m, k, t, kind, u, chained: bool) -> float:
    """Value on day t of a leg held since the previous index day (cut or hike probability).
    one_day (Milestone 1 method): the index rule's price only. chained: if the rule has no price, mark the leg
    as index/futures.py marks a hedge leg (book mid, or a one-sided book near 0 or 1), because the holder
    still owns it."""
    if not chained:
        return build.leg(bk, m, k, t, kind, u)[0]
    if kind == "C" and u <= 0.25:
        return 0.0
    y = F.mark(bk.get(m, k, t))[0]
    return 1 - y if kind == "C" else y


def daily(rule: str, horizon: int = HORIZON, start: dt.date = build.SAMPLE_START,
          end: dt.date | None = None, method: str = "chained") -> pd.DataFrame:
    """One row per (index, interval) with portfolio P&L, index change, gap and interval type.
    Values are in probability units (1.0 = 100 index points).

    method="one_day": consecutive calendar days with an index value on both (Milestone 1 tracking backtest).
    method="chained": consecutive days *with an index value*, so an interval can span days where the index is
        missing. The portfolio is held with fixed weights over the interval. Under a 3-day freshness rule the
        index is often missing on the day before a decision, so one-day pairs lose most rate-change days."""
    chained = method == "chained"
    bk = legs.book(rule)
    ix = build.build_index(rule, horizon, book=bk, end=end).set_index("date")
    fomc = sorted(legs.fomc_dates())
    rows = []
    for name, kind in KINDS:
        col = f"{name}{horizon}"
        strike = build.cut_strike if kind == "C" else build.hike_strike
        days = [d for d in ix.index if np.isfinite(ix.at[d, col])] if chained else list(ix.index)
        for t0, t1 in zip(days[:-1], days[1:]):
            if t1 < start:
                continue
            if not chained and (t1 - t0).days != 1:
                continue
            a, b = ix.loc[t0], ix.loc[t1]
            if not (np.isfinite(a[col]) and np.isfinite(b[col])):
                continue
            k = strike(a["ub"])
            wts = (a["w"], 1 - a["w"])
            p0 = (a[f"{kind}1"], a[f"{kind}2"])
            p1 = tuple(_held_value(bk, m, k, t1, kind, a["ub"], chained) for m in (a["d1"], a["d2"]))
            if chained:  # a zero-weight leg does not need a price
                p0, p1 = (tuple(p if wt > 0 else 0.0 for p, wt in zip(pp, wts)) for pp in (p0, p1))
            if not np.all(np.isfinite(p0 + p1)):
                rows.append({"index": col, "date": t1, "days": (t1 - t0).days, "dropped": True,
                             "dI": b[col] - a[col]})
                continue
            pnl = wts[0] * (p1[0] - p0[0]) + wts[1] * (p1[1] - p0[1])
            ann = any(t0 < f <= t1 for f in fomc)
            roll = (a["d1"] != b["d1"]) or (a["d2"] != b["d2"])
            rows.append({"index": col, "date": t1, "days": (t1 - t0).days, "dropped": False,
                         "pnl": pnl, "dI": b[col] - a[col],
                         "type": "announcement" if ann else ("bracket roll" if roll else "ordinary"),
                         "rate_change": bool(b["ub"] != a["ub"]),
                         "slope_t0": (a[f"{kind}2"] - a[f"{kind}1"]) / (a["d2"] - a["d1"]).days,
                         "slope_t1": (b[f"{kind}2"] - b[f"{kind}1"]) / (b["d2"] - b["d1"]).days})
    out = pd.DataFrame(rows)
    out["gap"] = out["pnl"] - out["dI"]
    out["rule"], out["start"], out["method"] = rule, start, method
    return out


def components(x: pd.DataFrame, label: str, end: dt.date) -> list[dict]:
    """Four-part split of the summed index change, in index points. Dropped intervals (index on both ends but
    a held leg cannot be priced) are counted but left out of the sums."""
    rows = []
    for col, gg in x.groupby("index", sort=False):
        g = gg[~gg["dropped"]]
        gap = g.groupby("type")["gap"].sum()
        ann = g[g["type"] == "announcement"]
        start = gg["start"].iloc[0]
        rows.append({
            "configuration": label, "index": col, "intervals": len(g),
            "dropped": int(gg["dropped"].sum()),
            "share_one_day": (g["days"] == 1).mean(),
            "share_of_days_covered": g["days"].sum() / max((end - start).days, 1),
            "index_change_incl_dropped": 100 * gg["dI"].sum(),
            "index_change": 100 * g["dI"].sum(),
            "belief_change": 100 * g["pnl"].sum(),
            "roll_down": -100 * gap.get("ordinary", 0.0),
            "bracket_rolls": -100 * gap.get("bracket roll", 0.0),
            "announcement_resets": -100 * gap.get("announcement", 0.0),
            "of_which_rate_change_days": -100 * ann.loc[ann["rate_change"], "gap"].sum(),
        })
    return rows


def by_type(x: pd.DataFrame) -> pd.DataFrame:
    """The 11/12 log table: index change, portfolio P&L and gap by interval type."""
    out = []
    for col, gg in x.groupby("index", sort=False):
        g = gg[~gg["dropped"]]
        for typ in ("ordinary", "bracket roll", "announcement"):
            s = g[g["type"] == typ]
            r = {"index": col, "type": typ, "intervals": len(s), "days": int(s["days"].sum()),
                 "index_change": 100 * s["dI"].sum(), "portfolio_pnl": 100 * s["pnl"].sum(),
                 "gap": 100 * s["gap"].sum()}
            if typ == "ordinary":
                r["mean_gap_bp_per_day"] = 1e4 * s["gap"].sum() / s["days"].sum()
                r["mean_slope_bp_per_day"] = 1e4 * (s["slope_t0"] * s["days"]).sum() / s["days"].sum()
            if typ == "announcement":
                r["rate_change"] = int(s["rate_change"].sum())
            out.append(r)
        out.append({"index": col, "type": "total", "intervals": len(g), "days": int(g["days"].sum()),
                    "index_change": 100 * g["dI"].sum(), "portfolio_pnl": 100 * g["pnl"].sum(),
                    "gap": 100 * g["gap"].sum()})
    return pd.DataFrame(out)


def by_year(x: pd.DataFrame) -> pd.DataFrame:
    x = x.assign(year=[d.year for d in x["date"]])
    rows = []
    for (col, yr), g in x.groupby(["index", "year"], sort=False):
        rows.extend({**r, "year": yr} for r in components(g, "", g["date"].max()))
    t = pd.DataFrame(rows).drop(columns=["configuration", "share_one_day", "share_of_days_covered"])
    return t[["index", "year"] + [c for c in t.columns if c not in ("index", "year")]]


def _git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", choices=("final", "src", "m1"), default=None,
                    help="price rule for the main row (default: 'final' if index/legs.py has it, else 'src')")
    args = ap.parse_args(argv)
    rule = args.rule or final_rule()
    end = legs.data_end()
    configs = [  # label, rule, start, method
        (f"Main: {rule} rule, from {build.SAMPLE_START}", rule, build.SAMPLE_START, "chained"),
        (f"{rule} rule, from {build.EXT_START}", rule, build.EXT_START, "chained"),
        (f"Milestone 1 rule, from {build.SAMPLE_START}", "m1", build.SAMPLE_START, "chained"),
        (f"Milestone 1 rule, from {build.EXT_START}", "m1", build.EXT_START, "chained"),
        (f"Milestone 1 report: Milestone 1 rule, from {build.EXT_START}, one-day pairs", "m1", build.EXT_START,
         "one_day"),
    ]
    frames, comp = {}, []
    for label, cfg_rule, start, method in configs:
        frames[label] = daily(cfg_rule, start=start, end=end, method=method)
        comp += components(frames[label], label, end)
    comp = pd.DataFrame(comp)
    parts = ["belief_change", "roll_down", "bracket_rolls", "announcement_resets"]
    assert (comp[parts].sum(axis=1) - comp["index_change"]).abs().max() < 1e-6, "components do not add up"
    main_label, m1_label = configs[0][0], configs[-1][0]
    allx = pd.concat([f.assign(configuration=lab) for lab, f in frames.items()], ignore_index=True)
    OUT.mkdir(exist_ok=True)
    allx.to_csv(OUT / "decomposition_daily.csv", index=False)
    comp.to_csv(OUT / "decomposition.csv", index=False)

    md = lambda d: d.to_markdown(index=False, floatfmt=".2f")  # noqa: E731
    head = ["configuration", "index", "intervals", "index_change"] + parts + ["of_which_rate_change_days"]
    cover = ["configuration", "index", "intervals", "dropped", "share_one_day", "share_of_days_covered",
             "index_change", "index_change_incl_dropped"]
    lines = [
        "# Return decomposition of CUT90 and HIKE90 (P3)", "",
        f"Generated by `src/decomposition.py` on {dt.date.today()}, repo commit {_git('rev-parse', '--short', 'HEAD')}, "
        f"`index/` at commit {_git('log', '-1', '--format=%h', '--', 'index')}. Main price rule: `{rule}`. "
        f"Data through {end}. All values in index points (1 point = $1 on the $100 contract).", "",
    ]
    lines += pre_a4_note(rule)
    lines += [
        "## Method", "",
        "Take two consecutive days on which the index has a value. Between them, a portfolio holds w of the near "
        "meeting's contract and 1 - w of the far meeting's, at the first day's strike, with w from the first day. "
        "Its P&L is the **belief change**: how much fixed-meeting, fixed-strike probabilities moved. The **gap** is "
        "portfolio P&L minus the index change. Each interval is an announcement (an FOMC decision falls in it), a "
        "bracket roll (otherwise, the pair of meetings changes) or ordinary (neither). On an ordinary interval of "
        "k days the gap equals exactly -k times the term-structure slope (C_m2 - C_m1) / (d2 - d1) at its end, so "
        "it is the **roll-down**. The four parts add up to the summed index change:", "",
        "index change = belief change + roll-down + bracket rolls + announcement resets", "",
        "with each part signed as its contribution to the index. Held legs are priced at the index rule's price; "
        "if the rule has none on the second day, at the standing book as `index/futures.py` marks a hedge leg.", "",
        "The Milestone 1 report used one-day pairs only (both calendar days with an index value, rule prices "
        "only). Under the 3-day freshness rule the index is often missing on the day before an FOMC decision, so "
        "one-day pairs would drop most rate-change days. The chained intervals keep them. The last row uses the "
        "Milestone 1 method and reproduces `index_m1/data/backtest_cut90.csv` and `backtest_hike90.csv`.", "",
        "## 1. Index change split into four parts", "", md(comp[head]), "",
        "## 2. Coverage", "",
        "dropped: intervals with an index value on both ends where a held leg had no price, left out of the sums. "
        "index_change_incl_dropped: the summed index change including them, which for chained rows equals the "
        "change from the first to the last day with an index value.", "", md(comp[cover]), "",
        "## 3. By interval type, main configuration", "", md(by_type(frames[main_label])), "",
        "## 4. By interval type, Milestone 1 report method (the 11/12 log table)", "",
        md(by_type(frames[m1_label])), "",
        "## 5. By calendar year, main configuration", "", md(by_year(frames[main_label])), "",
    ]
    (OUT / "decomposition.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
