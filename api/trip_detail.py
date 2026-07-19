import requests

from config import BASE_URL, HEADERS

DETAIL_API = BASE_URL + "/api/admin/transportation/trip/history/detail"


def get_trip_detail(trip_id):
    """
    Lấy toàn bộ thông tin của Trip
    """

    params = {
        "trip_id": trip_id,
        "new_process_switch": "false"
    }

    r = requests.get(
        DETAIL_API,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    if data["retcode"] != 0:
        raise Exception(data["message"])

    return data