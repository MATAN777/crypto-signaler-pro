from __future__ import annotations

from threading import Lock
from typing import Optional

from pybit.unified_trading import HTTP

from app.config import settings


_session: Optional[HTTP] = None
_lock: Lock = Lock()


def get_bybit_http() -> HTTP:
    global _session
    if _session is not None:
        return _session
    with _lock:
        if _session is None:
            _session = HTTP(
                testnet=False,
                api_key=settings.bybit_api_key,
                api_secret=settings.bybit_api_secret,
            )
    return _session

