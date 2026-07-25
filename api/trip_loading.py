import requests

from config import BASE_URL, HEADERS

LOADING_API = BASE_URL + "/api/admin/transportation/trip/history/loading/list"


def get_trip_loading(
    trip_id,
    page=1,
    count=100,
    actual_unloaded_sequence_number=2,
    loading_type="inbound",
):
    params = {
        "trip_id": trip_id,
        "pageno": page,
        "count": count,
        "actual_unloaded_sequence_number": actual_unloaded_sequence_number,
        "type": loading_type,
    }

    r = requests.get(
        LOADING_API,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    r.raise_for_status()

    data = r.json()

    if data["retcode"] != 0:
        raise Exception(data["message"])

    return data


def get_all_trip_loading(
    trip_id,
    actual_unloaded_sequence_number=2,
    loading_type="inbound",
):
    page = 1
    count = 100

    items = []

    while True:
        data = get_trip_loading(
            trip_id=trip_id,
            page=page,
            count=count,
            actual_unloaded_sequence_number=actual_unloaded_sequence_number,
            loading_type=loading_type,
        )

        lst = data["data"]["list"]

        if not lst:
            break

        items.extend(lst)

        if len(items) >= data["data"]["total"]:
            break

        page += 1

    return items