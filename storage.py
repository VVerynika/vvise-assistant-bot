import os
import json
import threading
from typing import Any, Dict, List

_DB_PATH = os.getenv("STORAGE_DB_FILE", "/workspace/.vvise_assistant_store.json")
_lock = threading.Lock()


def _load_db() -> Dict[str, Any]:
    try:
        if os.path.exists(_DB_PATH):
            with open(_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"slack_messages": [], "clickup_tasks": []}


def _save_db(db: Dict[str, Any]) -> None:
    tmp = _DB_PATH + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False)
        os.replace(tmp, _DB_PATH)


def append_slack_message(msg: Dict[str, Any]) -> None:
    db = _load_db()
    db.setdefault("slack_messages", []).append(msg)
    _save_db(db)


def append_clickup_task(task: Dict[str, Any]) -> None:
    db = _load_db()
    db.setdefault("clickup_tasks", []).append(task)
    _save_db(db)


def read_all() -> Dict[str, Any]:
    return _load_db()