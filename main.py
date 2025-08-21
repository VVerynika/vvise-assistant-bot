from threading import Thread
import time
import bot
import slack_watcher
import clickup_monitor

if __name__ == "__main__":
    # Telegram bot thread (safe even if token missing)
    Thread(target=bot.run_polling, daemon=True).start()
    # Slack and ClickUp watchers
    Thread(target=slack_watcher.run, daemon=True).start()
    Thread(target=clickup_monitor.run, daemon=True).start()
    while True:
        time.sleep(3600)
