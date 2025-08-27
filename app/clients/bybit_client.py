import asyncio
import pandas as pd
from app.services.bybit_session import get_bybit_http

INTERVAL_MAP = {
    "1m":"1","3m":"3","5m":"5","15m":"15","30m":"30",
    "1h":"60","2h":"120","4h":"240","6h":"360","12h":"720",
    "d":"D","w":"W","m":"M",
}

def to_bybit_interval(interval: str) -> str:
    return INTERVAL_MAP.get(interval.lower(), interval)

async def _get_kline(category: str, symbol: str, interval: str, limit: int):
    session = get_bybit_http()
    def _call():
        return session.get_kline(
            category=category,
            symbol=symbol,
            interval=interval,
            limit=min(limit, 1000),
        )
    return await asyncio.to_thread(_call)

async def fetch_klines(symbol: str, interval: str, limit: int = 400) -> pd.DataFrame:
    bybit_int = to_bybit_interval(interval)

    data = await _get_kline("linear", symbol, bybit_int, limit)
    if not isinstance(data, dict) or data.get("retCode") != 0:
        data = await _get_kline("spot", symbol, bybit_int, limit)
        if not isinstance(data, dict) or data.get("retCode") != 0:
            raise RuntimeError(f"Bybit error: {data}")

    rows = list(reversed(data["result"]["list"]))
    df = pd.DataFrame(rows, columns=["open_time","open","high","low","close","volume","turnover"])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df[["open_time","open","high","low","close","volume"]]
