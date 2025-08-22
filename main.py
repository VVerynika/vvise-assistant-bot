from threading import Thread, Event
import time
import signal
import sys
import bot
import slack_watcher
import clickup_monitor
from datetime import datetime

stop_event = Event()


def handle_signal(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    stop_event.set()


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


if __name__ == "__main__":

    # Telegram bot thread (safe even if token missing)
    t_bot = Thread(target=bot.run_polling, daemon=True)
    t_slack = Thread(target=slack_watcher.run, daemon=True)
    t_click = Thread(target=clickup_monitor.run, daemon=True)

    t_bot.start()
    t_slack.start()
    t_click.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        print("Main exiting. Threads are daemons and will stop with process.")
        sys.exit(0)
