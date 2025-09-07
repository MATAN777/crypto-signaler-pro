from __future__ import annotations
import pandas as pd
from app.indicators.ta import IndicatorParams

BASE_KEYS = ["EMA 35/75", "EMA 75/200", "MACD Cross", "StochRSI Divergence"]

def _last_cross_confirmed(a: pd.Series, b: pd.Series) -> int:
    if len(a) < 3 or len(b) < 3:
        return 0
    d2 = a.iloc[-3] - b.iloc[-3]
    d1 = a.iloc[-2] - b.iloc[-2]
    d0 = a.iloc[-1] - b.iloc[-1]
    if pd.isna(d2) or pd.isna(d1) or pd.isna(d0):
        return 0
    if d2 <= 0 and d1 > 0 and d0 > 0:
        return 1
    if d2 >= 0 and d1 < 0 and d0 < 0:
        return -1
    return 0

def _find_swings(series: pd.Series, win: int = 5):
    if len(series) < win * 3:
        return None
    s = series.reset_index(drop=True)
    highs, lows = [], []
    half = win // 2
    for i in range(half, len(s) - half):
        w = s.iloc[i - half:i + half + 1]
        if s.iloc[i] == w.max(): highs.append(i)
        if s.iloc[i] == w.min(): lows.append(i)
    highs = highs[-2:] if len(highs) >= 2 else []
    lows  = lows[-2:]  if len(lows)  >= 2 else []
    return {"highs": highs, "lows": lows}

def _stoch_rsi_divergence(close: pd.Series, stoch_k: pd.Series, win: int = 5) -> int:
    sp = _find_swings(close, win=win)
    ss = _find_swings(stoch_k, win=win)
    if not sp or not ss:
        return 0
    if len(sp["lows"]) >= 2 and len(ss["lows"]) >= 2:
        p1, p2 = sp["lows"][-2], sp["lows"][-1]
        s1, s2 = ss["lows"][-2], ss["lows"][-1]
        if p1 < p2 and s1 < s2:
            if close.iloc[p2] < close.iloc[p1] and stoch_k.iloc[s2] > stoch_k.iloc[s1]:
                return 1
    if len(sp["highs"]) >= 2 and len(ss["highs"]) >= 2:
        p1, p2 = sp["highs"][-2], sp["highs"][-1]
        s1, s2 = ss["highs"][-2], ss["highs"][-1]
        if p1 < p2 and s1 < s2:
            if close.iloc[p2] > close.iloc[p1] and stoch_k.iloc[s2] < stoch_k.iloc[s1]:
                return -1
    return 0

def make_signal(df: pd.DataFrame, timeframe: str, params: IndicatorParams, risk_reward: float = 3.0, decision_threshold: float = 1.0) -> dict:
    if df is None or len(df) < 30:
        return {
            "timeframe": timeframe,
            "side": "NEUTRAL",
            "confidence": 0.0,
            "entry": None,
            "target": None,
            "metadata": {"indicators": {k: "NEUTRAL" for k in BASE_KEYS}, "reasons": []},
        }

    row = df.iloc[-1]
    score = 0.0
    notes = []
    entry_price = float(row["close"]) if "close" in row and pd.notna(row["close"]) else None
    indicators = {k: "NEUTRAL" for k in BASE_KEYS}

    if {"ema_fast","ema_mid"}.issubset(df.columns):
        c = _last_cross_confirmed(df["ema_fast"], df["ema_mid"])
        if c == 1:
            indicators["EMA 35/75"] = "BUY";  score += 0.4
            notes.append({"name":"EMA 35/75","rationale":"Cross up","entry":entry_price,"target":None,"side":"BUY","confidence":0.4})
        elif c == -1:
            indicators["EMA 35/75"] = "SELL"; score -= 0.4
            notes.append({"name":"EMA 35/75","rationale":"Cross down","entry":entry_price,"target":None,"side":"SELL","confidence":-0.4})

    if {"ema_mid","ema_slow"}.issubset(df.columns):
        c = _last_cross_confirmed(df["ema_mid"], df["ema_slow"])
        if c == 1:
            indicators["EMA 75/200"] = "BUY";  score += 0.3
            notes.append({"name":"EMA 75/200","rationale":"Cross up","entry":entry_price,"target":None,"side":"BUY","confidence":0.3})
        elif c == -1:
            indicators["EMA 75/200"] = "SELL"; score -= 0.3
            notes.append({"name":"EMA 75/200","rationale":"Cross down","entry":entry_price,"target":None,"side":"SELL","confidence":-0.3})

    if {"macd","macd_signal"}.issubset(df.columns):
        c = _last_cross_confirmed(df["macd"], df["macd_signal"])
        if c == 1:
            indicators["MACD Cross"] = "BUY";  score += 0.5
            notes.append({"name":"MACD Cross","rationale":"Cross up","entry":entry_price,"target":None,"side":"BUY","confidence":0.5})
        elif c == -1:
            indicators["MACD Cross"] = "SELL"; score -= 0.5
            notes.append({"name":"MACD Cross","rationale":"Cross down","entry":entry_price,"target":None,"side":"SELL","confidence":-0.5})

    if {"stoch_k","stoch_d","close"}.issubset(df.columns):
        div = _stoch_rsi_divergence(df["close"], df["stoch_k"], win=5)
        if div == 1:
            indicators["StochRSI Divergence"] = "BUY";  score += 0.25
            notes.append({"name":"StochRSI Divergence","rationale":"Bullish","entry":entry_price,"target":None,"side":"BUY","confidence":0.25})
        elif div == -1:
            indicators["StochRSI Divergence"] = "SELL"; score -= 0.25
            notes.append({"name":"StochRSI Divergence","rationale":"Bearish","entry":entry_price,"target":None,"side":"SELL","confidence":-0.25})

    side = "NEUTRAL"
    if score >= decision_threshold: side = "BUY"
    elif score <= -decision_threshold: side = "SELL"

    # --- Ensure all indicators are present in reasons ---
    for k in BASE_KEYS:
        if not any(r["name"] == k for r in notes):
            notes.append({
                "name": k,
                "rationale": "",
                "entry": entry_price,
                "target": None,
                "side": indicators[k],
                "confidence": 0.0
            })

    # --- Calculate target if not set ---
    target = None
    # Example: set target as entry + 1% for BUY, entry - 1% for SELL
    if side == "BUY" and entry_price is not None:
        target = round(entry_price * 1.01, 2)
    elif side == "SELL" and entry_price is not None:
        target = round(entry_price * 0.99, 2)

    return {
        "timeframe": timeframe,
        "side": side,
        "confidence": float(max(min(score, 3.0), -3.0)),
        "entry": entry_price,
        "target": target,
        "metadata": {"indicators": indicators, "reasons": notes},
    }