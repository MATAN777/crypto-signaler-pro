from __future__ import annotations
import json, os
from typing import Dict, Any

_STATE_PATH = os.environ.get("SIGNAL_STATE_PATH", "data/signal_state.json")

def _ensure_dir():
    d = os.path.dirname(_STATE_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

def _load() -> Dict[str, Any]:
    if not os.path.isfile(_STATE_PATH):
        return {}
    with open(_STATE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def _save(data: Dict[str, Any]):
    _ensure_dir()
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def key(symbol: str, timeframe: str) -> str:
    return f"{symbol.upper()}::{timeframe}"

def diff_indicators(old: Dict[str, str] | None, new: Dict[str, str]) -> list[str]:
    changed = []
    old = old or {}
    all_keys = set(old.keys()) | set(new.keys())
    for k in sorted(all_keys):
        if old.get(k) != new.get(k):
            changed.append(k)
    return changed

def load_for(symbol: str, timeframe: str) -> Dict[str, str] | None:
    return _load().get(key(symbol, timeframe))

def save_for(symbol: str, timeframe: str, indicators: Dict[str, str]):
    data = _load()
    data[key(symbol, timeframe)] = indicators
    _save(data)