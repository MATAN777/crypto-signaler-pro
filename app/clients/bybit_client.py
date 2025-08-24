import httpx
import pandas as pd

BASE_URL = "https://api.bybit.com"
INTERVAL_MAP = {
    "1m":"1","3m":"3","5m":"5","15m":"15","30m":"30",
    "1h":"60","2h":"120","4h":"240","6h":"360","12h":"720",
    "d":"D","w":"W","m":"M",
}

def to_bybit_interval(interval: str) -> str:
    return INTERVAL_MAP.get(interval.lower(), interval)

async def fetch_klines(symbol: str, interval: str, limit: int = 400) -> pd.DataFrame:
    bybit_int = to_bybit_interval(interval)
    url = f"{BASE_URL}/v5/market/kline"
    params = {"category":"linear","symbol":symbol,"interval":bybit_int,"limit":min(limit,1000)}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        data = r.json()
        if r.status_code != 200 or data.get("retCode") != 0:
            params["category"] = "spot"
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if data.get("retCode") != 0:
                raise RuntimeError(f"Bybit error: {data}")
    rows = list(reversed(data["result"]["list"]))
    df = pd.DataFrame(rows, columns=["open_time","open","high","low","close","volume","turnover"])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df[["open_time","open","high","low","close","volume"]]
