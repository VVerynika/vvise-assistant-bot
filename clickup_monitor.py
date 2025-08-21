import os
import requests
import time

def run():
    token = os.getenv("CLICKUP_API_TOKEN")
    folder_id = os.getenv("CLICKUP_FOLDER_ID")
    if not token or not folder_id:
    print("CLICKUP_API_TOKEN/CLICKUP_FOLDER_ID не заданы — ClickUp монитор отключён")
    return
resp = requests.get(url, headers=headers, timeout=15)
if not resp.ok:
    print(f"[ClickUp error] {resp.status_code} {resp.text[:200]}")
    time.sleep(90); continue

    while True:
        try:
            url = f"https://api.clickup.com/api/v2/folder/{folder_id}/task"
            tasks = requests.get(url, headers=headers).json().get("tasks", [])
            for task in tasks:
                print(f"[ClickUp] {task.get('name')} — {task.get('status', {}).get('status')}")
            time.sleep(90)
        except Exception as e:
            print(f"[ClickUp error] {e}")
            time.sleep(90)
