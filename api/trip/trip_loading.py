from config import BASE_URL
from core.spx_request import spx_get


LOADING_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/loading/list"
)


HUNG_YEN_SOC_ID = 3909


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
            f"loaded_sequence_number="
            f"{loaded_sequence_number} "
            f"received={len(rows)} "
            f"collected={len(items)} "
            f"total={total}"
        )

        if (
            total
            and
            len(
                items
            ) >= total
        ):
            break

        if len(
            rows
        ) < count:
            break

        page += 1

    return items


def get_all_inbound_loading(
    trip_id,
    actual_unloaded_sequence_number,
):
    if (
        actual_unloaded_sequence_number
        is None
    ):
        raise RuntimeError(
            "actual_unloaded_sequence_number rỗng"
        )

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

                actual_unloaded_sequence_number=
                    actual_unloaded_sequence_number,
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
            f"actual_unloaded_sequence_number="
            f"{actual_unloaded_sequence_number} "
            f"received={len(rows)} "
            f"collected={len(items)} "
            f"total={total}"
        )

        if (
            total
            and
            len(
                items
            ) >= total
        ):
            break

        if len(
            rows
        ) < count:
            break

        page += 1

    return items


def get_station_sequence(
    trip_detail,
    station_id,
):
    if not isinstance(
        trip_detail,
        dict,
    ):
        return None

    data = trip_detail.get(
        "data",
        trip_detail,
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    stations = data.get(
        "trip_station",
        [],
    )

    if not isinstance(
        stations,
        list,
    ):
        return None

    target_station_id = str(
        station_id
    ).strip()

    for station in stations:
        if not isinstance(
            station,
            dict,
        ):
            continue

        current_station_id = (
            station.get(
                "station"
            )
            or station.get(
                "station_id"
            )
            or ""
        )

        if (
            str(
                current_station_id
            ).strip()
            != target_station_id
        ):
            continue

        sequence = (
            station.get(
                "sequence_number"
            )
            or station.get(
                "sequence"
            )
            or station.get(
                "station_sequence"
            )
        )

        if sequence in (
            None,
            "",
        ):
            return None

        try:
            return int(
                sequence
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    return None


def get_hung_yen_sequence(
    trip_detail,
):
    return get_station_sequence(
        trip_detail=
            trip_detail,

        station_id=
            HUNG_YEN_SOC_ID,
    )


def get_all_hung_yen_inbound_loading(
    trip_id,
    trip_detail,
):
    hung_yen_sequence = (
        get_hung_yen_sequence(
            trip_detail
        )
    )

    if hung_yen_sequence is None:
        print(
            f"[Trip {trip_id}] "
            f"Không tìm thấy Hung Yen SOC "
            f"station_id={HUNG_YEN_SOC_ID}"
        )

        return []

    if hung_yen_sequence <= 1:
        print(
            f"[Trip {trip_id}] "
            f"Hung Yen SOC sequence="
            f"{hung_yen_sequence} "
            f"=> origin, không phải inbound"
        )

        return []

    print(
        f"[Trip {trip_id}] "
        f"Hung Yen SOC sequence="
        f"{hung_yen_sequence}"
    )

    return (
        get_all_inbound_loading(
            trip_id=
                trip_id,

            actual_unloaded_sequence_number=
                hung_yen_sequence,
        )
    )


def get_all_trip_loading(
    trip_id,
    loading_type="inbound",
    loaded_sequence_number=1,
    actual_unloaded_sequence_number=None,
    trip_detail=None,
    station_id=None,
):
    loading_type = str(
        loading_type
        or ""
    ).strip().lower()

    if loading_type == "outbound":
        return (
            get_all_outbound_loading(
                trip_id=
                    trip_id,

                loaded_sequence_number=
                    loaded_sequence_number,
            )
        )

    if loading_type != "inbound":
        raise RuntimeError(
            f"loading_type không hợp lệ: "
            f"{loading_type}"
        )

    sequence = (
        actual_unloaded_sequence_number
    )

    if (
        sequence is None
        and trip_detail is not None
    ):
        target_station_id = (
            station_id
            if station_id is not None
            else HUNG_YEN_SOC_ID
        )

        sequence = (
            get_station_sequence(
                trip_detail=
                    trip_detail,

                station_id=
                    target_station_id,
            )
        )

    if sequence is None:
        raise RuntimeError(
            "Không xác định được "
            "actual_unloaded_sequence_number"
        )

    return (
        get_all_inbound_loading(
            trip_id=
                trip_id,

            actual_unloaded_sequence_number=
                sequence,
        )
    )