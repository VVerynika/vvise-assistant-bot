import os
import requests
import time

def run():
    CLICKUP_TOKEN = os.getenv("CLICKUP_API_TOKEN")
    headers = {"Authorization": CLICKUP_TOKEN}
    folder_id = os.getenv("CLICKUP_FOLDER_ID")

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
