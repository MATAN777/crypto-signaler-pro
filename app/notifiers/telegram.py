from __future__ import annotations
import httpx

async def send_telegram(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML"):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
    return True

async def send_telegram_photo(bot_token: str, chat_id: str, photo_bytes: bytes, caption: str = "", parse_mode: str = "HTML"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": parse_mode}
    files = {"photo": ("chart.png", photo_bytes, "image/png")}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, data=data, files=files)
        r.raise_for_status()
    return True