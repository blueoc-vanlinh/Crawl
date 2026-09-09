from pathlib import Path
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


BASE_DIR = Path(__file__).resolve().parent.parent

SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"

SPREADSHEET_ID = "1IdOPNNXLDvG52gjPRzZlzDHUxVaN-c0fkFOvlEsrOYA"

SHEET_NAME = "cookie"


def get_google_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=scopes,
    )

    return gspread.authorize(credentials)


def get_cookie_sheet():
    client = get_google_client()

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    try:
        worksheet = spreadsheet.worksheet(
            SHEET_NAME
        )

    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=SHEET_NAME,
            rows=10,
            cols=5,
        )

    return worksheet


def push_spx_auth_to_sheet(auth):
    if not auth:
        raise RuntimeError(
            "Auth SPX đang trống."
        )

    cookie = str(
        auth.get("cookie", "")
        or ""
    ).strip()

    csrf = str(
        auth.get("csrf", "")
        or ""
    ).strip()

    if not cookie:
        raise RuntimeError(
            "Không có Cookie SPX."
        )

    if not csrf:
        raise RuntimeError(
            "Không có CSRF SPX."
        )

    updated_at = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    sheet = get_cookie_sheet()

    sheet.update(
        range_name="A1:C2",
        values=[
            [
                "Cookie",
                "CSRF",
                "Updated",
            ],
            [
                cookie,
                csrf,
                updated_at,
            ],
        ],
    )

    print(
        "Đã đẩy Cookie + CSRF lên Google Sheet."
    )

    print(
        f"Updated: {updated_at}"
    )

    return True