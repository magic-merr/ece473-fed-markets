"""Worked examples for report sections 2 and 7, computed by the same code as the index and the backtest.

  1. Index on 2024-01-11: the 90-day point falls halfway between two meetings (w = 0.5), all legs are clean
     quotes.
  2. The reset on 2024-12-18: the Fed cut 25bp; CUT90 the day before, on the day, and on the day at the old
     strike (what it would have been without re-anchoring).
  3. One futures trade: CUT90 future expiring 2024-12-27, sold and hedged on 2024-11-27 (30-day lead), with
     the 2024-12-18 cut before expiry.
Outputs: index/results/worked_examples.md and worked_examples.csv (one row per quantity: example, key, value).
Run after futures.py: cd index && python examples.py
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import build
import futures as F
import legs

D = dt.date
INDEX_DAY = D(2024, 1, 11)
RESET_BEFORE, RESET_DAY = D(2024, 12, 17), D(2024, 12, 18)
TRADE = dict(side="cut", horizon=90, expiry=D(2024, 12, 27), entry=D(2024, 11, 27))


def index_day(book, d=INDEX_DAY):
    m1, m2, w = build.bracket(d, 90)
    u = build.ub_at(d)
    rows = [("date", d), ("upper_bound_pct", u), ("target_date_T", d + dt.timedelta(days=90)),
            ("m1_meeting", m1), ("m2_meeting", m2), ("w", w)]
    out = {}
    for kind, k, name in (("C", build.cut_strike(u), "CUT90"), ("H", build.hike_strike(u), "HIKE90")):
        vals = []
        for j, m in (("1", m1), ("2", m2)):
            r = book.get(m, k, d)
            yes, bid, ask, src = r[0], r[1], r[2], r[3]
            p, _ = build.leg(book, m, k, d, kind, u)
            vals.append(p)
            rows += [(f"{name}_leg{j}_strike_above", k), (f"{name}_leg{j}_yes_bid", bid),
                     (f"{name}_leg{j}_yes_ask", ask), (f"{name}_leg{j}_yes_price", yes),
                     (f"{name}_leg{j}_source", src), (f"{name}_leg{j}_probability", p)]
        out[name] = w * vals[0] + (1 - w) * vals[1]
        rows.append((f"{name}_points", 100 * out[name]))
    ix = build.build_index(build.RULE, 90, book=book).set_index("date")
    assert abs(ix.at[d, "CUT90"] - out["CUT90"]) < 1e-12 and abs(ix.at[d, "HIKE90"] - out["HIKE90"]) < 1e-12
    return [("index_2024-01-11", k, v) for k, v in rows]


def reset(book):
    ix = build.build_index(build.RULE, 90, book=book).set_index("date")
    d = RESET_DAY
    m1, m2, w = build.bracket(d, 90)
    u_old, u_new = build.ub_at(RESET_BEFORE), build.ub_at(d)
    old = [build.leg(book, m, build.cut_strike(u_old), d, "C", u_old)[0] for m in (m1, m2)]
    old = [p if np.isfinite(p) else 1 - F.mark(book.get(m, build.cut_strike(u_old), d))[0]
           for p, m in zip(old, (m1, m2))]
    cut_old_strike = w * old[0] + (1 - w) * old[1]
    rows = [("upper_bound_before_pct", u_old), ("upper_bound_after_pct", u_new),
            ("cut90_day_before_points", 100 * ix.at[RESET_BEFORE, "CUT90"]),
            ("cut90_decision_day_points", 100 * ix.at[d, "CUT90"]),
            ("change_points", 100 * (ix.at[d, "CUT90"] - ix.at[RESET_BEFORE, "CUT90"])),
            ("cut90_decision_day_at_old_strike_points", 100 * cut_old_strike),
            ("reset_points", 100 * (ix.at[d, "CUT90"] - cut_old_strike)),
            ("belief_change_points", 100 * (cut_old_strike - ix.at[RESET_BEFORE, "CUT90"])),
            ("m1_meeting", m1), ("m2_meeting", m2), ("w", w),
            ("m1_prob_below_new_level", ix.at[d, "C1"]), ("m2_prob_below_new_level", ix.at[d, "C2"]),
            ("m1_prob_below_old_level", old[0]), ("m2_prob_below_old_level", old[1])]
    return [("reset_2024-12-18", k, v) for k, v in rows]


def trade(book):
    t = TRADE
    ix = build.build_index(build.RULE, t["horizon"], book=book)
    imap = dict(zip(ix["date"], ix[f"{t['side'].upper()}{t['horizon']}"]))
    r = F.hedge_trade(book, imap, t["horizon"], t["side"], t["expiry"], t["entry"], fallback=F.FALLBACK)
    tr = pd.read_csv(build.PROCESSED / "futures_trades.csv", parse_dates=["expiry", "entry"])
    m = tr[(tr["side"] == t["side"]) & (tr["horizon"] == t["horizon"]) & (tr["expiry"].dt.date == t["expiry"])
           & (tr["entry"].dt.date == t["entry"])]
    assert len(m) == 1 and abs(m["err_mid"].iloc[0] - r["err_mid"]) < 1e-9
    keys = ["entry", "expiry", "u_entry", "u_expiry", "strike", "contracts", "rate_moves", "settle_method",
            "index_entry", "F0", "basis", "S_unrounded", "S", "futures_pnl_long", "hedge_pnl_mid", "err_mid",
            "cost_spread", "cost_fee", "cost_total", "cost_near", "cost_far", "capital_dealer", "capital_long"]
    rows = [(k, r[k]) for k in keys]
    rows.append(("hedge_proceeds", r["S"] + r["err_mid"]))
    return [("trade_cut90_2024-12-27", k, v) for k, v in rows]


def main():
    book = legs.book(build.RULE)
    rows = index_day(book) + reset(book) + trade(book)
    df = pd.DataFrame(rows, columns=["example", "key", "value"])
    df["value"] = [round(v, 6) if isinstance(v, (float, np.floating)) else v for v in df["value"]]
    df.to_csv(build.RESULTS / "worked_examples.csv", index=False)
    lines = ["# Worked examples (report sections 2 and 7)", "",
             f"Generated by `index/examples.py` on {dt.date.today()} with the decision 007 index and backtest. "
             "Prices are YES prices of Kalshi 'upper bound above K' contracts; probabilities and index values "
             "in percent (index points).", ""]
    for ex, g in df.groupby("example", sort=False):
        lines += [f"## {ex}", "", g[["key", "value"]].to_markdown(index=False), ""]
    (build.RESULTS / "worked_examples.md").write_text("\n".join(lines))
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
