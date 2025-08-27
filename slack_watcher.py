import os
import time
import json
import requests
from typing import Dict, Any, List, Optional

from storage import (
    init_db,
    upsert_slack_channel,
    upsert_slack_user,
    upsert_slack_message,
    upsert_analysis_item,
    upsert_content_index,
    set_status,
)
from lifecycle import is_stopping, wait

def _state_path_default(name: str) -> str:
    base = os.getenv("STATE_DIR") or os.getenv("DATA_DIR") or "/var/tmp"
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, name)


STATE_PATH = os.getenv("SLACK_STATE_FILE", _state_path_default(".slack_state.json"))
FETCH_DM_AND_IM = os.getenv("SLACK_FETCH_DMS", "1") == "1"
CHANNEL_TYPES = os.getenv(
    "SLACK_CHANNEL_TYPES",
    "public_channel,private_channel,mpim,im" if FETCH_DM_AND_IM else "public_channel,private_channel",
)


def _slack_ts_to_epoch(ts: Optional[str]) -> Optional[int]:
    try:
        if not ts:
            return None
        # ts like "1700000000.1234" -> seconds
        return int(float(ts))
    except Exception:
        return None


def _load_state():
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"last_ts_by_channel": {}}


def _save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def run():
    SLACK_TOKEN = os.getenv("SLACK_TOKEN")

    if not SLACK_TOKEN:
        print("SLACK_TOKEN не задан — Slack watcher отключён")
        return

    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    channels_url = f"https://slack.com/api/conversations.list?limit=200&types={CHANNEL_TYPES}"
    users_url = "https://slack.com/api/users.list?limit=200"

    backoff_seconds = 30
    state = _load_state()
    last_ts_by_channel = state.get("last_ts_by_channel", {})

    # Ensure DB exists
    try:
        init_db()
    except Exception:
        pass

    while not is_stopping():
        try:
            # Periodically refresh users
            try:
                next_cursor_u = None
                while True:
                    u_url = users_url + (f"&cursor={next_cursor_u}" if next_cursor_u else "")
                    u_resp = requests.get(u_url, headers=headers, timeout=20)
                    if u_resp.status_code == 429:
                        retry_after = int(u_resp.headers.get("Retry-After", "30"))
                        print(f"[Slack 429] users.list, sleep {retry_after}s")
                        time.sleep(retry_after)
                        continue
                    if not u_resp.ok:
                        print(f"[Slack error] users.list {u_resp.status_code} {u_resp.text[:200]}")
                        break
                    u_data = u_resp.json()
                    for user in u_data.get("members", []) or []:
                        try:
                            upsert_slack_user(user)
                        except Exception as e:
                            print(f"[Slack] user upsert error: {e}")
                    next_cursor_u = (u_data.get("response_metadata") or {}).get("next_cursor") or None
                    if not next_cursor_u:
                        break
            except Exception as e:
                print(f"[Slack users] exception: {e}")

            # Получим список каналов с пагинацией
            channels = []
            next_cursor = None
            while True:
                url = channels_url + (f"&cursor={next_cursor}" if next_cursor else "")
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "30"))
                    print(f"[Slack 429] conversations.list, sleep {retry_after}s")
                    time.sleep(retry_after)
                    continue
                if not resp.ok:
                    print(f"[Slack error] {resp.status_code} {resp.text[:200]}")
                    time.sleep(backoff_seconds)
                    break
                data = resp.json()
                channels_batch = data.get("channels", []) or []
                for ch in channels_batch:
                    try:
                        upsert_slack_channel(ch)
                    except Exception as e:
                        print(f"[Slack] channel upsert error: {e}")
                channels.extend(channels_batch)
                next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
                if not next_cursor:
                    break

            # Для каждого канала, читаем историю с учётом last_ts
            for channel in channels:
                ch_id = channel['id']
                latest_known = last_ts_by_channel.get(ch_id)
                history_url = f"https://slack.com/api/conversations.history?channel={ch_id}&limit=200"
                if latest_known:
                    history_url += f"&oldest={latest_known}"
                next_cursor = None
                newest_seen_ts = latest_known

                while True:
                    url = history_url + (f"&cursor={next_cursor}" if next_cursor else "")
                    resp = requests.get(url, headers=headers, timeout=20)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", "30"))
                        print(f"[Slack 429] conversations.history, sleep {retry_after}s")
                        time.sleep(retry_after)
                        continue
                    if not resp.ok:
                        print(f"[Slack error] {resp.status_code} {resp.text[:200]}")
                        time.sleep(backoff_seconds)
                        break
                    data = resp.json()
                    messages = data.get("messages", [])
                    # Slack возвращает от новых к старым; выведем в обратном порядке для хронологии
                    for msg in reversed(messages):
                        try:
                            text = msg.get("text") or ""
                            is_dm = 1 if channel.get("is_im") or channel.get("is_mpim") else 0
                            ts = msg.get("ts")
                            # Persist raw message
                            upsert_slack_message({
                                "channel_id": ch_id,
                                "ts": ts,
                                "user": msg.get("user") or (msg.get("bot_id") or ""),
                                "text": text,
                                "thread_ts": msg.get("thread_ts") or None,
                                "subtype": msg.get("subtype"),
                                "is_dm": is_dm,
                                "reactions": msg.get("reactions"),
                                "files": msg.get("files"),
                                "permalink": None,
                            })

                            # Upsert analysis item for unified processing
                            source_id = f"{ch_id}:{ts}"
                            created = _slack_ts_to_epoch(ts)
                            title = (text or "").strip()[:120]
                            item_id = upsert_analysis_item(
                                source="slack",
                                source_id=source_id,
                                title=title,
                                body=text or "",
                                created_at=created,
                                updated_at=created,
                                author=msg.get("user") or None,
                                url=None,
                            )
                            upsert_content_index(item_id, title, text or "")
                            set_status(item_id, priority=None, status=None, last_seen=created, labels=None)
                        except Exception as e:
                            print(f"[Slack] persist error: {e}")
                        # console tail for visibility
                        try:
                            print(f"[Slack] #{channel['name']}: {msg.get('text')}")
                        except Exception:
                            pass
                        # Fetch thread replies if present
                        try:
                            if msg.get("thread_ts") and (msg.get("reply_count") or 0) > 0:
                                thread_ts = msg.get("thread_ts")
                                next_cursor_r = None
                                while True:
                                    r_url = f"https://slack.com/api/conversations.replies?channel={ch_id}&ts={thread_ts}&limit=200"
                                    if next_cursor_r:
                                        r_url += f"&cursor={next_cursor_r}"
                                    r_resp = requests.get(r_url, headers=headers, timeout=20)
                                    if r_resp.status_code == 429:
                                        retry_after = int(r_resp.headers.get("Retry-After", "30"))
                                        print(f"[Slack 429] conversations.replies, sleep {retry_after}s")
                                        time.sleep(retry_after)
                                        continue
                                    if not r_resp.ok:
                                        print(f"[Slack error] {r_resp.status_code} {r_resp.text[:200]}")
                                        break
                                    r_data = r_resp.json() or {}
                                    replies = r_data.get("messages", []) or []
                                    # replies array includes parent; skip duplicates by ts == thread_ts handled by upsert
                                    for rep in replies:
                                        try:
                                            r_ts = rep.get("ts")
                                            r_text = rep.get("text") or ""
                                            upsert_slack_message({
                                                "channel_id": ch_id,
                                                "ts": r_ts,
                                                "user": rep.get("user") or (rep.get("bot_id") or ""),
                                                "text": r_text,
                                                "thread_ts": rep.get("thread_ts") or thread_ts,
                                                "subtype": rep.get("subtype"),
                                                "is_dm": is_dm,
                                                "reactions": rep.get("reactions"),
                                                "files": rep.get("files"),
                                                "permalink": None,
                                            })
                                            source_id_r = f"{ch_id}:{r_ts}"
                                            created_r = _slack_ts_to_epoch(r_ts)
                                            title_r = (r_text or "").strip()[:120]
                                            item_id_r = upsert_analysis_item(
                                                source="slack",
                                                source_id=source_id_r,
                                                title=title_r,
                                                body=r_text or "",
                                                created_at=created_r,
                                                updated_at=created_r,
                                                author=rep.get("user") or None,
                                                url=None,
                                            )
                                            upsert_content_index(item_id_r, title_r, r_text or "")
                                            set_status(item_id_r, priority=None, status=None, last_seen=created_r, labels=None)
                                        except Exception as e:
                                            print(f"[Slack] persist reply error: {e}")
                                    next_cursor_r = (r_data.get("response_metadata") or {}).get("next_cursor") or None
                                    if not next_cursor_r:
                                        break
                        except Exception as e:
                            print(f"[Slack] thread fetch error: {e}")
                        ts = msg.get("ts")
                        if ts and (newest_seen_ts is None or ts > newest_seen_ts):
                            newest_seen_ts = ts
                    next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
                    if not next_cursor:
                        break

                if newest_seen_ts and newest_seen_ts != latest_known:
                    last_ts_by_channel[ch_id] = newest_seen_ts
                    _save_state({"last_ts_by_channel": last_ts_by_channel})

            if wait(60):
                break
        except Exception as e:
            print(f"[Slack exception] {e}")
            if wait(backoff_seconds):
                break
