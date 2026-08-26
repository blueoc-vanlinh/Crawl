# api/station_detail.py

import requests

from config import BASE_URL, get_headers


STATION_API = (
    BASE_URL
    + "/api/admin/station/details/"
)


def get_station_detail(station_id):
    params = {
        "station_id": station_id
    }

    r = requests.get(
        STATION_API,
        headers=get_headers(),
        params=params,
        timeout=30,
    )

    r.raise_for_status()

    data = r.json()

    if data.get("retcode") != 0:
        raise Exception(
            data.get("message", "Unknown station error")
        )

    return data