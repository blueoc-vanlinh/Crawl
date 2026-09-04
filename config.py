import os

from dotenv import load_dotenv

from core.auth import get_spx_headers


load_dotenv()


BASE_URL = os.getenv(
    "BASE_URL",
    "https://spx.shopee.vn",
)


def get_headers(
    force_refresh=False,
    silent=False,
):
    return get_spx_headers(
        force_refresh=
            force_refresh
    )