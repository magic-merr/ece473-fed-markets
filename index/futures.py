"""Futures on the constant-maturity index: fair value from the static hedge, and a backtest of the
future against that hedge (tracking, trading cost, capital), for H = 90 and H = 60.

Contract (decision 007, docs/spec.md sections 3 to 5)
  Pays $1 per index point: $100 x settlement value S. Fully collateralized: at price F the long posts F
  and the short posts 100 - F. Expiry: last Friday of each month, moved back one week at a time until no
  FOMC decision is in the 5-day settlement window or on the first business day after expiry. S = mean of
  the valid daily index values in the 5 calendar days ending on expiry if at least 3 are valid; else the
  window extends back (10 days at most, not before the last decision) to 3 valid values; else settlement
  is deferred to the next valid business day (10 at most); else the last valid value. No rounding of S
  (007 does not apply the spec's 0.25 rounding; Request R2). Index price rule: `final` (index/legs.py).
  The 11/12 terms (Milestone 1 calendar; mean of valid days, else wait up to 14 days) remain available as
  calendar="m1", fallback="ari1112" for the robustness rows.

Natural hedge (static; docs/notes/futures_pricing.md)
  On each settlement day d the index is w(d) C_m1(d)(d) + (1 - w(d)) C_m2(d)(d) at strike U_d - 0.25 (cut)
  or U_d (hike). Meeting dates are known, so m1(d), m2(d) and w(d) are known at entry t. The dealer who
  sells the future at t buys, for every settlement day d, 20 x w(d) units of meeting m1(d)'s contract and
  20 x (1 - w(d)) of m2(d)'s, all at today's strike, and sells day d's tranche at the close of d. A day
  without a valid index value: its tranche is sold on the next valid window day, else on the day the
  settlement value is known (expiry, or the deferred or backstop day). The 11/12 fallback instead sold it on
  the next valid day, else the last valid one.
  Usually two contracts in total, three when the window straddles a bracket roll.
  Fair value F0 = what the hedge costs at the index's own prices on day t.
  If the upper bound does not change between t and expiry, the hedge holds exactly what the index prices,
  so hedge proceeds = settlement identically (up to the fallback reallocation). A meeting at which the Fed
  holds changes nothing. A rate change moves the index to a new strike while the hedge keeps the old one.

Measures (dollars per $100 contract = index points)
  err_mid      hedge proceeds - settlement, both at index prices. > 0: the dealer (short future, long
               hedge) gains.
  cost         spread paid vs the index's price for each leg (buy at the ask of the side held, sell at its
               bid; cut legs are NO: NO ask = 1 - yes bid) + Kalshi taker fee 0.07 P(1 - P) per contract
               at the execution price (unrounded: the large-order limit; Kalshi rounds each order up to the
               cent). A one-sided book is executed at the boundary (buy at 1, sell at 0) only when the leg is
               pinned at a tail (value <= 3c or >= 97c); otherwise the trade is not executable. Execution uses
               the standing book (last observed bid/ask) and assumes top-of-book size is enough.
  capital      dealer: (100 - F0) futures collateral to expiry + hedge purchase (ask + fee) until each
               tranche is sold. Investor (long): F0 to expiry. Also in dollar-days.
  basis        F0 - 100 x index(t): the forward roll-down the future prices in (Palmer's 11/12 log).

Run: cd index && python futures.py   ->  index/results/futures_*.csv, index/results/futures_backtest.md,
     processed/futures_trades.csv (one row per trade) and processed/futures_skipped.csv
"""
from __future__ import annotations

import argparse
import datetime as dt

import numpy as np
import pandas as pd

import build
import legs
from stale import TAIL

HORIZONS = (90, 60)
SIDES = ("cut", "hike")
LEADS = (7, 14, 21, 30, 45, 60, 90)       # calendar days from entry to expiry
SETTLE_DAYS = 5
HEDGE_BOUND = 0.15                        # one-sided books this close to 0 or 1 still mark hedge legs
MAX_SETTLE_WAIT = 14                      # Ari's 11/12 fallback: days to wait if all 5 are missing
SPEC_MIN_VALID = 3                        # spec section 5: at least 3 valid days
SPEC_MAX_WINDOW = 10                      # spec section 5: extend back to at most 10 calendar days in total
SPEC_DEFER_BDAYS = 10                     # spec section 5: defer up to 10 business days, then backstop
RULE, CALENDAR, FALLBACK = "final", "spec", "spec"   # decision 007; low-level defaults stay 11/12 (see run)
CAPITAL_RATE = 0.04                       # illustrative opportunity cost for the dollar-day conversion
RESULTS = build.RESULTS


# ---------------------------------------------------------------- calendar
def _spec_blocked(e: dt.date, fomc) -> bool:
    """Spec section 4: a decision inside the settlement window or on the first business day after expiry."""
    w0 = e - dt.timedelta(days=SETTLE_DAYS - 1)
    return any(w0 <= f <= e or (f > e and np.busday_count(e, f) <= 1) for f in fomc)


def expiries(start: dt.date, end: dt.date, calendar: str = "m1") -> list[dt.date]:
    """Monthly expiries: the last Friday of each month, moved back one week at a time while
    calendar="spec"  (docs/spec.md section 4, decision 007) a decision is in the settlement window or on the
                     first business day after expiry; same as src/settlement_check.py::expiries_no_decision;
    calendar="m1"    (Milestone 1 draft, the 11/12 backtest) a decision is within one business day of expiry.
    The default stays "m1" so read-only importers of this module keep their 11/12 meaning; run() uses "spec"."""
    fomc = legs.fomc_dates()
    out = []
    for mo in pd.date_range(start.replace(day=1), end, freq="MS"):
        last = (mo + pd.offsets.MonthEnd(0)).date()
        e = last - dt.timedelta(days=(last.weekday() - 4) % 7)
        if calendar == "spec":
            while _spec_blocked(e, fomc):
                e -= dt.timedelta(days=7)
        elif calendar == "m1":
            while any(abs(np.busday_count(min(e, f), max(e, f))) <= 1 for f in fomc
                      if abs((f - e).days) <= 7):
                e -= dt.timedelta(days=7)
        else:
            raise ValueError(calendar)
        if start <= e <= end:
            out.append(e)
    return out


def window(expiry: dt.date) -> list[dt.date]:
    return [expiry - dt.timedelta(days=k) for k in range(SETTLE_DAYS - 1, -1, -1)]


def settle_spec(imap: dict, expiry: dt.date, data_end: dt.date | None = None) -> dict:
    """Settlement procedure of docs/spec.md section 5 (decision 007), on daily index values in `imap`.

    1. At least 3 of the 5 window days valid: S = 100 x mean of the valid days ("full" or "mean_of_valid").
    2. Else extend the window back one calendar day at a time, to at most 10 days in total, until 3 valid
       values are found; S = their mean ("extended"). Never before the last decision on or before expiry:
       the decision day itself counts, because its index is the close after the announcement and so already
       uses the new target range.
    3. Else defer: the first of the next 10 business days with a valid value settles alone ("deferred").
    4. Else the last valid value on or before expiry ("backstop").
    Returns S, the days used, the method, and `decided`: the day the settlement value is known."""
    data_end = data_end or legs.data_end()
    ok = lambda d: np.isfinite(imap.get(d, np.nan))  # noqa: E731
    W = window(expiry)
    valid = [d for d in W if ok(d)]
    if len(valid) >= SPEC_MIN_VALID:
        method = "full" if len(valid) == SETTLE_DAYS else "mean_of_valid"
        return {"S": 100.0 * np.mean([imap[d] for d in valid]), "days": valid, "method": method,
                "decided": expiry, "window_valid": len(valid)}
    floor = max((f for f in legs.fomc_dates() if f <= expiry), default=dt.date.min)
    used = list(valid)
    for j in range(SETTLE_DAYS, SPEC_MAX_WINDOW):
        d = expiry - dt.timedelta(days=j)
        if d < floor:
            break
        if ok(d):
            used.append(d)
            if len(used) >= SPEC_MIN_VALID:
                break
    if len(used) >= SPEC_MIN_VALID:
        used = sorted(used)
        return {"S": 100.0 * np.mean([imap[d] for d in used]), "days": used, "method": "extended",
                "decided": expiry, "window_valid": len(valid)}
    bdays = [x.date() for x in pd.bdate_range(expiry + dt.timedelta(days=1), periods=SPEC_DEFER_BDAYS)]
    for d in bdays:
        if d > data_end:
            return {"status": "settlement_beyond_data"}
        if ok(d):
            return {"S": 100.0 * imap[d], "days": [d], "method": "deferred", "decided": d,
                    "window_valid": len(valid)}
    if bdays[-1] > data_end:
        return {"status": "settlement_beyond_data"}
    back = [d for d in imap if d <= expiry and ok(d)]
    if not back:
        return {"status": "no_settlement"}
    d = max(back)
    return {"S": 100.0 * imap[d], "days": [d], "method": "backstop", "decided": bdays[-1],
            "window_valid": len(valid)}


def strike(side: str, u: float) -> float:
    return build.cut_strike(u) if side == "cut" else build.hike_strike(u)


def leg_value(side: str, yes: float) -> float:
    return 1.0 - yes if side == "cut" else yes


def _one_sided(bid, ask):
    """'lo' if no bid and ask <= HEDGE_BOUND, 'hi' if no ask and bid >= 1 - HEDGE_BOUND, else None."""
    no_bid = not np.isfinite(bid) or bid <= 0
    no_ask = not np.isfinite(ask) or ask >= 1
    if no_bid and np.isfinite(ask) and ask <= HEDGE_BOUND:
        return "lo"
    if no_ask and np.isfinite(bid) and bid >= 1 - HEDGE_BOUND:
        return "hi"
    return None


def mark(rec):
    """(yes value, how) for a hedge leg: the index rule's value; if unusable, the standing book's mid if
    two-sided, or the midpoint of the bounded interval if one-sided within HEDGE_BOUND of 0 or 1 (Palmer's
    BOUND logic, widened from 3c for hedge legs only; the index keeps the src rule). The dealer holds the
    position whether or not the index rule would use its price."""
    if rec is None:
        return np.nan, "missing"
    if np.isfinite(rec[0]):
        return rec[0], "rule"
    bid, ask = rec[1], rec[2]
    if np.isfinite(bid) and np.isfinite(ask) and bid > 0 and ask < 1:
        return (bid + ask) / 2, "book_mid"
    side = _one_sided(bid, ask)
    if side == "lo":
        return ask / 2, "book_bound"
    if side == "hi":
        return (1 + bid) / 2, "book_bound"
    return np.nan, "missing"


def exec_price(side: str, action: str, rec) -> float:
    """Execution price of the side held (NO for cut, YES for hike); NaN if not executable."""
    yes, bid, ask = mark(rec)[0], rec[1], rec[2]
    has_bid = np.isfinite(bid) and bid > 0
    has_ask = np.isfinite(ask) and ask < 1
    if side == "cut":
        px = (1 - bid if has_bid else np.nan) if action == "buy" else (1 - ask if has_ask else np.nan)
    else:
        px = (ask if has_ask else np.nan) if action == "buy" else (bid if has_bid else np.nan)
    if np.isfinite(px):
        return float(px)
    # needed side of the book missing: trade at the boundary if the leg is pinned near a tail
    v = leg_value(side, yes)
    if (np.isfinite(v) and (v <= TAIL or v >= 1 - TAIL)) or _one_sided(bid, ask):
        return 1.0 if action == "buy" else 0.0
    return np.nan


# ---------------------------------------------------------------- one trade
def hedge_trade(book: legs.Book, imap: dict, horizon: int, side: str, expiry: dt.date, entry: dt.date,
                fallback: str = "ari1112") -> dict:
    """One futures trade and its static hedge. fallback="spec" uses settle_spec (decision 007);
    fallback="ari1112" is the 11/12 rule (mean of valid days; if none, wait up to 14 days), the default so
    that read-only importers keep their 11/12 meaning; run() passes "spec"."""
    W = window(expiry)
    if entry >= W[0]:
        return {"status": "entry_in_window"}
    I = {d: imap.get(d, np.nan) for d in W}
    valid = [d for d in W if np.isfinite(I[d])]
    if fallback == "ari1112":
        if not valid:
            # 11/12: if all five days are missing, settlement waits for the next valid index value
            nxt = next((expiry + dt.timedelta(days=j) for j in range(1, MAX_SETTLE_WAIT + 1)
                        if np.isfinite(imap.get(expiry + dt.timedelta(days=j), np.nan))), None)
            if nxt is None:
                return {"status": "no_settlement"}
            valid, I[nxt] = [nxt], imap[nxt]
        S = 100.0 * np.mean([I[d] for d in valid])
        method = "full" if len(valid) == SETTLE_DAYS and valid[-1] <= expiry else (
            "deferred" if valid[-1] > expiry else "mean_of_valid")
        settle_days, last = valid, W[-1]
    elif fallback == "spec":
        st = settle_spec(imap, expiry)
        if "S" not in st:
            return st
        S, method, settle_days = st["S"], st["method"], st["days"]
        last = max(W[-1], st["decided"])
    else:
        raise ValueError(fallback)

    u_t = build.ub_at(entry)
    k = strike(side, u_t)
    # tranches: (meeting, role, planned day, sale day, qty)
    tranches = []
    for d in W:
        m1, m2, w = build.bracket(d, horizon)
        if fallback == "ari1112":
            sale = d if d in valid else next((x for x in valid if x > d), valid[-1])
        else:
            # causal: sell on d if its index is valid, else on the next valid window day, else on the day the
            # settlement value is known (expiry, or the deferred / backstop day)
            sale = d if d in valid else next((x for x in valid if x > d), st["decided"])
        if w > 0:
            tranches.append((m1, "near", d, sale, 100.0 / SETTLE_DAYS * w))
        if w < 1:
            tranches.append((m2, "far", d, sale, 100.0 / SETTLE_DAYS * (1 - w)))

    contracts = sorted({t[0] for t in tranches})
    rec_in = {m: book.get(m, k, entry) for m in contracts}
    if any(not np.isfinite(mark(r)[0]) for r in rec_in.values()):
        return {"status": "no_entry_price"}
    rec_out = {}
    for m, _, _, sale, _ in tranches:
        r = book.get(m, k, sale)
        if not np.isfinite(mark(r)[0]):
            return {"status": "no_exit_price"}
        rec_out[(m, sale)] = r
    n_book_mid = sum(mark(r)[1] != "rule" for r in rec_in.values()) + \
        sum(mark(r)[1] != "rule" for r in rec_out.values())

    F0 = proceeds = 0.0
    sp = {"near": 0.0, "far": 0.0}
    fee = {"near": 0.0, "far": 0.0}
    qty = {"near": 0.0, "far": 0.0}
    c_in = c_out = 0.0
    hedge_paid = cap_hedge_days = 0.0
    executable, old_books = True, 0
    rate = book.taker_rate
    for m, role, _, sale, q in tranches:
        v0 = leg_value(side, mark(rec_in[m])[0])
        v1 = leg_value(side, mark(rec_out[(m, sale)])[0])
        F0 += q * v0
        proceeds += q * v1
        qty[role] += q
        pb = exec_price(side, "buy", rec_in[m])
        ps = exec_price(side, "sell", rec_out[(m, sale)])
        old_books += (rec_in[m][4] > 3) + (rec_out[(m, sale)][4] > 3)
        if not (np.isfinite(pb) and np.isfinite(ps)):
            executable = False
            continue
        s_in, s_out = q * (pb - v0), q * (v1 - ps)
        f_in, f_out = q * rate * pb * (1 - pb), q * rate * ps * (1 - ps)
        sp[role] += s_in + s_out
        fee[role] += f_in + f_out
        c_in += s_in + f_in
        c_out += s_out + f_out
        hedge_paid += q * pb + f_in
        cap_hedge_days += (q * pb + f_in) * (sale - entry).days

    meets = [m for m in legs.fomc_dates() if entry < m <= last]
    moves = [m for m in meets if build.ub_at(m) != build.ub_at(m - dt.timedelta(days=1))]
    dirs = {"cut" if build.ub_at(m) < build.ub_at(m - dt.timedelta(days=1)) else "hike" for m in moves}
    direction = "none" if not dirs else (dirs.pop() if len(dirs) == 1 else "mixed")
    hold = (expiry - entry).days
    i_t = imap.get(entry, np.nan)
    out = {
        "status": "ok", "horizon": horizon, "side": side, "expiry": expiry, "entry": entry,
        "hold_days": (expiry - entry).days, "u_entry": u_t, "u_expiry": build.ub_at(last), "strike": k,
        "contracts": "/".join(legs.meeting_ids()[m] for m in contracts), "n_contracts": len(contracts),
        "n_meetings_before_expiry": len(meets), "rate_moves": "/".join(str(m) for m in moves),
        "case": "rate_move" if moves else ("meeting_hold" if meets else "no_meeting"),
        "move_direction": direction,
        "settle_days_valid": len(valid) if fallback == "ari1112" else st["window_valid"],
        "fallback": len(valid) < SETTLE_DAYS,
        "settle_waited": max(settle_days) > expiry, "settle_method": method,
        "settle_days_used": len(settle_days), "settle_first_day": min(settle_days),
        "decision_in_window": any(W[0] <= m <= W[-1] for m in legs.fomc_dates()), "legs_marked_from_book": n_book_mid,
        "index_entry": 100 * i_t if np.isfinite(i_t) else np.nan, "F0": F0,
        "basis": F0 - 100 * i_t if np.isfinite(i_t) else np.nan,
        "S": S, "futures_pnl_long": S - F0, "hedge_pnl_mid": proceeds - F0, "err_mid": proceeds - S,
        "entry_sources": "/".join(rec_in[m][3] for m in contracts),
        "old_book_legs": old_books, "executable": executable,
        "qty_near": qty["near"], "qty_far": qty["far"],
    }
    if executable:
        tot = sum(sp.values()) + sum(fee.values())
        out.update({
            "cost_spread": sum(sp.values()), "cost_fee": sum(fee.values()), "cost_total": tot,
            "cost_entry": c_in, "cost_exit": c_out,
            "cost_near": sp["near"] + fee["near"], "cost_far": sp["far"] + fee["far"],
            "cost_per_unit_near": (sp["near"] + fee["near"]) / qty["near"] if qty["near"] else np.nan,
            "cost_per_unit_far": (sp["far"] + fee["far"]) / qty["far"] if qty["far"] else np.nan,
            "err_exec": proceeds - S - tot,
            "capital_dealer": (100 - F0) + hedge_paid,
            "capital_dealer_dollar_days": (100 - F0) * hold + cap_hedge_days,
            "capital_long": F0, "capital_long_dollar_days": F0 * hold,
        })
    return out


def run(rule=RULE, horizons=HORIZONS, sides=SIDES, leads=LEADS, start=build.SAMPLE_START, end=None,
        calendar=CALENDAR, fallback=FALLBACK):
    """All trades for one configuration. Defaults are decision 007 (rule final, spec calendar, spec
    fallback). run("src", calendar="m1", fallback="ari1112") is the 11/12 configuration."""
    end = end or legs.data_end()
    book = legs.book(rule)
    rows, skipped = [], []
    for h in horizons:
        ix = build.build_index(rule, h, book=book)
        for side in sides:
            col = f"{side.upper()}{h}"
            imap = dict(zip(ix["date"], ix[col]))
            for E in expiries(start, end, calendar):
                for L in leads:
                    t = E - dt.timedelta(days=L)
                    while t.weekday() >= 5:
                        t -= dt.timedelta(days=1)
                    if t < start:
                        continue
                    r = hedge_trade(book, imap, h, side, E, t, fallback)
                    if r["status"] == "ok":
                        rows.append({**r, "lead": L})     # nominal lead; hold_days is the actual one
                    else:
                        skipped.append({"horizon": h, "side": side, "expiry": E, "lead": L, "reason": r["status"]})
    tr = pd.DataFrame(rows)
    tr.insert(0, "rule", rule)
    return tr, pd.DataFrame(skipped)


# ---------------------------------------------------------------- tables
def _name(h, s):
    return f"{s.upper()}{h}"


def _acc(g):
    e, fp = g["err_mid"], g["futures_pnl_long"]
    return {"trades": len(g), "expiries": g["expiry"].nunique(),
            "rmse_err": float(np.sqrt((e ** 2).mean())), "mean_err": e.mean(), "max_abs_err": e.abs().max(),
            "share_abs_err_lt_0.5": (e.abs() < 0.5).mean(),
            "rms_futures_pnl": float(np.sqrt((fp ** 2).mean())),
            "hedge_effectiveness": 1 - (e ** 2).sum() / (fp ** 2).sum() if (fp ** 2).sum() else np.nan}


def accuracy_by_case(tr):
    rows = []
    for (h, s), g in tr.groupby(["horizon", "side"]):
        for c in ("no_meeting", "meeting_hold", "rate_move", "all"):
            x = g if c == "all" else g[g["case"] == c]
            if len(x):
                rows.append({"index": _name(h, s), "case": c, **_acc(x)})
    return pd.DataFrame(rows)


def accuracy_by_lead(tr):
    rows = []
    for (h, s, l), g in tr.groupby(["horizon", "side", "lead"]):
        rows.append({"index": _name(h, s), "lead": l, "share_rate_move": (g["case"] == "rate_move").mean(),
                     "share_no_meeting": (g["case"] == "no_meeting").mean(), **_acc(g)})
    return pd.DataFrame(rows)


def move_events(tr):
    g = tr[tr["case"] == "rate_move"].copy()
    rows = []
    for (h, s, mv), x in g.groupby(["horizon", "side", "rate_moves"]):
        rows.append({"index": _name(h, s), "rate_moves": mv, "trades": len(x), "expiries": x["expiry"].nunique(),
                     "mean_err": x["err_mid"].mean(), "min_err": x["err_mid"].min(), "max_err": x["err_mid"].max()})
    return pd.DataFrame(rows)


def costs(tr):
    rows = []
    for (h, s, l), g in tr.groupby(["horizon", "side", "lead"]):
        ex = g[g["executable"]]
        tot = ex["cost_total"].sum()
        rows.append({"index": _name(h, s), "lead": l, "trades": len(g), "executable": g["executable"].mean(),
                     "spread": ex["cost_spread"].mean(), "fees": ex["cost_fee"].mean(),
                     "total": ex["cost_total"].mean(), "median_total": ex["cost_total"].median(),
                     "p90_total": ex["cost_total"].quantile(0.9),
                     "near_leg": ex["cost_near"].mean(), "far_leg": ex["cost_far"].mean(),
                     "far_share_of_cost": ex["cost_far"].sum() / tot if tot else np.nan,
                     "far_share_of_qty": ex["qty_far"].mean() / 100,
                     "per_unit_near": ex["cost_per_unit_near"].mean(), "per_unit_far": ex["cost_per_unit_far"].mean(),
                     "share_legs_old_book": g["old_book_legs"].sum() / (2 * g["n_contracts"].sum())})
    return pd.DataFrame(rows)


def costs_pooled(tr):
    rows = []
    for (h, s), g in tr.groupby(["horizon", "side"]):
        ex = g[g["executable"]]
        tot = ex["cost_total"].sum()
        rows.append({"index": _name(h, s), "trades": len(g), "executable": g["executable"].mean(),
                     "total": ex["cost_total"].mean(), "median_total": ex["cost_total"].median(),
                     "spread": ex["cost_spread"].mean(), "fees": ex["cost_fee"].mean(),
                     "near_leg": ex["cost_near"].mean(), "far_leg": ex["cost_far"].mean(),
                     "far_share_of_cost": ex["cost_far"].sum() / tot if tot else np.nan,
                     "far_share_of_qty": ex["qty_far"].mean() / 100,
                     "per_unit_near": ex["cost_per_unit_near"].mean(), "per_unit_far": ex["cost_per_unit_far"].mean()})
    return pd.DataFrame(rows)


def capital(tr):
    rows = []
    for (h, s, l), g in tr.groupby(["horizon", "side", "lead"]):
        ex = g[g["executable"]]
        dd = ex["capital_dealer_dollar_days"]
        rows.append({"index": _name(h, s), "lead": l, "F0": ex["F0"].mean(),
                     "dealer_capital": ex["capital_dealer"].mean(), "dealer_dollar_days": dd.mean(),
                     "dealer_capital_cost": (dd * CAPITAL_RATE / 365).mean(), "long_capital": ex["capital_long"].mean(),
                     "trading_cost": ex["cost_total"].mean()})
    return pd.DataFrame(rows)


def fair_value(tr):
    rows = []
    for (h, s, l), g in tr.groupby(["horizon", "side", "lead"]):
        x = g.dropna(subset=["basis"])
        rows.append({"index": _name(h, s), "lead": l, "trades": len(x), "mean_index_entry": x["index_entry"].mean(),
                     "mean_F0": x["F0"].mean(), "mean_basis": x["basis"].mean(), "sd_basis": x["basis"].std(ddof=0),
                     "mean_settlement": x["S"].mean(), "mean_futures_pnl_long": x["futures_pnl_long"].mean()})
    return pd.DataFrame(rows)


def coverage(tr, sk):
    a = tr.groupby(["horizon", "side"]).size().rename("ok")
    if len(sk):
        b = sk.groupby(["horizon", "side", "reason"]).size().unstack(fill_value=0)
        a = pd.concat([a, b], axis=1).fillna(0)
    a = a.reset_index()
    a.insert(0, "index", [_name(h, s) for h, s in zip(a["horizon"], a["side"])])
    return a.drop(columns=["horizon", "side"])


ROBUSTNESS = [   # (label, run kwargs); decision 007 rows plus the 11/12 reproduction row
    ("Main: decision 007 (final rule, spec calendar, spec fallback, from 2023-02-02)", None),
    ("Only trades where every hedge leg had a rule price", "rule_priced_only"),
    ("Milestone 1 price rule", dict(rule="m1")),
    ("src rule with the trade branch (pre-006)", dict(rule="src")),
    ("Milestone 1 expiry rule", dict(calendar="m1")),
    ("Ari's 11/12 fallback", dict(fallback="ari1112")),
    ("Sample from 2022-03-17", dict(start=build.EXT_START)),
    ("11/12 configuration (src rule, Milestone 1 calendar, 11/12 fallback): reproduces the 11/12 tables",
     dict(rule="src", calendar="m1", fallback="ari1112")),
]


def error_by_direction(tr):
    """A5: hedge error on trades with a rate change before expiry, by the direction of the change. 'With the
    index' means a cut for a CUT index or a hike for a HIKE index. err > 0: the dealer (short future, long
    hedge) gains."""
    rows = []
    g0 = tr[tr["case"] == "rate_move"]
    for (h, s), g in g0.groupby(["horizon", "side"]):
        for d in ("cut", "hike", "mixed"):
            x = g[g["move_direction"] == d]
            if not len(x):
                continue
            e = x["err_mid"]
            rows.append({"index": _name(h, s), "direction": d,
                         "relative_to_index": "with" if d == s else ("against" if d in ("cut", "hike") else "mixed"),
                         "trades": len(x), "expiries": x["expiry"].nunique(),
                         "mean_err": e.mean(), "median_err": e.median(), "rmse_err": float(np.sqrt((e ** 2).mean())),
                         "min_err": e.min(), "max_err": e.max(), "share_dealer_gains": (e > 0).mean(),
                         "mean_futures_pnl_long": x["futures_pnl_long"].mean()})
    return pd.DataFrame(rows)


def settlement_methods(tr):
    rows = []
    for (h, s), g in tr.groupby(["horizon", "side"]):
        x = g.drop_duplicates("expiry")
        rows.append({"index": _name(h, s), "expiries": len(x),
                     **{m: int((x["settle_method"] == m).sum())
                        for m in ("full", "mean_of_valid", "extended", "deferred", "backstop")}})
    return pd.DataFrame(rows)


def robustness(main_tr, main_sk):
    """Headline numbers under each robustness configuration of decision 007."""
    rows = []
    for lab, kw in ROBUSTNESS:
        if kw is None:
            tr, sk = main_tr, main_sk
        elif kw == "rule_priced_only":
            tr, sk = main_tr[main_tr["legs_marked_from_book"] == 0], pd.DataFrame()
        else:
            tr, sk = run(**kw)
        for (h, s), g in tr.groupby(["horizon", "side"]):
            ex = g[g["executable"]]
            nm = g[g["case"] != "rate_move"]
            mv = g[g["case"] == "rate_move"]
            nsk = int(((sk["horizon"] == h) & (sk["side"] == s)).sum()) if len(sk) else 0
            rows.append({"variant": lab, "index": _name(h, s), "expiries": g["expiry"].nunique(), "trades": len(g),
                         "skipped": nsk,
                         "max_abs_err_no_move": nm["err_mid"].abs().max() if len(nm) else np.nan,
                         "rate_move_trades": len(mv),
                         "rmse_err_rate_move": float(np.sqrt((mv["err_mid"] ** 2).mean())) if len(mv) else np.nan,
                         "rmse_err_all": float(np.sqrt((g["err_mid"] ** 2).mean())),
                         "hedge_effectiveness": _acc(g)["hedge_effectiveness"],
                         "mean_cost": ex["cost_total"].mean(),
                         "far_share_of_cost": ex["cost_far"].sum() / ex["cost_total"].sum(),
                         "share_settle_not_full": (g["settle_method"] != "full").mean()})
    return pd.DataFrame(rows)


def _md(df, fmt=".2f"):
    return df.to_markdown(index=False, floatfmt=fmt)


def report(tr, sk, rob):
    tabs = {"futures_trades": tr, "futures_skipped": sk, "futures_coverage": coverage(tr, sk),
            "futures_fair_value": fair_value(tr), "futures_accuracy_by_case": accuracy_by_case(tr),
            "futures_accuracy_by_lead": accuracy_by_lead(tr), "futures_rate_move_events": move_events(tr),
            "futures_costs": costs(tr), "futures_costs_pooled": costs_pooled(tr),
            "futures_capital": capital(tr), "futures_settlement_methods": settlement_methods(tr),
            "futures_error_by_direction": error_by_direction(tr),
            "futures_robustness": rob}
    RESULTS.mkdir(parents=True, exist_ok=True)
    build.PROCESSED.mkdir(exist_ok=True)
    for k, v in tabs.items():   # trade-level files are large and rebuildable: processed/ (gitignored)
        v.to_csv((build.PROCESSED if k in ("futures_trades", "futures_skipped") else RESULTS) / f"{k}.csv",
                 index=False)
    n_exp = tr["expiry"].nunique()
    lines = [
        "# CUT/HIKE futures vs. the static hedge: backtest tables", "",
        f"Generated by `index/futures.py` on {dt.date.today()}. Data: committed Kalshi pull in `index_m1/` "
        f"(through {legs.data_end()}). Configuration: decision 007 (price rule `{RULE}`, expiry calendar and "
        f"settlement fallback of `docs/spec.md` sections 4 and 5). Sample: {n_exp} monthly expiries, "
        f"entries from {build.SAMPLE_START}, leads {', '.join(map(str, LEADS))} calendar days. "
        "Units: dollars per $100 contract (= index points). Trades with leads above about 30 days overlap "
        "across expiries, so they are not independent.", "",
        "## Coverage (trades run / skipped by reason)", "", _md(tabs["futures_coverage"], ".0f"), "",
        "## Settlement procedure used (docs/spec.md section 5), expiries with at least one trade", "",
        _md(tabs["futures_settlement_methods"], ".0f"), "",
        "## Fair value and basis (F0 - 100 x index at entry)", "", _md(tabs["futures_fair_value"]), "",
        "## Hedge error at index prices, by what happens before expiry", "",
        "err = hedge proceeds - settlement. Positive: the dealer (short future, long hedge) gains. "
        "Hedge effectiveness = 1 - sum(err^2) / sum(futures P&L^2).", "",
        _md(tabs["futures_accuracy_by_case"]), "", "### By lead", "", _md(tabs["futures_accuracy_by_lead"]), "",
        "### Trades with a rate change before expiry, by direction of the change", "",
        "with: a cut for CUT, a hike for HIKE. share_dealer_gains: share of trades with err > 0.", "",
        _md(tabs["futures_error_by_direction"]), "",
        "### Trades with a rate change before expiry, by meeting", "", _md(tabs["futures_rate_move_events"]), "",
        "## Trading cost of the hedge (taker, vs. the index's own prices)", "",
        _md(tabs["futures_costs_pooled"]), "", "### By lead", "", _md(tabs["futures_costs"]), "",
        "## Capital", "", f"dealer_capital_cost: dollar-days at an illustrative {CAPITAL_RATE:.0%} a year.", "",
        _md(tabs["futures_capital"]), "", "## Robustness", "", _md(rob), "",
    ]
    (RESULTS / "futures_backtest.md").write_text("\n".join(lines))
    return tabs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-robustness", action="store_true")
    a = ap.parse_args(argv)
    tr, sk = run()
    rob = pd.DataFrame() if a.no_robustness else robustness(tr, sk)
    tabs = report(tr, sk, rob)
    print(tabs["futures_accuracy_by_case"].round(3).to_string(index=False))
    print(tabs["futures_costs_pooled"].round(3).to_string(index=False))
    return tr, tabs


if __name__ == "__main__":
    main()
