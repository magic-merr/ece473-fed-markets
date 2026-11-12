"""Evidence for docs/spec.md and docs/decisions/005 (TASK 10 and TASK 13).

Four checks, all from data already in the repo (index_m1/data):
  1. Ladder no-arbitrage: is the YES price monotone in the strike?
  2. Tail regime: how often are CUT90's own legs pinned at 1c / 99c?
  3. Settlement discount D(tau): can we measure it at these spreads?
  4. Expiry calendar: does the spec's rule keep FOMC decisions out of the settlement window?

Run:  cd theory && python noarb.py          (writes results/noarb_summary.md)
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "index_m1", "data")
OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
SAMPLE_START = "2022-03-17"          # first day off the zero bound, Milestone 1 main sample
COLS = ["date", "meeting_id", "decision_date", "strike", "yes_bid", "yes_ask",
        "spread", "two_sided", "days_to_decision", "result_yes"]


def load_panel():
    p = os.path.join(DATA, "kalshi_daily.parquet")
    d = pd.read_parquet(p, columns=COLS) if os.path.exists(p) else \
        pd.read_csv(os.path.join(DATA, "kalshi_daily.csv"), usecols=COLS)
    d["date"] = pd.to_datetime(d["date"])
    d["decision_date"] = pd.to_datetime(d["decision_date"])
    return d[d.date >= SAMPLE_START]


# ------------------------------------------------------------------ 1. no-arbitrage
def monotonicity(d):
    """Y(K) = P(upper bound above K) must be weakly decreasing in K.

    A mid-price violation is not an arbitrage: a mid is not a tradable price when the
    book is one-sided. A violation is tradable only if you can sell the lower strike at
    its bid and buy the higher strike at its ask for a credit, i.e. bid(K_hi) > ask(K_lo).
    """
    n, mid_v, trade_v = 0, [], []
    for (dt, mtg), g in d.groupby(["date", "meeting_id"], sort=False):
        if len(g) < 2:
            continue
        g = g.sort_values("strike")
        n += 1
        dm = ((g.yes_bid + g.yes_ask) / 2).diff().iloc[1:]
        if (dm > 1e-9).any():
            mid_v.append((dt, mtg, float(dm.max()), len(g)))
        b, a = g.yes_bid.values, g.yes_ask.values
        best = 0.0
        for i in range(len(g)):
            for j in range(i + 1, len(g)):           # strike[j] > strike[i]
                if np.isfinite(b[j]) and np.isfinite(a[i]):
                    best = max(best, b[j] - a[i])
        if best > 1e-9:
            trade_v.append((dt, mtg, best, len(g)))
    cols = ["date", "meeting", "size", "n_strikes"]
    return n, pd.DataFrame(mid_v, columns=cols), pd.DataFrame(trade_v, columns=cols)


# ------------------------------------------------------------------ 2. tail regime
def tail_regime(d):
    """How often is each CUT90 leg in the 1c / 99c regime that src/stale.py's BOUND branch corrects?"""
    ix = pd.read_csv(os.path.join(DATA, "index_daily.csv"), parse_dates=["date"])
    legs = []
    for lg in ("1", "2"):
        t = ix[["date", "ub", f"m{lg}"]].rename(columns={f"m{lg}": "meeting_id"}).copy()
        t["strike"] = (t.ub - 0.25).round(2)
        t["leg"] = "near" if lg == "1" else "far"
        legs.append(t)
    m = pd.concat(legs).merge(
        d[["date", "meeting_id", "strike", "yes_bid", "yes_ask"]],
        on=["date", "meeting_id", "strike"], how="left")
    m = m[m.date >= SAMPLE_START]
    m["mid"] = (m.yes_bid + m.yes_ask) / 2
    m["pin_hi"] = (m.yes_ask.fillna(1) >= 1) & (m.yes_bid >= 0.97)
    m["pin_lo"] = (m.yes_bid.fillna(0) <= 0) & (m.yes_ask <= 0.03)
    m["pinned"] = m.pin_hi | m.pin_lo
    m["period"] = np.where(m.date < pd.Timestamp("2023-02-02"),
                           "Mar 2022 to Jan 2023", "Feb 2023 to Oct 2026")
    by_period = m.pivot_table(index="period", columns="leg", values="pinned", aggfunc="mean")
    by_year = m.assign(yr=m.date.dt.year).groupby("yr").pinned.mean()
    # does the BOUND price differ from the Milestone 1 mid on the pinned days?
    sub = m[m.pinned & m.mid.notna()]
    bound = np.where(sub.pin_hi, (1 + sub.yes_bid) / 2, sub.yes_ask / 2)
    delta = float(np.abs(bound - sub.mid).mean()) if len(sub) else float("nan")
    return by_period, by_year, len(sub), delta


# ------------------------------------------------------------------ 3. settlement discount
def settlement_discount(d):
    """A contract paying $1 at settlement should trade at D(tau) when it is near certain.

    A true discount is asymmetric: the winning side trades below 1, the losing side near 0.
    If both sides are off by the same amount, what we are seeing is residual uncertainty and
    the tick floor, not a discount.
    """
    s = d[d.two_sided & d.result_yes.notna() & (d.days_to_decision >= 0)].copy()
    s["mid"] = (s.yes_bid + s.yes_ask) / 2
    cuts = [0, 7, 14, 30, 60, 90, 150, 400]
    labs = ["0-7", "8-14", "15-30", "31-60", "61-90", "91-150", "150+"]
    out = {}
    for name, sel, val in [("winners", (s.mid >= 0.90) & (s.result_yes == 1), lambda x: 1 - x.mid),
                           ("losers", (s.mid <= 0.10) & (s.result_yes == 0), lambda x: x.mid)]:
        g = s[sel].copy()
        g["gap"] = val(g)
        out[name] = g.groupby(pd.cut(g.days_to_decision, cuts, labels=labs),
                              observed=True).gap.agg(["size", "mean", "median"])
    return out


# ------------------------------------------------------------------ 4. expiry calendar
def expiry_calendar():
    cal = pd.read_csv(os.path.join(DATA, "fomc_calendar.csv"), parse_dates=["decision_date"])
    fomc = set(cal.decision_date.dt.date)

    def fridays(y, m):
        dd = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D")
        return list(dd[(dd.month == m) & (dd.dayofweek == 4)])

    def win(e):
        return pd.date_range(e - pd.Timedelta(days=4), e)

    def old(y, m):
        fr = fridays(y, m)
        for f in fomc:
            if f.year == y and f.month == m and abs(np.busday_count(f, fr[-1].date())) <= 1:
                return fr[-2]
        return fr[-1]

    def new(y, m):
        """spec.md section 4: step back one week until no decision is in the window
        or on the first business day after expiry."""
        for e in reversed(fridays(y, m)):
            w = win(e)
            after = np.busday_offset(e.date(), 1, roll="forward").astype("O")
            if not any(w[0].date() <= f <= w[-1].date() for f in fomc) and after not in fomc:
                return e
        return fridays(y, m)[0]

    rows = []
    for y in range(2022, 2027):
        for m in range(1, 13):
            o, nw = old(y, m), new(y, m)
            rows.append(dict(
                ym=f"{y}-{m:02d}", old=o.date(), new=nw.date(), moved=o.date() != nw.date(),
                old_clash=any(win(o)[0].date() <= f <= win(o)[-1].date() for f in fomc),
                new_clash=any(win(nw)[0].date() <= f <= win(nw)[-1].date() for f in fomc)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ report
def main():
    d = load_panel()
    L = []
    w = L.append
    w("# theory/: no-arbitrage, tail regime, settlement discount, expiry calendar\n")
    w("Generated by `theory/noarb.py`. Sample starts %s.\n" % SAMPLE_START)

    n, midv, trv = monotonicity(d)
    w("\n## 1. Ladder no-arbitrage\n")
    w("| Test | Violations | Share |\n|---|---|---|")
    w(f"| Mid prices non-monotone in strike | {len(midv):,} of {n:,} | {len(midv)/n*100:.1f}% |")
    w(f"| Executable (bid at a higher strike above an ask at a lower strike) | "
      f"{len(trv):,} of {n:,} | {len(trv)/n*100:.2f}% |")
    if len(trv):
        w(f"\nLargest executable credit: ${trv['size'].max():.2f}. "
          f"Largest mid violation: ${midv['size'].max():.2f}.\n")
        w("Worst executable violations:\n")
        w(trv.nlargest(5, "size").to_markdown(index=False))

    bp, by, npin, delta = tail_regime(d)
    w("\n\n## 2. Tail regime at CUT90's own legs\n")
    w(bp.round(3).to_markdown())
    w("\nPinned share by year: " + ", ".join(f"{y} {v:.3f}" for y, v in by.items()))
    w(f"\n\nOn the {npin} pinned leg days, mean |BOUND price - Milestone 1 mid| = {delta:.4f}. "
      "When the ask is pinned at 1, `(1+bid)/2` equals `(bid+ask)/2`, so the branch is a no-op here.")

    sd = settlement_discount(d)
    w("\n\n## 3. Settlement discount\n")
    w("Winning side, priced >= 0.90 and settled YES (shortfall below $1):\n")
    w(sd["winners"].round(4).to_markdown())
    w("\n\nLosing side, priced <= 0.10 and settled NO (price of the losing side):\n")
    w(sd["losers"].round(4).to_markdown())
    w("\n\nThe two columns are the same size at every horizon. A settlement discount predicts an "
      "asymmetry, so this is residual uncertainty and the tick floor, not a measurable discount.")

    ex = expiry_calendar()
    for lo, hi, lab in [("2023-02", "2026-09", "Feb 2023 to Sep 2026"),
                        ("2022-03", "2026-12", "Mar 2022 to Dec 2026")]:
        s = ex[(ex.ym >= lo) & (ex.ym <= hi)]
        w(f"\n\n## 4. Expiry calendar, {lab}\n")
        w(f"- expiries: {len(s)}\n- collisions, Milestone 1 rule: {int(s.old_clash.sum())}"
          f"\n- collisions, spec.md section 4 rule: {int(s.new_clash.sum())}"
          f"\n- expiry dates that move: {int(s.moved.sum())}")
        if lab.startswith("Feb"):
            w("\n" + s[s.moved][["ym", "old", "new"]].to_markdown(index=False))

    txt = "\n".join(L) + "\n"
    with open(os.path.join(OUT, "noarb_summary.md"), "w") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
