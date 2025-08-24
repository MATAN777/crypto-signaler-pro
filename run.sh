#!/usr/bin/env bash
set -e
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "יצרתי .env ברירת מחדל"
fi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PORT=${PORT:-7000}
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
