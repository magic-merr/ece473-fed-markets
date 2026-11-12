"""Pull every Kalshi Fed contract (strike ladder + decision series) with daily candles.

Stdlib only. Usage: python3 fetch_kalshi.py OUTDIR
Writes OUTDIR/kalshi/markets_<SERIES>.json and OUTDIR/kalshi/candles/<TICKER>.json
Resumable: skips tickers whose candle file already exists.
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"
# Strike ladder ("above X%") and the cut/hold/hike decision markets, legacy + KX tickers
SERIES = ["KXFED", "FED", "KXFEDDECISION", "FEDDECISION"]
START = int(datetime(2021, 6, 1, tzinfo=timezone.utc).timestamp())
DAY = 86400


def get(path, params=None, tries=5):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ece473-research"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i)
                continue
            body = e.read()[:300]
            print(f"HTTP {e.code} {url} {body}", file=sys.stderr)
            return None
        except Exception as e:
            time.sleep(2 ** i)
    print(f"FAILED {url}", file=sys.stderr)
    return None


def paged(path, params, key):
    out, cursor = [], None
    while True:
        p = dict(params, limit=1000)
        if cursor:
            p["cursor"] = cursor
        d = get(path, p)
        if not d:
            break
        out += d.get(key, [])
        cursor = d.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    return out


def candles(series, m):
    t = m["ticker"]
    o = m.get("open_time") or m.get("created_time")
    c = m.get("close_time") or m.get("expiration_time")
    def ts(s):
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    s = max(START, ts(o)) if o else START
    e = min(int(time.time()), ts(c) + 2 * DAY) if c else int(time.time())
    res = []
    # API caps candles per request; walk in 180-day windows
    for path in (f"/series/{series}/markets/{t}/candlesticks", f"/historical/markets/{t}/candlesticks"):
        res, cur = [], s
        while cur < e:
            nxt = min(e, cur + 180 * DAY)
            d = get(path, {"start_ts": cur, "end_ts": nxt, "period_interval": 1440})
            if d and d.get("candlesticks"):
                res += d["candlesticks"]
            cur = nxt
        if res:
            return res, path.split("/")[1]
    return res, None


def main(outdir):
    kdir = os.path.join(outdir, "kalshi")
    cdir = os.path.join(kdir, "candles")
    os.makedirs(cdir, exist_ok=True)
    cutoff = get("/historical/cutoff")
    json.dump(cutoff, open(os.path.join(kdir, "historical_cutoff.json"), "w"))
    for s in SERIES:
        live = paged("/markets", {"series_ticker": s}, "markets")
        hist = paged("/historical/markets", {"series_ticker": s}, "markets")
        seen, mkts = set(), []
        for m in live + hist:
            if m["ticker"] not in seen:
                seen.add(m["ticker"])
                m["_source"] = "live" if m in live else "historical"
                mkts.append(m)
        json.dump(mkts, open(os.path.join(kdir, f"markets_{s}.json"), "w"))
        print(f"{s}: {len(live)} live + {len(hist)} historical -> {len(mkts)} markets", flush=True)
        for i, m in enumerate(mkts):
            f = os.path.join(cdir, m["ticker"] + ".json")
            if os.path.exists(f):
                continue
            cs, src = candles(s, m)
            json.dump({"series": s, "ticker": m["ticker"], "endpoint": src, "candlesticks": cs}, open(f, "w"))
            if i % 50 == 0:
                print(f"  {s} {i}/{len(mkts)}", flush=True)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data_raw")
