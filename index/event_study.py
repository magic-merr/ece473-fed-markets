"""Event study (A6, promised in the Milestone I update): how CUT90 and HIKE90 move on FOMC decision days.

For every scheduled FOMC decision from 2023-02-02 (decision 007 main sample) to the end of the data:
  decision    cut, hold or hike, from the upper bound before and after (index_m1/data/realized_upper_bound.csv)
  pre         the index at the close of the last day before the decision with a valid value (at most 3 days back)
  post        the index at the close of the decision day (the close is after the 2:00pm announcement), or the
              first valid value in the next 3 days if the decision day has none
  change      post - pre, in percentage points
The index is the decision 007 index (rule `final`, index/build.py), H = 90. Around several decisions the final rule
has no valid value within 3 days (the books went stale), so the same table is also computed on the Milestone 1
price rule (a decision 007 robustness row; it carries a mid up to 10 days), in columns prefixed `m1_`.
On a day the Fed moves, the index re-anchors to the new upper bound (decision 003), so its change mixes news about
later meetings with the reset.
Next to each move: the mean hedge error of the CUT90 and HIKE90 futures trades whose only rate change before expiry
was that decision (index/results/futures_rate_move_events.csv, run futures.py first).

Outputs: index/results/event_study.csv (one row per decision), event_study_summary.csv (by decision type),
         event_study.md
Run: cd index && python event_study.py
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import build
import legs

LOOK = 3          # days to look back for `pre` and forward for `post`
COLS = ("CUT90", "HIKE90")


def decisions(start=build.SAMPLE_START, end=None) -> pd.DataFrame:
    end = end or legs.data_end()
    p = legs.rate_path()
    known = set(p["decision_date"])
    rows = []
    for d in legs.fomc_dates():
        if not (start <= d <= end) or d not in known:
            continue
        before, after = build.ub_at(d - dt.timedelta(days=1)), build.ub_at(d)
        chg = round((after - before) * 100)
        rows.append({"decision_date": d, "meeting": legs.meeting_ids()[d], "ub_before": before, "ub_after": after,
                     "change_bps": chg, "decision": "cut" if chg < 0 else ("hike" if chg > 0 else "hold")})
    return pd.DataFrame(rows)


def _value(series: dict, days):
    for d in days:
        v = series.get(d, np.nan)
        if np.isfinite(v):
            return d, v
    return None, np.nan


def event_table(ix: pd.DataFrame, dec: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    rows = []
    for r in dec.itertuples(index=False):
        d = r.decision_date
        row = r._asdict()
        for c0 in COLS:
            col = c0
            s = dict(zip(ix["date"], ix[col]))
            pd_, pv = _value(s, [d - dt.timedelta(days=k) for k in range(1, LOOK + 1)])
            qd, qv = _value(s, [d + dt.timedelta(days=k) for k in range(0, LOOK + 1)])
            col = prefix + col
            row.update({f"{col}_pre_date": pd_, f"{col}_pre": 100 * pv, f"{col}_post_date": qd,
                        f"{col}_post": 100 * qv, f"{col}_change": 100 * (qv - pv)})
        rows.append(row)
    return pd.DataFrame(rows)


def with_hedge_errors(ev: pd.DataFrame) -> pd.DataFrame:
    f = build.RESULTS / "futures_rate_move_events.csv"
    if not f.exists():
        return ev
    me = pd.read_csv(f)
    me = me[~me["rate_moves"].astype(str).str.contains("/")]          # trades with exactly one rate change
    out = ev.copy()
    for col in COLS:
        x = me[me["index"] == col].set_index("rate_moves")
        key = out["decision_date"].astype(str)
        out[f"{col}_futures_trades"] = key.map(x["trades"]).fillna(0).astype(int)
        out[f"{col}_futures_mean_hedge_err"] = key.map(x["mean_err"])
    return out


def summary(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rule, prefix in (("final", ""), ("m1", "m1_")):
        for dname in ("cut", "hold", "hike"):
            g = ev[ev["decision"] == dname]
            for col in COLS:
                c = g[f"{prefix}{col}_change"].dropna()
                rows.append({"rule": rule, "decision": dname, "index": col, "decisions": len(g),
                             "with_value": len(c), "mean_change_pp": c.mean(), "median_change_pp": c.median(),
                             "min_change_pp": c.min(), "max_change_pp": c.max(),
                             "share_index_fell": (c < 0).mean() if len(c) else np.nan})
    return pd.DataFrame(rows)


def main():
    ix = build.build_index(build.RULE, 90)
    dec = decisions()
    ev = event_table(ix, dec)
    m1 = event_table(build.build_index("m1", 90), dec, prefix="m1_")
    ev = with_hedge_errors(ev.merge(m1.drop(columns=[c for c in dec.columns if c != "decision_date"]),
                                    on="decision_date"))
    sm = summary(ev)
    build.RESULTS.mkdir(parents=True, exist_ok=True)
    ev.to_csv(build.RESULTS / "event_study.csv", index=False)
    sm.to_csv(build.RESULTS / "event_study_summary.csv", index=False)
    show = ["decision_date", "meeting", "decision", "change_bps", "CUT90_pre", "CUT90_post", "CUT90_change",
            "HIKE90_pre", "HIKE90_post", "HIKE90_change", "m1_CUT90_change", "m1_HIKE90_change"]
    show += [c for c in ("CUT90_futures_mean_hedge_err", "HIKE90_futures_mean_hedge_err") if c in ev.columns]
    gaps = ev[(ev["CUT90_pre_date"] != ev["decision_date"] - dt.timedelta(days=1))
              | (ev["CUT90_post_date"] != ev["decision_date"])
              | (ev["HIKE90_pre_date"] != ev["decision_date"] - dt.timedelta(days=1))
              | (ev["HIKE90_post_date"] != ev["decision_date"])]
    lines = [
        "# Event study: CUT90 and HIKE90 on FOMC decision days", "",
        f"Generated by `index/event_study.py` on {dt.date.today()}. Index: decision 007 (rule `{build.RULE}`), H = 90. "
        f"Decisions from {build.SAMPLE_START} to {legs.data_end()}: {len(ev)}. Change = index at the close of the "
        "decision day minus the close of the day before, in percentage points (pp). When either day has no valid "
        f"value, the nearest valid day within {LOOK} days is used ({len(gaps)} decisions; dates in the csv). "
        "On a cut or hike the index re-anchors to the new upper bound (decision 003), so a fully expected move "
        "still moves the index. futures_mean_hedge_err: mean hedge error of the futures trades whose only rate "
        "change before expiry was that decision ($ per $100; > 0 means the dealer gains).", "",
        "## By decision type (rule final; rule m1 = Milestone 1 price rule, robustness)", "",
        sm.to_markdown(index=False, floatfmt=".2f"), "",
        "## Every decision", "", ev[show].to_markdown(index=False, floatfmt=".2f"), "",
    ]
    (build.RESULTS / "event_study.md").write_text("\n".join(lines))
    print(sm.round(2).to_string(index=False))
    return ev, sm


if __name__ == "__main__":
    main()
