"""FedWatch-style meeting probabilities from 30-day fed funds futures (ZQ).

Contract M settles at 100 - (average daily EFFR over calendar month M). For a meeting on day d of a
month with N days, the new rate takes effect the next day, so
        avg_M = (d * r0 + (N - d) * r1) / N.
For each meeting after the observation date we get the post-meeting rate r1 by
    A. 100 - F_{M+1}, when month M+1 has no FOMC meeting (the "clean month" anchor), else
    B. (N * avg_M - d * r0) / (N - d), using the month-M contract and the pre-meeting rate r0.
r0 is the latest published EFFR for the first meeting, and the previous meeting's r1 after that
(or 100 - F_{M-1} when month M-1 has no meeting). The expected change dE = r1 - r0 is split between
the two adjacent 25 bp outcomes, as CME FedWatch does:
        k = floor(dE / 25), P(25(k+1)) = dE/25 - k, P(25k) = 1 - that.
"""
from __future__ import annotations

import calendar
import datetime as dt
import math

from config import FOMC_DATES


def _add_months(d: dt.date, k: int) -> dt.date:
    y, m = divmod(d.month - 1 + k, 12)
    return dt.date(d.year + y, m + 1, 1)


def _has_meeting(month: dt.date) -> bool:
    return any(x.year == month.year and x.month == month.month for x in FOMC_DATES)


def meeting_rates(obs_date: dt.date, effr: float, futures: dict[dt.date, float],
                  horizon: int = 8) -> dict[dt.date, tuple[float, float]]:
    """Return {meeting: (r0, r1)} in percent for meetings strictly after obs_date that can be priced.

    futures: {first-of-month date: settlement/close price} as of obs_date.
    """
    out: dict[dt.date, tuple[float, float]] = {}
    meets = [m for m in FOMC_DATES if m > obs_date][:horizon]
    prev_r1 = effr
    for i, m in enumerate(meets):
        month = dt.date(m.year, m.month, 1)
        n = calendar.monthrange(m.year, m.month)[1]
        d = m.day
        # pre-meeting rate
        if i == 0:
            r0 = effr
        elif prev_r1 is not None:
            r0 = prev_r1
        else:
            pm = _add_months(month, -1)
            r0 = 100 - futures[pm] if (not _has_meeting(pm) and pm in futures) else None
        # post-meeting rate
        nm = _add_months(month, 1)
        if not _has_meeting(nm) and nm in futures:
            r1 = 100 - futures[nm]
        elif month in futures and r0 is not None and n - d > 0:
            r1 = (n * (100 - futures[month]) - d * r0) / (n - d)
        else:
            r1 = None
        if r0 is not None and r1 is not None:
            out[m] = (r0, r1)
        prev_r1 = r1
    return out


def two_point(delta_bps: float) -> dict[int, float]:
    k = math.floor(delta_bps / 25.0)
    frac = delta_bps / 25.0 - k
    probs = {25 * k: 1 - frac}
    if frac > 1e-12:
        probs[25 * (k + 1)] = frac
    return probs


def decision_probs(delta_bps: float) -> dict[str, float]:
    p = two_point(delta_bps)
    return {"p_cut": sum(v for k, v in p.items() if k < 0),
            "p_hold": p.get(0, 0.0),
            "p_hike": sum(v for k, v in p.items() if k > 0),
            "exp_change_bps": delta_bps}
