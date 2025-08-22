import os
import time
import telebot
from google_logger import log_message
from notifier import send_startup_status

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = None


def _safe_text(message) -> str:
    try:
        return getattr(message, 'text', None) or getattr(message, 'caption', None) or ""
    except Exception:
        return ""


def register_handlers(b: telebot.TeleBot) -> None:
    @b.message_handler(commands=['start'])
    def handle_start(message):
        try:
            b.reply_to(message, "Привет! Я готов работать.")
        except Exception as e:
            print(f"[bot] reply error /start: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error /start: {e}")

    @b.message_handler(commands=['ping'])
    def handle_ping(message):
        try:
            b.reply_to(message, "👋 Я здесь. Готов работать.")
        except Exception as e:
            print(f"[bot] reply error /ping: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error /ping: {e}")

    @b.message_handler(func=lambda message: True)
    def echo_message(message):
        text = _safe_text(message)
        try:
            if text:
                b.reply_to(message, f"Ты сказал: {text}")
            else:
                b.reply_to(message, "Принял сообщение")
        except Exception as e:
            print(f"[bot] reply error echo: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error echo: {e}")


def init_bot():
    global bot
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN не задан — Telegram бот отключён")
        bot = None
        return
    try:
        b = telebot.TeleBot(TELEGRAM_TOKEN)
        # На всякий случай убираем webhook, если был настроен ранее
        try:
            b.remove_webhook()
        except Exception:
            pass
        register_handlers(b)
        bot = b
    except Exception as e:
        print(f"Не удалось инициализировать Telegram бот: {e}")
        bot = None


def run_polling():
    if bot is None:
        print("Telegram бот не запущен (нет токена или ошибка инициализации)")
        return
    backoff_seconds = 5
    while True:
        try:
            print("Бот запущен...")
            send_startup_status()
            bot.polling(none_stop=True, interval=0, timeout=60)
            backoff_seconds = 5
        except Exception as e:
            is_api_exc = hasattr(telebot, 'apihelper') and isinstance(e, getattr(telebot.apihelper, 'ApiTelegramException', Exception))
            if is_api_exc and getattr(e, 'error_code', None) == 409:
                print("[Telegram] 409 Conflict: другой инстанс getUpdates. Ретраю позже...")
                time.sleep(min(backoff_seconds, 300))
                backoff_seconds = min(backoff_seconds * 2, 300)
                continue
            print(f"Ошибка в polling: {e}")
            time.sleep(min(backoff_seconds, 60))
            backoff_seconds = min(backoff_seconds * 2, 60)


# Инициализация при импорте модуля, без запуска polling
init_bot()

if __name__ == "__main__":
    run_polling()