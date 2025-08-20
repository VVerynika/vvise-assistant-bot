import os
import gspread
from datetime import datetime

def log_message(message):
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            print("GOOGLE_SHEET_ID не найден в окружении")
            return

        gc = gspread.service_account(filename="service_account.json")
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        content = message.text

        worksheet.append_row([timestamp, user, content])

    except Exception as e:
        print(f"Ошибка при логировании в Google Sheets: {e}")