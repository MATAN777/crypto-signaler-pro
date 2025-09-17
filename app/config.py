from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    bybit_api_key: str | None = os.getenv("BYBIT_API_KEY")
    bybit_api_secret: str | None = os.getenv("BYBIT_API_SECRET")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
    symbols: list[str] = [s.strip().upper() for s in os.getenv("SYMBOLS", "BTCUSDT").split(",") if s.strip()]
    # Default to required signal timeframes
    timeframes: list[str] = [t.strip() for t in os.getenv("TIMEFRAMES", "15m,30m,1h,2h,4h,6h,12h,d,w").split(",") if t.strip()]
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    risk_reward: float = float(os.getenv("RISK_REWARD", "3.0"))
    port: int = int(os.getenv("PORT", "7000"))

settings = Settings()