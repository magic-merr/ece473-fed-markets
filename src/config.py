"""Shared configuration: paths, FOMC calendar, endpoints, stale-price rule parameters."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
KALSHI_RAW = RAW / "kalshi"
KALSHI_CANDLES = KALSHI_RAW / "candles"
POLY_RAW = RAW / "polymarket"
RATES_RAW = RAW / "rates"
PROCESSED = ROOT / "processed"
RESULTS = ROOT / "results"

# --- Endpoints (all public, no auth) ---------------------------------------------------
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA = "https://gamma-api.polymarket.com"
POLY_CLOB = "https://clob.polymarket.com"
POLY_DATA = "https://data-api.polymarket.com"
NYFED_API = "https://markets.newyorkfed.org/api"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"
ATL_MPT_XLSX = ("https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/"
                "research-and-data/data/market-probability-tracker/mpt_histdata.xlsx")

# Kalshi series. FED/KXFED = "upper bound above X% after meeting" (threshold ladder).
# FEDDECISION/KXFEDDECISION = cut/hold/hike buckets (same shape as Polymarket).
KALSHI_LEVEL_SERIES = ["FED", "KXFED"]
KALSHI_DECISION_SERIES = ["FEDDECISION", "KXFEDDECISION"]

# --- FOMC decision dates (statement day, 2pm ET). Source: federalreserve.gov calendars.
FOMC_DATES = [dt.date.fromisoformat(d) for d in [
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08",
]]
SAMPLE_START = dt.date(2023, 1, 1)   # first meeting in sample: Feb 2023

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def meeting_for_month(year: int, month: int) -> dt.date | None:
    for d in FOMC_DATES:
        if d.year == year and d.month == month:
            return d
    return None


# --- Stale-price rule (see README.md, "Stale-price rule") ------------------------------
STALE_N_DAYS = 3          # a price is usable only if it traded, or a qualifying quote updated, within N days
STALE_MAX_SPREAD = 0.10   # a quote qualifies only if two-sided with ask - bid <= this (Polymarket's own display cutoff)
# Kalshi books pinned at the price boundary (no bid & ask <= 3c, or no ask & bid >= 97c) only bound the
# probability; at a 1c minimum tick the last trade sits on the bound. If True, such a (fresh) book is priced
# at the midpoint of the bounded interval instead of the last trade. See README, "Stale-price rule".
KALSHI_TICK_BOUND = True
STALE_SENSITIVITY_N = [1, 3, 7]
STALE_SENSITIVITY_SPREAD = [0.05, 0.10, 0.20]

# --- Fees -------------------------------------------------------------------------------
# Kalshi: fee = ceil_to_cent(rate * C * P * (1-P)); taker 0.07, maker 0.0175 on "quadratic_with_maker_fees"
# series; series fee_multiplier scales both. Pulled live from /series/{ticker}; these are fallbacks.
KALSHI_TAKER_RATE = 0.07
KALSHI_MAKER_RATE = 0.0175
# Polymarket: fee = C * feeRate * p * (1-p), taker only, from 2026-03-30, on markets flagged fee-enabled
# (gamma feesEnabled / CLOB base_fee > 0). Fed decisions fall under Economics: feeRate 0.05.
POLY_FEE_START = dt.date(2026, 3, 30)
POLY_FALLBACK_TAKER_RATE = 0.05

HTTP_SLEEP = 0.12  # seconds between calls (stay well under public rate limits)
