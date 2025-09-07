from __future__ import annotations
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from app.config import settings
from app.clients.bybit_client import fetch_klines
from app.indicators.ta import (
    IndicatorParams,
    compute_indicators,
    compute_fib_031,
    approximate_zones,
)
from app.strategies.rules import make_signal
from app.clients.plot import plot_chart
from app.notifiers.telegram import send_telegram_photo
from app.services.signal_state import load_for, save_for, diff_indicators

CRON_MAP = {
    "1m":  CronTrigger(minute="*"),
    "5m":  CronTrigger(minute="*/5"),
    "15m": CronTrigger(minute="*/15"),
    "30m": CronTrigger(minute="*/30"),
    "1h":  CronTrigger(minute=1),
    "2h":  CronTrigger(hour="*/2", minute=1),
    "4h":  CronTrigger(hour="*/4", minute=1),
    "6h":  CronTrigger(hour="*/6", minute=1),
    "12h": CronTrigger(hour="*/12", minute=1),
    "d":   CronTrigger(hour=0, minute=5),
    "w":   CronTrigger(day_of_week="mon", hour=0, minute=10),
    "m":   CronTrigger(day=1, hour=0, minute=15),
}

def _format_caption(symbol: str, timeframe: str, sig: dict, changed: list[str], fib: dict | None, zones: dict | None) -> str:
    ind = sig.get("metadata", {}).get("indicators", {})
    rows = []
    for k in ["EMA 35/75", "EMA 75/200", "MACD Cross", "StochRSI Divergence"]:
        v = ind.get(k, "-")
        mark = " 🔥" if k in changed else ""
        rows.append(f"{k}: <b>{v}</b>{mark}")
    body = "\n".join(rows)

    # Include fib and zones for context in notifications
    fib_line = ""
    if fib and fib.get("level") is not None:
        fib_line = f"\nFib 0.31: <b>{fib['level']:.3f}</b> ({fib.get('direction','')})"

    z_line = ""
    if zones:
        d = zones.get("demand") or {}
        s = zones.get("supply") or {}
        if d.get("low") is not None and d.get("high") is not None:
            z_line += f"\nDemand: {d['low']:.3f}–{d['high']:.3f}"
        if s.get("low") is not None and s.get("high") is not None:
            z_line += f"\nSupply: {s['low']:.3f}–{s['high']:.3f}"

    return (
        f"<b>{symbol}</b> [{timeframe}] — Side: <b>{sig.get('side','-')}</b>\n"
        f"Entry: {sig.get('entry')}\n"
        f"Confidence: {sig.get('confidence',0):.3f}\n"
        f"{body}{fib_line}{z_line}"
    )

async def run_signal_once(symbol: str, timeframe: str, params: "IndicatorParams"):
    df = await fetch_klines(symbol, timeframe, limit=500)
    data = compute_indicators(df, params)

    fib = compute_fib_031(data)
    zones = approximate_zones(data)

    sig = make_signal(data, timeframe, params, risk_reward=settings.risk_reward)
    new_ind = sig.get("metadata", {}).get("indicators", {})
    old_ind = load_for(symbol, timeframe)
    changed = diff_indicators(old_ind, new_ind)

    if settings.telegram_bot_token and settings.telegram_chat_id and changed:
        png = plot_chart(data, symbol, timeframe, fib=fib, zones=zones)
        caption = _format_caption(symbol, timeframe, sig, changed, fib, zones)
        await send_telegram_photo(settings.telegram_bot_token, settings.telegram_chat_id, png, caption)

    save_for(symbol, timeframe, new_ind)
    return sig

def configure_scheduler(app_state, params: "IndicatorParams"):
    scheduler = AsyncIOScheduler()
    symbols = settings.symbols if settings.symbols else [settings.default_symbol]
    for sym in symbols:
        for tf, trig in CRON_MAP.items():
            if tf in settings.timeframes:
                scheduler.add_job(
                    run_signal_once,
                    trig,
                    args=[sym, tf, params]
                )
    scheduler.start()
    app_state.scheduler = scheduler