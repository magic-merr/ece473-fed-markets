"""Constant-maturity (90-day) Fed cut / hike probability index from the Kalshi strike ladder,
plus a first mid-price tracking backtest.

Definitions (t = daily snapshot, 00:00 ET at the end of calendar day t)
  U_t        upper bound of the target range in effect at t (from settled ladders)
  C_m(t)     P(upper bound after meeting m < U_t)  = 1 - mid YES of the "above U_t - 0.25" contract
  H_m(t)     P(upper bound after meeting m > U_t)  =     mid YES of the "above U_t" contract
  T          t + 90 days; m1 = last meeting with decision <= T, m2 = first meeting after T
  w_t        (d2 - T) / (d2 - d1), weight on m1
  CUT90_t    w_t C_m1 + (1 - w_t) C_m2      (headline index, as in the one-pager)
  HIKE90_t   same with H
"""
import numpy as np, pandas as pd

def load_daily():
    """kalshi_daily.csv is not committed (17 MB); fall back to the identical parquet."""
    import os
    if os.path.exists("data/kalshi_daily.csv"):
        return pd.read_csv("data/kalshi_daily.csv", parse_dates=["date", "decision_date"])
    x = pd.read_parquet("data/kalshi_daily.parquet")
    for c in ("date", "decision_date"):
        x[c] = pd.to_datetime(x[c])
    return x



H = 90
MAXFILL = int(__import__("os").environ.get("MAXFILL", 10))   # forward-fill a stale quote for at most this many days
MAXSPREAD = float(__import__("os").environ.get("MAXSPREAD", 0.10))   # wider spread -> quote treated as missing

d = load_daily()
mk = pd.read_csv("data/kalshi_markets.csv", parse_dates=["decision_date"])
cal = pd.read_csv("data/fomc_calendar.csv", parse_dates=["decision_date"])

# ---------------------------------------------------------------- realized upper bound path
s = mk[mk.result_yes.notna()]
ub = {}
for mid, g in s.groupby("meeting_id"):
    no = g[g.result_yes == 0].strike
    yes = g[g.result_yes == 1].strike
    u = no.min() if len(no) else yes.max() + 0.25
    assert not len(yes) or abs(yes.max() + 0.25 - u) < 1e-9, mid
    ub[mid] = u
cal["ub_after"] = cal.meeting_id.map(ub)
cal.loc[cal.meeting_id == "21NOV", "ub_after"] = 0.25   # no Kalshi contract; range unchanged at 0-0.25
path = cal.dropna(subset=["ub_after"])[["decision_date", "ub_after", "meeting_id"]].sort_values("decision_date")
path["change_bp"] = (path.ub_after.diff() * 100).round().fillna(0).astype(int)
path.to_csv("data/realized_upper_bound.csv", index=False)

# ---------------------------------------------------------------- clean quote panel
q = d[~d.post_decision & ~d.partial_day].copy()
q.loc[q.spread > MAXSPREAD, ["yes_bid", "yes_ask"]] = np.nan
q["mid_q"] = (q.yes_bid + q.yes_ask) / 2
days = pd.date_range(q.date.min(), q.date.max(), freq="D")
panel = {}
for (mid, k), g in q.groupby(["meeting_id", "strike"]):
    sr = g.set_index("date").mid_q.sort_index()
    last = g.date.max()
    sr = sr.reindex(pd.date_range(sr.index.min(), last, freq="D"))
    filled = sr.ffill(limit=MAXFILL)
    panel[(mid, k)] = pd.DataFrame({"mid": filled, "stale": sr.isna() & filled.notna()})
dec = cal.set_index("meeting_id").decision_date

def ub_at(t):
    p = path[path.decision_date <= t]
    return p.ub_after.iloc[-1] if len(p) else 0.25

rows = []
meet = cal.sort_values("decision_date")
for t in days:
    T = t + pd.Timedelta(days=H)
    U = ub_at(t)
    fut = meet[meet.decision_date > t]
    m1 = fut[fut.decision_date <= T].tail(1)
    m2 = fut[fut.decision_date > T].head(1)
    if m1.empty or m2.empty:
        continue
    m1, m2 = m1.iloc[0], m2.iloc[0]
    w = (m2.decision_date - T).days / (m2.decision_date - m1.decision_date).days
    r = dict(date=t, ub=U, m1=m1.meeting_id, m2=m2.meeting_id, d1=m1.decision_date, d2=m2.decision_date, w=w)
    for leg, m in (("1", m1.meeting_id), ("2", m2.meeting_id)):
        for name, k in (("cutK", round(U - 0.25, 2)), ("hikeK", U)):
            x = panel.get((m, k))
            v = x.mid.get(t, np.nan) if x is not None else np.nan
            st = bool(x.stale.get(t, False)) if x is not None else False
            r[f"{name}{leg}_yes"] = v
            r[f"{name}{leg}_stale"] = st
    rows.append(r)
ix = pd.DataFrame(rows)
ix["C1"] = 1 - ix.cutK1_yes; ix["C2"] = 1 - ix.cutK2_yes
ix["H1"] = ix.hikeK1_yes;    ix["H2"] = ix.hikeK2_yes
ix.loc[ix.ub <= 0.25, ["C1", "C2"]] = 0.0          # at the zero lower bound a cut is impossible
ix["CUT90"] = ix.w * ix.C1 + (1 - ix.w) * ix.C2
ix["HIKE90"] = ix.w * ix.H1 + (1 - ix.w) * ix.H2
ix["any_stale"] = ix[[c for c in ix if c.endswith("_stale")]].any(axis=1)
ix["announcement"] = ix.date.isin(cal.decision_date)
ix.to_csv("data/index_daily.csv", index=False)

# coverage by quarter -> sample choice
ix["q"] = ix.date.dt.to_period("Q")
cov = ix.groupby("q").agg(days=("date", "size"), cut_ok=("CUT90", lambda x: x.notna().mean()),
                          hike_ok=("HIKE90", lambda x: x.notna().mean()), ub=("ub", "last"))
print(cov.round(2).to_string())

# ---------------------------------------------------------------- mid-price tracking backtest (no costs)
def cprice(m, k, t, kind):
    x = panel.get((m, round(k, 2)))
    v = x.mid.get(t, np.nan) if x is not None else np.nan
    if kind == "cut":
        return 0.0 if k < 0.25 else 1 - v      # below the ZLB strike a cut is impossible
    return v

def backtest(col, kind):
    out = []
    ixs = ix.set_index("date")
    dts = ixs.index
    for t0, t1 in zip(dts[:-1], dts[1:]):
        a, b = ixs.loc[t0], ixs.loc[t1]
        if np.isnan(a[col]) or np.isnan(b[col]) or (t1 - t0).days != 1:
            continue
        k = a.ub - 0.25 if kind == "cut" else a.ub
        p0 = [cprice(a.m1, k, t0, kind), cprice(a.m2, k, t0, kind)]
        p1 = [cprice(a.m1, k, t1, kind), cprice(a.m2, k, t1, kind)]
        if np.isnan(p0 + p1).any():
            continue
        pnl = a.w * (p1[0] - p0[0]) + (1 - a.w) * (p1[1] - p0[1])
        out.append(dict(date=t1, pnl=pnl, dI=b[col] - a[col], announce=bool(b.announcement),
                        ub_change=b.ub != a.ub, roll=(b.m1 != a.m1) or (b.m2 != a.m2),
                        slope=(p0[1] - p0[0]) / (a.d2 - a.d1).days))
    bt = pd.DataFrame(out)
    bt["err"] = bt.pnl - bt.dI
    return bt

START = pd.Timestamp("2022-03-17")    # first day off the zero lower bound
for col, kind in (("CUT90", "cut"), ("HIKE90", "hike")):
    bt = backtest(col, kind)
    bt.to_csv(f"data/backtest_{col.lower()}.csv", index=False)
    s = bt[bt.date >= START]
    for lab, x in (("all days", s), ("ex announcement days", s[~s.announce])):
        print(f"{col} {lab}: n={len(x)} corr(pnl,dI)={x.pnl.corr(x.dI):.3f} "
              f"TE_daily={x.err.std()*100:.2f}pp mean_err={x.err.mean()*1e4:.2f}bp/day "
              f"cum_pnl={x.pnl.sum()*100:.1f}pp cum_dI={x.dI.sum()*100:.1f}pp "
              f"mean_slope={x.slope.mean()*1e4:.2f}bp/day")
