import os
import time
import requests

def run():
    SLACK_TOKEN = os.getenv("SLACK_TOKEN")
if not SLACK_TOKEN:
    print("SLACK_TOKEN не задан — Slack watcher отключён")
    return
resp = requests.get(channels_url, headers=headers, timeout=15)
if not resp.ok:
    print(f"[Slack error] {resp.status_code} {resp.text[:200]}")
    time.sleep(60); continue
    
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    channels_url = "https://slack.com/api/conversations.list"

    while True:
        try:
            channels = requests.get(channels_url, headers=headers).json().get("channels", [])
            for channel in channels:
                messages_url = f"https://slack.com/api/conversations.history?channel={channel['id']}&limit=5"
                messages = requests.get(messages_url, headers=headers).json().get("messages", [])
                for msg in messages:
                    print(f"[Slack] #{channel['name']}: {msg.get('text')}")
            time.sleep(60)
        except Exception as e:
            print(f"[Slack error] {e}")
            time.sleep(60)
