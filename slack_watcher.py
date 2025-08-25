import os
import time
import json
import requests

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

    while True:
        try:
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
                channels.extend(data.get("channels", []))
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
                        print(f"[Slack] #{channel['name']}: {msg.get('text')}")
                        ts = msg.get("ts")
                        if ts and (newest_seen_ts is None or ts > newest_seen_ts):
                            newest_seen_ts = ts
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
