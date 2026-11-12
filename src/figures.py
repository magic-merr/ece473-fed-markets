"""Figures for results/. Palette validated with the dataviz validator (light surface):
Kalshi #2a78d6, Polymarket #eb6834, ZQ #1baf7a (ZQ also dashed + direct label: below 3:1 contrast)."""
from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from config import RESULTS  # noqa: E402
import compare as C  # noqa: E402

COL = {"kalshi": "#2a78d6", "polymarket": "#eb6834", "zq": "#1baf7a"}
NAME = {"kalshi": "Kalshi", "polymarket": "Polymarket", "zq": "Fed funds futures (FedWatch method)"}
STYLE = {"kalshi": "-", "polymarket": "-", "zq": "--"}
INK, MUTED, GRID, SURF = "#1f1f1e", "#6b6a64", "#e6e5e0", "#fcfcfb"

plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 9, "lines.linewidth": 2})


def gapped(s: pd.DataFrame, xcol: str, ycol: str, step: int):
    """Insert NaN where consecutive x values jump by more than one step, so lines break at data gaps."""
    s = s.sort_values(xcol)
    x = s[xcol].to_numpy()
    y = s[ycol].to_numpy(float)
    if len(x) < 2:
        return x, y
    dx = np.abs(np.diff(x.astype("datetime64[D]").astype(int) if x.dtype.kind in "OM" else x))
    cut = np.where(dx > step)[0] + 1
    return np.insert(x.astype(object), cut, None), np.insert(y, cut, np.nan)


def p_realized(pn, oc):
    o = oc.set_index("meeting")["decision"]
    pn = pn[pn.meeting.isin(o.index)].copy()
    pn["p_real"] = [getattr(r, f"p_{o[r.meeting]}") for r in pn.itertuples()]
    return pn


def fig_meetings(pn, oc, max_days=60):
    d = p_realized(pn[pn.venue.isin(C.MAIN)], oc)
    both = d.groupby("meeting")["venue"].nunique()
    meets = sorted(both[both >= 2].index)
    if not meets:
        return
    n = len(meets)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(12, 2.4 * rows), sharex=True, sharey=True, squeeze=False)
    dec = oc.set_index("meeting")["decision"]
    for ax, m in zip(axs.flat, meets):
        g = d[(d.meeting == m) & (d.days_to_meeting <= max_days)]
        for v in C.MAIN:
            s = g[g.venue == v]
            if len(s):
                x, y = gapped(s, "days_to_meeting", "p_real", 4)   # futures skip weekends
                ax.plot(x.astype(float), y, STYLE[v], color=COL[v], label=NAME[v])
        ax.set_title(f"{m:%b %Y}: {dec[m]}", fontsize=9, loc="left", color=INK)
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlim(max_days, 0)
    for ax in axs.flat[n:]:
        ax.set_visible(False)
    for ax in axs[:, 0]:
        ax.set_ylabel("P(realized decision)")
    for ax in axs[-1, :]:
        ax.set_xlabel("days to meeting")
    h, lab = [], []
    for ax in axs.flat[:n]:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in lab:
                h.append(hh); lab.append(ll)
    fig.legend(h, lab, loc="upper left", ncol=3, frameon=False, bbox_to_anchor=(0.01, 1.0))
    fig.suptitle("Probability each venue put on the decision the Fed actually made", x=0.01, y=1.04,
                 ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_meetings.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_scatter(pn):
    x = pn[pn.venue == "kalshi"].merge(pn[pn.venue == "polymarket"], on=["meeting", "date"])
    if x.empty:
        return
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.scatter(x.exp_change_bps_x, x.exp_change_bps_y, s=10, color=COL["kalshi"], alpha=0.35,
               edgecolor=SURF, linewidth=0.5)
    lo, hi = np.nanmin([x.exp_change_bps_x.min(), x.exp_change_bps_y.min()]), np.nanmax(
        [x.exp_change_bps_x.max(), x.exp_change_bps_y.max()])
    ax.plot([lo, hi], [lo, hi], color=MUTED, linewidth=1)
    ax.set_xlabel("Kalshi expected change (bps)")
    ax.set_ylabel("Polymarket expected change (bps)")
    ax.set_title(f"Same meeting, same day ({len(x):,} meeting-days)", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_kalshi_vs_poly.png", dpi=160)
    plt.close(fig)


def fig_sources(shares):
    s = shares[shares.horizon != "all"]
    if s.empty:
        return
    fig, axs = plt.subplots(1, s.venue.nunique(), figsize=(9, 3.2), sharey=True, squeeze=False)
    cols = {"share_quote": "#1c5cab", "share_bound": "#3987e5", "share_trade": "#9ec5f4", "share_stale": "#c9c8c1"}
    labs = {"share_quote": "tight fresh quote (mid)", "share_bound": "pinned at tick bound",
            "share_trade": "recent trade", "share_stale": "stale"}
    for ax, (v, g) in zip(axs.flat, s.groupby("venue")):
        bottom = np.zeros(len(g))
        for k in [c for c in cols if c in g]:
            ax.bar(g.horizon.astype(str), g[k], bottom=bottom, color=cols[k], edgecolor=SURF, linewidth=2,
                   label=labs[k], width=0.6)
            bottom += g[k].to_numpy()
        ax.set_title(NAME.get(v, v), loc="left", fontsize=10)
        ax.set_xlabel("days to meeting")
        ax.grid(axis="x", visible=False)
    axs.flat[0].set_ylabel("share of contract-days")
    h, lab = axs.flat[0].get_legend_handles_labels()
    fig.tight_layout()
    fig.legend(h, lab, frameon=False, loc="lower left", bbox_to_anchor=(0.01, 1.0), ncol=4)
    fig.savefig(RESULTS / "fig_price_sources.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_live(pn):
    up = [m for m in sorted(pn.meeting.unique()) if m > dt.date.today()][:2]
    if not up:
        return
    fig, axs = plt.subplots(1, len(up), figsize=(5 * len(up), 3.2), sharey=True, squeeze=False)
    for ax, m in zip(axs.flat, up):
        g = pn[(pn.meeting == m) & pn.venue.isin(C.MAIN) & (pn.days_to_meeting <= 120)]
        for v in C.MAIN:
            s = g[g.venue == v].sort_values("date")
            if len(s):
                x, y = gapped(s.assign(dd=pd.to_datetime(s.date)), "dd", "p_hike", 4)
                ax.plot(pd.to_datetime(pd.Series(x)), y, STYLE[v], color=COL[v], label=NAME[v])
        ax.set_title(f"{m:%b %d, %Y} meeting: P(hike)", loc="left", fontsize=10)
        ax.set_ylim(-0.02, 1.02)
        ax.tick_params(axis="x", rotation=30)
    h, lab = axs.flat[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper left", ncol=3, frameon=False, bbox_to_anchor=(0.01, 1.08))
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_upcoming.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_mpt(mp):
    if mp is None or mp.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 3))
    for k, c in ((1, COL["kalshi"]), (2, "#6da7ec")):
        s = mp[mp.window_rank == k].sort_values("date")
        x, y = gapped(s.assign(dd=pd.to_datetime(s.date)), "dd", "diff_bps", 7)
        ax.plot(pd.to_datetime(pd.Series(x)), y, color=c, linewidth=1.5,
                label=f"{'nearest' if k == 1 else 'second'} SOFR window")
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylabel("Kalshi-implied minus MPT (bps)")
    ax.set_title("Expected 3-month average rate: Kalshi ladder vs Atlanta Fed MPT", loc="left", fontsize=10)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_mpt_path.png", dpi=160)
    plt.close(fig)


def main():
    pn, oc, kc, pc = C.load()
    fig_meetings(pn, oc)
    fig_scatter(pn)
    p = RESULTS / "price_source_shares.csv"
    if p.exists():
        fig_sources(pd.read_csv(p))
    fig_live(pn)
    p = RESULTS / "mpt_path_daily.csv"
    if p.exists() and p.stat().st_size > 5:
        fig_mpt(pd.read_csv(p, parse_dates=["date"]))
    print("figures written to", RESULTS)


if __name__ == "__main__":
    main()
