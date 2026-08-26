from config import BASE_URL
from core.spx_request import spx_get


LOADING_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/loading/list"
)


def get_trip_loading(
    trip_id,
    page=1,
    count=2000,
    loading_type="outbound",
    loaded_sequence_number=None,
    unloaded_sequence_number=None,
    actual_unloaded_sequence_number=None,
):
    params = {
        "trip_id":
            trip_id,

        "pageno":
            page,

        "count":
            count,

        "type":
            loading_type,
    }

    if loaded_sequence_number is not None:
        params[
            "loaded_sequence_number"
        ] = (
            loaded_sequence_number
        )

    if unloaded_sequence_number is not None:
        params[
            "unloaded_sequence_number"
        ] = (
            unloaded_sequence_number
        )

    if (
        actual_unloaded_sequence_number
        is not None
    ):
        params[
            "actual_unloaded_sequence_number"
        ] = (
            actual_unloaded_sequence_number
        )

    response = spx_get(
        LOADING_API,
        params=params,
        timeout=60,
    )

    data = response.json()

    if data.get(
        "retcode"
    ) != 0:
        raise RuntimeError(
            data.get(
                "message",
                "SPX loading API error",
            )
        )

    return data


def get_all_outbound_loading(
    trip_id,
    loaded_sequence_number=1,
):
    page = 1
    count = 2000

    items = []

    while True:
        response = (
            get_trip_loading(
                trip_id=
                    trip_id,

                page=
                    page,

                count=
                    count,

                loading_type=
                    "outbound",

                loaded_sequence_number=
                    loaded_sequence_number,
            )
        )

        data = (
            response.get(
                "data",
                {},
            )
        )

        rows = (
            data.get(
                "list",
                [],
            )
        )

        total = int(
            data.get(
                "total",
                0,
            )
            or 0
        )

        if not rows:
            break

        items.extend(
            rows
        )

        print(
            f"[Trip {trip_id}] "
            f"Outbound page={page} "
            f"received={len(rows)} "
            f"collected={len(items)} "
            f"total={total}"
        )

        if (
            total
            and
            len(items) >= total
        ):
            break

        page += 1

    return items


def get_all_inbound_loading(
    trip_id,
    unloaded_sequence_number=2,
):
    page = 1
    count = 2000

    items = []

    while True:
        response = (
            get_trip_loading(
                trip_id=
                    trip_id,

                page=
                    page,

                count=
                    count,

                loading_type=
                    "inbound",

                unloaded_sequence_number=
                    unloaded_sequence_number,
            )
        )

        data = (
            response.get(
                "data",
                {},
            )
        )

        rows = (
            data.get(
                "list",
                [],
            )
        )

        total = int(
            data.get(
                "total",
                0,
            )
            or 0
        )

        if not rows:
            break

        items.extend(
            rows
        )

        print(
            f"[Trip {trip_id}] "
            f"Inbound page={page} "
            f"received={len(rows)} "
            f"collected={len(items)} "
            f"total={total}"
        )

        if (
            total
            and
            len(items) >= total
        ):
            break

        page += 1

    return items


def get_all_trip_loading(
    trip_id,
    actual_unloaded_sequence_number=2,
    loading_type="inbound",
):
    if (
        loading_type
        == "outbound"
    ):
        return (
            get_all_outbound_loading(
                trip_id=
                    trip_id,

                loaded_sequence_number=
                    1,
            )
        )

    return (
        get_all_inbound_loading(
            trip_id=
                trip_id,

            unloaded_sequence_number=
                actual_unloaded_sequence_number,
        )
    )