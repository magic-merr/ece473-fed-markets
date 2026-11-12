"""Pull Polymarket Fed-decision markets and their daily price history. Stdlib only.

Usage: python3 fetch_polymarket.py OUTDIR
Writes OUTDIR/polymarket/events.json and OUTDIR/polymarket/prices/<market_id>.json
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DAY = 86400
TITLE_RE = re.compile(r"\bfed\b.*\b(decision|interest rates?)\b|\bfomc\b", re.I)


def get(url, params=None, tries=5):
    url = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ece473-research"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(2 ** i); continue
            print(f"HTTP {e.code} {url}", file=sys.stderr); return None
        except Exception:
            time.sleep(2 ** i)
    print(f"FAILED {url}", file=sys.stderr)
    return None


def discover():
    events = {}
    # 1) tag-based listing, open and closed
    for tag in ("fed-rates", "fed", "fomc", "economic-policy"):
        for closed in ("true", "false"):
            off = 0
            while True:
                d = get(f"{GAMMA}/events", {"tag_slug": tag, "closed": closed, "limit": 500, "offset": off})
                if not d:
                    break
                for ev in d:
                    if TITLE_RE.search(ev.get("title", "")):
                        events[ev["id"]] = ev
                if len(d) < 500:
                    break
                off += 500
    # 2) text search fallback
    for q in ("Fed decision", "Fed interest rates", "FOMC"):
        for page in range(1, 6):
            d = get(f"{GAMMA}/public-search", {"q": q, "events_status": "all", "limit_per_type": 50, "page": page})
            evs = (d or {}).get("events") or []
            if not evs:
                break
            for ev in evs:
                if TITLE_RE.search(ev.get("title", "")) and ev["id"] not in events:
                    full = get(f"{GAMMA}/events/{ev['id']}")
                    if full:
                        events[ev["id"]] = full
    return list(events.values())


def history(token, start, end):
    # Resolved markets often return empty for interval=max, so walk explicit windows
    pts, cur = [], start
    while cur < end:
        nxt = min(end, cur + 15 * DAY)
        d = get(f"{CLOB}/prices-history", {"market": token, "startTs": cur, "endTs": nxt, "fidelity": 60})
        pts += (d or {}).get("history", [])
        cur = nxt
        time.sleep(0.05)
    return pts


def ts(s):
    from datetime import datetime
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def main(outdir):
    pdir = os.path.join(outdir, "polymarket")
    os.makedirs(os.path.join(pdir, "prices"), exist_ok=True)
    events = discover()
    json.dump(events, open(os.path.join(pdir, "events.json"), "w"))
    print(f"{len(events)} Fed events", flush=True)
    for ev in events:
        for m in ev.get("markets", []):
            f = os.path.join(pdir, "prices", f"{m['id']}.json")
            if os.path.exists(f):
                continue
            toks = json.loads(m.get("clobTokenIds") or "[]")
            if not toks:
                continue
            start = ts(m.get("startDate") or ev.get("startDate") or ev["creationDate"])
            end = ts(m.get("closedTime") or m.get("endDate") or ev["endDate"]) + 2 * DAY
            end = min(end, int(time.time()))
            pts = history(toks[0], start, end)  # YES token
            json.dump({"event_id": ev["id"], "market_id": m["id"], "question": m.get("question"),
                       "yes_token": toks[0], "history": pts}, open(f, "w"))
        print(f"  {ev.get('title')}", flush=True)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data_raw")
