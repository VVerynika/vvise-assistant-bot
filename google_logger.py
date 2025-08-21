import os
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials


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


def log_message(message):
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        # Backward compatible env; but if not set, try SERVICE_ACCOUNT_JSON_PATH or common defaults
        creds_file_path = os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") or _detect_service_account_path()

        if not sheet_id:
            print("GOOGLE_SHEET_ID не найден")
            return

        if creds_json:
            # Используем строку из переменной окружения
            creds_dict = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif creds_file_path:
            # Используем путь к файлу сервис-аккаунта
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)
        else:
            print("Нет ни GOOGLE_CREDS_JSON, ни доступного service_account.json (попробуйте SERVICE_ACCOUNT_JSON_PATH)")
            return

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        content = message.text

        worksheet.append_row([timestamp, user, content])
        print("Лог записан в таблицу")

    except Exception as e:
        print(f"Ошибка при логировании в Google Sheets: {e}")
