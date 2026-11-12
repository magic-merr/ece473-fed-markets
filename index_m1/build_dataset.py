"""Build the FOMC calendar and the clean daily Kalshi panel for Milestone 1.

Inputs  raw/kalshi/markets_{historical,live}.psv, raw/kalshi/candles*/<ticker>.csv
Outputs data/fomc_calendar.csv, data/kalshi_markets.csv, data/kalshi_daily.csv(.parquet)
"""
import glob, os, re
import numpy as np
import pandas as pd

os.makedirs("data", exist_ok=True)
ET = "America/New_York"

# ---------------------------------------------------------------- FOMC calendar
# Scheduled FOMC meetings, Jul 2021 onward (last day = statement day, 2:00pm ET).
# Through Jun 2026 from the Fed's published calendars; Jul 2026 onward taken from
# Kalshi's own event strike dates (cross-checked below). No unscheduled meetings in sample.
MEETINGS = """
2021-07-27,2021-07-28  2021-09-21,2021-09-22  2021-11-02,2021-11-03  2021-12-14,2021-12-15
2022-01-25,2022-01-26  2022-03-15,2022-03-16  2022-05-03,2022-05-04  2022-06-14,2022-06-15
2022-07-26,2022-07-27  2022-09-20,2022-09-21  2022-11-01,2022-11-02  2022-12-13,2022-12-14
2023-01-31,2023-02-01  2023-03-21,2023-03-22  2023-05-02,2023-05-03  2023-06-13,2023-06-14
2023-07-25,2023-07-26  2023-09-19,2023-09-20  2023-10-31,2023-11-01  2023-12-12,2023-12-13
2024-01-30,2024-01-31  2024-03-19,2024-03-20  2024-04-30,2024-05-01  2024-06-11,2024-06-12
2024-07-30,2024-07-31  2024-09-17,2024-09-18  2024-11-06,2024-11-07  2024-12-17,2024-12-18
2025-01-28,2025-01-29  2025-03-18,2025-03-19  2025-05-06,2025-05-07  2025-06-17,2025-06-18
2025-07-29,2025-07-30  2025-09-16,2025-09-17  2025-10-28,2025-10-29  2025-12-09,2025-12-10
2026-01-27,2026-01-28  2026-03-17,2026-03-18  2026-04-28,2026-04-29  2026-06-16,2026-06-17
2026-07-28,2026-07-29  2026-09-15,2026-09-16  2026-10-27,2026-10-28  2026-12-08,2026-12-09
2027-01-26,2027-01-27  2027-03-16,2027-03-17  2027-04-27,2027-04-28  2027-06-08,2027-06-09
2027-07-27,2027-07-28  2027-09-14,2027-09-15  2027-10-26,2027-10-27  2027-12-07,2027-12-08
2028-01-25,2028-01-26
"""
cal = pd.DataFrame([p.split(",") for p in MEETINGS.split()], columns=["start_date", "decision_date"])
cal["decision_ts_et"] = pd.to_datetime(cal.decision_date + " 14:00").dt.tz_localize(ET)
cal["decision_ts_utc"] = cal.decision_ts_et.dt.tz_convert("UTC")
cal["meeting_id"] = pd.to_datetime(cal.decision_date).dt.strftime("%y%b").str.upper()

# ---------------------------------------------------------------- markets
mh = pd.read_csv("raw/kalshi/markets_historical.psv", sep="|"); mh["source"] = "historical"
ml = pd.read_csv("raw/kalshi/markets_live.psv", sep="|"); ml["source"] = "live"
m = pd.concat([mh, ml], ignore_index=True)
m["series"] = m.event.str.split("-").str[0]
m["strike"] = m.ticker.str.extract(r"-T(\d+(?:\.\d+)?)$")[0].astype(float)
# event code like 22JUL / 22JULY -> YYMON
code = m.event.str.split("-").str[1].str[:5]
m["meeting_id"] = code
m = m.merge(cal[["meeting_id", "decision_date", "decision_ts_utc"]], on="meeting_id", how="left")
for c in ["open", "close", "settle_ts"]:
    m[c] = pd.to_datetime(m[c], utc=True, format="ISO8601")
m = m.rename(columns={"open": "open_ts", "close": "close_ts", "event": "event_ticker", "ticker": "market_ticker"})
m["result_yes"] = m.result.map({"yes": 1, "no": 0})
mk = m[["market_ticker", "event_ticker", "series", "meeting_id", "decision_date", "decision_ts_utc", "strike",
        "open_ts", "close_ts", "settle_ts", "status", "result", "result_yes", "volume", "subtitle", "rules", "source"]]
mk = mk.sort_values(["decision_date", "strike"])
mk.to_csv("data/kalshi_markets.csv", index=False)

# calendar cross-check against Kalshi strike dates (live events carry them)
ev = pd.read_csv("raw/kalshi/events_kxfed.csv") if os.path.exists("raw/kalshi/events_kxfed.csv") else None
cal["kalshi_event"] = cal.meeting_id.map(mk.drop_duplicates("meeting_id").set_index("meeting_id").event_ticker)
cal["kalshi_n_strikes"] = cal.meeting_id.map(mk.groupby("meeting_id").size()).fillna(0).astype(int)
ev["kalshi_strike_date"] = pd.to_datetime(ev.strike_date, utc=True).dt.tz_convert(ET).dt.date.astype(str)
cal["kalshi_strike_date"] = cal.kalshi_event.map(ev.set_index("event_ticker").kalshi_strike_date)
chk = cal.dropna(subset=["kalshi_strike_date"])
chk = chk[chk.kalshi_strike_date != "NaT"]
bad = chk[chk.kalshi_strike_date != chk.decision_date]
print("calendar vs Kalshi strike dates:", len(chk), "checked,", len(bad), "mismatches")
if len(bad): print(bad[["meeting_id", "decision_date", "kalshi_strike_date"]])
print("meetings with no Kalshi event:", cal[(cal.kalshi_n_strikes == 0) & (cal.decision_date < "2026-10-28")].meeting_id.tolist())
cal.drop(columns=["decision_ts_et"]).to_csv("data/fomc_calendar.csv", index=False)

# ---------------------------------------------------------------- daily candles
frames = []
for d in ["raw/kalshi/candles", "raw/kalshi/candles_live"]:
    for f in glob.glob(f"{d}/*.csv"):
        x = pd.read_csv(f)
        if x.empty:
            continue
        x["market_ticker"] = os.path.basename(f)[:-4]
        x["endpoint"] = "historical" if d.endswith("candles") else "live"
        frames.append(x)
c = pd.concat(frames, ignore_index=True)
c = c.drop_duplicates(["market_ticker", "end_period_ts"])
end_et = pd.to_datetime(c.end_period_ts, unit="s", utc=True).dt.tz_convert(ET)
c["candle_end_utc"] = pd.to_datetime(c.end_period_ts, unit="s", utc=True)
# Kalshi daily candles close at ~00:00 ET (01:00 or 23:00 on DST switch days); the candle covers the previous ET day
c["date"] = (end_et - pd.Timedelta(hours=3)).dt.date  # robust to the 1h DST shifts in Kalshi candle closes
c = c.rename(columns={"yes_bid_close": "yes_bid", "yes_ask_close": "yes_ask", "price_close": "last_price",
                      "price_mean": "vwap_day", "open_interest": "open_interest"})
c = c.merge(mk[["market_ticker", "event_ticker", "series", "meeting_id", "decision_date", "decision_ts_utc", "strike",
                "close_ts", "result_yes"]], on="market_ticker", how="left")
c["mid"] = ((c.yes_bid + c.yes_ask) / 2).round(4)
c["spread"] = (c.yes_ask - c.yes_bid).round(4)
# no two-sided market: bid at 0 and ask at 1 (or missing) -> mid is not informative
c["two_sided"] = (c.yes_bid > 0) & (c.yes_ask < 1) & c.yes_bid.notna() & c.yes_ask.notna()
c["days_to_decision"] = (pd.to_datetime(c.decision_date) - pd.to_datetime(c.date)).dt.days
c["tau_years"] = ((c.decision_ts_utc - c.candle_end_utc).dt.total_seconds() / (365.25 * 86400)).round(6)
# candle whose period contains the 2pm ET announcement, or later
c["post_decision"] = c.candle_end_utc > c.decision_ts_utc
c["partial_day"] = c.candle_end_utc > pd.Timestamp.now(tz="UTC")
cols = ["date", "candle_end_utc", "meeting_id", "decision_date", "event_ticker", "series", "market_ticker", "strike",
        "yes_bid", "yes_ask", "mid", "spread", "two_sided", "last_price", "vwap_day", "volume", "open_interest",
        "days_to_decision", "tau_years", "post_decision", "partial_day", "result_yes", "endpoint"]
c = c[cols].sort_values(["date", "decision_date", "strike"])
c.to_csv("data/kalshi_daily.csv", index=False)
try:
    c.to_parquet("data/kalshi_daily.parquet", index=False)
except Exception as e:
    print("parquet skipped:", e)
print(len(cal), "meetings;", len(mk), "markets;", len(c), "daily rows;", c.date.min(), "->", c.date.max())
