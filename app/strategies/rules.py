# app/strategies/rules.py
from __future__ import annotations

import pandas as pd
from app.indicators.ta import IndicatorParams

def _last_cross(a: pd.Series, b: pd.Series) -> int:
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

def make_signal(
    df: pd.DataFrame,
    timeframe: str,
    params: IndicatorParams,
    risk_reward: float = 3.0,
    decision_threshold: float = 1.0,
) -> dict:
    """מחזיר מילון עם side/confidence/entry/target/metadata.reasons – תואם ל-UI."""
    if df is None or len(df) < 30:
        return {"side":"NEUTRAL","confidence":0.0,"entry":None,"target":None,"metadata":{"reasons":["insufficient data"]}}

    row = df.iloc[-1]
    notes = []
    score = 0.0

    # EMA stack
    if "ema_fast" in df and "ema_mid" in df and "ema_slow" in df:
        if row["ema_fast"] > row["ema_mid"] > row["ema_slow"]:
            score += 1.0; notes.append("Bullish EMA stack")
        elif row["ema_fast"] < row["ema_mid"] < row["ema_slow"]:
            score -= 1.0; notes.append("Bearish EMA stack")
        c1 = _last_cross(df["ema_fast"], df["ema_mid"])
        c2 = _last_cross(df["ema_mid"], df["ema_slow"])
        if c1 == 1: score += 0.4; notes.append("EMA fast crossed above mid")
        if c1 == -1: score -= 0.4; notes.append("EMA fast crossed below mid")
        if c2 == 1: score += 0.3; notes.append("EMA mid crossed above slow")
        if c2 == -1: score -= 0.3; notes.append("EMA mid crossed below slow")

    # MACD histogram
    if "macd" in df and "macd_signal" in df:
        hist = row["macd"] - row["macd_signal"]
        if pd.notna(hist):
            if hist > 0: score += 0.5; notes.append("MACD histogram positive")
            else:        score -= 0.5; notes.append("MACD histogram negative")

    # StochRSI cross extremes
    if "stoch_k" in df and "stoch_d" in df:
        if row["stoch_k"] > row["stoch_d"] and row["stoch_k"] < 20:
            score += 0.4; notes.append("Stoch K cross up from oversold")
        if row["stoch_k"] < row["stoch_d"] and row["stoch_k"] > 80:
            score -= 0.4; notes.append("Stoch K cross down from overbought")

    side = "NEUTRAL"
    if score >= decision_threshold:
        side = "BUY"
    elif score <= -decision_threshold:
        side = "SELL"

    payload = {
        "timeframe": timeframe,
        "side": side,
        "confidence": float(max(min(score, 3.0), -3.0)),
        "entry": float(row["close"]) if "close" in row and pd.notna(row["close"]) else None,
        "target": None,  # ה-UI שלך מציג '-' אם None; יעד מתקבל לרוב מפיבו, לא מהסיגנל
        "metadata": {"reasons": notes},
    }
    return payload
