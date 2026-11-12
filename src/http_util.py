"""Small HTTP helper: retries with backoff on 429/5xx, polite pacing, JSON or bytes."""
from __future__ import annotations

import time

import requests

from config import HTTP_SLEEP

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "ece473-fed-markets/1.0 (academic research)", "Accept": "application/json"})


BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def get(url: str, params: dict | None = None, *, as_json: bool = True, tries: int = 10, timeout: int = 30):
    last = None
    headers = {"User-Agent": BROWSER_UA} if "yahoo.com" in url else None   # Yahoo 429s non-browser agents
    for k in range(tries):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout, headers=headers)
        except requests.RequestException as e:  # network hiccup
            last = e
            time.sleep(min(2 ** k, 60))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After")
            time.sleep(float(ra) if ra and ra.replace(".", "").isdigit() else min(2 ** k, 60))
            last = RuntimeError(f"{r.status_code} {url}")
            continue
        time.sleep(HTTP_SLEEP)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json() if as_json else r.content
    raise RuntimeError(f"GET failed after {tries} tries: {url} {params} ({last})")


def post(url: str, payload: dict, tries: int = 10, timeout: int = 30):
    for k in range(tries):
        r = _SESSION.post(url, json=payload, timeout=timeout)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(2 ** k, 60))
            continue
        time.sleep(HTTP_SLEEP)
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"POST failed: {url}")
