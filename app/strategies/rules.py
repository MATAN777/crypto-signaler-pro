from __future__ import annotations
import pandas as pd
from app.indicators.ta import IndicatorParams

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

def make_signal(df: pd.DataFrame, timeframe: str, params: IndicatorParams, risk_reward: float = 3.0, decision_threshold: float = 1.0) -> dict:
    if df is None or len(df) < 30:
        return {"timeframe": timeframe, "side":"NEUTRAL","confidence":0.0,"entry":None,"target":None,"metadata":{"indicators":{}, "reasons":[]}}
    row = df.iloc[-1]
    score = 0.0
    notes = []
    entry_price = float(row["close"]) if "close" in row and pd.notna(row["close"]) else None
    indicators = {}

    if {"ema_fast","ema_mid"}.issubset(df.columns):
        c = _last_cross_confirmed(df["ema_fast"], df["ema_mid"])
        if c == 1:
            indicators["EMA 35/75"] = "BUY"; score += 0.4
            notes.append({"name":"EMA cross","rationale":"EMA35 crossed above EMA75","entry":entry_price,"target":None,"side":"BUY","confidence":0.4})
        elif c == -1:
            indicators["EMA 35/75"] = "SELL"; score -= 0.4
            notes.append({"name":"EMA cross","rationale":"EMA35 crossed below EMA75","entry":entry_price,"target":None,"side":"SELL","confidence":-0.4})
        else:
            indicators["EMA 35/75"] = "NEUTRAL"

    if {"ema_mid","ema_slow"}.issubset(df.columns):
        c = _last_cross_confirmed(df["ema_mid"], df["ema_slow"])
        if c == 1:
            indicators["EMA 75/200"] = "BUY"; score += 0.3
            notes.append({"name":"EMA cross","rationale":"EMA75 crossed above EMA200","entry":entry_price,"target":None,"side":"BUY","confidence":0.3})
        elif c == -1:
            indicators["EMA 75/200"] = "SELL"; score -= 0.3
            notes.append({"name":"EMA cross","rationale":"EMA75 crossed below EMA200","entry":entry_price,"target":None,"side":"SELL","confidence":-0.3})
        else:
            indicators["EMA 75/200"] = "NEUTRAL"

    if {"macd","macd_signal"}.issubset(df.columns):
        hist = row["macd"] - row["macd_signal"]
        if pd.notna(hist) and hist > 0:
            indicators["MACD"] = "BUY"; score += 0.5
            notes.append({"name":"MACD","rationale":"MACD histogram positive","entry":entry_price,"target":None,"side":"BUY","confidence":0.5})
        else:
            indicators["MACD"] = "SELL"; score -= 0.5
            notes.append({"name":"MACD","rationale":"MACD histogram negative","entry":entry_price,"target":None,"side":"SELL","confidence":-0.5})

    if {"stoch_k","stoch_d"}.issubset(df.columns):
        k, d = row["stoch_k"], row["stoch_d"]
        side = "NEUTRAL"; conf = 0.0
        if pd.notna(k) and pd.notna(d):
            if k > d and k < 20:
                side, conf = "BUY", 0.25; score += conf
                notes.append({"name":"StochRSI","rationale":f"K={k:.2f}, %D={d:.2f} (oversold cross up)","entry":entry_price,"target":None,"side":"BUY","confidence":conf})
            elif k < d and k > 80:
                side, conf = "SELL", -0.25; score += conf
                notes.append({"name":"StochRSI","rationale":f"K={k:.2f}, %D={d:.2f} (overbought cross down)","entry":entry_price,"target":None,"side":"SELL","confidence":conf})
            else:
                notes.append({"name":"StochRSI","rationale":f"K={k:.2f}, %D={d:.2f} (neutral)","entry":entry_price,"target":None,"side":"NEUTRAL","confidence":0.0})
        indicators["StochRSI"] = side

    side = "NEUTRAL"
    if score >= decision_threshold: side = "BUY"
    elif score <= -decision_threshold: side = "SELL"

    return {
        "timeframe": timeframe,
        "side": side,
        "confidence": float(max(min(score, 3.0), -3.0)),
        "entry": entry_price,
        "target": None,
        "metadata": {"indicators": indicators, "reasons": notes},
    }