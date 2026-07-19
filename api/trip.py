import requests
from config import BASE_URL, HEADERS

TRIP_API = BASE_URL + "/api/admin/transportation/trip/history/loading/list"


def get_trip(
    trip_id,
    unloaded_sequence_number=2,
    actual_unloaded_sequence_number=0,
    page=1,
    count=24,
    trip_type="pending"
):
    params = {
        "trip_id": trip_id,
        "pageno": page,
        "count": count,
        "unloaded_sequence_number": unloaded_sequence_number,
        "actual_unloaded_sequence_number": actual_unloaded_sequence_number,
        "type": trip_type
    }

    r = requests.get(
        TRIP_API,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    r.raise_for_status()

    return r.json()