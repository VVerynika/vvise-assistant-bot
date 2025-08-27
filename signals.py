import time
from typing import List, Tuple

from storage import db_cursor, kv_get, kv_set


def detect_stalled_issues(days_without_update: int = 14) -> List[int]:
    cutoff = int(time.time()) - days_without_update * 86400
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT i.id
            FROM analysis_items i
            LEFT JOIN analysis_status s ON s.item_id = i.id
            WHERE COALESCE(s.last_seen, i.updated_at) < ?
              AND (s.labels IS NULL OR instr(lower(s.labels), 'muted') = 0)
            ORDER BY COALESCE(s.priority, 999), i.id DESC
            LIMIT 500
            """,
            (cutoff,),
        )
        return [int(r[0]) for r in cur.fetchall()]


def find_important_slack_requests(min_reactions: int = 3) -> List[int]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT i.id
            FROM analysis_items i
            WHERE i.source = 'slack'
            ORDER BY i.id DESC
            LIMIT 1000
            """
        )
        return [int(r[0]) for r in cur.fetchall()]


def find_unread_dms() -> List[int]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT i.id
            FROM analysis_items i
            JOIN slack_messages sm ON sm.channel_id || ':' || sm.ts = i.source_id
            JOIN slack_channels sc ON sc.id = sm.channel_id
            WHERE sc.is_im = 1
              AND (
                SELECT COALESCE(instr(lower(s.labels), 'muted'), 0)
                FROM analysis_status s WHERE s.item_id = i.id
              ) = 0
            ORDER BY i.id DESC
            LIMIT 500
            """
        )
        return [int(r[0]) for r in cur.fetchall()]


def stalled_stats(days_without_update: int = 14, sample_size: int = 3) -> Tuple[int, List[int]]:
    ids = detect_stalled_issues(days_without_update)
    return len(ids), ids[:sample_size]


def should_send_alert(key: str, current_count: int, min_interval_seconds: int = 21600) -> bool:
    now = int(time.time())
    last = kv_get(f"alert_last_{key}")
    last_count = kv_get(f"alert_last_count_{key}")
    try:
        last_ts = int(last) if last else 0
    except Exception:
        last_ts = 0
    try:
        last_cnt = int(last_count) if last_count else -1
    except Exception:
        last_cnt = -1
    if now - last_ts >= min_interval_seconds or current_count != last_cnt:
        kv_set(f"alert_last_{key}", str(now))
        kv_set(f"alert_last_count_{key}", str(current_count))
        return True
    return False

