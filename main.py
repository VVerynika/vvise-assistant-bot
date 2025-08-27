from threading import Thread, Event
import time
import signal
import sys
import bot
import slack_watcher
import clickup_monitor
from datetime import datetime
from analyzer import run_similarity_and_clusters
from sheets_sync import sync_snapshot_to_sheet
from signals import detect_stalled_issues, find_unread_dms
from notifier import send_alert

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

    last_analysis = 0
    last_sync = 0
    last_alerts = 0

    try:
        while not stop_event.is_set():
            now = time.time()
            # Run analyzer every 10 minutes
            if now - last_analysis > 600:
                try:
                    run_similarity_and_clusters()
                    last_analysis = now
                except Exception as e:
                    print(f"[Main] analyzer error: {e}")
            # Sync to sheets every 15 minutes
            if now - last_sync > 900:
                try:
                    sync_snapshot_to_sheet()
                    last_sync = now
                except Exception as e:
                    print(f"[Main] sheet sync error: {e}")
            # Alerts every 5 minutes
            if now - last_alerts > 300:
                try:
                    stalled = detect_stalled_issues(days_without_update=14)
                    if stalled:
                        send_alert(f"Застрявших задач: {len(stalled)}. Пример: #{stalled[0]}")
                    dms = find_unread_dms()
                    if dms:
                        send_alert(f"Есть личные сообщения, требующие внимания: {len(dms)}. Пример: #{dms[0]}")
                    last_alerts = now
                except Exception as e:
                    print(f"[Main] alerts error: {e}")
            time.sleep(5)
    finally:
        print("Main exiting. Threads are daemons and will stop with process.")
        sys.exit(0)
