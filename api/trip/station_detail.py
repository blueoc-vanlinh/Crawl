from config import BASE_URL
from core.spx_request import spx_get


TRIP_HISTORY_DETAIL_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/detail"
)

TRIP_DETAIL_V2_API = (
    BASE_URL
    + "/api/admin/transportation/trip/detail_v2"
)


def _request_trip_detail(
    url,
    trip_id,
):
    params = {
        "trip_id": trip_id,
        "new_process_switch": "false",
    }

    response = spx_get(
        url,
        params=params,
        timeout=60,
    )

    data = response.json()

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            f"Trip detail response không hợp lệ: {trip_id}"
        )

    if (
        data.get("retcode")
        not in (
            None,
            0,
            "0",
        )
    ):
        raise RuntimeError(
            data.get(
                "message",
                f"SPX trip detail error: {trip_id}",
            )
        )

    payload = (
        data.get("data")
        or {}
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            f"Trip detail data không hợp lệ: {trip_id}"
        )

    if not payload:
        raise RuntimeError(
            f"Không có trip detail: {trip_id}"
        )

    return payload


def get_trip_detail_data(
    trip_id,
):
    if trip_id in (
        None,
        "",
    ):
        raise ValueError(
            "trip_id không được để trống"
        )

    history_error = None

    try:
        return _request_trip_detail(
            TRIP_HISTORY_DETAIL_API,
            trip_id,
        )

    except Exception as exc:
        history_error = exc

    try:
        return _request_trip_detail(
            TRIP_DETAIL_V2_API,
            trip_id,
        )

    except Exception as detail_v2_error:
        raise RuntimeError(
            f"Không lấy được trip detail "
            f"trip_id={trip_id} | "
            f"history={history_error} | "
            f"detail_v2={detail_v2_error}"
        ) from detail_v2_error


def get_trip_stations(
    trip_id,
):
    detail = get_trip_detail_data(
        trip_id
    )

    stations = (
        detail.get("trip_station")
        or []
    )

    if not isinstance(
        stations,
        list,
    ):
        return []

    return [
        station
        for station in stations
        if isinstance(
            station,
            dict,
        )
    ]


def get_station_detail(
    trip_id,
    station_id=None,
    sequence_number=None,
):
    if (
        station_id in (
            None,
            "",
        )
        and sequence_number in (
            None,
            "",
        )
    ):
        raise ValueError(
            "Phải truyền station_id hoặc sequence_number"
        )

    stations = get_trip_stations(
        trip_id
    )

    station_id_text = (
        str(station_id).strip()
        if station_id not in (
            None,
            "",
        )
        else None
    )

    sequence_text = (
        str(sequence_number).strip()
        if sequence_number not in (
            None,
            "",
        )
        else None
    )

    for station in stations:
        current_station_id = (
            station.get("station")
        )

        if current_station_id in (
            None,
            "",
        ):
            station_info = (
                station.get("station_info")
                or {}
            )

            if isinstance(
                station_info,
                dict,
            ):
                current_station_id = (
                    station_info.get("id")
                )

        current_sequence = (
            station.get(
                "sequence_number"
            )
        )

        station_match = True
        sequence_match = True

        if station_id_text is not None:
            station_match = (
                str(
                    current_station_id
                ).strip()
                == station_id_text
            )

        if sequence_text is not None:
            sequence_match = (
                str(
                    current_sequence
                ).strip()
                == sequence_text
            )

        if (
            station_match
            and sequence_match
        ):
            return station

    return {}


def get_station_data(
    trip_id,
    station_id=None,
    sequence_number=None,
):
    station = get_station_detail(
        trip_id=trip_id,
        station_id=station_id,
        sequence_number=sequence_number,
    )

    if not station:
        return {}

    station_info = (
        station.get(
            "station_info"
        )
        or {}
    )

    if not isinstance(
        station_info,
        dict,
    ):
        station_info = {}

    result = dict(
        station_info
    )

    result.update(
        {
            "trip_id":
                trip_id,

            "sequence_number":
                station.get(
                    "sequence_number"
                ),

            "station":
                station.get(
                    "station"
                ),

            "station_name":
                station.get(
                    "station_name"
                ),

            "station_code":
                station.get(
                    "station_code"
                ),

            "station_type":
                station.get(
                    "station_type"
                ),

            "group_name":
                station.get(
                    "group_name"
                ),

            "sta":
                station.get(
                    "sta"
                ),

            "std":
                station.get(
                    "std"
                ),

            "ata":
                station.get(
                    "ata"
                ),

            "atd":
                station.get(
                    "atd"
                ),

            "trip_station_status":
                station.get(
                    "trip_station_status"
                ),

            "trip_driver_status":
                station.get(
                    "trip_driver_status"
                ),

            "load_quantity":
                station.get(
                    "load_quantity"
                ),

            "unload_quantity":
                station.get(
                    "unload_quantity"
                ),

            "expect_unload_quantity":
                station.get(
                    "expect_unload_quantity"
                ),

            "abnormal_unload_quantity":
                station.get(
                    "abnormal_unload_quantity"
                ),

            "transport_quantity":
                station.get(
                    "transport_quantity"
                ),

            "capacity_quantity":
                station.get(
                    "capacity_quantity"
                ),

            "loading_time":
                station.get(
                    "loading_time"
                ),

            "loaded_time":
                station.get(
                    "loaded_time"
                ),

            "seal_time":
                station.get(
                    "seal_time"
                ),

            "seal_code":
                station.get(
                    "seal_code"
                ),

            "unseal_time":
                station.get(
                    "unseal_time"
                ),

            "unloading_time":
                station.get(
                    "unloading_time"
                ),

            "unloaded_time":
                station.get(
                    "unloaded_time"
                ),

            "queuing_time":
                station.get(
                    "queuing_time"
                ),

            "assign_time":
                station.get(
                    "assign_time"
                ),

            "total_weight":
                station.get(
                    "total_weight"
                ),

            "actual_weight":
                station.get(
                    "actual_weight"
                ),

            "volume_weight":
                station.get(
                    "volume_weight"
                ),

            "operate_logs":
                station.get(
                    "operate_logs"
                )
                or [],

            "unloading_docked_logs":
                station.get(
                    "unloading_docked_logs"
                )
                or [],

            "loading_docked_logs":
                station.get(
                    "loading_docked_logs"
                )
                or [],

            "inbound_dock_infos":
                station.get(
                    "inbound_dock_infos"
                )
                or [],

            "outbound_dock_infos":
                station.get(
                    "outbound_dock_infos"
                )
                or [],
        }
    )

    return result