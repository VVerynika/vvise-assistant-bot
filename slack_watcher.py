import os
import time
import json
import re
import requests
from storage import append_slack_thread, get_slack_oldest_ts

STATE_PATH = os.getenv("SLACK_STATE_FILE", "/workspace/.slack_state.json")


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


def _get(url, headers, timeout=20):
    backoff = 2
    while True:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "30"))
            time.sleep(retry_after)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        return r


def run():
    SLACK_TOKEN = os.getenv("SLACK_TOKEN")
    if not SLACK_TOKEN:
        print("SLACK_TOKEN не задан — Slack watcher отключён")
        return

    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    channels_url = "https://slack.com/api/conversations.list?limit=200"

    backoff_seconds = 30
    state = _load_state()
    last_ts_by_channel = state.get("last_ts_by_channel", {})
    manual_oldest = get_slack_oldest_ts()

    while True:
        try:
            channels = []
            next_cursor = None
            while True:
                url = channels_url + (f"&cursor={next_cursor}" if next_cursor else "")
                resp = _get(url, headers=headers)
                if not resp.ok:
                    time.sleep(backoff_seconds)
                    break
                data = resp.json()
                channels.extend(data.get("channels", []))
                next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
                if not next_cursor:
                    break

            for channel in channels:
                ch_id = channel['id']
                latest_known = last_ts_by_channel.get(ch_id)
                oldest_ts = manual_oldest or latest_known
                history_url = f"https://slack.com/api/conversations.history?channel={ch_id}&limit=200"
                if oldest_ts:
                    history_url += f"&oldest={oldest_ts}"
                next_cursor = None
                newest_seen_ts = latest_known

                while True:
                    url = history_url + (f"&cursor={next_cursor}" if next_cursor else "")
                    resp = _get(url, headers=headers)
                    if not resp.ok:
                        time.sleep(backoff_seconds)
                        break
                    data = resp.json()
                    messages = data.get("messages", [])
                    for msg in messages:
                        parent_ts = msg.get('thread_ts') or msg.get('ts')
                        is_parent = parent_ts == msg.get('ts')
                        reply_count = msg.get('reply_count') if is_parent else None
                        parent_user = msg.get('user') if is_parent else None

                        thread_msgs = []
                        if is_parent:
                            thread_msgs.append({"user": msg.get('user'), "text": msg.get('text') or '', "ts": msg.get('ts')})
                            if reply_count and reply_count > 0:
                                repl_url = f"https://slack.com/api/conversations.replies?channel={ch_id}&ts={parent_ts}&limit=200"
                                rcur = None
                                while True:
                                    rurl = repl_url + (f"&cursor={rcur}" if rcur else "")
                                    r = _get(rurl, headers=headers)
                                    if not r.ok:
                                        break
                                    rdata = r.json()
                                    for rm in rdata.get('messages', [])[1:]:
                                        thread_msgs.append({"user": rm.get('user'), "text": rm.get('text') or '', "ts": rm.get('ts')})
                                    rcur = (rdata.get("response_metadata") or {}).get("next_cursor") or None
                                    if not rcur:
                                        break
                            has_response = (len(thread_msgs) > 1)
                            mention_count = 0
                            try:
                                for m in thread_msgs:
                                    t = m.get('text') or ''
                                    mention_count += len(re.findall(r"<@[^>]+>", t))
                            except Exception:
                                mention_count = 0
                            append_slack_thread({
                                "thread_ts": parent_ts,
                                "channel_id": ch_id,
                                "channel": channel['name'],
                                "parent_user_id": parent_user,
                                "reply_count": reply_count or 0,
                                "has_response": has_response,
                                "mention_count": mention_count,
                                "has_mentions": mention_count > 0,
                                "messages": thread_msgs,
                            })

                        try:
                            tsf = float(msg.get("ts"))
                            if tsf and (newest_seen_ts is None or tsf > newest_seen_ts):
                                newest_seen_ts = tsf
                        except Exception:
                            pass

                    next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
                    if not next_cursor:
                        break

                if newest_seen_ts and newest_seen_ts != latest_known:
                    last_ts_by_channel[ch_id] = newest_seen_ts
                    _save_state({"last_ts_by_channel": last_ts_by_channel})

            time.sleep(60)
        except Exception as e:
            print(f"[Slack exception] {e}")
            time.sleep(backoff_seconds)
