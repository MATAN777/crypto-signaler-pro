from pydantic import BaseModel, Field
from typing import Literal, Dict, Any

SignalSide = Literal["BUY", "SELL", "NEUTRAL"]

class IndicatorParams(BaseModel):
    # Triple EMA (defaults for swing/position)
    ema_fast: int = Field(35, ge=1, le=500)
    ema_mid: int  = Field(75, ge=1, le=800)
    ema_slow: int = Field(200, ge=1, le=2000)
    stoch_rsi_length: int = Field(14, ge=2, le=200)
    stoch_rsi_k: int = Field(3, ge=1, le=50)
    stoch_rsi_d: int = Field(3, ge=1, le=50)
    macd_fast: int = Field(12, ge=1, le=200)
    macd_slow: int = Field(26, ge=1, le=300)
    macd_signal: int = Field(9, ge=1, le=100)

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
