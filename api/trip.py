from config import BASE_URL
from core.spx_request import spx_get


TRIP_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/loading/list"
)


def get_trip(
    trip_id,
    unloaded_sequence_number=2,
    actual_unloaded_sequence_number=0,
    page=1,
    count=24,
    trip_type="pending",
):
    params = {
        "trip_id":
            trip_id,

        "pageno":
            page,

        "count":
            count,

        "unloaded_sequence_number":
            unloaded_sequence_number,

        "actual_unloaded_sequence_number":
            actual_unloaded_sequence_number,

        "type":
            trip_type,
    }

    response = spx_get(
        TRIP_API,
        params=params,
        timeout=30,
    )

    data = response.json()

    if data.get(
        "retcode"
    ) not in (
        None,
        0,
        "0",
    ):
        raise RuntimeError(
            data.get(
                "message",
                "SPX trip error",
            )
        )

    return data