import os
from typing import List

import telebot


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID")


def send_alert(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        bot.send_message(TELEGRAM_CHAT_ID, text[:4000])
    except Exception as e:
        print(f"[Notifier] send_alert error: {e}")

