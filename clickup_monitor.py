import os
import requests
from datetime import datetime

CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID")

HEADERS = {"Authorization": CLICKUP_API_TOKEN}


def fetch_tasks_from_list(list_id=CLICKUP_LIST_ID):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    params = {"archived": "false"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("tasks", [])


def fetch_task_comments(task_id):
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("comments", [])


def analyze_task(task):
    task_id = task.get("id")
    name = task.get("name")
    status = task.get("status", {}).get("status")
    updated = int(task.get("date_updated", 0))
    updated_at = datetime.fromtimestamp(updated / 1000).strftime("%Y-%m-%d %H:%M")

    print(f"[{task_id}] {name} — {status} (обновлена: {updated_at})")


def run():
    print("🔍 Получаю задачи из ClickUp списка...")
    tasks = fetch_tasks_from_list()
    for task in tasks:
        analyze_task(task)

