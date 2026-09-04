import os

from config import BASE_URL
from core.spx_request import spx_get


TRIP_TRACKING_PATH = os.getenv(
    "TRIP_TRACKING_PATH",
    "/api/admin/transportation/trip/history/tracking",
)

TRIP_TRACKING_API = (
    BASE_URL
    + TRIP_TRACKING_PATH
)


def get_trip_tracking(
    trip_id
):
    params = {
        "trip_id":
            trip_id
    }

    response = spx_get(
        TRIP_TRACKING_API,
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
                "Unknown SPX tracking error",
            )
        )

    return data