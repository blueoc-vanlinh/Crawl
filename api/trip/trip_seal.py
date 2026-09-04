from config import BASE_URL
from core.spx_request import spx_get


SEAL_API = (
    BASE_URL
    + "/api/admin/transportation/trip/seal/detail"
)


def get_trip_seal_detail(
    trip_id,
    sequence_number,
    station,
):
    params = {
        "trip_id":
            trip_id,

        "sequence_number":
            sequence_number,

        "station":
            station,
    }

    response = spx_get(
        SEAL_API,
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
                "Unknown seal detail error",
            )
        )

    return data