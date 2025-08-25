# app/indicators/ta.py
from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class IndicatorParams:
    # שמירה על תאימות אם אתה קורא ישירות למחלקה מכאן
    ema_fast: int = 35
    ema_mid: int = 75
    ema_slow: int = 200
    rsi_len: int = 14
    stoch_len: int = 14
    stoch_k: int = 3
    stoch_d: int = 3
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    mfi_len: int = 14
    cmf_len: int = 20


# ---------- Utils ----------
def _ema(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(span=length, adjust=False).mean()


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/length, adjust=False).mean()
    roll_down = down.ewm(alpha=1/length, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    hl = (df["high"] - df["low"]).abs()
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()


def last_cross(a: pd.Series, b: pd.Series) -> int:
    """Return 1 if a crossed above b on the last bar, -1 if crossed below, else 0."""
    if len(a) < 2 or len(b) < 2:
        return 0
    prev = (a.iloc[-2] - b.iloc[-2])
    curr = (a.iloc[-1] - b.iloc[-1])
    if pd.isna(prev) or pd.isna(curr):
        return 0
    if prev <= 0 and curr > 0:
        return 1
    if prev >= 0 and curr < 0:
        return -1
    return 0


def _mfi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    # Money Flow Index based on typical price and volume
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    mf = tp * df["volume"]
    up = tp > tp.shift(1)
    down = tp < tp.shift(1)
    pos_mf = mf.where(up, 0.0)
    neg_mf = mf.where(down, 0.0)
    pos_sum = pos_mf.rolling(length, min_periods=length).sum()
    neg_sum = neg_mf.rolling(length, min_periods=length).sum()
    denom = (pos_sum + neg_sum).replace(0, np.nan)
    mfi = 100.0 * (pos_sum / denom)
    return mfi.clip(0, 100)


def _cmf(df: pd.DataFrame, length: int = 20) -> pd.Series:
    # Chaikin Money Flow
    hl_range = (df["high"] - df["low"]).replace(0, np.nan)
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl_range
    mfv = mfm.fillna(0.0) * df["volume"]
    mfv_sum = mfv.rolling(length, min_periods=length).sum()
    vol_sum = df["volume"].rolling(length, min_periods=length).sum().replace(0, np.nan)
    cmf = mfv_sum / vol_sum
    return cmf


# ---------- Core indicators ----------
def compute_indicators(df: pd.DataFrame, p: IndicatorParams) -> pd.DataFrame:
    """מוסיף EMA/MACD/StochRSI/ATR ל-DataFrame"""
    data = df.copy()

    # EMA
    data["ema_fast"] = _ema(data["close"], p.ema_fast)
    data["ema_mid"]  = _ema(data["close"], p.ema_mid)
    data["ema_slow"] = _ema(data["close"], p.ema_slow)

    # MACD
    ema_f = _ema(data["close"], p.macd_fast)
    ema_s = _ema(data["close"], p.macd_slow)
    data["macd"] = ema_f - ema_s
    data["macd_signal"] = _ema(data["macd"], p.macd_signal)

    # RSI + StochRSI
    rsi = _rsi(data["close"], p.rsi_len)
    min_rsi = rsi.rolling(p.stoch_len).min()
    max_rsi = rsi.rolling(p.stoch_len).max()
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)
    data["stoch_k"] = stoch_rsi.rolling(p.stoch_k).mean()
    data["stoch_d"] = data["stoch_k"].rolling(p.stoch_d).mean()

    # ATR
    data["atr"] = _atr(data, 14)

    # Money Flow indicators
    try:
        data["mfi"] = _mfi(data, getattr(p, "mfi_len", 14))
    except Exception:
        data["mfi"] = np.nan
    try:
        data["cmf"] = _cmf(data, getattr(p, "cmf_len", 20))
    except Exception:
        data["cmf"] = np.nan

    return data


# ---------- Fib 0.31 ----------
def compute_fib_031(df: pd.DataFrame, lookback: int = 180) -> dict | None:
    """לוקח את הסווינגים האחרונים (max/min) בחלון lookback ומחשב רמת 0.31.
    כיוון 'up' אם close > ema_mid ו-ema_fast>ema_mid, אחרת 'down'."""
    if df is None or len(df) < max(lookback, 50):
        return None

    data = df.copy()
    last = data.iloc[-1]

    # אם אין ema_mid נחשב מינימלי
    if "ema_mid" not in data.columns:
        data["ema_mid"] = _ema(data["close"], 75)

    window = data.tail(lookback)
    swing_high = float(window["high"].max())
    swing_low  = float(window["low"].min())

    # כיוון
    direction = "up" if (last["close"] > last["ema_mid"] and
                         ("ema_fast" not in data.columns or last.get("ema_fast", last["close"]) > last["ema_mid"])) else "down"

    rng = swing_high - swing_low
    if rng <= 0 or math.isnan(rng):
        return None

    if direction == "up":
        level = swing_low + 0.31 * rng
    else:
        level = swing_high - 0.31 * rng

    atr_val = float(window["atr"].iloc[-1] if "atr" in window.columns else _atr(window, 14).iloc[-1])
    last_price = float(last["close"])
    distance_pct = abs(level - last_price) / last_price * 100.0

    return {
        "direction": direction,
        "swing_low": round(swing_low, 3),
        "swing_high": round(swing_high, 3),
        "level": round(level, 3),
        "basis_time": str(len(window)),
        "atr": round(atr_val, 2),
        "distance_pct": round(distance_pct, 3),
    }


def suggest_entry_from_fib(fib: dict, rr: float = 3.0) -> dict | None:
    if not fib:
        return None
    entry = float(fib["level"])
    atr = float(fib.get("atr", 0)) or 0.0
    side = "BUY" if fib["direction"] == "up" else "SELL"

    # מרחק סטופ ~1.8*ATR (אפשר לכוונן)
    stop = entry - 1.8 * atr if side == "BUY" else entry + 1.8 * atr
    risk = entry - stop if side == "BUY" else stop - entry
    target = entry + rr * risk if side == "BUY" else entry - rr * risk

    return {
        "side": side,
        "entry": round(entry, 3),
        "stop": round(stop, 3),
        "target": round(target, 3),
        "rr": rr,
        "basis": {"type": "fib_0.31", "swing_low": fib["swing_low"], "swing_high": fib["swing_high"]},
    }


# ---------- Demand / Supply (פשוט) ----------
def approximate_zones(df: pd.DataFrame, lookback: int = 200) -> dict | None:
    """אומדן אזורי דרישה/היצע: demand סביב swing_low, supply סביב swing_high ± ATR."""
    if df is None or len(df) < max(lookback, 50):
        return None
    data = df.copy()
    window = data.tail(lookback)
    swing_high = float(window["high"].max())
    swing_low  = float(window["low"].min())
    atr_val = float(window["atr"].iloc[-1] if "atr" in window.columns else _atr(window, 14).iloc[-1])

    demand = {"low": round(swing_low, 3), "high": round(swing_low + atr_val, 3)}
    supply = {"low": round(swing_high - atr_val, 3), "high": round(swing_high, 3)}

    return {"demand": demand, "supply": supply, "atr": round(atr_val, 2)}
