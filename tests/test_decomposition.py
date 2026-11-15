"""Tests for src/decomposition.py (P3): reproduction of the Milestone 1 tracking backtest and the identities."""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EXT = dt.date(2022, 3, 17)


@pytest.fixture(scope="module")
def D():
    """Imported at run time, not collection: importing index/legs.py early changes the sys.path order that
    test_pipeline.py relies on for `import figures` (src/ and index/ both have figures.py)."""
    import decomposition
    return decomposition


@pytest.fixture(scope="module")
def m1_one_day(D):
    return D.daily("m1", start=EXT, method="one_day")


@pytest.fixture(scope="module")
def main_chained(D):
    return D.daily(D.final_rule(), method="chained")


@pytest.mark.parametrize("col", ["CUT90", "HIKE90"])
def test_one_day_reproduces_milestone1_backtest(m1_one_day, col):
    bt = pd.read_csv(ROOT / "index_m1" / "data" / f"backtest_{col.lower()}.csv", parse_dates=["date"])
    bt = bt[bt["date"] >= pd.Timestamp(EXT)]
    bt["date"] = bt["date"].dt.date
    x = m1_one_day[(m1_one_day["index"] == col) & ~m1_one_day["dropped"]]
    assert len(x) == len(bt)
    m = x.merge(bt, on="date", suffixes=("", "_m1"))
    assert len(m) == len(bt)
    assert np.allclose(m["pnl"], m["pnl_m1"], atol=1e-9)
    assert np.allclose(m["dI"], m["dI_m1"], atol=1e-9)
    assert ((m["type"] == "announcement") == m["announce"]).all()


def test_ordinary_gap_is_minus_slope(main_chained):
    o = main_chained[~main_chained["dropped"] & (main_chained["type"] == "ordinary")]
    assert len(o) > 500
    assert np.allclose(o["gap"], -o["days"] * o["slope_t1"], atol=1e-12)


def test_components_add_up(D, main_chained):
    end = D.legs.data_end()
    c = pd.DataFrame(D.components(main_chained, "main", end))
    parts = c[["belief_change", "roll_down", "bracket_rolls", "announcement_resets"]].sum(axis=1)
    assert np.allclose(parts, c["index_change"], atol=1e-9)


def test_chained_telescopes(D, main_chained):
    """Chained intervals with nothing dropped sum to the change from first to last day with a value."""
    ix = D.build.build_index(D.final_rule(), 90).set_index("date")
    for col, g in main_chained.groupby("index"):
        s = ix[col].dropna()
        first = s[s.index < g["date"].min()].iloc[-1]
        assert np.isclose(g["dI"].sum(), s.iloc[-1] - first, atol=1e-9)


def test_every_rate_change_in_sample_is_an_announcement_interval(D, main_chained):
    p = D.legs.rate_path()
    moves = {d for d, c in zip(p["decision_date"], p["ub_after"].diff()) if c != 0 and d > D.build.SAMPLE_START}
    for col, g in main_chained.groupby("index"):
        rc = g[~g["dropped"] & g["rate_change"].astype(bool)]
        assert (rc["type"] == "announcement").all()
        assert len(rc) == len(moves)
