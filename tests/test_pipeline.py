import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fedwatch  # noqa: E402
import panel as P  # noqa: E402
import stale  # noqa: E402
from pull_polymarket import meeting_from_event, parse_bucket, TITLE_RE  # noqa: E402
from pull_kalshi import meeting_from_event as k_meeting, parse_candle  # noqa: E402


# ---------------------------------------------------------------- parsing
@pytest.mark.parametrize("label,exp", [
    ("No change", (0, False)), ("25 bps decrease", (-25, False)), ("50+ bps decrease", (-50, True)),
    ("25+ bps increase", (25, True)), ("Increase", (25, True)), ("Decrease 25 bps", (-25, False)),
])
def test_parse_bucket(label, exp):
    assert parse_bucket(label) == exp


@pytest.mark.parametrize("ticker,sub,exp", [
    ("KXFEDDECISION-25DEC-H0", "Hold", (0, False)), ("KXFEDDECISION-25DEC-C25", "Cut 25bps", (-25, False)),
    ("KXFEDDECISION-25DEC-C26", "Cut >25bps", (-50, True)), ("KXFEDDECISION-25DEC-H25", "Hike 25bps", (25, False)),
    ("KXFEDDECISION-25DEC-H26", "Hike >25bps", (50, True)),
    ("FEDDECISION-23MAY-TC25", "Cut >25bps", (-50, True)), ("FEDDECISION-23MAY-TH50", "Hike >50bps", (75, True)),
    ("FEDDECISION-23JUN-H>25", "Hike >25bps", (50, True)), ("FEDDECISION-23JUN-H0", "Hike 0bps", (0, False)),
    ("FEDDECISION-23MAY-H50", "Hike 50bps", (50, False)), ("X-OTHER", "Cut >25bps", (-50, True)),
    ("FEDDECISION-23DEC-C24", "Cut >25bps", (-50, True)), ("KXFEDDECISION-24DEC-H0", "No cut/hike", (0, False)), ("KXFEDDECISION-25DEC-C26", None, (-50, True)),
])
def test_kalshi_bucket(ticker, sub, exp):
    assert P.kalshi_bucket(ticker, sub) == exp


def test_titles_and_meetings():
    assert TITLE_RE.search("Fed decision in March?")
    assert TITLE_RE.search("Fed Interest Rates: November 2023")
    assert not TITLE_RE.search("Fed rate cut by June?")
    assert not TITLE_RE.search("How many Fed rate cuts in 2025?")
    assert meeting_from_event("Fed decision in December?", "2025-12-10T00:00:00Z") == dt.date(2025, 12, 10)
    assert k_meeting("FED-24MAR") == dt.date(2024, 3, 20)
    assert k_meeting("KXFED-26DEC") == dt.date(2026, 12, 9)
    assert k_meeting("KXFEDDECISION-23JUL") == dt.date(2023, 7, 26)


def test_strike_eff():
    assert P.strike_eff(4.25, "greater") == 4.25
    assert P.strike_eff(4.24, "greater") == 4.00          # U > 4.24  <=>  U > 4.00 on the grid
    assert P.strike_eff(4.25, "greater_or_equal") == 4.00  # U >= 4.25 <=>  U > 4.00


def test_parse_candle_both_formats():
    c_cents = {"end_period_ts": 1, "yes_bid": {"close": 42}, "yes_ask": {"close": 45},
               "price": {"close": 44, "mean": 43}, "volume": 10, "open_interest": 100}
    c_dollar = {"end_period_ts": 1, "yes_bid": {"close_dollars": "0.4200"}, "yes_ask": {"close_dollars": "0.4500"},
                "price": {"close_dollars": "0.4400", "mean_dollars": "0.4300"}, "volume_fp": "10.00",
                "open_interest_fp": "100.00"}
    c_hist = {"end_period_ts": 1, "yes_bid": {"close": "0.4200"}, "yes_ask": {"close": "0.4500"},
              "price": {"close": "0.4400", "mean": "0.4300"}, "volume": "10.00", "open_interest": "100.00"}
    assert parse_candle(c_cents) == parse_candle(c_dollar) == parse_candle(c_hist)


# ---------------------------------------------------------------- stale rule on the real project file
def test_rule_on_project_candles():
    c = pd.read_csv(ROOT / "raw/kalshi/candles/FED-23JUL-T3.75.csv")
    d = stale.kalshi_daily(c)
    # first candle (ends 2022-11-03 00:00 ET) covers 2022-11-02 and printed a trade at 0.53
    assert d.index[0] == dt.date(2022, 11, 2)
    assert d.loc[dt.date(2022, 11, 2), "last_trade"] == pytest.approx(0.53)
    r = stale.apply_kalshi_rule(d, n_days=3, max_spread=0.10)
    # ask is 1.00 (one-sided), so only trades can qualify: trade Nov 6 (0.14) is usable through Nov 9
    assert r.loc[dt.date(2022, 11, 5), "source"] == "trade"
    assert r.loc[dt.date(2022, 11, 9), "price"] == pytest.approx(0.14)
    assert r.loc[dt.date(2022, 11, 10), "source"] == "stale"
    # Mar 2023: bid 0.95 / ask 0.99 two-sided, 4c wide, updated that day -> quote
    assert r.loc[dt.date(2023, 3, 22), "source"] == "quote"
    assert r.loc[dt.date(2023, 3, 22), "price"] == pytest.approx(0.97)
    # tail fill: a stale day after a usable 0.97+ price keeps it for aggregation
    tf = stale.tail_filled(r["price"], r["last_usable"])
    assert tf.loc[dt.date(2023, 3, 30)] == pytest.approx(r["last_usable"].loc[dt.date(2023, 3, 30)])


def test_poly_rule():
    t0 = int(pd.Timestamp("2025-01-01 15:00", tz="America/New_York").timestamp())
    prices = pd.DataFrame({"t": [t0 + 86400 * k for k in range(10)], "p": np.linspace(0.5, 0.6, 10)})
    trades = pd.DataFrame({"ts": [t0, t0 + 86400 * 5], "yes_price": [0.5, 0.55], "size": [10, 20],
                           "side": ["BUY", "SELL"], "token": ["yes", "no"]})
    d = stale.apply_poly_rule(stale.poly_daily(prices, trades), n_days=3)
    assert d.loc[dt.date(2025, 1, 4), "source"] == "trade"
    assert d.loc[dt.date(2025, 1, 5), "source"] == "stale"
    assert d.loc[dt.date(2025, 1, 6), "source"] == "trade"
    assert d.loc[dt.date(2025, 1, 6), "volume"] == 20


# ---------------------------------------------------------------- FedWatch math
def test_fedwatch_clean_month_and_in_month():
    obs = dt.date(2026, 10, 1)
    effr = 4.33
    futures = {dt.date(2026, 11, 1): 100 - 4.08,                              # no Nov meeting: clean anchor
               dt.date(2026, 12, 1): 100 - (9 * 4.08 + 22 * 3.95) / 31}       # Dec 9 meeting
    rates = fedwatch.meeting_rates(obs, effr, futures)
    r0, r1 = rates[dt.date(2026, 10, 28)]
    assert (r0, r1) == pytest.approx((4.33, 4.08))
    assert fedwatch.decision_probs((r1 - r0) * 100)["p_cut"] == pytest.approx(1.0)
    r0, r1 = rates[dt.date(2026, 12, 9)]
    assert r0 == pytest.approx(4.08) and r1 == pytest.approx(3.95)
    p = fedwatch.decision_probs((r1 - r0) * 100)
    assert p["p_cut"] == pytest.approx(13 / 25) and p["p_hold"] == pytest.approx(12 / 25)


def test_two_point_hike_and_big_cut():
    assert fedwatch.two_point(10) == pytest.approx({0: 0.6, 25: 0.4})
    assert fedwatch.two_point(-40) == pytest.approx({-50: 0.6, -25: 0.4})


# ---------------------------------------------------------------- end-to-end on synthetic raw data
def _candle_rows(days, bid, ask, last, vol, oi=100):
    out = []
    for d in days:
        end = int((pd.Timestamp(d, tz="America/New_York") + pd.Timedelta(days=1)).timestamp())
        out.append({"end_period_ts": end, "yes_bid_close": bid, "yes_ask_close": ask, "price_close": last,
                    "price_mean": last, "volume": vol, "open_interest": oi})
    return pd.DataFrame(out)


def test_end_to_end(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    kal, kc_dir, poly, rates = raw / "kalshi", raw / "kalshi/candles", raw / "polymarket", raw / "rates"
    for p in (kc_dir, poly / "prices", poly / "trades", rates / "zq", tmp_path / "processed"):
        p.mkdir(parents=True, exist_ok=True)
    meet = dt.date(2025, 12, 10)
    days = pd.date_range("2025-12-01", "2025-12-09").date
    # EFFR / target range: 3.75-4.00 before, 3.50-3.75 after
    eff = pd.DataFrame({"date": pd.date_range("2025-10-01", "2025-12-20").date})
    eff["rate"] = np.where(eff["date"] <= meet, 3.88, 3.63)
    eff["target_lo"] = np.where(eff["date"] <= meet, 3.75, 3.50)
    eff["target_hi"] = eff["target_lo"] + 0.25
    eff["volume_bn"] = 100
    eff.to_csv(rates / "effr.csv", index=False)
    # Kalshi: decision series (cut 0.80, hold 0.18, hike tail 0.02 stale) + ladder strikes 3.50 / 3.75 / 4.00
    mk = []
    def add(t, series, strike=None, sub=None, result="", **kw):
        mk.append({"series": series, "tier": "historical", "ticker": t, "event_ticker": t.rsplit("-", 1)[0],
                   "meeting": meet, "status": "settled", "result": result, "open_time": "2025-11-01T00:00:00Z",
                   "close_time": "2025-12-10T19:00:00Z", "strike_type": "greater" if strike else None,
                   "floor_strike": strike, "cap_strike": None, "yes_sub_title": sub, "subtitle": None,
                   "title": None, "volume": 0, "open_interest": 0})
        _candle_rows(days, **kw).to_csv(kc_dir / f"{t}.csv", index=False)
    add("KXFEDDECISION-25DEC-C25", "KXFEDDECISION", sub="Cut 25bps", bid=0.79, ask=0.81, last=0.80, vol=50)
    add("KXFEDDECISION-25DEC-H0", "KXFEDDECISION", sub="Hold", bid=0.17, ask=0.19, last=0.18, vol=50)
    add("KXFEDDECISION-25DEC-H25", "KXFEDDECISION", sub="Hike 25bps", bid=0.0, ask=0.02, last=0.02, vol=0)
    add("KXFED-25DEC-T3.50", "KXFED", strike=3.50, result="yes", bid=0.98, ask=0.99, last=0.99, vol=5)
    add("KXFED-25DEC-T3.75", "KXFED", strike=3.75, result="no", bid=0.19, ask=0.21, last=0.20, vol=5)
    add("KXFED-25DEC-T4.00", "KXFED", strike=4.00, result="no", bid=0.01, ask=0.02, last=0.01, vol=5)
    pd.DataFrame(mk).to_csv(kal / "markets.csv", index=False)
    pd.DataFrame([{"series": "KXFED", "fee_type": "quadratic_with_maker_fees", "fee_multiplier": 1},
                  {"series": "KXFEDDECISION", "fee_type": "quadratic", "fee_multiplier": 1}]).to_csv(
        kal / "series_fees.csv", index=False)
    # the hike tail never traded and has a one-sided book: it must be tail-filled for the decision aggregate
    # Polymarket: cut 0.70, hold 0.30
    pm = []
    for cid, lab, bps, p in (("0xcut", "25 bps decrease", -25, 0.70), ("0xhold", "No change", 0, 0.30)):
        pm.append({"meeting": meet, "condition_id": cid, "label": lab, "bps": bps, "open_ended": False,
                   "yes_token": cid + "y", "no_token": cid + "n", "start": "2025-11-01", "end": "2025-12-10",
                   "closed": True})
        ts = [int(pd.Timestamp(d, tz="America/New_York").timestamp()) + 50000 for d in days]
        pd.DataFrame({"t": ts, "p": p}).to_csv(poly / "prices" / f"{cid}.csv", index=False)
        pd.DataFrame({"ts": ts, "yes_price": p, "size": 10.0, "side": "BUY", "token": "yes"}).to_csv(
            poly / "trades" / f"{cid}.csv", index=False)
    pd.DataFrame(pm).to_csv(poly / "markets.csv", index=False)
    for name, val in {"KALSHI_RAW": kal, "KALSHI_CANDLES": kc_dir, "POLY_RAW": poly, "RATES_RAW": rates,
                      "PROCESSED": tmp_path / "processed", "TODAY": dt.date(2025, 12, 20)}.items():
        monkeypatch.setattr(P, name, val)
    panel, kc, pc, oc, lvl = P.build(3, 0.10, write=True)
    assert oc.set_index("meeting").loc[meet, "decision"] == "cut"
    pol = panel[(panel.venue == "polymarket") & (panel.date == dt.date(2025, 12, 9))].iloc[0]
    assert pol.p_cut == pytest.approx(0.70) and pol.p_hold == pytest.approx(0.30)
    lad = panel[(panel.venue == "kalshi_ladder") & (panel.date == dt.date(2025, 12, 9))].iloc[0]
    # U0 = 4.00: P(cut) = 1 - P(U > 3.75) = 0.80, P(hike) = P(U > 4.00) = 0.015
    assert lad.p_cut == pytest.approx(0.80) and lad.p_hike == pytest.approx(0.015)
    # hike bucket: no bid, ask 0.02, never traded -> bounded tail, filled at 0.01; decision series is used
    k = panel[(panel.venue == "kalshi") & (panel.date == dt.date(2025, 12, 9))].iloc[0]
    assert k.kalshi_source == "kalshi_decision"
    assert k.p_hike == pytest.approx(0.01 / 0.99) and k.p_cut == pytest.approx(0.80 / 0.99)
    # E[upper] from the full ladder: 3.50 + 0.25*(0.985 + 0.20 + 0.015) = 3.80
    assert lvl.set_index("date").loc[dt.date(2025, 12, 9), "exp_upper"] == pytest.approx(3.80)
    # fees on the ladder series include maker fees
    r = kc[(kc.ticker == "KXFED-25DEC-T3.75") & (kc.date == dt.date(2025, 12, 9))].iloc[0]
    assert r.fee_taker == pytest.approx(0.07 * 0.2 * 0.8) and r.fee_maker == pytest.approx(0.0175 * 0.2 * 0.8)
    assert r.fee_taker_1lot == pytest.approx(0.02)
    # compare.py smoke test on the same synthetic build
    import compare as C
    monkeypatch.setattr(C, "RESULTS", tmp_path)
    pw = C.pairwise(panel)
    row = pw[(pw.pair == "kalshi - polymarket") & (pw.horizon == "all")].iloc[0]
    assert row.mean_diff_p_cut == pytest.approx(0.80 / 0.99 - 0.70)
    acc = C.accuracy(panel, oc, horizons=(1,))
    assert acc.set_index("venue").loc["polymarket", "brier"] == pytest.approx(0.3 ** 2 + 0.3 ** 2)
    g = C.gap_vs_cost(kc, pc)
    hold = g[(g.bps == 0) & (g.date == dt.date(2025, 12, 9))].iloc[0]
    assert hold.gap == pytest.approx(0.12)
    assert hold.cost_lb == pytest.approx(0.01 + 0.07 * 0.18 * 0.82 + 0.0)   # Poly fee on (Dec 2025 > Mar 2026? no)
    liq = C.kalshi_liquidity(kc.assign(meeting=kc.meeting))
    assert len(liq) > 0
    import figures as F
    monkeypatch.setattr(F, "RESULTS", tmp_path)
    F.fig_meetings(panel, oc)
    F.fig_scatter(panel)
    F.fig_sources(C.source_shares(kc, pc))
    assert (tmp_path / "fig_meetings.png").exists() and (tmp_path / "fig_price_sources.png").exists()
    import shutil; shutil.copy(tmp_path / "fig_meetings.png", "/tmp/fig_test.png")
    shutil.copy(tmp_path / "fig_price_sources.png", "/tmp/fig_test2.png")


def test_clean_bucket_filter():
    from pull_polymarket import is_clean_bucket
    for ok in ("No change", "25 bps decrease", "50+ bps decrease", "0 bps increase after May meeting?", "25bp hike"):
        assert is_clean_bucket(ok), ok
    for bad in ("25bp cut, Dissents: >2", "'No change' or '25 bps cut' favored for Fed decision in January on December 10?"):
        assert not is_clean_bucket(bad), bad


def test_tick_bound_branch():
    d = pd.DataFrame({"bid": [0.0, 0.99, 0.40], "ask": [0.01, 1.0, 0.42], "quote_age": [0, 0, 0],
                      "trade_age": [0, 0, 0], "last_trade": [0.01, 0.99, 0.41]},
                     index=pd.Index([dt.date(2025, 1, d) for d in (1, 2, 3)], name="date"))
    on = stale.apply_kalshi_rule(d, 3, 0.10, tick_bound=True)
    off = stale.apply_kalshi_rule(d, 3, 0.10, tick_bound=False)
    assert list(on["source"]) == ["bound", "bound", "quote"]
    assert list(on["price"]) == pytest.approx([0.005, 0.995, 0.41])
    assert list(off["price"]) == pytest.approx([0.01, 0.99, 0.41])
