"""Pull rate benchmarks.

Outputs
  raw/rates/effr.csv        NY Fed EFFR + FOMC target range by day (also used to resolve outcomes)
  raw/rates/sofr.csv        NY Fed SOFR by day (for the SOFR-vs-target spread in the MPT comparison)
  raw/rates/zq/{SYM}.csv    Yahoo daily OHLCV for every 30-day fed funds future Yahoo still lists
  raw/rates/mpt.csv         Atlanta Fed Market Probability Tracker history (long format)

Yahoo drops expired futures, so ZQ history only exists for contracts that have not yet expired.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import time

import pandas as pd

from config import ATL_MPT_XLSX, NYFED_API, RATES_RAW, SAMPLE_START, YAHOO_CHART
from http_util import get

MONTH_CODES = "FGHJKMNQUVXZ"


def pull_nyfed(kind: str) -> pd.DataFrame:
    path = {"effr": "rates/unsecured/effr", "sofr": "rates/secured/sofr"}[kind]
    start = SAMPLE_START - dt.timedelta(days=60)
    rows, a = [], start
    today = dt.date.today()
    while a <= today:  # chunk by year to stay under response caps
        b = min(dt.date(a.year, 12, 31), today)
        j = get(f"{NYFED_API}/{path}/search.json", {"startDate": a.isoformat(), "endDate": b.isoformat()})
        rows.extend((j or {}).get("refRates") or [])
        a = b + dt.timedelta(days=1)
    df = pd.DataFrame(rows)
    keep = {"effectiveDate": "date", "percentRate": "rate", "targetRateFrom": "target_lo",
            "targetRateTo": "target_hi", "volumeInBillions": "volume_bn"}
    df = df[[c for c in keep if c in df.columns]].rename(columns=keep)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.drop_duplicates("date").sort_values("date")


def zq_symbols(today: dt.date, months_ahead: int = 24) -> list[tuple[str, dt.date]]:
    out = []
    y, m = today.year, today.month
    for k in range(0, months_ahead):   # Yahoo drops expired contracts; current month is still listed
        mm, yy = (m - 1 + k) % 12 + 1, y + (m - 1 + k) // 12
        out.append((f"ZQ{MONTH_CODES[mm - 1]}{str(yy)[-2:]}.CBT", dt.date(yy, mm, 1)))
    return out


def pull_zq(sym: str) -> pd.DataFrame | None:
    p1 = int(pd.Timestamp("2021-01-01").timestamp())
    p2 = int(pd.Timestamp.now("UTC").timestamp())
    time.sleep(2)  # Yahoo rate-limits bursts
    try:
        j = get(f"{YAHOO_CHART}/{sym}", {"period1": p1, "period2": p2, "interval": "1d"}, tries=8)
    except RuntimeError as ex:
        print(f"  {sym}: {ex}")
        return None
    res = ((j or {}).get("chart") or {}).get("result")
    if not res:
        return None
    r = res[0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"ts": r["timestamp"], "close": q.get("close"), "volume": q.get("volume")})
    tz = (r.get("meta") or {}).get("exchangeTimezoneName", "America/Chicago")
    df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(tz).dt.date
    return df.dropna(subset=["close"]).drop_duplicates("date", keep="last")[["date", "close", "volume"]]


def pull_mpt() -> pd.DataFrame:
    content = get(ATL_MPT_XLSX, as_json=False, timeout=180)
    df = pd.read_excel(io.BytesIO(content), sheet_name="DATA", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    rs = df["reference_start"]
    # reference_start is an Excel serial in the file
    df["reference_start"] = (pd.to_datetime(rs, unit="D", origin="1899-12-30").dt.date
                             if pd.api.types.is_numeric_dtype(rs) else pd.to_datetime(rs).dt.date)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mpt", action="store_true")
    ap.add_argument("--only-zq", action="store_true")
    a = ap.parse_args(argv)
    (RATES_RAW / "zq").mkdir(parents=True, exist_ok=True)

    ap_only_zq = a.only_zq
    for kind in (() if ap_only_zq else ("effr", "sofr")):
        d = pull_nyfed(kind)
        d.to_csv(RATES_RAW / f"{kind}.csv", index=False)
        print(f"{kind}: {len(d)} days, {d['date'].min()} .. {d['date'].max()}")

    got = []
    for sym, month in zq_symbols(dt.date.today()):
        d = pull_zq(sym)
        if d is None or d.empty:
            continue
        d.insert(0, "contract_month", month)
        d.to_csv(RATES_RAW / "zq" / f"{sym.split('.')[0]}.csv", index=False)
        got.append(f"{sym}({d['date'].min()}..)")
    print("ZQ contracts on Yahoo:", ", ".join(got) or "none")

    if not (a.skip_mpt or a.only_zq):
        m = pull_mpt()
        m.to_csv(RATES_RAW / "mpt.csv", index=False)
        print(f"MPT: {len(m)} rows, {m['date'].min()} .. {m['date'].max()}")


if __name__ == "__main__":
    main()
