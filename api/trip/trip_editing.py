from config import BASE_URL
from core.spx_request import spx_get

def get_trip_detail_data(
    trip_id,
):
    endpoints = [
        (
            BASE_URL
            + "/api/admin/transportation/trip/history/detail",
            {
                "trip_id": trip_id,
                "new_process_switch": "false",
            },
        ),
    ]

    last_error = None

    for url, params in endpoints:
        try:
            response = spx_get(
                url,
                params=params,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Không lấy được Trip Detail: "
        f"{last_error}"
    )