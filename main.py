from threading import Thread, Event
import time
import signal
import sys
import bot
import slack_watcher
import clickup_monitor
from analyzer import analyze
from notifier import send_message, format_summary

stop_event = Event()


def handle_signal(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    stop_event.set()


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def analyzer_loop():
    while not stop_event.is_set():
        try:
            result = analyze()
            summary = format_summary(result)
            if summary:
                send_message(summary)
        except Exception as e:
            print(f"[analyzer] error: {e}")
        # run every 10 minutes
        for _ in range(60):
            if stop_event.is_set():
                break
            time.sleep(10)


if __name__ == "__main__":
    # Telegram bot thread (safe even if token missing)
    t_bot = Thread(target=bot.run_polling, daemon=True)
    t_slack = Thread(target=slack_watcher.run, daemon=True)
    t_click = Thread(target=clickup_monitor.run, daemon=True)
    t_anlz = Thread(target=analyzer_loop, daemon=True)

    t_bot.start()
    t_slack.start()
    t_click.start()
    t_anlz.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        print("Main exiting. Threads are daemons and will stop with process.")
        sys.exit(0)
