"""Figures for the futures backtest. Reads processed/futures_trades.csv (run futures.py first).

  fig_hedge_error.png   hedge error at index prices vs entry lead, by what happens before expiry
  fig_hedge_cost.png    round-trip trading cost of the hedge, near vs far contract, by index
Run: cd index && python figures.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from build import PROCESSED, RESULTS  # noqa: E402

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
CASES = [("no_meeting", "No FOMC meeting before expiry", "#2a78d6", "o"),
         ("meeting_hold", "Meeting, Fed held", "#eb6834", "s"),
         ("rate_move", "Meeting, Fed moved the rate", "#1baf7a", "^")]
NEAR, FAR = "#2a78d6", "#eb6834"


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def hedge_error(tr: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True, facecolor=SURF)
    leads = sorted(tr["lead"].unique())
    pos = {l: i for i, l in enumerate(leads)}
    rng = np.random.default_rng(0)
    for ax, idx in zip(axes, ("CUT90", "CUT60")):
        h = int(idx[3:])
        g = tr[(tr["side"] == "cut") & (tr["horizon"] == h)]
        for j, (c, lab, col, mk) in enumerate(CASES):
            x = g[g["case"] == c]
            xs = x["lead"].map(pos) + (j - 1) * 0.22 + rng.uniform(-0.06, 0.06, len(x))
            ax.scatter(xs, x["err_mid"], s=22, color=col, marker=mk, edgecolor=SURF, linewidth=0.8,
                       label=lab, zorder=3)
        ax.axhline(0, color=INK2, linewidth=0.8, zorder=2)
        ax.set_xticks(range(len(leads)), [str(l) for l in leads])
        ax.set_xlabel("Days from hedge purchase to expiry", color=INK2, fontsize=9)
        ax.set_title(idx, color=INK, fontsize=11, loc="left")
        _style(ax)
    axes[0].set_ylabel("Hedge proceeds minus settlement (\\$ per \\$100)", color=INK2, fontsize=9)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left", labelcolor=INK)
    fig.suptitle("The static hedge is exact unless the Fed changes the rate before expiry",
                 color=INK, fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_hedge_error.png", dpi=200, facecolor=SURF)
    plt.close(fig)


def hedge_cost(tr: pd.DataFrame):
    ex = tr[tr["executable"]]
    order = ["CUT60", "CUT90", "HIKE60", "HIKE90"]
    ex = ex.assign(index=ex["side"].str.upper() + ex["horizon"].astype(str))
    m = ex.groupby("index")[["cost_near", "cost_far"]].mean().reindex(order)
    q = ex.groupby("index")["qty_far"].mean().reindex(order)
    fig, ax = plt.subplots(figsize=(7.5, 3.6), facecolor=SURF)
    y = np.arange(len(order))[::-1]
    ax.barh(y, m["cost_near"], height=0.55, color=NEAR, label="Near contract (meeting before day H)")
    ax.barh(y, m["cost_far"], left=m["cost_near"] + 0.04, height=0.55, color=FAR,
            label="Far contract (meeting after day H)")
    for yi, i in zip(y, order):
        tot = m.loc[i].sum()
        ax.text(tot + 0.15, yi, f"\\${tot:.2f}  (far: {m.loc[i, 'cost_far'] / tot:.0%} of cost, "
                f"{q.loc[i] / 100:.0%} of contracts)", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, order)
    ax.set_xlim(0, max(m.sum(axis=1)) * 1.9)
    ax.set_xlabel("Mean round-trip cost of the hedge, spread + taker fees (\\$ per \\$100 contract)",
                  color=INK2, fontsize=9)
    _style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, labelcolor=INK)
    ax.set_title("The later contract costs more per contract and carries over half the hedging cost",
                 color=INK, fontsize=11, loc="left", pad=26)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_hedge_cost.png", dpi=200, facecolor=SURF)
    plt.close(fig)


def main():
    tr = pd.read_csv(PROCESSED / "futures_trades.csv")
    hedge_error(tr)
    hedge_cost(tr)


if __name__ == "__main__":
    main()
