from pydantic import BaseModel, Field
from typing import Literal, Dict, Any

SignalSide = Literal["BUY", "SELL", "NEUTRAL"]

class IndicatorParams(BaseModel):
    # Triple EMA (defaults for swing/position)
    ema_fast: int = Field(35, ge=1, le=500)
    ema_mid: int  = Field(75, ge=1, le=800)
    ema_slow: int = Field(200, ge=1, le=2000)

    # Stochastic RSI defaults (updated: 14,25,7,7)
    rsi_len: int = Field(14, ge=2, le=200)
    stoch_len: int = Field(25, ge=2, le=200)
    stoch_k: int = Field(7, ge=1, le=50)
    stoch_d: int = Field(7, ge=1, le=50)

    # MACD defaults (updated: 33,55,55)
    macd_fast: int = Field(33, ge=1, le=200)
    macd_slow: int = Field(55, ge=1, le=300)
    macd_signal: int = Field(55, ge=1, le=100)

class Signal(BaseModel):
    timeframe: str
    side: SignalSide
    entry: float | None = None
    target: float | None = None
    last_price: float | None = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = {}

class SettingsDTO(BaseModel):
    symbol: str
    params: IndicatorParams
