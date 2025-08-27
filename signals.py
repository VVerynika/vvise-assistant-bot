import time
from typing import List

from storage import db_cursor


def detect_stalled_issues(days_without_update: int = 14) -> List[int]:
    cutoff = int(time.time()) - days_without_update * 86400
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT i.id
            FROM analysis_items i
            LEFT JOIN analysis_status s ON s.item_id = i.id
            WHERE COALESCE(s.last_seen, i.updated_at) < ?
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
            ORDER BY i.id DESC
            LIMIT 500
            """
        )
        return [int(r[0]) for r in cur.fetchall()]

