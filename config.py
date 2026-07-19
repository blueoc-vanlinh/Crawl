import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
COOKIE = os.getenv("COOKIE")
CSRF = os.getenv("CSRF")

HEADERS = {
    "Cookie": COOKIE,
    "X-Csrftoken": CSRF,
    "Referer": "https://spx.shopee.vn/",
    "Origin": "https://spx.shopee.vn",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}