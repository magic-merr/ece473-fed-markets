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
    assert t["move_direction"] == "cut"
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
    return F.run()[0]          # decision 007: rule final, spec calendar, spec fallback


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
    cd = legs.contract_days("final")
    px = {(r.meeting, round(r.strike, 4), r.date): r for r in cd.itertuples(index=False)}
    ix = {h: build.build_index("final", h).set_index("date") for h in (60, 90)}
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


# ---------------------------------------------------------------- decision 007 (A2, A3)
def test_final_rule_is_wide_mid_days():
    """A2: rule `final` equals src/settlement_check.py::wide_mid_days exactly."""
    sys.path.insert(0, str(legs.ROOT / "src"))
    import settlement_check as SC
    a, b = legs.contract_days("final"), SC.wide_mid_days()
    assert a.shape == b.shape and (a["source"].to_numpy() == b["source"].to_numpy()).all()
    assert np.array_equal(a["value"].to_numpy(float), b["value"].to_numpy(float), equal_nan=True)
    w = a[a["source"] == "wide_mid"]
    assert len(w) > 0 and (w["bid"] > 0).all() and (w["ask"] < 1).all() and (w["quote_age"] <= 3).all()
    assert np.allclose(w["value"], (w["bid"] + w["ask"]) / 2)
    import inspect
    assert build.RULE == "final" and F.RULE == "final"
    assert inspect.signature(legs.book).parameters["rule"].default == "final"
    assert inspect.signature(build.build_index).parameters["rule"].default == "final"


def test_spec_calendar():
    """A3: spec section 4 calendar = the reference; 5 of the 44 old expiries move, each back one week."""
    sys.path.insert(0, str(legs.ROOT / "src"))
    import settlement_check as SC
    end = legs.data_end()
    for start in (build.SAMPLE_START, build.EXT_START):
        assert F.expiries(start, end, "spec") == SC.expiries_no_decision(start, end)
    old, new = F.expiries(build.SAMPLE_START, end, "m1"), F.expiries(build.SAMPLE_START, end, "spec")
    moved = sorted(set(old) - set(new))
    assert len(old) == 44 and len(moved) == 5
    assert all(m - dt.timedelta(days=7) in new for m in moved)
    assert sorted(set(new) - set(old)) == sorted([m - dt.timedelta(days=7) for m in moved] + [D(2026, 10, 23)])
    for e in new:
        assert not F._spec_blocked(e, legs.fomc_dates())


def _imap(values: dict):
    return {d: v for d, v in values.items()}


E0 = D(2024, 10, 25)   # spec expiry, no decision within 10 days before it (2024-09-18 and 2024-11-07 decisions)


def test_settle_spec_full_and_mean_of_valid():
    W = F.window(E0)
    st = F.settle_spec(_imap({d: 0.1 * (i + 1) for i, d in enumerate(W)}), E0)
    assert st["method"] == "full" and st["S"] == pytest.approx(30.0)
    st = F.settle_spec(_imap({W[0]: 0.2, W[2]: 0.4, W[4]: 0.9, W[1]: np.nan}), E0)
    assert st["method"] == "mean_of_valid" and st["S"] == pytest.approx(50.0) and st["days"] == [W[0], W[2], W[4]]


def test_settle_spec_extended_takes_three_most_recent():
    v = {E0: 0.6, E0 - dt.timedelta(days=6): 0.3, E0 - dt.timedelta(days=7): 0.9,
         E0 - dt.timedelta(days=9): 0.0, E0 - dt.timedelta(days=12): 0.5}
    st = F.settle_spec(_imap(v), E0)
    assert st["method"] == "extended" and st["days"] == sorted([E0, E0 - dt.timedelta(days=6), E0 - dt.timedelta(days=7)])
    assert st["S"] == pytest.approx(60.0)
    # only 2 valid within 10 days (E-12 is outside) -> not extended
    st = F.settle_spec(_imap({E0: 0.6, E0 - dt.timedelta(days=9): 0.2, E0 - dt.timedelta(days=12): 0.5,
                              E0 + dt.timedelta(days=3): 0.7}), E0)
    assert st["method"] == "deferred"


def test_settle_spec_extension_stops_at_a_decision(monkeypatch):
    dec = E0 - dt.timedelta(days=7)
    monkeypatch.setattr(legs, "fomc_dates", lambda: (dec,))
    v = {E0: 0.6, dec: 0.2, E0 - dt.timedelta(days=8): 0.9, E0 + dt.timedelta(days=3): 0.4}
    st = F.settle_spec(_imap(v), E0)
    assert st["method"] == "deferred" and st["S"] == pytest.approx(40.0)   # E-8 is before the decision
    v[E0 - dt.timedelta(days=5)] = 0.3                                      # third valid day after it
    st = F.settle_spec(_imap(v), E0)
    assert st["method"] == "extended" and dec in st["days"] and st["S"] == pytest.approx(100 * (0.6 + 0.3 + 0.2) / 3)


def test_settle_spec_deferred_uses_business_days_then_backstop():
    sat, mon = E0 + dt.timedelta(days=1), E0 + dt.timedelta(days=3)
    st = F.settle_spec(_imap({sat: 0.9, mon: 0.4}), E0)
    assert st["method"] == "deferred" and st["days"] == [mon] and st["decided"] == mon
    last10 = [x.date() for x in pd.bdate_range(E0 + dt.timedelta(days=1), periods=10)][-1]
    st = F.settle_spec(_imap({E0 - dt.timedelta(days=20): 0.35, last10 + dt.timedelta(days=1): 0.8}), E0)
    assert st["method"] == "backstop" and st["S"] == pytest.approx(35.0) and st["decided"] == last10
    st = F.settle_spec(_imap({}), E0, data_end=E0 + dt.timedelta(days=2))
    assert st == {"status": "settlement_beyond_data"}


def test_spec_fallback_hedge_is_causal(syn):
    """A window day without an index value: its tranche is sold on the next valid window day."""
    book, ix = syn
    E, t0 = D(2025, 8, 29), D(2025, 7, 31)
    im = imap(ix, 90, "cut")
    gap = E - dt.timedelta(days=2)
    im[gap] = np.nan
    t = F.hedge_trade(book, im, 90, "cut", E, t0, fallback="spec")
    assert t["settle_method"] == "mean_of_valid" and t["settle_days_valid"] == 4
    proceeds = 0.0
    for d in F.window(E):
        sale = d if d != gap else d + dt.timedelta(days=1)
        m1, m2, w = build.bracket(d, 90)
        for m, x in ((m1, w), (m2, 1 - w)):
            proceeds += 20 * x * (1 - yes_price(m, 4.25, sale))
    S = 100 * np.mean([im[d] for d in F.window(E) if d != gap])
    assert t["S"] == pytest.approx(S) and t["err_mid"] == pytest.approx(proceeds - S)
    # same trade under the 11/12 fallback sells the same way (a later valid day exists)
    t2 = F.hedge_trade(book, im, 90, "cut", E, t0, fallback="ari1112")
    assert t2["err_mid"] == pytest.approx(t["err_mid"])


def test_final_config_exact_without_rate_change(real):
    full = real[(real["case"] != "rate_move") & (real["settle_method"] == "full")]
    assert len(full) > 400 and full["err_mid"].abs().max() < 1e-9
    assert set(real["settle_method"]) <= {"full", "mean_of_valid", "extended", "deferred", "backstop"}
    assert real["expiry"].nunique() == 45 and not real["decision_in_window"].any()


def test_1112_configuration_reproduces_the_1112_tables():
    """Robustness row: src rule, Milestone 1 calendar, 11/12 fallback == the committed 11/12 tables."""
    tr, sk = F.run("src", calendar="m1", fallback="ari1112")
    ref = Path(__file__).resolve().parent / "ref_1112"
    tabs = {"futures_accuracy_by_case": F.accuracy_by_case(tr), "futures_costs_pooled": F.costs_pooled(tr),
            "futures_fair_value": F.fair_value(tr), "futures_capital": F.capital(tr),
            "futures_rate_move_events": F.move_events(tr), "futures_coverage": F.coverage(tr, sk)}
    for k, v in tabs.items():
        assert v.to_csv(index=False) == (ref / f"{k}.csv").read_text(), k


# ---------------------------------------------------------------- A5, A6
def test_direction_table(real):
    assert ((real["move_direction"] == "none") == (real["case"] != "rate_move")).all()
    tab = F.error_by_direction(real)
    assert set(tab["relative_to_index"]) <= {"with", "against", "mixed"}
    assert tab["trades"].sum() == (real["case"] == "rate_move").sum()
    for r in tab.itertuples(index=False):
        x = real[(real["case"] == "rate_move") & (real["move_direction"] == r.direction)
                 & (real["side"] + real["horizon"].astype(str) == r.index.lower())]
        assert r.mean_err == pytest.approx(x["err_mid"].mean()) and r.trades == len(x)


def test_event_study():
    import event_study as ES
    dec = ES.decisions()
    assert len(dec) == 29 and dec["decision"].value_counts().to_dict() == {"hold": 19, "cut": 6, "hike": 4}
    assert dec["decision_date"].min() >= build.SAMPLE_START and dec["decision_date"].max() <= legs.data_end()
    ix = build.build_index("final", 90)
    ev = ES.event_table(ix, dec)
    s = dict(zip(ix["date"], ix["CUT90"]))
    r = ev[ev["decision_date"] == D(2024, 12, 18)].iloc[0]           # 25bp cut
    assert r["CUT90_change"] == pytest.approx(100 * (s[D(2024, 12, 18)] - s[D(2024, 12, 17)]))
    assert r["CUT90_change"] < -40
