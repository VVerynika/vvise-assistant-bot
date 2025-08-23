import os
import time
import json
import requests
from storage import upsert_clickup_task, get_clickup_since_ms

STATE_PATH = os.getenv("CLICKUP_STATE_FILE", "/workspace/.clickup_state.json")


def _load_state():
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"date_updated_gt": None}


def _save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def _get(url, headers, timeout=20):
    backoff = 2
    while True:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code in (429, 408):
            retry_after = int(r.headers.get("Retry-After", "10"))
            time.sleep(retry_after)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        return r


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
    manual_since_ms = get_clickup_since_ms() or date_updated_gt

    while True:
        try:
            page = 0
            newest_update = manual_since_ms
            while True:
                url = f"https://api.clickup.com/api/v2/folder/{folder_id}/task?page={page}&subtasks=true&include_closed=true"
                if manual_since_ms:
                    url += f"&date_updated_gt={manual_since_ms}"
                resp = _get(url, headers=headers)
                if not resp.ok:
                    time.sleep(backoff_seconds)
                    break
                data = resp.json()
                tasks = data.get("tasks", [])
                if not tasks:
                    break
                for task in tasks:
                    tid = task.get('id')
                    name = task.get('name')
                    status = (task.get('status') or {}).get('status')
                    due = task.get('due_date')
                    due_ts = None
                    try:
                        due_ts = int(due) / 1000.0 if due else None
                    except Exception:
                        due_ts = None
                    # checklists
                    checklists = []
                    try:
                        ckl = _get(f"https://api.clickup.com/api/v2/task/{tid}/checklist", headers=headers)
                        if ckl.ok:
                            cldata = ckl.json()
                            checklists = cldata.get('checklists', []) or cldata.get('checklist', []) or []
                    except Exception:
                        pass
                    # comments
                    comments = []
                    try:
                        cm = _get(f"https://api.clickup.com/api/v2/task/{tid}/comment", headers=headers)
                        if cm.ok:
                            cdata = cm.json()
                            comments = cdata.get('comments', []) or []
                    except Exception:
                        pass
                    description = task.get('text_content') or task.get('description') or ''
                    upsert_clickup_task({
                        "id": tid,
                        "name": name,
                        "description": description,
                        "status": {"status": status},
                        "due_date_ts": due_ts,
                        "checklists": checklists,
                        "comments": comments,
                        "assignees": task.get('assignees') or [],
                        "creator": task.get('creator') or {},
                    })
                    print(f"[ClickUp] {name} — {status}")
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
                state['date_updated_gt'] = newest_update
                _save_state(state)

            time.sleep(90)
        except Exception as e:
            print(f"[ClickUp exception] {e}")
            time.sleep(backoff_seconds)
