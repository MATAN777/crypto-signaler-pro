# app/services/confluence.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

import pandas as pd


@dataclass
class ConfluenceResult:
    score: float
    label: str
    reasons: list[str]


def compute_confluence(df: pd.DataFrame) -> ConfluenceResult:
    """Aggregate multiple indicators into a simple confluence score and label.

    Heuristics:
    - EMA stack alignment ±1.0
    - MACD histogram sign ±0.5
    - Stoch RSI crosses near extremes ±0.6
    - Money Flow Index oversold/overbought rebounds ±0.5
    - Chaikin Money Flow sign ±0.4
    """
    if df is None or len(df) < 30:
        return ConfluenceResult(0.0, "NEUTRAL", ["insufficient data"])

    row = df.iloc[-1]
    reasons: list[str] = []
    score = 0.0

    # EMA structure
    if set(["ema_fast","ema_mid","ema_slow"]).issubset(df.columns):
        if row["ema_fast"] > row["ema_mid"] > row["ema_slow"]:
            score += 1.0; reasons.append("Bullish EMA stack")
        elif row["ema_fast"] < row["ema_mid"] < row["ema_slow"]:
            score -= 1.0; reasons.append("Bearish EMA stack")

    # MACD histogram
    if set(["macd","macd_signal"]).issubset(df.columns):
        hist = (row["macd"] - row["macd_signal"]) if pd.notna(row.get("macd")) and pd.notna(row.get("macd_signal")) else 0.0
        if hist > 0: score += 0.5; reasons.append("MACD histogram positive")
        elif hist < 0: score -= 0.5; reasons.append("MACD histogram negative")

    # Stoch RSI extremes
    if set(["stoch_k","stoch_d"]).issubset(df.columns):
        if pd.notna(row.get("stoch_k")) and pd.notna(row.get("stoch_d")):
            if row["stoch_k"] > row["stoch_d"] and row["stoch_k"] < 20:
                score += 0.6; reasons.append("Stoch K cross up from oversold")
            if row["stoch_k"] < row["stoch_d"] and row["stoch_k"] > 80:
                score -= 0.6; reasons.append("Stoch K cross down from overbought")

    # Money Flow Index
    if "mfi" in df.columns and pd.notna(row.get("mfi")):
        if row["mfi"] < 20:
            score += 0.5; reasons.append("MFI oversold")
        elif row["mfi"] > 80:
            score -= 0.5; reasons.append("MFI overbought")

    # Chaikin Money Flow
    if "cmf" in df.columns and pd.notna(row.get("cmf")):
        if row["cmf"] > 0:
            score += 0.4; reasons.append("CMF positive (inflow)")
        elif row["cmf"] < 0:
            score -= 0.4; reasons.append("CMF negative (outflow)")

    label = "NEUTRAL"
    if score >= 2.0:
        label = "EXTREME BUY"
    elif score <= -2.0:
        label = "SUPER SELL"

    return ConfluenceResult(float(score), label, reasons)

