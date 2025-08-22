from threading import Thread
import time
import bot
import slack_watcher
import clickup_monitor

if __name__ == "__main__":
    Thread(target=bot.bot.polling, kwargs={'none_stop': True, 'interval': 0, 'timeout': 60}, daemon=True).start()
    Thread(target=slack_watcher.run, daemon=True).start()
    Thread(target=clickup_monitor.run_clickup_monitor, daemon=True).start()
    while True:
        time.sleep(3600)
