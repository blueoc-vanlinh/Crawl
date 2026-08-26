import os
from dotenv import load_dotenv
from core.auth import get_spx_headers

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://spx.shopee.vn")

def get_headers(
    force_refresh=False,
    silent=False,
):
    if cache_valid:
        if not silent:
            print(
                f"SPX auth cache: OK "
                f"({minutes_left} phút còn lại)"
            )

        return headers