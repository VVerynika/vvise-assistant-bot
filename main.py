from threading import Thread
import time
import bot
import slack_watcher
import clickup_monitor
from datetime import datetime

if __name__ == "__main__":
    print(f"✅ Polling запущен на Render в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    Thread(target=bot.bot.polling, kwargs={'none_stop': True, 'interval': 0, 'timeout': 60}, daemon=True).start()
    Thread(target=slack_watcher.run, daemon=True).start()
    Thread(target=clickup_monitor.run, daemon=True).start()

    while True:
        time.sleep(3600)

