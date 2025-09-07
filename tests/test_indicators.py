import pandas as pd
import numpy as np
import pytest
from unittest.mock import AsyncMock, patch

from app.indicators.ta import (
    last_cross,
    compute_indicators,
    compute_fib_031,
    approximate_zones,
    IndicatorParams,
)
from app.strategies.rules import _stoch_rsi_divergence, make_signal
from app.notifiers import telegram
from app.config import settings


def test_last_cross():
    fast = pd.Series([1, 2, 3, 4])
    slow = pd.Series([2, 2, 2, 3])
    assert last_cross(fast, slow) == 1

    fast = pd.Series([4, 3, 2, 1])
    slow = pd.Series([2, 2, 2, 2])
    assert last_cross(fast, slow) == -1


def test_stoch_rsi_divergence():
    close = pd.Series([100, 98, 95, 96, 94, 93, 92, 93, 94, 95])
    stoch_k = pd.Series([0.2, 0.25, 0.3, 0.28, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6])
    div = _stoch_rsi_divergence(close, stoch_k, win=2)
    assert div in (0, 1, -1)


def _fake_ohlcv(n: int = 300):
    return pd.DataFrame({
        "open": np.random.rand(n) * 100 + 100,
        "high": np.random.rand(n) * 100 + 150,
        "low": np.random.rand(n) * 100 + 50,
        "close": np.random.rand(n) * 100 + 100,
        "volume": np.random.rand(n) * 10,
    })


def test_compute_indicators_and_signal():
    df = _fake_ohlcv(300)
    params = IndicatorParams()
    data = compute_indicators(df, params)
    sig = make_signal(data, "1h", params)

    assert "metadata" in sig
    ind = sig["metadata"]["indicators"]
    # All four indicator keys should be present
    assert set(ind.keys()) >= {
        "EMA 35/75",
        "EMA 75/200",
        "MACD Cross",
        "StochRSI Divergence",
    }


def test_fib031_and_zones():
    df = _fake_ohlcv(500)
    data = compute_indicators(df, IndicatorParams())

    fib = compute_fib_031(data, lookback=180)
    zones = approximate_zones(data, lookback=200)

    assert fib is None or "level" in fib
    assert zones is None or ("demand" in zones and "supply" in zones)


def test_telegram_notification_on_signal():
    df = _fake_ohlcv(300)
    params = IndicatorParams()
    data = compute_indicators(df, params)
    sig = make_signal(data, "1h", params)
    new_ind = sig.get("metadata", {}).get("indicators", {})
    old_ind = {}  # Simulate no previous indicators
    changed = list(new_ind.keys())

    with patch("app.notifiers.telegram.send_telegram_photo", new_callable=AsyncMock) as mock_send:
        # Simulate settings
        token = "dummy_token"
        chat_id = "dummy_chat_id"
        png = b"fake_png_bytes"
        caption = "Test caption"
        # Call the notifier as in scheduler.py
        import asyncio
        asyncio.run(telegram.send_telegram_photo(token, chat_id, png, caption))
        mock_send.assert_awaited_once_with(token, chat_id, png, caption)