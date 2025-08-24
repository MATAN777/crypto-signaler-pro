@echo off
IF NOT EXIST .env (
  copy .env.example .env
  echo Created default .env
)
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
set PORT=%PORT%
if "%PORT%"=="" set PORT=7000
uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload
