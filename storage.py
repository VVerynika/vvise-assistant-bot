import os
import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Tuple


DB_PATH = os.getenv("DB_PATH", "/workspace/data.db")


_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        setattr(_local, "conn", conn)
    return conn


@contextmanager
def db_cursor():
    conn = _get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    with db_cursor() as cur:
        # Slack entities
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS slack_channels (
                id TEXT PRIMARY KEY,
                name TEXT,
                is_im INTEGER DEFAULT 0,
                is_private INTEGER DEFAULT 0,
                created INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS slack_users (
                id TEXT PRIMARY KEY,
                real_name TEXT,
                name TEXT,
                display_name TEXT,
                email TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS slack_messages (
                channel_id TEXT,
                ts TEXT,
                user TEXT,
                text TEXT,
                thread_ts TEXT,
                subtype TEXT,
                is_dm INTEGER DEFAULT 0,
                reactions TEXT,
                files TEXT,
                permalink TEXT,
                PRIMARY KEY (channel_id, ts)
            )
            """
        )

        # ClickUp entities
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clickup_tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                status TEXT,
                folder_id TEXT,
                list_id TEXT,
                assignees TEXT,
                tags TEXT,
                date_created INTEGER,
                date_updated INTEGER,
                due_date INTEGER,
                url TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clickup_comments (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                user TEXT,
                text TEXT,
                date INTEGER
            )
            """
        )

        # Unified analysis items
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT,
                body TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                author TEXT,
                url TEXT,
                UNIQUE(source, source_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_a INTEGER NOT NULL,
                item_b INTEGER NOT NULL,
                link_type TEXT NOT NULL,
                score REAL,
                note TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_links_pair ON analysis_links(item_a, item_b)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_clusters (
                cluster_id INTEGER,
                item_id INTEGER,
                score REAL,
                PRIMARY KEY(cluster_id, item_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_status (
                item_id INTEGER PRIMARY KEY,
                priority INTEGER,
                status TEXT,
                last_seen INTEGER,
                labels TEXT
            )
            """
        )

        # Key/value state
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS job_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        # Optional FTS for search
        try:
            cur.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS content_index USING fts5(
                    item_id UNINDEXED,
                    title,
                    body,
                    content=''
                )
                """
            )
        except Exception:
            pass


def kv_get(key: str, default: Optional[str] = None) -> Optional[str]:
    with db_cursor() as cur:
        cur.execute("SELECT value FROM job_state WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default


def kv_set(key: str, value: str) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO job_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def upsert_slack_channel(ch: Dict[str, Any]) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO slack_channels(id, name, is_im, is_private, created)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                is_im=excluded.is_im,
                is_private=excluded.is_private,
                created=excluded.created
            """,
            (
                ch.get("id"),
                ch.get("name") or ch.get("user") or ch.get("id"),
                1 if ch.get("is_im") else 0,
                1 if ch.get("is_private") else 0,
                ch.get("created") or 0,
            ),
        )


def upsert_slack_user(u: Dict[str, Any]) -> None:
    profile = u.get("profile") or {}
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO slack_users(id, real_name, name, display_name, email)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                real_name=excluded.real_name,
                name=excluded.name,
                display_name=excluded.display_name,
                email=excluded.email
            """,
            (
                u.get("id"),
                u.get("real_name"),
                u.get("name"),
                profile.get("display_name"),
                profile.get("email"),
            ),
        )


def upsert_slack_message(m: Dict[str, Any]) -> None:
    reactions = json.dumps(m.get("reactions")) if m.get("reactions") is not None else None
    files = json.dumps(m.get("files")) if m.get("files") is not None else None
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO slack_messages(channel_id, ts, user, text, thread_ts, subtype, is_dm, reactions, files, permalink)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id, ts) DO UPDATE SET
                user=excluded.user,
                text=excluded.text,
                thread_ts=excluded.thread_ts,
                subtype=excluded.subtype,
                is_dm=excluded.is_dm,
                reactions=excluded.reactions,
                files=excluded.files,
                permalink=excluded.permalink
            """,
            (
                m.get("channel_id"),
                m.get("ts"),
                m.get("user"),
                m.get("text"),
                m.get("thread_ts"),
                m.get("subtype"),
                1 if m.get("is_dm") else 0,
                reactions,
                files,
                m.get("permalink"),
            ),
        )


def upsert_clickup_task(t: Dict[str, Any]) -> None:
    assignees = json.dumps(t.get("assignees")) if t.get("assignees") is not None else None
    tags = json.dumps(t.get("tags")) if t.get("tags") is not None else None
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO clickup_tasks(id, name, description, status, folder_id, list_id, assignees, tags, date_created, date_updated, due_date, url)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                status=excluded.status,
                folder_id=excluded.folder_id,
                list_id=excluded.list_id,
                assignees=excluded.assignees,
                tags=excluded.tags,
                date_created=excluded.date_created,
                date_updated=excluded.date_updated,
                due_date=excluded.due_date,
                url=excluded.url
            """,
            (
                t.get("id"),
                t.get("name"),
                (t.get("description") or {}).get("text") if isinstance(t.get("description"), dict) else t.get("description"),
                (t.get("status") or {}).get("status") if isinstance(t.get("status"), dict) else t.get("status"),
                (t.get("folder") or {}).get("id") or t.get("folder_id"),
                (t.get("list") or {}).get("id") or t.get("list_id"),
                assignees,
                tags,
                _safe_int(t.get("date_created")),
                _safe_int(t.get("date_updated")),
                _safe_int(t.get("due_date")),
                t.get("url") or _clickup_web_url(t.get("id")),
            ),
        )


def upsert_clickup_comment(c: Dict[str, Any]) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO clickup_comments(id, task_id, user, text, date)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                task_id=excluded.task_id,
                user=excluded.user,
                text=excluded.text,
                date=excluded.date
            """,
            (
                c.get("id"),
                c.get("task_id"),
                c.get("user"),
                c.get("text"),
                _safe_int(c.get("date")),
            ),
        )


def upsert_analysis_item(source: str, source_id: str, title: Optional[str], body: Optional[str], created_at: Optional[int], updated_at: Optional[int], author: Optional[str], url: Optional[str]) -> int:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO analysis_items(source, source_id, title, body, created_at, updated_at, author, url)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                title=excluded.title,
                body=excluded.body,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                author=excluded.author,
                url=excluded.url
            """,
            (source, source_id, title, body, created_at, updated_at, author, url),
        )
        cur.execute("SELECT id FROM analysis_items WHERE source = ? AND source_id = ?", (source, source_id))
        row = cur.fetchone()
        return int(row[0])


def upsert_content_index(item_id: int, title: Optional[str], body: Optional[str]) -> None:
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM content_index WHERE item_id = ?", (item_id,))
            cur.execute(
                "INSERT INTO content_index(item_id, title, body) VALUES(?, ?, ?)",
                (item_id, title or "", body or ""),
            )
    except Exception:
        # FTS might be unavailable; ignore
        pass


def record_link(item_a: int, item_b: int, link_type: str, score: float, note: Optional[str] = None) -> None:
    if item_a == item_b:
        return
    a, b = (item_a, item_b) if item_a < item_b else (item_b, item_a)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO analysis_links(item_a, item_b, link_type, score, note)
            VALUES(?, ?, ?, ?, ?)
            """,
            (a, b, link_type, float(score), note),
        )


def set_status(item_id: int, priority: Optional[int], status: Optional[str], last_seen: Optional[int], labels: Optional[List[str]] = None) -> None:
    labels_json = json.dumps(labels) if labels is not None else None
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO analysis_status(item_id, priority, status, last_seen, labels)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                priority=COALESCE(excluded.priority, analysis_status.priority),
                status=COALESCE(excluded.status, analysis_status.status),
                last_seen=COALESCE(excluded.last_seen, analysis_status.last_seen),
                labels=COALESCE(excluded.labels, analysis_status.labels)
            """,
            (item_id, priority, status, last_seen, labels_json),
        )


def fetch_items_for_analysis(limit: int = 5000) -> List[sqlite3.Row]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, source, source_id, title, body FROM analysis_items ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()


def list_status_snapshot(limit: int = 1000) -> List[sqlite3.Row]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.source, i.source_id, i.title, i.url, s.priority, s.status, s.last_seen, s.labels
            FROM analysis_items i
            LEFT JOIN analysis_status s ON s.item_id = i.id
            ORDER BY COALESCE(s.priority, 999), i.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()


def replace_clusters(label_by_item: Dict[int, int], score_by_item: Optional[Dict[int, float]] = None) -> None:
    with db_cursor() as cur:
        cur.execute("DELETE FROM analysis_clusters")
        for item_id, label in label_by_item.items():
            score = float(score_by_item.get(item_id)) if score_by_item and item_id in score_by_item else None
            cur.execute(
                "INSERT INTO analysis_clusters(cluster_id, item_id, score) VALUES(?, ?, ?)",
                (int(label), int(item_id), score),
            )


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _clickup_web_url(task_id: Optional[str]) -> Optional[str]:
    if not task_id:
        return None
    return f"https://app.clickup.com/t/{task_id}"

