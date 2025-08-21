import os
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

def log_message(message):
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        creds_file_path = os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON")

        if not sheet_id:
            print("GOOGLE_SHEET_ID не найден")
            return

        if creds_json:
            # Используем строку из переменной окружения
            creds_dict = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif creds_file_path:
            # Используем путь к секретному файлу Render
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)
        else:
            print("Нет ни GOOGLE_CREDS_JSON, ни service_account.json в окружении")
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
        print(f"❌ Ошибка при логировании в Google Sheets: {e}") в Google Sheets: {e}")
