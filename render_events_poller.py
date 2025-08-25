import os
import time
import json
import urllib.request
import urllib.error

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "srv-d2je5fv5r7bs73eouf8g")
EVENTS_URL_BASE = f"https://api.render.com/v1/services/{SERVICE_ID}/events?limit=50"
LOG_PATH = os.getenv("RENDER_EVENTS_LOG", "/workspace/render_events.log")
POLL_INTERVAL_SECONDS = int(os.getenv("RENDER_POLL_INTERVAL_SECONDS", "10"))
STATE_PATH = os.getenv("RENDER_EVENTS_STATE", "/workspace/.render_events_cursor")


def load_last_cursor() -> str:
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def save_last_cursor(cursor: str) -> None:
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            f.write(cursor or "")
    except Exception:
        pass


def append_log(lines: list) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
    except Exception:
        print("[poller] failed to write log")


def http_get_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {RENDER_API_KEY}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def fetch_events(cursor: str):
    url = EVENTS_URL_BASE
    if cursor:
        url = url + f"&cursor={cursor}"
    return http_get_json(url)


def format_event(ev: dict) -> str:
    event = ev.get("event", {})
    event_type = event.get("type")
    timestamp = event.get("timestamp")
    details = event.get("details", {})
    return json.dumps({
        "timestamp": timestamp,
        "type": event_type,
        "details": details,
    }, ensure_ascii=False)


def run():
    if not RENDER_API_KEY:
        print("RENDER_API_KEY not set; poller disabled")
        return
    cursor = load_last_cursor()
    print(f"[poller] starting, service={SERVICE_ID}, cursor={cursor or 'None'}")
    while True:
        try:
            data = fetch_events(cursor)
            entries = list(reversed(data)) if isinstance(data, list) else []
            lines = [format_event(e) for e in entries]
            if lines:
                append_log(lines)
                last_cursor = entries[-1].get("cursor") if entries else cursor
                if last_cursor and last_cursor != cursor:
                    cursor = last_cursor
                    save_last_cursor(cursor)
            time.sleep(POLL_INTERVAL_SECONDS)
        except urllib.error.HTTPError as e:
            print(f"[poller] http error: {e.code} {e.reason}")
            time.sleep(max(5, POLL_INTERVAL_SECONDS))
        except Exception as e:
            print(f"[poller] error: {e}")
            time.sleep(max(5, POLL_INTERVAL_SECONDS))


if __name__ == "__main__":
    run()