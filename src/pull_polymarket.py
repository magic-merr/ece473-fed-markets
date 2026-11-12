"""Pull Polymarket "Fed decision in <month>?" markets: metadata, hourly price history, trade prints, fees.

Outputs
  raw/polymarket/markets.csv                 one row per outcome market (bucket) with Yes token id
  raw/polymarket/prices/{conditionId}.csv    hourly price history of the Yes token (t, p)
  raw/polymarket/trades/{conditionId}.csv    trade prints converted to Yes-equivalent price
  raw/polymarket/fees.csv                    taker fee rate per Yes token (current), plus gamma fee flags

Notes
  * CLOB /prices-history `p` is Polymarket's displayed price: the midpoint when the spread is <= 10c,
    otherwise the last trade. Historical order books are not published, so Polymarket spreads can only be
    observed for live markets (raw/polymarket/books_live.csv).
  * Trades come from Data API v2 (/v2/trades, cursor pagination, full history).
  * A No-token trade at price q is recorded as a Yes-equivalent price of 1 - q.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import pandas as pd

from config import (MONTHS, POLY_CLOB, POLY_DATA, POLY_GAMMA, POLY_RAW, SAMPLE_START, meeting_for_month)
from http_util import get

MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
               "october", "november", "december"]
# Per-meeting decision events only ("Fed decision in March?", "Fed Interest Rates: March 2024").
# Excludes cumulative markets such as "Fed rate cut by June?" or "How many Fed cuts in 2025?".
TITLE_RE = re.compile(r"^(?!.*\b(by|how many|before|cuts in|hikes in)\b).*\bfed\b.*(\bdecision\b|interest rates?:)",
                      re.I)


def parse_bucket(label: str):
    """Map an outcome label to a change in bps. Returns (bps, open_ended) or None.

    'No change' -> (0, False); '25 bps decrease' -> (-25, False); '50+ bps decrease' -> (-50, True);
    '25+ bps increase' -> (25, True); 'Increase' -> (25, True).
    """
    s = (label or "").lower().strip()
    if not s:
        return None
    if "no change" in s or s in ("hold", "pause", "unchanged"):
        return 0, False
    sign = -1 if re.search(r"decreas|cut|lower", s) else (1 if re.search(r"increas|hike|raise", s) else 0)
    if sign == 0:
        return None
    m = re.search(r"(\d+)\s*(\+)?\s*(?:bps|bp|basis)", s)
    if not m:
        return sign * 25, True
    return sign * int(m.group(1)), bool(m.group(2))


CLEAN_LABEL = re.compile(r"^(no change|\d+\+? ?bps? (increase|decrease|cut|hike))$")


def is_clean_bucket(label: str) -> bool:
    """Plain decision buckets only: drops dissent-count side markets ('25bp cut, Dissents: >2') and
    meta markets ("'No change' or '25 bps cut' favored ...")."""
    s = re.sub(r"\s+after .* meeting\??$", "", (label or "").lower().strip()).rstrip("?").strip()
    return bool(CLEAN_LABEL.match(s))


def clean_markets(df: pd.DataFrame) -> pd.DataFrame:
    """Keep clean buckets, and for each meeting only the event with the most volume (Polymarket sometimes
    lists a duplicate, near-empty event for the same meeting)."""
    df = df[df["label"].map(is_clean_bucket)].copy()
    vol = df.groupby(["meeting", "event_id"])["volume_total"].sum().rename("event_volume").reset_index()
    keep = vol.sort_values("event_volume").drop_duplicates("meeting", keep="last")[["meeting", "event_id"]]
    return df.merge(keep, on=["meeting", "event_id"]).sort_values(["meeting", "bps"]).reset_index(drop=True)


def meeting_from_event(title: str, end_date: str | None):
    t = (title or "").lower()
    mon = next((i + 1 for i, n in enumerate(MONTH_NAMES) if re.search(rf"\b{n}\b", t)), None)
    if mon is None:
        return None
    ym = re.search(r"\b(20\d{2})\b", t)
    year = int(ym.group(1)) if ym else (pd.Timestamp(end_date).year if end_date else None)
    if year is None:
        return None
    meet = meeting_for_month(year, mon)
    if meet is None and end_date:  # e.g. event ends early January for a December meeting
        meet = meeting_for_month(year - 1, mon)
    return meet


def discover_events() -> list[dict]:
    seen, events = set(), []
    for tag in ("fed-rates", "fed", "economic-policy"):
        for closed in ("true", "false"):
            off = 0
            while True:
                j = get(f"{POLY_GAMMA}/events", {"tag_slug": tag, "closed": closed, "limit": 500, "offset": off})
                if not j:
                    break
                for e in j:
                    if e.get("id") not in seen:
                        seen.add(e.get("id"))
                        events.append(e)
                if len(j) < 500:
                    break
                off += 500
    # Fallback / supplement: text search
    for q in ("Fed decision in", "Fed interest rates"):
        page = 1
        while page <= 10:
            j = get(f"{POLY_GAMMA}/public-search", {"q": q, "events_status": "all", "limit_per_type": 50,
                                                   "page": page})
            evs = (j or {}).get("events") or []
            for e in evs:
                if e.get("id") not in seen:
                    seen.add(e.get("id"))
                    events.append(e)
            if not (j or {}).get("pagination", {}).get("hasMore"):
                break
            page += 1
    return [e for e in events if TITLE_RE.search(e.get("title") or "")]


def event_markets(e: dict) -> list[dict]:
    ms = e.get("markets")
    if not ms or "clobTokenIds" not in ms[0]:
        full = get(f"{POLY_GAMMA}/events/{e['id']}") or {}
        ms = full.get("markets") or []
    return ms


def build_market_table(events: list[dict]) -> pd.DataFrame:
    rows = []
    for e in events:
        meet = meeting_from_event(e.get("title"), e.get("endDate"))
        if meet is None or pd.Timestamp(meet) < pd.Timestamp(SAMPLE_START):
            continue
        for m in event_markets(e):
            label = m.get("groupItemTitle") or m.get("question")
            b = parse_bucket(label)
            if b is None:
                continue
            outcomes = json.loads(m.get("outcomes") or "[]")
            tokens = json.loads(m.get("clobTokenIds") or "[]")
            if len(tokens) != 2:
                continue
            yes_i = outcomes.index("Yes") if "Yes" in outcomes else 0
            rows.append({
                "meeting": meet, "event_id": e.get("id"), "event_slug": e.get("slug"), "event_title": e.get("title"),
                "market_id": m.get("id"), "condition_id": m.get("conditionId"), "label": label,
                "bps": b[0], "open_ended": b[1], "yes_token": tokens[yes_i], "no_token": tokens[1 - yes_i],
                "start": m.get("startDate") or e.get("startDate"), "end": m.get("endDate") or e.get("endDate"),
                "closed": m.get("closed"), "outcome_prices": m.get("outcomePrices"),
                "volume_total": m.get("volumeNum", m.get("volume")),
                "fees_enabled": m.get("feesEnabled"), "maker_base_fee": m.get("makerBaseFee"),
                "taker_base_fee": m.get("takerBaseFee"),
                "best_bid": m.get("bestBid"), "best_ask": m.get("bestAsk"), "spread_now": m.get("spread"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return clean_markets(df.drop_duplicates("condition_id"))


def pull_prices(m: pd.Series, refresh: bool) -> int:
    out = POLY_RAW / "prices" / f"{m.condition_id}.csv"
    if out.exists() and m.closed and not refresh:
        return -1
    start = int(pd.Timestamp(m.start).timestamp()) if m.start else int(pd.Timestamp(SAMPLE_START).timestamp())
    end = int(pd.Timestamp(m.end).timestamp()) + 3 * 86400 if m.end else int(pd.Timestamp.now("UTC").timestamp())
    end = min(end, int(pd.Timestamp.now("UTC").timestamp()))
    pts, step = [], 14 * 86400   # long ranges at hourly fidelity can come back empty; chunk them
    for a in range(start, end, step):
        j = get(f"{POLY_CLOB}/prices-history", {"market": m.yes_token, "startTs": a, "endTs": min(a + step, end),
                                                 "fidelity": 60})
        pts.extend((j or {}).get("history") or [])
    df = pd.DataFrame(pts, columns=["t", "p"]).drop_duplicates("t").sort_values("t")
    df.to_csv(out, index=False)
    return len(df)


def pull_trades(m, refresh: bool) -> tuple[int, bool]:
    """Data API v2: /v2/trades?condition=<conditionId>, cursor-paginated (v1 was retired)."""
    out = POLY_RAW / "trades" / f"{m.condition_id}.csv"
    if out.exists() and m.closed and not refresh:
        return -1, False
    rows, cursor, truncated, pages = [], None, False, 0
    while True:
        params = {"condition": m.condition_id, "limit": 500, "taker_only": "true"}
        if cursor:
            params["cursor"] = cursor
        try:
            j = get(f"{POLY_DATA}/v2/trades", params)
        except Exception as ex:
            print(f"    trades {m.condition_id[:10]} stopped after {pages} pages: {ex}", file=sys.stderr)
            truncated = True
            break
        rows.extend((j or {}).get("data") or [])
        pages += 1
        pg = (j or {}).get("pagination") or {}
        cursor = pg.get("next_cursor")
        if not pg.get("has_more") or not cursor:
            break
    recs = []
    for t in rows:
        px = float(t["price"])
        is_yes = str(t.get("token_id")) == str(m.yes_token) or (t.get("outcome") or "").lower() == "yes"
        recs.append({"ts": int(t["timestamp"]), "yes_price": px if is_yes else 1 - px, "size": float(t["size"]),
                     "side": t.get("side"), "token": "yes" if is_yes else "no"})
    pd.DataFrame(recs, columns=["ts", "yes_price", "size", "side", "token"]).sort_values("ts").to_csv(out, index=False)
    return len(recs), truncated


def pull_fee_rate(token: str):
    j = get(f"{POLY_CLOB}/fee-rate", {"token_id": token})
    if not isinstance(j, dict):
        return None, None
    for k in ("base_fee", "fee_rate_bps", "feeRateBps", "taker_fee", "fee"):
        if k in j and j[k] is not None:
            return float(j[k]), json.dumps(j)
    return None, json.dumps(j)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    for sub in ("prices", "trades"):
        (POLY_RAW / sub).mkdir(parents=True, exist_ok=True)

    events = discover_events()
    print(f"{len(events)} Fed events found")
    mk = build_market_table(events)
    mk.to_csv(POLY_RAW / "markets.csv", index=False)   # already cleaned (clean_markets)
    print(f"{len(mk)} outcome markets across {mk['meeting'].nunique() if len(mk) else 0} meetings")

    trunc_log, fee_rows, books = [], [], []
    for i, m in enumerate(mk.itertuples(index=False), 1):
        pull_prices(m, a.refresh)
        n, tr = pull_trades(m, a.refresh)
        if tr:
            trunc_log.append(m.condition_id)
        rate, raw = pull_fee_rate(m.yes_token)
        fee_rows.append({"condition_id": m.condition_id, "yes_token": m.yes_token, "fee_rate_raw": rate,
                         "fee_json": raw, "fees_enabled": m.fees_enabled, "taker_base_fee": m.taker_base_fee})
        if not m.closed:
            b = get(f"{POLY_CLOB}/book", {"token_id": m.yes_token}) or {}
            bids = [float(x["price"]) for x in b.get("bids", [])]
            asks = [float(x["price"]) for x in b.get("asks", [])]
            books.append({"condition_id": m.condition_id, "meeting": m.meeting, "bps": m.bps,
                          "best_bid": max(bids) if bids else None, "best_ask": min(asks) if asks else None,
                          "pulled_at": pd.Timestamp.now("UTC").isoformat()})
        if i % 20 == 0:
            print(f"  {i}/{len(mk)}")
    pd.DataFrame(fee_rows).to_csv(POLY_RAW / "fees.csv", index=False)
    pd.DataFrame(books).to_csv(POLY_RAW / "books_live.csv", index=False)
    pd.Series(trunc_log, name="condition_id").to_csv(POLY_RAW / "trades_truncated.csv", index=False)
    print(f"done. trade history truncated for {len(trunc_log)} markets (oldest prints missing)")


if __name__ == "__main__":
    main()
