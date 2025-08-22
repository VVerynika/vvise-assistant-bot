import os
from typing import Dict, Any, List
import telebot
from config import ADMIN_TELEGRAM_CHAT_ID


def _bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return None
    try:
        return telebot.TeleBot(token)
    except Exception:
        return None


def send_message(text: str):
    b = _bot()
    if not b or not ADMIN_TELEGRAM_CHAT_ID:
        return
    try:
        b.send_message(ADMIN_TELEGRAM_CHAT_ID, text)
    except Exception as e:
        print(f"[notifier] send_message error: {e}")


def format_summary(analysis: Dict[str, Any]) -> str:
    parts: List[str] = []
    items = analysis.get("items", [])[:10]
    parts.append("Приоритетные пункты:")
    for it in items:
        src = it.get("source")
        title = it.get("text") or it.get("name") or "(без текста)"
        pr = it.get("priority", 0)
        cls = it.get("class") or ""
        parts.append(f"- [{src}] {title[:120]} (prio {pr}) {cls}")
    for sug in analysis.get("suggestions", []):
        parts.append(f"→ {sug}")
    return "\n".join(parts)