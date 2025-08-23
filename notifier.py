import os
from typing import Dict, Any, List
import telebot
from datetime import datetime
from config import ADMIN_TELEGRAM_CHAT_ID


_MD_SPECIALS = "_[]()~`>#+-=|{}.!"  # broad set for MarkdownV2; we use Markdown (basic), safe to escape


def _escape_markdown(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    out = []
    for ch in text:
        if ch in _MD_SPECIALS:
            out.append(f"\\{ch}")
        else:
            out.append(ch)
    return "".join(out)


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
            safe_text = _escape_markdown(text)
            b.send_message(ADMIN_TELEGRAM_CHAT_ID, safe_text, parse_mode="Markdown")
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
        src = _escape_markdown(it.get("source"))
        title = it.get("text") or it.get("name") or "(без текста)"
        title = _escape_markdown(title[:120])
        pr = it.get("priority", 0)
        cls = _escape_markdown(it.get("class") or "")
        parts.append(f"- [{src}] *{title}* _(prio {pr})_ {cls}")
    for sug in analysis.get("suggestions", []):
        parts.append(_escape_markdown(f"→ {sug}"))
    return "\n".join(parts)