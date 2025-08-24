# Crypto Signaler PRO — Bybit (Clean)

סטארטר יציב ומוכן להרצה (Python + FastAPI) עם אינדיקטורים נקיים (ללא pandas_ta):
- **EMA משולש** 35 / 75 / 200
- **StochRSI** (14,3,3) עם איתותי חצייה מאיזורי 20/80
- **MACD** (12,26,9)
- **ATR** ל-Target לפי Risk-Reward
- תזמונים אוטומטיים 4H / Daily / Weekly / Monthly
- UI רספונסיבי שמתאים לנייד

## הפעלה בפקודה אחת (לוקאלית)
```bash
bash run.sh
```
ייפתח ב- `http://127.0.0.1:7000`

## Docker
```bash
docker build -t crypto-signaler-pro .
docker run -it --env-file .env -p 7000:7000 crypto-signaler-pro
```
ואז http://127.0.0.1:7000

## התקנה ידנית (venv)
```bash
python -m venv .venv
source .venv/bin/activate  # ב-Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7000 --workers 2
```

## .env (רשות)
```
BYBIT_API_KEY=
BYBIT_API_SECRET=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DEFAULT_SYMBOL=BTCUSDT
TIMEFRAMES=w,m
RISK_REWARD=3.0
PORT=7000
```

> אם תרצה Bitget במקום Bybit — מחליפים קלות את `clients/bybit_client.py`.
