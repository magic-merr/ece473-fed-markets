"""Settlement-rule check for decisions 005 and 006 (TASKS 13, 15, 17, 19). Palmer.

Reuses Ari's backtest in index/ without changing it, and asks two questions about the settlement rule:

  1. Trade branch. Under the src rule a contract whose book is wider than 10c is priced at its last trade
     (if one printed within 3 days). How often does that branch set a settlement-day index value, and how
     far are those prints from the standing book?
  2. Decision in the window. The Milestone 1 expiry rule only moves expiry if it is within one business day
     of an FOMC decision, so a Wednesday decision can land inside a Friday expiry's 5-day window.

Variants run through index/futures.hedge_trade (same hedge, same costs, only settlement changes):
  base        Ari's main run: src rule, Milestone 1 expiry rule
  no_trade    settlement days whose index uses a trade-branch leg drop out of the settlement mean
  no_decision expiry moves back a week until no FOMC decision falls in the 5-day window (or the next
              business day after expiry)
  both        no_trade + no_decision
  wide_mid    a contract whose book is two-sided and quoted within 3 days but wider than 10c is priced at
              the mid of that book instead of its last trade; the trade branch is left for books that are
              not two-sided. The hedge legs use the same prices, so the hedge identity still holds.
  proposed    wide_mid + no_decision (decision 006 with the docs/spec.md section 4 expiry rule)

Run: cd src && python settlement_check.py   ->  results/settlement_rule_check.md (+ .csv)
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "index"))

import build  # noqa: E402
import futures as F  # noqa: E402
import legs  # noqa: E402

OUT = ROOT / "results"


def expiries_no_decision(start: dt.date, end: dt.date) -> list[dt.date]:
    """Last Friday of each month, moved back a week while an FOMC decision falls in the 5-day settlement
    window or on the next business day after expiry."""
    fomc = legs.fomc_dates()
    out = []
    for mo in pd.date_range(start.replace(day=1), end, freq="MS"):
        last = (mo + pd.offsets.MonthEnd(0)).date()
        e = last - dt.timedelta(days=(last.weekday() - 4) % 7)

        def bad(e):
            w0 = e - dt.timedelta(days=F.SETTLE_DAYS - 1)
            return any(w0 <= f <= e or (f > e and np.busday_count(e, f) <= 1) for f in fomc)
        while bad(e):
            e -= dt.timedelta(days=7)
        if start <= e <= end:
            out.append(e)
    return out


def wide_mid_days() -> pd.DataFrame:
    """src contract-days with the trade branch replaced by the book mid where the book is fresh and two-sided."""
    cd = legs.contract_days("src").copy()
    sel = (cd["source"] == "trade") & (cd["bid"] > 0) & (cd["ask"] < 1) & (cd["quote_age"] <= 3)
    cd.loc[sel, "value"] = (cd.loc[sel, "bid"] + cd.loc[sel, "ask"]) / 2
    cd.loc[sel, "source"] = "wide_mid"
    return cd


def trade_vs_mid_forecast() -> dict:
    """On trade-branch days with a fresh two-sided book, which is closer to the next quote-branch mid
    (1 to 3 days later): the last trade or the wide book's mid?"""
    cd = legs.contract_days("src")
    cd = cd[cd["date"] >= build.SAMPLE_START].sort_values(["ticker", "date"])
    out = []
    for _, g in cd.groupby("ticker"):
        g = g.set_index("date")
        q = g["value"].where(g["source"] == "quote")
        nxt = pd.concat([q.shift(-k) for k in (1, 2, 3)], axis=1).bfill(axis=1).iloc[:, 0]
        sel = (g["source"] == "trade") & (g["bid"] > 0) & (g["ask"] < 1) & (g["quote_age"] <= 3)
        out.append(g[sel].assign(nxt=nxt[sel]))
    r = pd.concat(out).dropna(subset=["nxt"])
    e_t = (r["value"] - r["nxt"]).abs()
    e_m = ((r["bid"] + r["ask"]) / 2 - r["nxt"]).abs()
    return {"contract_days": len(r), "median_spread": (r["ask"] - r["bid"]).median(),
            "mae_last_trade": e_t.mean(), "mae_book_mid": e_m.mean(),
            "p90_last_trade": e_t.quantile(0.9), "p90_book_mid": e_m.quantile(0.9),
            "share_mid_closer": (e_m < e_t).mean()}


def index_maps(book, h):
    """Index series and per-day 'uses a trade-branch leg' flag, for CUT and HIKE at horizon h."""
    ix = build.build_index("src", h, book=book)
    maps = {}
    for side, a, b in (("cut", "C1_src", "C2_src"), ("hike", "H1_src", "H2_src")):
        col = f"{side.upper()}{h}"
        used_a = ix["w"] > 0
        used_b = ix["w"] < 1
        trade = (used_a & (ix[a] == "trade")) | (used_b & (ix[b] == "trade"))
        base = dict(zip(ix["date"], ix[col]))
        no_trade = dict(zip(ix["date"], ix[col].where(~trade)))
        maps[side] = (base, no_trade, dict(zip(ix["date"], trade)))
    return maps


def run_variant(book, maps, exp_fn, use_no_trade, start=build.SAMPLE_START):
    end = legs.data_end()
    rows, skipped = [], []
    for h in F.HORIZONS:
        for side in F.SIDES:
            base, no_trade, tflag = maps[h][side]
            imap = no_trade if use_no_trade else base
            for E in exp_fn(start, end):
                for L in F.LEADS:
                    t = E - dt.timedelta(days=L)
                    while t.weekday() >= 5:
                        t -= dt.timedelta(days=1)
                    if t < start:
                        continue
                    r = F.hedge_trade(book, imap, h, side, E, t)
                    if r["status"] == "ok":
                        W = F.window(E)
                        r["trade_days_in_window"] = sum(bool(tflag.get(d, False)) for d in W)
                        rows.append({**r, "lead": L})
                    else:
                        skipped.append({"horizon": h, "side": side, "expiry": E, "lead": L, "reason": r["status"]})
    return pd.DataFrame(rows), pd.DataFrame(skipped)


def summarize(lab, tr, sk, base_tr=None):
    out = []
    for (h, s), g in tr.groupby(["horizon", "side"]):
        k = sk[(sk["horizon"] == h) & (sk["side"] == s)] if len(sk) else sk
        nm = g[g["case"] != "rate_move"]
        mv = g[g["case"] == "rate_move"]
        ex = g[g["executable"]]
        r = {"variant": lab, "index": f"{s.upper()}{h}", "expiries": g["expiry"].nunique(), "trades": len(g),
             "no_settlement": int((k["reason"] == "no_settlement").sum()) if len(k) else 0,
             "share_fallback": g["fallback"].mean(),
             "share_lt3_valid": (g["settle_days_valid"] < 3).mean(), "share_waited": g["settle_waited"].mean(),
             "share_trade_day_in_window": (g["trade_days_in_window"] > 0).mean(),
             "share_decision_in_window": g["decision_in_window"].mean(),
             "max_abs_err_no_move": nm["err_mid"].abs().max(),
             "rmse_err_rate_move": float(np.sqrt((mv["err_mid"] ** 2).mean())) if len(mv) else np.nan,
             "mean_cost": ex["cost_total"].mean()}
        if base_tr is not None:
            b = base_tr[(base_tr["horizon"] == h) & (base_tr["side"] == s)]
            m = g.merge(b[["expiry", "lead", "S"]], on=["expiry", "lead"], suffixes=("", "_base"))
            dS = (m["S"] - m["S_base"]).abs()
            r["trades_matched"] = len(m)
            r["share_S_changed"] = (dS > 1e-9).mean()
            r["max_abs_dS"] = dS.max()
        out.append(r)
    return out


def trade_branch_gap(book):
    """How far trade-branch prices sit from the standing book's mid, for index legs."""
    cd = legs.contract_days("src")
    t = cd[(cd["source"] == "trade") & (cd["date"] >= build.SAMPLE_START)].copy()
    two = (t["bid"] > 0) & (t["ask"] < 1)
    t = t[two]
    t["gap"] = (t["value"] - (t["bid"] + t["ask"]) / 2).abs()
    t["spread"] = t["ask"] - t["bid"]
    return {"trade_branch_contract_days": len(t), "median_spread": t["spread"].median(),
            "median_abs_gap_to_mid": t["gap"].median(), "p90_abs_gap_to_mid": t["gap"].quantile(0.9),
            "share_gap_gt_5c": (t["gap"] > 0.05).mean(), "share_gap_gt_10c": (t["gap"] > 0.10).mean()}


def main():
    OUT.mkdir(exist_ok=True)
    book = legs.book("src")
    wbook = legs.Book(wide_mid_days())
    maps = {h: index_maps(book, h) for h in F.HORIZONS}
    wmaps = {h: index_maps(wbook, h) for h in F.HORIZONS}
    variants = {}
    for lab, bk, mp, exp_fn, nt in (
            ("base", book, maps, F.expiries, False), ("no_trade", book, maps, F.expiries, True),
            ("no_decision", book, maps, expiries_no_decision, False),
            ("both", book, maps, expiries_no_decision, True),
            ("wide_mid", wbook, wmaps, F.expiries, False),
            ("proposed", wbook, wmaps, expiries_no_decision, False)):
        variants[lab] = run_variant(bk, mp, exp_fn, nt)
    base_tr = variants["base"][0]
    rows = []
    for lab, (tr, sk) in variants.items():
        rows += summarize(lab, tr, sk, base_tr)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "settlement_rule_check.csv", index=False)

    e_old = F.expiries(build.EXT_START, legs.data_end())
    e_new = expiries_no_decision(build.EXT_START, legs.data_end())
    moved = sorted(set(e_old) - set(e_new))
    dec_in = [e for e in e_old if any(F.window(e)[0] <= f <= e for f in legs.fomc_dates())]
    gap = trade_branch_gap(book)
    fc = trade_vs_mid_forecast()
    m1 = pd.read_csv(legs.M1 / "data" / "index_daily.csv", parse_dates=["date"])
    m1["date"] = m1["date"].dt.date
    vs_m1 = []
    for lab, bk in (("src rule", book), ("wide_mid", wbook)):
        ix = build.build_index("src", 90, book=bk)
        x = ix.merge(m1[["date", "CUT90", "HIKE90"]], on="date", suffixes=("", "_m1"))
        for col in ("CUT90", "HIKE90"):
            b = x[[col, col + "_m1"]].dropna()
            d = 100 * (b[col] - b[col + "_m1"]).abs()
            vs_m1.append({"rule": lab, "index": col, "days_both": len(b), "days_gap_gt_5pp": int((d > 5).sum()),
                          "max_gap_pp": d.max(), "mae_pp": d.mean()})

    lines = ["# Settlement rule check (decisions 005 and 006)", "",
             f"Generated by `src/settlement_check.py` on {dt.date.today()} from Ari's `index/futures.py` "
             "(hedge, costs and sample unchanged; only the settlement rule varies). $ per $100 contract.", "",
             "## Expiry calendar", "",
             f"Monthly expiries since {build.EXT_START}: {len(e_old)}. Under the Milestone 1 rule, "
             f"{len(dec_in)} have an FOMC decision inside the 5-day window: "
             + ", ".join(str(e) for e in dec_in) + ". "
             f"The no-decision rule moves {len(moved)} of them one week earlier.", "",
             "## Trade-branch prices vs the standing book (index legs, src rule, from 2023-02-02)", "",
             pd.DataFrame([gap]).to_markdown(index=False, floatfmt=".3f"), "",
             "### Last trade vs book mid as a forecast of the next tight quote (1 to 3 days ahead)", "",
             pd.DataFrame([fc]).to_markdown(index=False, floatfmt=".3f"), "",
             "### Rebuilt CUT90/HIKE90 vs the Milestone 1 index (all days both exist, from Jul 2021)", "",
             pd.DataFrame(vs_m1).to_markdown(index=False, floatfmt=".2f"), "",
             "## Settlement variants", "",
             "share_fallback: settlement mean used fewer than 5 days. share_lt3_valid: fewer than 3 valid days, which "
             "triggers the window extension in docs/spec.md section 5 (this run uses Ari's simpler fallback). "
             "no_trade is decision 005 point 3. share_S_changed / max_abs_dS: vs the base "
             "run, same expiry and lead.", "",
             tab.to_markdown(index=False, floatfmt=".3f"), ""]
    (OUT / "settlement_rule_check.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
