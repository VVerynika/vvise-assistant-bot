import os
import time
import requests


def run():
    SLACK_TOKEN = os.getenv("SLACK_TOKEN")

    if not SLACK_TOKEN:
        print("SLACK_TOKEN не задан — Slack watcher отключён")
        return

    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    channels_url = "https://slack.com/api/conversations.list"

    backoff_seconds = 60

    while True:
        try:
            channels_resp = requests.get(channels_url, headers=headers, timeout=15)
            if not channels_resp.ok:
                print(f"[Slack error] {channels_resp.status_code} {channels_resp.text[:200]}")
                time.sleep(backoff_seconds)
                continue
            channels = channels_resp.json().get("channels", [])

            for channel in channels:
                messages_url = f"https://slack.com/api/conversations.history?channel={channel['id']}&limit=5"
                messages_resp = requests.get(messages_url, headers=headers, timeout=15)
                if not messages_resp.ok:
                    print(f"[Slack error] {messages_resp.status_code} {messages_resp.text[:200]}")
                    time.sleep(backoff_seconds)
                    continue
                messages = messages_resp.json().get("messages", [])
                for msg in messages:
                    print(f"[Slack] #{channel['name']}: {msg.get('text')}")
            time.sleep(60)
        except Exception as e:
            print(f"[Slack exception] {e}")
            time.sleep(backoff_seconds)
