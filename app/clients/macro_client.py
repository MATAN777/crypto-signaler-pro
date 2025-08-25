# app/clients/macro_client.py
from __future__ import annotations

import os
from typing import Literal, Dict, Any

from app.services.http_client import get_http_client


# Simple wrapper over public macro APIs with free endpoints and fallbacks.
# Priority: St. Louis FRED (requires API key), then alternative demo APIs.

FRED_API_KEY = os.getenv("FRED_API_KEY")


async def _fred_series(series_id: str) -> dict | None:
    if not FRED_API_KEY:
        return None
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json"}
    client = await get_http_client()
    r = await client.get(url, params=params)
    if r.status_code != 200:
        return None
    j = r.json()
    obs = j.get("observations") or []
    if not obs:
        return None
    last = next((x for x in reversed(obs) if x.get("value") not in (".", None)), None)
    if not last:
        return None
    return {"date": last.get("date"), "value": float(last.get("value"))}


async def _alt_series(name: str) -> dict | None:
    # Minimal fallback with demo/provider; returns None if unavailable
    # These are placeholders; many providers require keys. Keep best-effort.
    endpoints = {
        "cpi": "https://api.api-ninjas.com/v1/economy?country=US",  # requires API key in header
    }
    return None


async def get_macro(metric: Literal["cpi","unemployment","interest"]) -> dict | None:
    # FRED IDs: CPIAUCSL, UNRATE, FEDFUNDS
    fred_ids = {
        "cpi": "CPIAUCSL",
        "unemployment": "UNRATE",
        "interest": "FEDFUNDS",
    }
    data = await _fred_series(fred_ids[metric])
    if data:
        return {"source": "FRED", "metric": metric, **data}
    # No key available for fallbacks here. Return None to indicate missing.
    return None

