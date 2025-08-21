import os
import telebot
from google_logger import log_message

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Привет! Я готов работать.")
    log_message(message)

@bot.message_handler(commands=['ping'])
def handle_ping(message):
    bot.reply_to(message, "👋 Я здесь. Готов работать.")
    log_message(message)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, f"Ты сказал: {message.text}")
    log_message(message)

if __name__ == "__main__":
    print("Бот запущен...")

    bot.polling(none_stop=True, interval=0, timeout=60)

