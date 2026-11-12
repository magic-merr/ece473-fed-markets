"""Reset adjustment to the futures fair value, and dealer break-even (input for TASKS 14 and Ari's section).

Background (index/README.md, "For the spec and the theory"): the static-hedge fair value F0 is exact only if
the upper bound does not change before expiry. When the Fed moves, the index re-anchors to the new strike
while the hedge keeps the old one.

Mechanism, for CUT (HIKE is the mirror image). The hedge holds C_m = P(U_m <= U - 0.25), "at least one net
cut by meeting m". The index after a cut uses the new bound U' = U - 0.25, so it pays P(U_m <= U - 0.5),
"a further cut". The hedge leg goes to about 1 and the index only to the conditional probability of a second
cut, so the dealer (short future, long hedge) gains about 1 - P(2 cuts)/P(1 cut) per unit. A move against the
index costs the dealer only a little: the old strike is then two steps away and worth almost nothing.

Ex-ante adjustment, everything read off the Kalshi ladder on the entry day t:
  p_dir  = P(at least one step in the index's direction by the last meeting before expiry)
           (cut: 1 - Y_k(U - 0.25); hike: Y_k(U); k = last meeting on or before expiry)
  G      = sum over hedge tranches of q x (1 - P_two(m) / P_one(m)), the dealer's gain if that move happens
  F_adj  = F0 - p_dir x G
It ignores moves against the index and assumes the old hedge legs go to 1 after a move, so it is an upper
bound on the correction.

Run: cd src && python reset_check.py  (needs processed/futures_trades.csv: cd index && python futures.py)
     -> results/reset_adjustment.md
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


def adjustment(tr: pd.DataFrame, book) -> pd.DataFrame:
    def yes(m, k, d):
        return F.mark(book.get(m, k, d))[0]

    rows = []
    for r in tr.itertuples(index=False):
        W = F.window(r.expiry)
        U, side = r.u_entry, r.side
        meets = [m for m in legs.fomc_dates() if r.entry < m <= W[-1]]
        k1, k2 = (U - 0.25, U - 0.5) if side == "cut" else (U, U + 0.25)

        def p_one(m):
            y = yes(m, k1, r.entry)
            return np.nan if not np.isfinite(y) else (1 - y if side == "cut" else y)

        def p_two(m):
            y = yes(m, k2, r.entry)
            if not np.isfinite(y):
                return np.nan
            return 1 - y if side == "cut" else y

        if not meets or (side == "cut" and U <= 0.25):
            rows.append((0.0, 0.0))
            continue
        p_dir, G = p_one(meets[-1]), 0.0
        for d in W:
            m1, m2, w = build.bracket(d, r.horizon)
            for m, q in ((m1, 100 / F.SETTLE_DAYS * w), (m2, 100 / F.SETTLE_DAYS * (1 - w))):
                if q == 0:
                    continue
                a, b = p_one(m), p_two(m)
                if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
                    G = np.nan
                    break
                G += q * (1 - min(b / a, 1.0))
            if not np.isfinite(G):
                break
        rows.append((p_dir, G))
    tr = tr.copy()
    tr["p_dir"], tr["G"] = zip(*rows)
    tr["adj"] = tr["p_dir"] * tr["G"]
    tr["F_adj"] = tr["F0"] - tr["adj"]
    tr["pnl_long_adj"] = tr["S"] - tr["F_adj"]
    du = tr["u_expiry"] - tr["u_entry"]
    tr["move"] = np.where(tr["case"] != "rate_move", "none",
                          np.where(du == 0, "round_trip",
                                   np.where((du < 0) == (tr["side"] == "cut"), "with_index", "against_index")))
    return tr


def _rms(x):
    return float(np.sqrt((x ** 2).mean()))


def main():
    tr = pd.read_csv(ROOT / "processed" / "futures_trades.csv", parse_dates=["entry", "expiry"])
    tr["entry"], tr["expiry"] = tr["entry"].dt.date, tr["expiry"].dt.date
    tr["index"] = tr["side"].str.upper() + tr["horizon"].astype(str)
    tr = adjustment(tr, legs.book("src"))
    v = tr.dropna(subset=["adj"])

    by_move = (tr.groupby(["index", "move"])
               .agg(trades=("err_mid", "size"), mean_err=("err_mid", "mean"), sd_err=("err_mid", "std"))
               .reset_index())
    w = v[v["move"] == "with_index"]
    gain_check = (w.groupby("index")
                  .agg(trades=("err_mid", "size"), realized_gain=("err_mid", "mean"), predicted_G=("G", "mean"),
                       corr=("err_mid", lambda x: np.corrcoef(x, w.loc[x.index, "G"])[0, 1]))
                  .reset_index())
    calib = (v.groupby("index")
             .agg(trades=("adj", "size"), mean_p_dir=("p_dir", "mean"),
                  realized_share_with=("move", lambda m: (m == "with_index").mean()),
                  realized_share_against=("move", lambda m: (m == "against_index").mean()),
                  mean_adj=("adj", "mean"), mean_dealer_err=("err_mid", "mean"),
                  long_pnl_at_F0=("futures_pnl_long", "mean"), long_pnl_at_Fadj=("pnl_long_adj", "mean"),
                  rms_pnl_F0=("futures_pnl_long", _rms), rms_pnl_Fadj=("pnl_long_adj", _rms))
             .reset_index())
    by_lead = (v.groupby(["index", "lead"])
               .agg(trades=("adj", "size"), mean_p_dir=("p_dir", "mean"), mean_adj=("adj", "mean"),
                    mean_dealer_err=("err_mid", "mean"))
               .reset_index())
    ex = tr[tr["executable"]]
    be = (ex.groupby(["index", "lead"])
          .agg(trades=("err_mid", "size"), share_rate_move=("case", lambda c: (c == "rate_move").mean()),
               mean_err=("err_mid", "mean"), mean_cost=("cost_total", "mean"), mean_net=("err_exec", "mean"),
               p05_net=("err_exec", lambda x: x.quantile(0.05)), share_net_negative=("err_exec", lambda x: (x < 0).mean()))
          .reset_index())
    be_pool = (ex.groupby("index")
               .agg(trades=("err_mid", "size"), mean_err=("err_mid", "mean"), mean_cost=("cost_total", "mean"),
                    mean_net=("err_exec", "mean"), share_net_negative=("err_exec", lambda x: (x < 0).mean()),
                    cost_when_no_move=("cost_total", lambda x: x[ex.loc[x.index, "case"] != "rate_move"].mean()))
               .reset_index())

    md = lambda d: d.to_markdown(index=False, floatfmt=".2f")  # noqa: E731
    lines = [
        "# Reset adjustment and dealer break-even", "",
        f"Generated by `src/reset_check.py` on {dt.date.today()} from `processed/futures_trades.csv` "
        "(Ari's main run: src rule, from 2023-02-02). $ per $100 contract. err = hedge proceeds - settlement "
        "(dealer short the future, long the hedge). net = err - round-trip hedge cost.", "",
        "## 1. Dealer P&L by what the Fed did before expiry", "", md(by_move), "",
        "## 2. Predicted vs realized dealer gain when the Fed moved in the index's direction", "",
        f"Predicted G is read off the ladder on the entry day. Coverage: {len(v)} of {len(tr)} trades "
        "(the rest lack a two-step ladder price at entry).", "", md(gain_check), "",
        "## 3. Calibration of the ex-ante adjustment F_adj = F0 - p_dir x G", "", md(calib), "",
        "### By lead", "", md(by_lead), "",
        "## 4. Dealer break-even before any futures spread", "", md(be_pool), "", "### By lead", "", md(be), "",
    ]
    OUT.mkdir(exist_ok=True)
    (OUT / "reset_adjustment.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
