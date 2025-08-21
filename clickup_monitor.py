import os
import requests
import time


def run():

    CLICKUP_TOKEN = os.getenv("CLICKUP_API_TOKEN")
    folder_id = os.getenv("CLICKUP_FOLDER_ID")
    if not CLICKUP_TOKEN or not folder_id:
        print("CLICKUP_API_TOKEN/CLICKUP_FOLDER_ID не заданы — ClickUp монитор отключён")
        return

    headers = {"Authorization": CLICKUP_TOKEN}

    backoff_seconds = 90

    while True:
        try:
            url = f"https://api.clickup.com/api/v2/folder/{folder_id}/task"
            resp = requests.get(url, headers=headers, timeout=15)
            if not resp.ok:
                print(f"[ClickUp error] {resp.status_code} {resp.text[:200]}")
                time.sleep(backoff_seconds)
                continue
            tasks = resp.json().get("tasks", [])
            for task in tasks:
                print(f"[ClickUp] {task.get('name')} — {task.get('status', {}).get('status')}")
            time.sleep(90)
        except Exception as e:
            print(f"[ClickUp exception] {e}")
            time.sleep(backoff_seconds)
