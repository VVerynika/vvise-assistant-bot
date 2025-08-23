import os
import json
import threading
import time
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from config import CLEANUP_PRIORITY_MAX, CLEANUP_NO_RESPONSE_SECS, CLEANUP_OLDER_THAN_DAYS, CLEANUP_RETENTION_DAYS

_DB_PATH = os.getenv("STORAGE_DB_FILE", "/workspace/.vvise_assistant_store.json")
_lock = threading.Lock()
_cache: Dict[str, Any] = {}
_cache_mtime: Optional[float] = None
_SCHEMA_VERSION = 2


def _empty_db() -> Dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "slack_threads": [],
        "clickup_tasks": [],
        "deleted_slack_threads": [],
        "analysis_state": {"last_analysis_ts": None, "slack_count": 0, "clickup_count": 0, "db_hash": None},
        "ingest_config": {"slack_oldest_ts": None, "clickup_since_ms": None},
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
    if db.get("schema_version") != _SCHEMA_VERSION:
        migrated = _empty_db()
        for key in ("slack_threads", "clickup_tasks", "deleted_slack_threads", "analysis_state", "ingest_config"):
            if key in db:
                migrated[key] = db[key]
        db = migrated
    _cache = db
    _cache_mtime = os.path.getmtime(_DB_PATH) if os.path.exists(_DB_PATH) else time.time()
    return db


def _save_db(db: Dict[str, Any]) -> None:
    db["schema_version"] = _SCHEMA_VERSION
    db["analysis_state"]["slack_count"] = len(db.get("slack_threads", []))
    db["analysis_state"]["clickup_count"] = len(db.get("clickup_tasks", []))
    db["analysis_state"]["db_hash"] = _compute_hash({
        "slack_threads": db.get("slack_threads", []),
        "clickup_tasks": db.get("clickup_tasks", []),
        "deleted_slack_threads": db.get("deleted_slack_threads", []),
        "ingest_config": db.get("ingest_config", {}),
    })
    tmp = _DB_PATH + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False)
        os.replace(tmp, _DB_PATH)
    global _cache, _cache_mtime
    _cache = db
    _cache_mtime = os.path.getmtime(_DB_PATH)


def append_slack_thread(thread_obj: Dict[str, Any]) -> None:
    db = _load_db()
    threads = db.setdefault("slack_threads", [])
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


def propose_cleanup(now_ts: Optional[float] = None) -> Dict[str, Any]:
    db = _load_db()
    now_ts = now_ts or time.time()
    threshold_ts = now_ts - CLEANUP_OLDER_THAN_DAYS * 86400
    candidates = []
    for th in db.get("slack_threads", []):
        msgs = th.get("messages", [])
        last_ts = None
        for m in msgs:
            try:
                tsf = float(m.get("ts"))
                last_ts = max(last_ts or tsf, tsf)
            except Exception:
                continue
        prio = th.get("priority", 0)
        no_resp = th.get("no_response_secs", 0)
        if last_ts and last_ts < threshold_ts and prio <= CLEANUP_PRIORITY_MAX and no_resp <= CLEANUP_NO_RESPONSE_SECS:
            candidates.append({
                "thread_ts": th.get("thread_ts"),
                "channel_id": th.get("channel_id"),
                "channel": th.get("channel"),
                "last_ts": last_ts,
                "reply_count": th.get("reply_count", 0),
                "thread_len": len(msgs),
            })
    return {"candidates": candidates, "count": len(candidates)}


def soft_delete_threads(threads_keys: List[Dict[str, str]]) -> None:
    db = _load_db()
    remaining = []
    deleted = db.setdefault("deleted_slack_threads", [])
    for th in db.get("slack_threads", []):
        key = {"thread_ts": th.get("thread_ts"), "channel_id": th.get("channel_id")}
        if key in threads_keys:
            th["deleted_at_ts"] = time.time()
            deleted.append(th)
        else:
            remaining.append(th)
    db["slack_threads"] = remaining
    _save_db(db)


def purge_deleted_expired(now_ts: Optional[float] = None) -> int:
    db = _load_db()
    now_ts = now_ts or time.time()
    keep = []
    removed = 0
    for th in db.get("deleted_slack_threads", []):
        if th.get("deleted_at_ts") and now_ts - float(th["deleted_at_ts"]) > CLEANUP_RETENTION_DAYS * 86400:
            removed += 1
        else:
            keep.append(th)
    db["deleted_slack_threads"] = keep
    _save_db(db)
    return removed


# Ingest config helpers

def set_slack_oldest_days(days: int) -> None:
    db = _load_db()
    db.setdefault("ingest_config", {})["slack_oldest_ts"] = time.time() - days * 86400
    _save_db(db)


def set_slack_oldest_ts(ts: float) -> None:
    db = _load_db()
    db.setdefault("ingest_config", {})["slack_oldest_ts"] = ts
    _save_db(db)


def get_slack_oldest_ts() -> Optional[float]:
    db = _load_db()
    return (db.get("ingest_config") or {}).get("slack_oldest_ts")


def set_clickup_since_days(days: int) -> None:
    db = _load_db()
    db.setdefault("ingest_config", {})["clickup_since_ms"] = int((time.time() - days * 86400) * 1000)
    _save_db(db)


def set_clickup_since_ms(ms: int) -> None:
    db = _load_db()
    db.setdefault("ingest_config", {})["clickup_since_ms"] = ms
    _save_db(db)


def get_clickup_since_ms() -> Optional[int]:
    db = _load_db()
    return (db.get("ingest_config") or {}).get("clickup_since_ms")