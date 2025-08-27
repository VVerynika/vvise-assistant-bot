import os
from datetime import datetime
from typing import List, Dict

import gspread
from google.oauth2.service_account import Credentials

from storage import list_status_snapshot, set_muted


def _get_creds():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID not set")
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_file_path = os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON_PATH") or ""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    if creds_json:
        from json import loads
        creds = Credentials.from_service_account_info(loads(creds_json), scopes=scopes)
    elif creds_file_path and os.path.isfile(creds_file_path):
        creds = Credentials.from_service_account_file(creds_file_path, scopes=scopes)
    else:
        raise RuntimeError("Service account creds not provided")
    return sheet_id, creds


def sync_snapshot_to_sheet() -> None:
    try:
        sheet_id, creds = _get_creds()
    except Exception as e:
        print(f"[Sheets] creds error: {e}")
        return

    try:
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        ws_title = "Status"
        try:
            ws = sh.worksheet(ws_title)
        except Exception:
            ws = sh.add_worksheet(title=ws_title, rows=2000, cols=12)

        # Header
        header = [
            "ID",
            "Source",
            "Source ID",
            "Title",
            "URL",
            "Priority",
            "Status",
            "Last Seen",
            "Labels",
            "Muted",
        ]
        ws.resize(rows=2, cols=len(header))
        ws.update('A1', [header])

        # Pull current sheet values to catch Muted toggles from users
        sheet_muted_by_id: Dict[int, bool] = {}
        try:
            existing = ws.get_all_values()
            if existing:
                ex_header = existing[0]
                ex_rows = existing[1:]
                id_idx = ex_header.index("ID") if "ID" in ex_header else -1
                muted_idx = ex_header.index("Muted") if "Muted" in ex_header else -1
                if id_idx >= 0 and muted_idx >= 0:
                    for row in ex_rows:
                        if id_idx < len(row) and muted_idx < len(row):
                            try:
                                item_id = int(row[id_idx])
                            except Exception:
                                continue
                            val = (row[muted_idx] or '').strip().lower()
                            muted = val in ("true", "1", "yes", "да", "y", "x", "✓", "✔", "muted")
                            sheet_muted_by_id[item_id] = muted
        except Exception as e:
            print(f"[Sheets] read existing failed: {e}")

        rows = list_status_snapshot(limit=1000)
        values: List[List[str]] = []
        for r in rows:
            last_seen = int(r[7]) if r[7] is not None else None
            last_seen_str = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S') if last_seen else ''
            labels = r[8] or ''
            item_id = int(r[0])
            # Apply user's muted flag from sheet into DB
            try:
                if item_id in sheet_muted_by_id:
                    set_muted(item_id, sheet_muted_by_id[item_id])
            except Exception as e:
                print(f"[Sheets] set_muted failed for {item_id}: {e}")

            muted_final = 'muted' in labels.lower() or sheet_muted_by_id.get(item_id, False)

            values.append([
                str(item_id), str(r[1]), str(r[2] or ''), r[3] or '', r[4] or '',
                str(r[5] if r[5] is not None else ''),
                r[6] or '',
                last_seen_str,
                labels,
                'TRUE' if muted_final else 'FALSE',
            ])
        if values:
            ws.update(f'A2', values)
        print(f"[Sheets] Synced {len(values)} rows")
    except Exception as e:
        print(f"[Sheets] sync error: {e}")

