# app/services/http_client.py
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

_client: Optional[httpx.AsyncClient] = None
_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _lock:
        if _client is None:
            _client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers={
                    "user-agent": "CryptoSignalerPro/1.0 (+fastapi)"
                },
                http2=True,
            )
    return _client


async def aclose_http_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

