"""Tests for index/legs.py, index/build.py and index/futures.py.

Synthetic tests pin down the hedge mechanics with hand calculations; the real-data tests check the
rebuilt index against the frozen Milestone 1 index and recompute real trades independently.
Run: cd index && python -m pytest tests -q
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import futures as F  # noqa: E402
import legs  # noqa: E402

D = dt.date


# ---------------------------------------------------------------- synthetic market
def yes_price(meeting, k, day):
    base = 1 / (1 + np.exp((k - 4.25) * 3))
    drift = 0.02 * np.sin(day.toordinal() / 9.0 + k) + 0.01 * ((meeting.toordinal() % 7) - 3) / 3
    return float(np.clip(base + drift, 0.04, 0.96))


STRIKES = [3.25, 3.50, 3.75, 4.00, 4.25, 4.50, 4.75, 5.00]


@pytest.fixture(scope="module")
def syn():
    meets = [m for m in legs.fomc_dates() if D(2025, 6, 1) <= m <= D(2026, 6, 30)]
    rows = []
    for m in meets:
        for k in STRIKES:
            for d in pd.date_range("2025-06-01", "2026-01-31").date:
                if d < m:
                    p = yes_price(m, k, d)
                    rows.append({"date": d, "meeting": m, "strike": k, "value": p, "bid": p - 0.01,
                                 "ask": p + 0.01, "source": "quote", "quote_age": 0.0})
    book = legs.Book(pd.DataFrame(rows), taker_rate=0.07)
    ix = {h: build.build_index("src", h, start=D(2025, 6, 2), end=D(2026, 1, 31), book=book) for h in (60, 90)}
    return book, ix


def imap(ix, h, side):
    x = ix[h]
    return dict(zip(x["date"], x[f"{side.upper()}{h}"]))


# ---------------------------------------------------------------- calendar and index
def test_bracket_and_weights():
    m1, m2, w = build.bracket(D(2025, 12, 10) - dt.timedelta(days=90), 90)
    assert (m1, m2, w) == (D(2025, 12, 10), D(2026, 1, 28), 1.0)
    m1, m2, w = build.bracket(D(2025, 12, 10) - dt.timedelta(days=89), 90)
    assert w == pytest.approx(48 / 49)
    for h in (60, 90):
        for d in pd.date_range("2022-03-17", "2026-10-26").date:
            m1, m2, w = build.bracket(d, h)
            assert d < m1 <= d + dt.timedelta(days=h) < m2 and 0 < w <= 1


def test_rate_path_matches_ny_fed():
    """Upper bound from settled Kalshi ladders vs the NY Fed path Palmer's data layer reports."""
    ny = {"2023-02-01": 4.75, "2023-07-26": 5.50, "2024-09-18": 5.00, "2024-12-18": 4.50,
          "2025-12-10": 3.75, "2026-09-16": 4.00}
    for d, u in ny.items():
        assert build.ub_at(D.fromisoformat(d)) == u          # the announcement day already uses the new level


def test_expiry_calendar():
    ex = F.expiries(D(2022, 3, 1), D(2026, 10, 26))
    assert len(ex) == len(set(ex)) and all(e.weekday() == 4 for e in ex)
    for e in ex:
        assert all(abs(np.busday_count(min(e, f), max(e, f))) >= 2 for f in legs.fomc_dates())
        nxt = e + dt.timedelta(days=7)
        assert nxt.month != e.month or any(abs(np.busday_count(min(nxt, f), max(nxt, f))) <= 1
                                           for f in legs.fomc_dates())
    assert F.window(D(2026, 9, 25)) == [D(2026, 9, 21) + dt.timedelta(days=k) for k in range(5)]


def test_index_hand_calc(syn):
    book, ix = syn
    d = D(2025, 7, 15)
    r = ix[90][ix[90]["date"] == d].iloc[0]
    m1, m2, w = build.bracket(d, 90)
    assert r["ub"] == 4.50
    assert r["CUT90"] == pytest.approx(w * (1 - yes_price(m1, 4.25, d)) + (1 - w) * (1 - yes_price(m2, 4.25, d)))
    assert r["HIKE90"] == pytest.approx(w * yes_price(m1, 4.50, d) + (1 - w) * yes_price(m2, 4.50, d))


# ---------------------------------------------------------------- hedge mechanics
def test_hedge_exact_without_rate_change(syn):
    book, ix = syn
    for side in F.SIDES:
        for h in (60, 90):
            t = F.hedge_trade(book, imap(ix, h, side), h, side, D(2025, 8, 29), D(2025, 7, 31))
            assert t["case"] == "no_meeting" and abs(t["err_mid"]) < 1e-9
            t = F.hedge_trade(book, imap(ix, h, side), h, side, D(2025, 8, 29), D(2025, 7, 25))
            assert t["case"] == "meeting_hold" and abs(t["err_mid"]) < 1e-9     # 2025-07-30 hold


def test_hedge_error_on_cut_is_the_strike_reset(syn):
    book, ix = syn
    E, t0 = D(2025, 9, 26), D(2025, 9, 5)            # 2025-09-17: 4.50 -> 4.25
    t = F.hedge_trade(book, imap(ix, 90, "cut"), 90, "cut", E, t0)
    assert t["case"] == "rate_move" and t["strike"] == 4.25 and t["u_expiry"] == 4.25
    hedge = settle = 0.0
    for d in F.window(E):
        m1, m2, w = build.bracket(d, 90)
        for m, x in ((m1, w), (m2, 1 - w)):
            hedge += 20 * x * (1 - yes_price(m, 4.25, d))     # old strike, held since t0
            settle += 20 * x * (1 - yes_price(m, 4.00, d))    # index re-struck at the new upper bound
    assert t["err_mid"] == pytest.approx(hedge - settle) and t["err_mid"] > 0
    h = F.hedge_trade(book, imap(ix, 90, "hike"), 90, "hike", E, t0)
    assert h["err_mid"] < 0                               # a cut hurts the dealer hedging HIKE


def test_costs_and_capital(syn):
    book, ix = syn
    t = F.hedge_trade(book, imap(ix, 90, "cut"), 90, "cut", D(2025, 8, 29), D(2025, 7, 31))
    assert t["cost_spread"] == pytest.approx(2.0)          # 1c each way on 100 units in and 100 out
    exp_fee = 0.0                                         # hand calc: 0.07 P(1-P) at each execution price
    for d in F.window(D(2025, 8, 29)):
        m1, m2, w = build.bracket(d, 90)
        for m, x in ((m1, w), (m2, 1 - w)):
            pb = 1 - (yes_price(m, 4.25, D(2025, 7, 31)) - 0.01)     # buy NO at 1 - yes bid
            ps = 1 - (yes_price(m, 4.25, d) + 0.01)                   # sell NO at 1 - yes ask
            exp_fee += 20 * x * 0.07 * (pb * (1 - pb) + ps * (1 - ps))
    assert t["cost_fee"] == pytest.approx(exp_fee)
    assert t["cost_total"] == pytest.approx(t["cost_near"] + t["cost_far"])
    assert t["cost_total"] == pytest.approx(t["cost_entry"] + t["cost_exit"])
    assert t["err_exec"] == pytest.approx(t["err_mid"] - t["cost_total"])
    assert t["capital_dealer"] == pytest.approx(100 + t["cost_entry"])
    assert t["capital_long"] == pytest.approx(t["F0"]) and t["qty_near"] + t["qty_far"] == pytest.approx(100)
    assert t["F0"] + t["futures_pnl_long"] == pytest.approx(t["S"])


def test_marks_and_execution():
    assert F.exec_price("cut", "buy", (0.60, 0.58, 0.62, "quote", 0)) == pytest.approx(0.42)
    assert F.exec_price("cut", "sell", (0.60, 0.58, 0.62, "quote", 0)) == pytest.approx(0.38)
    assert F.exec_price("hike", "sell", (0.60, 0.58, 0.62, "quote", 0)) == pytest.approx(0.58)
    assert F.mark((np.nan, 0.40, 0.50, "stale", 9)) == (pytest.approx(0.45), "book_mid")
    assert F.mark((np.nan, 0.0, 0.08, "stale", 9)) == (pytest.approx(0.04), "book_bound")
    assert np.isnan(F.mark((np.nan, 0.0, 0.50, "stale", 9))[0])
    assert F.exec_price("hike", "sell", (np.nan, 0.0, 0.08, "stale", 9)) == 0.0
    assert np.isnan(F.exec_price("hike", "sell", (np.nan, 0.0, 0.50, "stale", 9)))


# ---------------------------------------------------------------- real data
@pytest.fixture(scope="module")
def real():
    return F.run("src")[0]


def test_rebuild_reproduces_milestone1_index():
    ix = build.build_index("m1", 90)
    m1 = pd.read_csv(legs.M1 / "data" / "index_daily.csv", parse_dates=["date"])
    m1["date"] = m1["date"].dt.date
    x = ix.merge(m1, on="date", suffixes=("", "_ref"))
    assert len(x) == len(m1) == len(ix)
    for c in ("w", "ub", "C1", "C2", "H1", "H2", "CUT90", "HIKE90"):
        assert (x[c].isna() == x[f"{c}_ref"].isna()).all()
        assert np.nanmax(np.abs(x[c] - x[f"{c}_ref"])) < 1e-12


def test_real_hedge_exact_unless_rate_moves(real):
    nm = real[(real["case"] != "rate_move") & ~real["fallback"]]
    assert len(nm) > 500 and nm["err_mid"].abs().max() < 1e-9


def test_real_trades_recomputed_independently(real):
    """Recompute settlement and hedge proceeds straight from the contract-day table for a sample of trades."""
    cd = legs.contract_days("src")
    px = {(r.meeting, round(r.strike, 4), r.date): r for r in cd.itertuples(index=False)}
    ix = {h: build.build_index("src", h).set_index("date") for h in (60, 90)}
    sample = pd.concat([real[real["case"] == c].sample(8, random_state=1) for c in ("no_meeting", "meeting_hold", "rate_move")])
    checked = {}
    for t in sample.itertuples(index=False):
        col = f"{t.side.upper()}{t.horizon}"
        win = [t.expiry - dt.timedelta(days=k) for k in range(4, -1, -1)]
        vals = [ix[t.horizon].loc[d, col] for d in win if d in ix[t.horizon].index]
        vals = [v for v in vals if np.isfinite(v)]
        if t.settle_waited or len(vals) < 5:
            continue
        assert t.S == pytest.approx(100 * np.mean(vals))
        proceeds = 0.0
        for d in win:
            m1, m2, w = build.bracket(d, t.horizon)
            for m, x in ((m1, w), (m2, 1 - w)):
                r = px[(m, t.strike, d)]
                y = r.value if np.isfinite(r.value) else F.mark((r.value, r.bid, r.ask, r.source, r.quote_age))[0]
                proceeds += 20 * x * ((1 - y) if t.side == "cut" else y)
        assert t.err_mid == pytest.approx(proceeds - t.S, abs=1e-9)
        checked[t.case] = checked.get(t.case, 0) + 1
    assert all(checked.get(c, 0) >= 3 for c in ("no_meeting", "meeting_hold", "rate_move")), checked
