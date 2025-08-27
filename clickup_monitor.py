import os
import time
import json
import requests
from typing import Optional, Dict, Any

from storage import (
    init_db,
    upsert_clickup_task,
    upsert_clickup_comment,
    upsert_analysis_item,
    upsert_content_index,
    set_status,
)

def _state_path_default(name: str) -> str:
    base = os.getenv("STATE_DIR") or os.getenv("DATA_DIR") or "/var/tmp"
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, name)


STATE_PATH = os.getenv("CLICKUP_STATE_FILE", _state_path_default(".clickup_state.json"))


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


def _safe_int(v):
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def run():
    CLICKUP_TOKEN = os.getenv("CLICKUP_API_TOKEN")
    # Prefer LIST_ID, fallback to legacy FOLDER_ID for backwards compatibility
    list_id = os.getenv("CLICKUP_LIST_ID") or os.getenv("CLICKUP_FOLDER_ID")
    if not CLICKUP_TOKEN or not list_id:
        print("CLICKUP_API_TOKEN/CLICKUP_LIST_ID не заданы — ClickUp монитор отключён")
        return

    headers = {"Authorization": CLICKUP_TOKEN}

    backoff_seconds = 60
    state = _load_state()
    date_updated_gt = state.get("date_updated_gt")

    # Ensure DB
    try:
        init_db()
    except Exception:
        pass

    while True:
        try:
            page = 0
            newest_update = date_updated_gt
            while True:
                # List-based tasks endpoint
                url = f"https://api.clickup.com/api/v2/list/{list_id}/task?page={page}&subtasks=true&include_closed=true"
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
                    try:
                        upsert_clickup_task(task)
                        name = task.get('name') or ''
                        desc = (task.get('description') or {})
                        if isinstance(desc, dict):
                            desc = desc.get('text') or desc.get('html') or ''
                        url_web = task.get('url')
                        created = _safe_int(task.get('date_created'))
                        updated = _safe_int(task.get('date_updated'))
                        item_id = upsert_analysis_item(
                            source='clickup',
                            source_id=str(task.get('id')),
                            title=name[:200] if name else None,
                            body=desc or '',
                            created_at=created,
                            updated_at=updated,
                            author=None,
                            url=url_web,
                        )
                        upsert_content_index(item_id, name, desc or '')
                        set_status(item_id, priority=None, status=(task.get('status') or {}).get('status') if isinstance(task.get('status'), dict) else task.get('status'), last_seen=updated or created, labels=None)
                    except Exception as e:
                        print(f"[ClickUp] persist task error: {e}")
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

                    # Ingest comments for the task
                    try:
                        task_id = str(task.get('id'))
                        # ClickUp v2 comments endpoint
                        # GET /api/v2/task/{task_id}/comment
                        c_page = 0
                        while True:
                            c_url = f"https://api.clickup.com/api/v2/task/{task_id}/comment?page={c_page}"
                            c_resp = requests.get(c_url, headers=headers, timeout=20)
                            if not c_resp.ok:
                                break
                            c_data = c_resp.json() or {}
                            comments = c_data.get('comments') or c_data.get('data') or []
                            if not comments:
                                break
                            for c in comments:
                                try:
                                    comment_id = str(c.get('id'))
                                    user = (c.get('user') or {}).get('username') if isinstance(c.get('user'), dict) else None
                                    text = c.get('comment_text') or c.get('text') or ''
                                    date = _safe_int(c.get('date')) or _safe_int(c.get('date_created'))
                                    upsert_clickup_comment({
                                        'id': comment_id,
                                        'task_id': task_id,
                                        'user': user,
                                        'text': text,
                                        'date': date,
                                    })
                                    # Also index as analysis item (optional)
                                    _ = upsert_analysis_item(
                                        source='clickup_comment',
                                        source_id=f"{task_id}:{comment_id}",
                                        title=(text or '')[:120],
                                        body=text or '',
                                        created_at=date,
                                        updated_at=date,
                                        author=user,
                                        url=None,
                                    )
                                except Exception as e:
                                    print(f"[ClickUp] comment persist error: {e}")
                            c_page += 1
                    except Exception as e:
                        print(f"[ClickUp] comments fetch error: {e}")
                page += 1

            if newest_update and newest_update != date_updated_gt:
                date_updated_gt = newest_update
                _save_state({"date_updated_gt": date_updated_gt})

            time.sleep(90)
        except Exception as e:
            print(f"[ClickUp exception] {e}")
            time.sleep(backoff_seconds)

