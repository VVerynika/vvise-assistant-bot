import os
import time
import telebot
from google_logger import log_message
from notifier import send_startup_status
from storage import set_slack_oldest_days, set_slack_oldest_ts, set_clickup_since_days, set_clickup_since_ms, propose_cleanup, soft_delete_threads

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

    @b.message_handler(commands=['ingest'])
    def handle_ingest(message):
        # /ingest slack 7  (последние 7 дней)
        # /ingest clickup 14
        try:
            parts = (_safe_text(message) or '').split()
            if len(parts) < 3:
                b.reply_to(message, "Использование: /ingest slack|clickup <days>")
                return
            target = parts[1].lower()
            days = int(parts[2])
            if target == 'slack':
                set_slack_oldest_days(days)
                b.reply_to(message, f"Slack: читать начиная с последних {days} дней")
            elif target == 'clickup':
                set_clickup_since_days(days)
                b.reply_to(message, f"ClickUp: читать начиная с последних {days} дней")
            else:
                b.reply_to(message, "Неизвестная цель. Используйте slack|clickup")
        except Exception as e:
            b.reply_to(message, f"Ошибка: {e}")

    @b.message_handler(commands=['cleanup'])
    def handle_cleanup(message):
        # Предложить список кандидатов и inline-кнопки
        try:
            props = propose_cleanup()
            count = props.get('count', 0)
            if count == 0:
                b.reply_to(message, "Нет кандидатов на очистку")
                return
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(text="Удалить всё", callback_data="cleanup:all"))
            kb.add(InlineKeyboardButton(text="Отмена", callback_data="cleanup:cancel"))
            b.send_message(message.chat.id, f"Найдено кандидатов: {count}. Удалить?", reply_markup=kb)
        except Exception as e:
            b.reply_to(message, f"Ошибка: {e}")

    @b.callback_query_handler(func=lambda c: c.data and c.data.startswith('cleanup:'))
    def on_cleanup_click(call):
        try:
            action = call.data.split(':', 1)[1]
            if action == 'all':
                props = propose_cleanup()
                keys = [{"thread_ts": c["thread_ts"], "channel_id": c["channel_id"]} for c in props.get('candidates', [])]
                soft_delete_threads(keys)
                b.answer_callback_query(call.id, "Удалено в архив")
                b.edit_message_text("✅ Перемещено в архив. Будет удалено через 7 дней.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            elif action == 'cancel':
                b.answer_callback_query(call.id, "Отменено")
                b.edit_message_text("Отменено", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            b.answer_callback_query(call.id, f"Ошибка: {e}")

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


init_bot()

if __name__ == "__main__":
    run_polling()