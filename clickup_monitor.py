import os
import time
import json
import requests

STATE_PATH = os.getenv("CLICKUP_STATE_FILE", "/workspace/.clickup_state.json")


def _load_state():
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # date_updated_gt in milliseconds
    return {"date_updated_gt": None}


def _save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def run():
    CLICKUP_TOKEN = os.getenv("CLICKUP_API_TOKEN")
    folder_id = os.getenv("CLICKUP_FOLDER_ID")
    if not CLICKUP_TOKEN or not folder_id:
        print("CLICKUP_API_TOKEN/CLICKUP_FOLDER_ID не заданы — ClickUp монитор отключён")
        return

    headers = {"Authorization": CLICKUP_TOKEN}

    backoff_seconds = 60
    state = _load_state()
    date_updated_gt = state.get("date_updated_gt")

    while True:
        try:
            page = 0
            newest_update = date_updated_gt
            while True:
                url = f"https://api.clickup.com/api/v2/folder/{folder_id}/task?page={page}&subtasks=true&include_closed=true"
                if date_updated_gt:
                    url += f"&date_updated_gt={date_updated_gt}"
                resp = requests.get(url, headers=headers, timeout=20)
                if not resp.ok:
                    print(f"[ClickUp error] {resp.status_code} {resp.text[:200]}")
                    time.sleep(backoff_seconds)
                    break
                data = resp.json()
                tasks = data.get("tasks", [])
                if not tasks:
                    break
                for task in tasks:
                    print(f"[ClickUp] {task.get('name')} — {task.get('status', {}).get('status')}")
                    # track newest date_updated across tasks
                    try:
                        updated = task.get("date_updated")
                        if updated:
                            updated = int(updated)
                            if newest_update is None or updated > int(newest_update):
                                newest_update = updated
                    except Exception:
                        pass
                page += 1

            if newest_update and newest_update != date_updated_gt:
                date_updated_gt = newest_update
                _save_state({"date_updated_gt": date_updated_gt})

            time.sleep(90)
        except Exception as e:
            print(f"[ClickUp exception] {e}")
            time.sleep(backoff_seconds)

