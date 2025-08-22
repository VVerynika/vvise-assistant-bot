import os
import gspread
import json
from datetime import datetime
from google.oauth2.service_account import Credentials


def _detect_service_account_path() -> str:
    # Prefer explicit env var
    explicit_path = os.getenv("SERVICE_ACCOUNT_JSON_PATH")
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path
    # Try common locations (Render secret files or manually added)
    common_paths = [
        os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") or "",
        "/etc/secrets/service_account.json",
        "/etc/secrets/SERVICE_ACCOUNT_JSON",
        "/opt/render/project/src/service_account.json",
        "/workspace/service_account.json",
        "/app/service_account.json",
    ]
    for path in common_paths:
        if path and os.path.isfile(path):
            return path
    return ""


def _extract_message_text(message) -> str:
    try:
        text = getattr(message, 'text', None) or getattr(message, 'caption', None)
        if text is None:
            return "<non-text message>"
        return str(text)
    except Exception:
        return "<unavailable message>"


def _get_creds():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_file_path = os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") or _detect_service_account_path()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=scopes)
    if creds_file_path:
        return Credentials.from_service_account_file(creds_file_path, scopes=scopes)
    return None


def _open_sheet():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return None, None
    creds = _get_creds()
    if not creds:
        return None, None
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return sh, sh.sheet1


def _open_or_create_events_sheet(sh):
    try:
        for ws in sh.worksheets():
            if ws.title == "Events":
                return ws
        return sh.add_worksheet(title="Events", rows=1000, cols=10)
    except Exception:
        return sh.sheet1


def log_message(message):
    try:
        sh, worksheet = _open_sheet()
        if not worksheet:
            print("Google Sheets недоступен: проверьте переменные")
            return
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = None
        try:
            if getattr(message, 'from_user', None):
                user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        except Exception:
            user = None
        user = user or "<unknown>"
        content = _extract_message_text(message)
        worksheet.append_row([timestamp, user, content])
        print("Лог записан в таблицу")
    except Exception as e:
        print(f"Ошибка при логировании в Google Sheets: {e}")


def log_event(source: str, event_type: str, severity: str, summary: str, extra: dict | None = None):
    try:
        sh, _ = _open_sheet()
        if not sh:
            return
        ws = _open_or_create_events_sheet(sh)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        extra = extra or {}
        row = [
            timestamp,
            source,
            event_type,
            severity,
            summary,
            str(extra.get("priority", "")),
            extra.get("category", ""),
            json.dumps(extra.get("linked_tasks", []), ensure_ascii=False),
            str(extra.get("has_response", "")),
            str(extra.get("thread_len", "")),
            extra.get("deadline_status", ""),
        ]
        ws.append_row(row)
    except Exception as e:
        print(f"Ошибка при логировании события в Google Sheets: {e}")
