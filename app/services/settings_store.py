# app/services/settings_store.py
from __future__ import annotations
import os, json
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
from typing import Optional, Dict, Any

DEFAULT_PATH = os.getenv("SETTINGS_PATH", str(BASE_DIR / "runtime-data" / "settings.json"))

def _ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def load_settings(path: str = DEFAULT_PATH) -> Optional[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(payload: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    p = Path(path)
    _ensure_dir(p)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(p)  # שמירה אטומית
