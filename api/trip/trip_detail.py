from config import BASE_URL
from core.spx_request import spx_get


DETAIL_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/detail"
)


def get_trip_detail(
    trip_id
):
    params = {
        "trip_id":
            trip_id,

        "new_process_switch":
            "false",
    }

    response = spx_get(
        DETAIL_API,
        params=params,
        timeout=30,
    )

    data = response.json()

    if data.get(
        "retcode"
    ) != 0:
        raise RuntimeError(
            data.get(
                "message",
                "Unknown trip detail error",
            )
        )

    return data