import pandas as pd, numpy as np, matplotlib

def load_daily():
    """kalshi_daily.csv is not committed (17 MB); fall back to the identical parquet."""
    import os
    if os.path.exists("data/kalshi_daily.csv"):
        return pd.read_csv("data/kalshi_daily.csv", parse_dates=["date", "decision_date"])
    x = pd.read_parquet("data/kalshi_daily.parquet")
    for c in ("date", "decision_date"):
        x[c] = pd.to_datetime(x[c])
    return x


matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

B, O, INK, INK2, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 200, "savefig.bbox": "tight", "legend.frameon": False})
START = pd.Timestamp("2022-03-17")
cal = pd.read_csv("data/fomc_calendar.csv", parse_dates=["decision_date"])
path = pd.read_csv("data/realized_upper_bound.csv", parse_dates=["decision_date"])
mk = pd.read_csv("data/kalshi_markets.csv", parse_dates=["decision_date"])
ix = pd.read_csv("data/index_daily.csv", parse_dates=["date", "d1", "d2"])
d = load_daily()

# ---- Figure 1: realized upper bound and ladder breadth
fig, ax = plt.subplots(2, 1, figsize=(6.5, 4.2), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
p = path[path.decision_date <= "2026-10-27"]
x = pd.concat([pd.Series([pd.Timestamp("2021-07-01")]), p.decision_date, pd.Series([pd.Timestamp("2026-10-27")])])
y = pd.concat([pd.Series([0.25]), p.ub_after, pd.Series([p.ub_after.iloc[-1]])])
ax[0].step(x, y, where="post", color=B, lw=2)
ax[0].set_ylabel("Upper bound (%)")
ax[0].set_title("A. Upper bound of the target range implied by settled Kalshi ladders", loc="left", fontsize=9, color=INK)
n = mk[mk.decision_date <= "2026-10-28"].groupby("decision_date").size()
ax[1].bar(n.index, n.values, width=20, color=B)
ax[1].bar([pd.Timestamp("2021-11-03")], [0.15], width=20, color=O)
ax[1].annotate("Nov 2021:\nno contract", (pd.Timestamp("2021-11-03"), 0.5), xytext=(pd.Timestamp("2021-07-01"), 8),
               fontsize=7.5, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax[1].set_ylabel("Strikes listed")
ax[1].set_title("B. Strikes in each meeting's ladder", loc="left", fontsize=9, color=INK)
ax[1].axvline(START, color=INK2, lw=0.8, ls="--")
ax[1].text(START, 22.5, " main sample starts 17 Mar 2022", fontsize=7.5, color=INK2, va="top"); ax[1].set_ylim(0, 23)
ax[1].xaxis.set_major_locator(mdates.YearLocator()); ax[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.savefig("figures/fig1_ladder.png"); plt.close(fig)

# ---- Figure 2: term structure on one date and the 90-day interpolation
t = pd.Timestamp("2024-07-15")
r = ix[ix.date == t].iloc[0]
U = r.ub
# same quote rule as the index: spread <= 0.10, last quote within 10 days
day = d[(d.date <= t) & (d.date >= t - pd.Timedelta(days=10)) & (d.decision_date > t) &
        (d.strike.round(2) == round(U - 0.25, 2)) & (d.spread <= 0.10)].sort_values("date").groupby("meeting_id").tail(1)
day = day.assign(C=1 - day["mid"], dtd=(day.decision_date - t).dt.days).sort_values("dtd")
day = day[day.dtd <= 200]
fig, ax = plt.subplots(figsize=(6.5, 3.0))
ax.plot(day.dtd, day.C * 100, color=B, lw=2, marker="o", ms=5, label="P(cut by meeting), one point per meeting")
ax.axvline(90, color=INK2, lw=0.8, ls="--")
ax.plot([90], [r.CUT90 * 100], marker="D", ms=8, color=O, ls="none", label=f"CUT90 = {r.CUT90*100:.1f}% (interpolated)")
for _, q in day.iterrows():
    ax.annotate(q.meeting_id, (q.dtd, q.C * 100), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7, color=INK2)
ax.set_xlabel("Days from snapshot to FOMC decision"); ax.set_ylabel("Probability (%)")
ax.set_title(f"Cut probabilities by meeting on {t:%d %b %Y} (upper bound {U:.2f}%)", loc="left", fontsize=9, color=INK)
ax.set_ylim(0, 105); ax.legend(loc="lower right", fontsize=8)
fig.savefig("figures/fig2_term_structure.png"); plt.close(fig)

# ---- Figure 3: index time series
s = ix[ix.date >= START].set_index("date")
fig, ax = plt.subplots(figsize=(6.5, 3.0))
for dd in cal[(cal.decision_date >= START) & (cal.decision_date <= "2026-10-27")].decision_date:
    ax.axvline(dd, color=GRID, lw=0.8, zorder=0)
ax.plot(s.index, s.CUT90 * 100, color=B, lw=1.6, label="CUT90: P(lower upper bound in 90 days)")
ax.plot(s.index, s.HIKE90 * 100, color=O, lw=1.6, label="HIKE90: P(higher upper bound in 90 days)")
ax.set_ylabel("Probability (%)"); ax.set_ylim(0, 100)
ax.set_title("Constant-maturity 90-day index, daily (vertical lines are FOMC decisions)", loc="left", fontsize=9, color=INK)
ax.legend(loc="upper left", fontsize=8, bbox_to_anchor=(0, -0.12), ncol=2)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.savefig("figures/fig3_index.png"); plt.close(fig)

# ---- Figure 4: tracking difference vs predicted roll term
bt = pd.read_csv("data/backtest_cut90.csv", parse_dates=["date"])
bt = bt[(bt.date >= START)]
fig, ax = plt.subplots(figsize=(6.5, 3.0))
ax.plot(bt.date, bt.dI.cumsum() * 100, color=B, lw=2, label="Cumulative daily change in CUT90")
ax.plot(bt.date, bt.pnl.cumsum() * 100, color=O, lw=2, label="Cumulative P&L of tracking portfolio (1 unit)")
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylabel("Probability points")
ax.set_title("CUT90 vs its daily-rebalanced replication, mid prices, no costs", loc="left", fontsize=9, color=INK)
ax.legend(loc="lower left", fontsize=8)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.savefig("figures/fig4_tracking.png"); plt.close(fig)
print("ok", r[["m1", "m2", "w", "C1", "C2", "CUT90"]].to_dict())
