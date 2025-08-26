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
המערכת תעלה על `http://127.0.0.1:7000` (או `http://localhost:7000`).

אם אין לך קובץ `.env`, יווצר אוטומטית מקובץ הדוגמה `.env.example`.

## התקנה ידנית (venv)
```bash
# ודא שמותקן python venv (אובונטו/דביאן):
# sudo apt-get update && sudo apt-get install -y python3-venv

python -m venv .venv
source .venv/bin/activate  # ב-Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7000 --reload
```

- ניתן לשנות פורט באמצעות משתנה סביבה: `PORT=7000` (ברירת מחדל 7000).
- בריצה מקומית: `http://127.0.0.1:7000`.

## Docker
קובץ `Dockerfile` מוכן לבנייה. מומלץ להשתמש ב-`.dockerignore` כדי לצמצם הקשר בנייה.
```bash
docker build -t crypto-signaler-pro .
docker run -it --rm --env-file .env -p 7000:7000 crypto-signaler-pro
```
ואז גלישה אל `http://127.0.0.1:7000`.

### ניקוי Docker היסטורי (אופציונלי)
```bash
docker system prune -a --volumes
```
זה מנקה אובייקטים לא בשימוש (תמונות/קונטיינרים/ווליום/רשתות) כדי למנוע התנגשויות.

## בדיקת API מהירה (curl)
לאחר שהשרת רץ על פורט 7000:
```bash
# Health
curl -s http://127.0.0.1:7000/api/health

# Settings (GET)
curl -s http://127.0.0.1:7000/api/settings

# Settings (PUT)
curl -s -X PUT 'http://127.0.0.1:7000/api/settings?persist=false' \
  -H 'content-type: application/json' \
  -d '{"symbol":"BTCUSDT","timeframes":["15m","1h"],"risk_reward":3,"decision_threshold":1.5,"ema":[35,75,200],"macd":[12,26,9],"stoch":[14,14,3,3]}'

# Analyze (דוגמה)
curl -s 'http://127.0.0.1:7000/api/analyze?symbol=BTCUSDT&timeframe=1h'

# Fib 0.31
curl -s 'http://127.0.0.1:7000/api/fib031?symbol=BTCUSDT&timeframe=1h'

# Zones
curl -s 'http://127.0.0.1:7000/api/zones?symbol=BTCUSDT&timeframe=1h'

# Chart bundle
curl -s 'http://127.0.0.1:7000/api/chart?symbol=BTCUSDT&timeframe=1h'

# Macro
curl -s 'http://127.0.0.1:7000/api/macro?metric=cpi'
```
ה-API מחזיר תמיד JSON ידידותי ל-UI. אם נתוני צד שלישי אינם זמינים (רשת/מפתח API), יוחזרו ערכי `null`/ברירת מחדל במקום שגיאת 500.

## Frontend
ה-UI הסטטי נטען מ-`/` (קובץ `app/static/index.html`). הפאנל של ה-Time Frame מותאם ל-RTL.

## .env (רשות)
ראה `.env.example`:
```
BYBIT_API_KEY=
BYBIT_API_SECRET=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DEFAULT_SYMBOL=BTCUSDT
TIMEFRAMES=15m,1h,4h,d,w
RISK_REWARD=3.0
PORT=7000
```

> החלפה לספק אחר (למשל Bitget) אפשרית ע"י התאמה של `app/clients/bybit_client.py`.
