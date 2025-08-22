import os
import json
import threading
import time
import hashlib
from typing import Any, Dict, List, Optional

_DB_PATH = os.getenv("STORAGE_DB_FILE", "/workspace/.vvise_assistant_store.json")
_lock = threading.Lock()
_cache: Dict[str, Any] = {}
_cache_mtime: Optional[float] = None
_SCHEMA_VERSION = 1


def _empty_db() -> Dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "slack_threads": [],  # list of {thread_ts, channel, channel_id, parent_user_id, reply_count, has_response, messages: [{user,text,ts}]}
        "clickup_tasks": [],  # list of enriched task dicts
        "analysis_state": {"last_analysis_ts": None, "slack_count": 0, "clickup_count": 0, "db_hash": None},
    }


def _compute_hash(obj: Any) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def _load_db() -> Dict[str, Any]:
    global _cache, _cache_mtime
    try:
        mtime = os.path.getmtime(_DB_PATH) if os.path.exists(_DB_PATH) else None
        if _cache and _cache_mtime and mtime == _cache_mtime:
            return _cache
        if os.path.exists(_DB_PATH):
            with open(_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
        else:
            db = _empty_db()
    except Exception:
        db = _empty_db()
    # migrate if schema changed
    if db.get("schema_version") != _SCHEMA_VERSION:
        migrated = _empty_db()
        migrated.update({k: v for k, v in db.items() if k in ("slack_threads", "clickup_tasks", "analysis_state")})
        db = migrated
    # cache it
    _cache = db
    _cache_mtime = os.path.getmtime(_DB_PATH) if os.path.exists(_DB_PATH) else time.time()
    return db


def _save_db(db: Dict[str, Any]) -> None:
    db["schema_version"] = _SCHEMA_VERSION
    db["analysis_state"]["slack_count"] = len(db.get("slack_threads", []))
    db["analysis_state"]["clickup_count"] = len(db.get("clickup_tasks", []))
    db["analysis_state"]["db_hash"] = _compute_hash({"slack_threads": db.get("slack_threads", []), "clickup_tasks": db.get("clickup_tasks", [])})
    tmp = _DB_PATH + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False)
        os.replace(tmp, _DB_PATH)
    # update cache metadata
    global _cache, _cache_mtime
    _cache = db
    _cache_mtime = os.path.getmtime(_DB_PATH)


def append_slack_thread(thread_obj: Dict[str, Any]) -> None:
    db = _load_db()
    threads = db.setdefault("slack_threads", [])
    # upsert by thread_ts + channel_id
    key_ts = thread_obj.get("thread_ts")
    key_ch = thread_obj.get("channel_id")
    for idx, t in enumerate(threads):
        if t.get("thread_ts") == key_ts and t.get("channel_id") == key_ch:
            threads[idx] = thread_obj
            _save_db(db)
            return
    threads.append(thread_obj)
    _save_db(db)


def upsert_clickup_task(task: Dict[str, Any]) -> None:
    db = _load_db()
    tasks = db.setdefault("clickup_tasks", [])
    tid = task.get("id")
    if tid:
        for i, t in enumerate(tasks):
            if t.get("id") == tid:
                tasks[i] = task
                _save_db(db)
                return
    tasks.append(task)
    _save_db(db)


def read_all() -> Dict[str, Any]:
    return _load_db()


def update_analysis_state(last_analysis_ts: float) -> None:
    db = _load_db()
    db.setdefault("analysis_state", {})["last_analysis_ts"] = last_analysis_ts
    _save_db(db)