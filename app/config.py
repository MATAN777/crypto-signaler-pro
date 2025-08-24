from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    bybit_api_key: str | None = os.getenv("BYBIT_API_KEY")
    bybit_api_secret: str | None = os.getenv("BYBIT_API_SECRET")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
    timeframes: list[str] = os.getenv("TIMEFRAMES", "w,m").split(",")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    risk_reward: float = float(os.getenv("RISK_REWARD", "3.0"))
    port: int = int(os.getenv("PORT", "7000"))

settings = Settings()
