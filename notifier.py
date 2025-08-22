import os
from typing import Dict, Any, List
import telebot
from datetime import datetime
from config import ADMIN_TELEGRAM_CHAT_ID


def _bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return None
    try:
        return telebot.TeleBot(token)
    except Exception:
        return None


def send_message(text: str, markdown: bool = True):
    b = _bot()
    if not b or not ADMIN_TELEGRAM_CHAT_ID:
        return
    try:
        if markdown:
            b.send_message(ADMIN_TELEGRAM_CHAT_ID, text, parse_mode="Markdown")
        else:
            b.send_message(ADMIN_TELEGRAM_CHAT_ID, text)
    except Exception as e:
        print(f"[notifier] send_message error: {e}")


def send_startup_status():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    send_message(f"✅ *Бот запущен на Render* — {ts}")


def format_summary(analysis: Dict[str, Any]) -> str:
    parts: List[str] = []
    items = analysis.get("items", [])[:10]
    parts.append("*Приоритетные пункты:*\n")
    for it in items:
        src = it.get("source")
        title = it.get("text") or it.get("name") or "(без текста)"
        pr = it.get("priority", 0)
        cls = it.get("class") or ""
        parts.append(f"- [{src}] *{title[:120]}* _(prio {pr})_ {cls}")
    for sug in analysis.get("suggestions", []):
        parts.append(f"→ {sug}")
    return "\n".join(parts)