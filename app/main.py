# app/main.py
from __future__ import annotations

import os, re
from typing import List, Optional

from fastapi import FastAPI, Query, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.settings_store import load_settings, save_settings
from app.indicators.ta import (
    IndicatorParams,
    compute_indicators,
    compute_fib_031,
    suggest_entry_from_fib,
    approximate_zones,
)
from app.services.confluence import compute_confluence

ALLOWED_TF = {"1m","5m","15m","30m","1h","2h","4h","6h","12h","d","w","m"}

# ---------------- Models ----------------
class SettingsModel(BaseModel):
    symbol: str = "BTCUSDT"
    timeframes: List[str] = ["15m","1h","4h","d","w"]
    risk_reward: float = 3.0
    ema:   List[int] = [35, 75, 200]     # fast, mid, slow
    stoch: List[int] = [14, 14, 3, 3]    # rsi_len, stoch_len, k, d
    macd:  List[int] = [12, 26, 9]       # fast, slow, signal
    decision_threshold: float = 1.5


# ---------------- Utils ----------------
def _validate_settings(s: SettingsModel):
    if not s.symbol:
        raise ValueError("symbol is required")
    if not s.timeframes:
        raise ValueError("timeframes cannot be empty")
    bad = [tf for tf in s.timeframes if tf not in ALLOWED_TF]
    if bad:
        raise ValueError(f"invalid timeframes: {bad}")

    if len(s.ema) != 3 or any(x <= 0 for x in s.ema):
        raise ValueError("ema must be 3 positive integers: fast,mid,slow")
    if len(s.stoch) != 4 or any(x <= 0 for x in s.stoch):
        raise ValueError("stoch must be 4 positive integers: rsi_len,stoch_len,k,d")
    if len(s.macd) != 3 or any(x <= 0 for x in s.macd):
        raise ValueError("macd must be 3 positive integers: fast,slow,signal")

    if not (0.5 <= s.risk_reward <= 10):
        raise ValueError("risk_reward must be between 0.5 and 10")
    if not (0.5 <= s.decision_threshold <= 5):
        raise ValueError("decision_threshold must be between 0.5 and 5")


def _csv_ints(s: str) -> List[int]:
    return [int(x.strip()) for x in (s or "").split(",") if x.strip()]


def _load_initial_settings() -> SettingsModel:
    file_cfg = load_settings() or {}
    env = {}
    if os.getenv("DEFAULT_SYMBOL"):
        env["symbol"] = os.getenv("DEFAULT_SYMBOL").upper()
    if os.getenv("TIMEFRAMES"):
        env["timeframes"] = [x.strip().lower() for x in os.getenv("TIMEFRAMES").split(",") if x.strip()]
    if os.getenv("RISK_REWARD"):
        try:
            env["risk_reward"] = float(os.getenv("RISK_REWARD"))
        except ValueError:
            pass
    base = {**file_cfg, **env}
    return SettingsModel(**base)


# ---------------- App ----------------
app = FastAPI(title="Crypto Signaler PRO", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.state.settings = _load_initial_settings()
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def _require_auth_if_configured(request: Request):
    if AUTH_TOKEN and request.headers.get("Authorization") != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------- Routes ----------------
@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/")
async def root():
    index_path = os.path.join(_static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "UI not found (app/static/index.html)."}, status_code=200)


@app.get("/api/settings")
async def get_settings():
    return app.state.settings


@app.put("/api/settings")
async def put_settings(
    payload: SettingsModel = Body(...),
    persist: bool = Query(True),
    request: Request = None,
):
    _require_auth_if_configured(request)
    try:
        _validate_settings(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    app.state.settings = payload
    if persist:
        save_settings(payload.dict())
    return {"ok": True}


# ---------- Helper: infer reasons if strategy didn't return ----------
def _infer_reasons(df) -> List[str]:
    reasons: List[str] = []
    if df is None or len(df) == 0:
        return reasons
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    cols = set(df.columns)

    if {"ema_fast","ema_mid","ema_slow"}.issubset(cols):
        try:
            if last["ema_fast"] > last["ema_mid"] > last["ema_slow"]:
                reasons.append("EMA structure up (35>75>200)")
            elif last["ema_fast"] < last["ema_mid"] < last["ema_slow"]:
                reasons.append("EMA structure down (35<75<200)")
        except Exception:
            pass

    if {"close","ema_mid"}.issubset(cols):
        try:
            if last["close"] > last["ema_mid"]:
                reasons.append("Price > EMA75")
            else:
                reasons.append("Price < EMA75")
        except Exception:
            pass

    if {"macd","macd_signal"}.issubset(cols):
        try:
            reasons.append("MACD > signal" if last["macd"] > last["macd_signal"] else "MACD < signal")
        except Exception:
            pass

    if {"stoch_k","stoch_d"}.issubset(cols) and prev is not None:
        try:
            if last["stoch_k"] > last["stoch_d"] and prev["stoch_k"] <= prev["stoch_d"]:
                reasons.append("Stoch K cross up")
            if last["stoch_k"] < last["stoch_d"] and prev["stoch_k"] >= prev["stoch_d"]:
                reasons.append("Stoch K cross down")
        except Exception:
            pass

    return reasons


# ---------- ANALYZE ----------
@app.get("/api/analyze")
async def analyze(
    symbol: Optional[str] = Query(None),
    timeframe: str = Query("4h"),
    ema: Optional[str] = Query(None),
    stoch: Optional[str] = Query(None),  # 1/3/4 values supported
    macd: Optional[str] = Query(None),
    risk_reward: Optional[float] = Query(None),
    limit: int = Query(500, ge=100, le=1000),
    fib031: bool = Query(False),  # אם רוצים להחזיר גם פיבו באותה תשובה
):
    from app.clients.bybit_client import fetch_klines
    from app.strategies.rules import make_signal

    s = app.state.settings
    sym = (symbol or s.symbol or "BTCUSDT").upper()
    sym = re.sub(r'[^A-Z0-9]', '', sym)
    rr  = risk_reward if risk_reward is not None else s.risk_reward

    # EMA
    ema_vals = s.ema if ema is None else _csv_ints(ema)
    if len(ema_vals) != 3:
        raise HTTPException(status_code=422, detail="ema must be 'fast,mid,slow'")
    ema_f, ema_m, ema_s = ema_vals

    # StochRSI
    if stoch is None:
        rsi_len, stoch_len, k_len, d_len = s.stoch
    else:
        st_vals = _csv_ints(stoch)
        if len(st_vals) == 1:
            rsi_len, stoch_len, k_len, d_len = st_vals[0], 14, 3, 3
        elif len(st_vals) == 3:
            rsi_len = stoch_len = st_vals[0]
            k_len, d_len = st_vals[1], st_vals[2]
        elif len(st_vals) == 4:
            rsi_len, stoch_len, k_len, d_len = st_vals
        else:
            raise HTTPException(status_code=422, detail="stoch must be 'RSI' or 'RSI,Stoch,K,D'")

    # MACD
    macd_vals = s.macd if macd is None else _csv_ints(macd)
    if len(macd_vals) != 3:
        raise HTTPException(status_code=422, detail="macd must be 'fast,slow,signal'")
    macd_f, macd_s, macd_sig = macd_vals

    params = IndicatorParams(
        ema_fast=ema_f, ema_mid=ema_m, ema_slow=ema_s,
        rsi_len=rsi_len, stoch_len=stoch_len, stoch_k=k_len, stoch_d=d_len,
        macd_fast=macd_f, macd_slow=macd_s, macd_signal=macd_sig
    )

    # נתונים + אינדיקטורים
    df = await fetch_klines(sym, timeframe, limit=limit)
    data = compute_indicators(df, params)

    # אסטרטגיה
    try:
        sig = make_signal(
            data, timeframe, params,
            risk_reward=rr, decision_threshold=s.decision_threshold
        )
    except TypeError:
        # תאימות אם make_signal לא מכירה decision_threshold
        sig = make_signal(data, timeframe, params, risk_reward=rr)

    # Reasons fallback
    if isinstance(sig, dict) and not sig.get("reasons"):
        inferred = _infer_reasons(data)
        if inferred:
            sig.setdefault("metadata", {})
            sig["metadata"]["reasons"] = inferred

    result = {
        "symbol": sym,
        "timeframe": timeframe,
        "params": params.__dict__,
        "decision_threshold": s.decision_threshold,
        "signal": sig,
    }

    # אופציונלי: גם פיבונאצ'י
    if fib031:
        fib = compute_fib_031(data)
        if fib:
            entry_sugg = suggest_entry_from_fib(fib, rr)
            result["fib031"] = fib
            result["entry_suggestion"] = entry_sugg

    return result


# ---------- FIB 0.31 ----------
@app.get("/api/fib031")
async def api_fib031(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=100, le=1000),
):
    from app.clients.bybit_client import fetch_klines

    s = app.state.settings
    sym = (symbol or s.symbol or "BTCUSDT").upper()
    sym = re.sub(r'[^A-Z0-9]', '', sym)

    df = await fetch_klines(sym, timeframe, limit=limit)
    data = compute_indicators(df, IndicatorParams())
    fib = compute_fib_031(data)
    if not fib:
        raise HTTPException(status_code=404, detail="not enough data for fib 0.31")

    entry_sugg = suggest_entry_from_fib(fib, s.risk_reward)
    return {
        "symbol": sym,
        "timeframe": timeframe,
        "fib031": fib,
        "entry_suggestion": entry_sugg,
    }


# ---------- Demand / Supply ----------
@app.get("/api/zones")
async def api_zones(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=100, le=1000),
):
    from app.clients.bybit_client import fetch_klines

    sym = symbol.upper()
    sym = re.sub(r'[^A-Z0-9]', '', sym)
    df = await fetch_klines(sym, timeframe, limit=limit)
    data = compute_indicators(df, IndicatorParams())
    zones = approximate_zones(data)
    if not zones:
        raise HTTPException(status_code=404, detail="zones unavailable")
    return {"symbol": sym, "timeframe": timeframe, "zones": zones}


# ---------- CHART BUNDLE ----------
@app.get("/api/chart")
async def api_chart(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=100, le=1000),
    include_confluence: bool = Query(True),
):
    from app.clients.bybit_client import fetch_klines
    sym = re.sub(r'[^A-Z0-9]', '', (symbol or "BTCUSDT").upper())
    df = await fetch_klines(sym, timeframe, limit=limit)
    data = compute_indicators(df, IndicatorParams())
    fib = compute_fib_031(data)
    zones = approximate_zones(data)
    conf = compute_confluence(data) if include_confluence else None
    # serialize a compact structure for the frontend
    ohlcv = [
        [
            int(row["open_time"].value // 10**6),
            float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), float(row["volume"])
        ] for _, row in data.iterrows()
    ]
    ind_tail = data.tail(1).iloc[0]
    indicators = {
        "ema": {
            "fast": float(ind_tail.get("ema_fast", float('nan'))),
            "mid": float(ind_tail.get("ema_mid", float('nan'))),
            "slow": float(ind_tail.get("ema_slow", float('nan'))),
        },
        "macd": {
            "macd": float(ind_tail.get("macd", float('nan'))),
            "signal": float(ind_tail.get("macd_signal", float('nan'))),
        },
        "stoch": {
            "k": float(ind_tail.get("stoch_k", float('nan'))),
            "d": float(ind_tail.get("stoch_d", float('nan'))),
        },
        "atr": float(ind_tail.get("atr", float('nan'))),
        "mfi": float(ind_tail.get("mfi", float('nan'))),
        "cmf": float(ind_tail.get("cmf", float('nan'))),
    }
    return {
        "symbol": sym,
        "timeframe": timeframe,
        "ohlcv": ohlcv,
        "fib031": fib,
        "zones": zones,
        "indicators": indicators,
        "confluence": None if not conf else {
            "score": conf.score,
            "label": conf.label,
            "reasons": conf.reasons,
        }
    }


# ---------- MACRO ----------
@app.get("/api/macro")
async def api_macro(metric: str = Query(..., pattern="^(cpi|unemployment|interest)$")):
    from app.clients.macro_client import get_macro
    data = await get_macro(metric)
    if not data:
        return JSONResponse({"metric": metric, "source": None, "value": None}, status_code=204)
    return data
