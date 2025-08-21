import os
import telebot
from google_logger import log_message

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = None


def register_handlers(b: telebot.TeleBot) -> None:
    @b.message_handler(commands=['start'])
    def handle_start(message):
        b.reply_to(message, "Привет! Я готов работать.")
        log_message(message)

    @b.message_handler(commands=['ping'])
    def handle_ping(message):
        b.reply_to(message, "👋 Я здесь. Готов работать.")
        log_message(message)

    @b.message_handler(func=lambda message: True)
    def echo_message(message):
        b.reply_to(message, f"Ты сказал: {message.text}")
        log_message(message)


def init_bot():
    global bot
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN не задан — Telegram бот отключён")
        bot = None
        return
    try:
        b = telebot.TeleBot(TELEGRAM_TOKEN)
        register_handlers(b)
        bot = b
    except Exception as e:
        print(f"Не удалось инициализировать Telegram бот: {e}")
        bot = None


def run_polling():
    if bot is None:
        print("Telegram бот не запущен (нет токена или ошибка инициализации)")
        return
    print("Бот запущен...")
    bot.polling(none_stop=True, interval=0, timeout=60)


# Инициализация при импорте модуля, без запуска polling
init_bot()

if __name__ == "__main__":
    run_polling()