from __future__ import annotations

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from config import BASE_URL

from core.spx_request import (
    spx_get,
)

from api.sheet.trip_sheet import (
    build_trip_row,
    push_trip_rows,
)

from api.sheet.trip_station_sheet import (
    build_trip_station_rows,
    push_trip_station_rows,
)


VN_TZ = timezone(
    timedelta(hours=7)
)

HUNG_YEN_SOC_ID = 3909

REALTIME_ENDPOINT = (
    BASE_URL
    + "/api/admin/transportation/"
    "trip/list_v2"
)

STATION_TYPES = (
    "2,3,7,12,14,16,18"
)


REALTIME_STATUSES = {
    50: "ARRIVED",
    60: "UNSEAL",
    80: "UNLOADED",
}


def parse_target_date(
    target_date=None,
) -> date:
    if target_date is None:
        return datetime.now(
            VN_TZ
        ).date()

    if isinstance(
        target_date,
        datetime,
    ):
        return target_date.astimezone(
            VN_TZ
        ).date()

    if isinstance(
        target_date,
        date,
    ):
        return target_date

    if isinstance(
        target_date,
        str,
    ):
        return datetime.strptime(
            target_date,
            "%Y-%m-%d",
        ).date()

    raise ValueError(
        "target_date không hợp lệ"
    )


def get_realtime_sta_range(
    target_date=None,
):
    """
    Range rộng hơn business window một chút
    để không bỏ mất trip có STA lệch
    nhưng thực tế ATA trong ngày vận hành.

    Day operation:
        06:00 -> 06:00 ngày hôm sau

    Query SPX:
        lấy rộng -12h / +12h
    """

    target_date = (
        parse_target_date(
            target_date
        )
    )

    business_start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        6,
        0,
        0,
        tzinfo=VN_TZ,
    )

    business_end = (
        business_start
        + timedelta(days=1)
    )

    query_start = (
        business_start
        - timedelta(hours=12)
    )

    query_end = (
        business_end
        + timedelta(hours=12)
    )

    return {
        "business_start":
            business_start,

        "business_end":
            business_end,

        "query_start":
            query_start,

        "query_end":
            query_end,

        "start_ts":
            int(
                query_start.timestamp()
            ),

        "end_ts":
            int(
                query_end.timestamp()
            ),
    }


def extract_rows(
    payload,
):
    if not isinstance(
        payload,
        dict,
    ):
        return (
            [],
            0,
        )

    data = payload.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return (
            [],
            0,
        )

    rows = (
        data.get(
            "list"
        )
        or []
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = []

    try:
        total = int(
            data.get(
                "total",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        total = 0

    return (
        rows,
        total,
    )


def has_hung_yen_station(
    trip,
):
    stations = (
        trip.get(
            "trip_station"
        )
        or []
    )

    if not isinstance(
        stations,
        list,
    ):
        return False

    for station in stations:
        if not isinstance(
            station,
            dict,
        ):
            continue

        station_id = (
            station.get(
                "station"
            )
            or station.get(
                "station_id"
            )
        )

        try:
            station_id = int(
                station_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            station_id
            == HUNG_YEN_SOC_ID
        ):
            return True

    return False


def get_hung_yen_station(
    trip,
):
    stations = (
        trip.get(
            "trip_station"
        )
        or []
    )

    if not isinstance(
        stations,
        list,
    ):
        return None

    candidates = []

    for station in stations:
        if not isinstance(
            station,
            dict,
        ):
            continue

        station_id = (
            station.get(
                "station"
            )
            or station.get(
                "station_id"
            )
        )

        try:
            station_id = int(
                station_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            station_id
            != HUNG_YEN_SOC_ID
        ):
            continue

        candidates.append(
            station
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: int(
            item.get(
                "sequence_number",
                0,
            )
            or 0
        ),
    )


def is_inbound_hung_yen(
    trip,
):
    station = (
        get_hung_yen_station(
            trip
        )
    )

    if station is None:
        return False

    try:
        sequence = int(
            station.get(
                "sequence_number",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        sequence > 1
    )


def realtime_page(
    trip_station_status,
    start_ts,
    end_ts,
    page_no=1,
    count=100,
):
    params = {
        "station_type":
            STATION_TYPES,

        "trip_station_status":
            int(
                trip_station_status
            ),

        "pageno":
            int(
                page_no
            ),

        "count":
            int(
                count
            ),

        "query_type":
            1,

        "tab_type":
            2,

        "sta":
            (
                f"{start_ts},"
                f"{end_ts}"
            ),
    }

    response = spx_get(
        REALTIME_ENDPOINT,
        params=params,
        timeout=60,
    )

    payload = (
        response.json()
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "Realtime response không hợp lệ"
        )

    if payload.get(
        "retcode"
    ) not in (
        None,
        0,
        "0",
    ):
        raise RuntimeError(
            payload.get(
                "message"
            )
            or (
                "Realtime SPX "
                f"status={trip_station_status} error"
            )
        )

    return payload


def crawl_realtime_status(
    trip_station_status,
    start_ts,
    end_ts,
    count=100,
    max_workers=5,
):
    status_name = (
        REALTIME_STATUSES.get(
            int(
                trip_station_status
            ),
            str(
                trip_station_status
            ),
        )
    )

    first_payload = (
        realtime_page(
            trip_station_status=
                trip_station_status,

            start_ts=
                start_ts,

            end_ts=
                end_ts,

            page_no=
                1,

            count=
                count,
        )
    )

    (
        first_rows,
        total,
    ) = extract_rows(
        first_payload
    )

    print(
        f"[REALTIME {status_name}] "
        f"PAGE 1 rows="
        f"{len(first_rows)} "
        f"total={total}"
    )

    if not first_rows:
        return []

    pages = {
        1: first_rows
    }

    if total > 0:
        total_pages = (
            total
            + count
            - 1
        ) // count
    else:
        total_pages = 1

    if total_pages > 1:
        worker_count = min(
            max(
                1,
                int(
                    max_workers
                ),
            ),
            total_pages - 1,
        )

        with ThreadPoolExecutor(
            max_workers=
                worker_count
        ) as executor:

            future_map = {
                executor.submit(
                    realtime_page,
                    trip_station_status,
                    start_ts,
                    end_ts,
                    page_no,
                    count,
                ):
                page_no

                for page_no
                in range(
                    2,
                    total_pages + 1,
                )
            }

            for future in as_completed(
                future_map
            ):
                page_no = (
                    future_map[
                        future
                    ]
                )

                payload = (
                    future.result()
                )

                rows, _ = (
                    extract_rows(
                        payload
                    )
                )

                pages[
                    page_no
                ] = rows

                print(
                    f"[REALTIME "
                    f"{status_name}] "
                    f"PAGE {page_no} "
                    f"rows={len(rows)}"
                )

    result = []

    seen = set()

    for page_no in sorted(
        pages
    ):
        for item in pages[
            page_no
        ]:
            if not isinstance(
                item,
                dict,
            ):
                continue

            trip_id = (
                item.get(
                    "id"
                )
                or item.get(
                    "trip_id"
                )
            )

            if not trip_id:
                continue

            trip_id = str(
                trip_id
            )

            if trip_id in seen:
                continue

            if not has_hung_yen_station(
                item
            ):
                continue

            if not is_inbound_hung_yen(
                item
            ):
                continue

            seen.add(
                trip_id
            )

            row = dict(
                item
            )

            row[
                "_trip_source"
            ] = (
                "REALTIME_"
                + status_name
            )

            row[
                "_realtime_status"
            ] = int(
                trip_station_status
            )

            result.append(
                row
            )

    print(
        f"[REALTIME {status_name}] "
        f"HY INBOUND="
        f"{len(result)}"
    )

    return result


def merge_realtime_trips(
    status_rows,
):
    """
    Nếu cùng trip xuất hiện nhiều nguồn:
        80 > 60 > 50

    Không downgrade trạng thái.
    """

    merged = {}

    for item in status_rows:
        if not isinstance(
            item,
            dict,
        ):
            continue

        trip_id = (
            item.get(
                "id"
            )
            or item.get(
                "trip_id"
            )
        )

        if not trip_id:
            continue

        key = str(
            trip_id
        )

        incoming_status = int(
            item.get(
                "_realtime_status",
                0,
            )
            or 0
        )

        old = merged.get(
            key
        )

        if old is None:
            merged[
                key
            ] = item
            continue

        old_status = int(
            old.get(
                "_realtime_status",
                0,
            )
            or 0
        )

        if (
            incoming_status
            >= old_status
        ):
            merged[
                key
            ] = item

    return list(
        merged.values()
    )


def build_realtime_sheet_rows(
    trips,
):
    trip_rows = []

    station_rows = []

    failed = []

    for item in trips:
        trip_id = (
            item.get(
                "id"
            )
            or item.get(
                "trip_id"
            )
        )

        trip_number = str(
            item.get(
                "trip_number",
                "",
            )
            or ""
        ).strip().upper()

        try:
            if not trip_id:
                raise RuntimeError(
                    "trip_id rỗng"
                )

            payload = {
                "retcode":
                    0,

                "message":
                    "",

                "data":
                    dict(
                        item
                    ),

                "_detail_endpoint":
                    item.get(
                        "_trip_source",
                        "REALTIME_LIST_V2",
                    ),
            }

            trip_row = (
                build_trip_row(
                    trip_id=
                        int(
                            trip_id
                        ),

                    trip_detail=
                        payload,
                )
            )

            current_station_rows = (
                build_trip_station_rows(
                    trip_id=
                        int(
                            trip_id
                        ),

                    trip_detail=
                        payload,
                )
            )

            if isinstance(
                trip_row,
                dict,
            ):
                trip_rows.append(
                    trip_row
                )

            if isinstance(
                current_station_rows,
                list,
            ):
                station_rows.extend(
                    current_station_rows
                )

        except Exception as exc:
            failed.append({
                "trip_id":
                    trip_id,

                "trip_number":
                    trip_number,

                "error":
                    str(
                        exc
                    ),
            })

    return {
        "trip_rows":
            trip_rows,

        "trip_station_rows":
            station_rows,

        "failed":
            failed,
    }


def sync_realtime_vehicle_trips(
    target_date=None,
    max_workers=5,
):
    range_info = (
        get_realtime_sta_range(
            target_date
        )
    )

    print()
    print("=" * 90)
    print(
        "REALTIME VEHICLE TRIP SYNC"
    )
    print(
        "QUERY FROM:",
        range_info[
            "query_start"
        ].isoformat(),
    )
    print(
        "QUERY TO:",
        range_info[
            "query_end"
        ].isoformat(),
    )
    print("=" * 90)

    all_status_rows = []

    for status in (
        50,
        60,
        80,
    ):
        rows = (
            crawl_realtime_status(
                trip_station_status=
                    status,

                start_ts=
                    range_info[
                        "start_ts"
                    ],

                end_ts=
                    range_info[
                        "end_ts"
                    ],

                count=
                    100,

                max_workers=
                    max_workers,
            )
        )

        all_status_rows.extend(
            rows
        )

    trips = (
        merge_realtime_trips(
            all_status_rows
        )
    )

    print()
    print(
        "REALTIME UNIQUE TRIPS:",
        len(
            trips
        ),
    )

    built = (
        build_realtime_sheet_rows(
            trips
        )
    )

    trip_rows = (
        built[
            "trip_rows"
        ]
    )

    trip_station_rows = (
        built[
            "trip_station_rows"
        ]
    )

    print(
        "REALTIME TRIP ROWS:",
        len(
            trip_rows
        ),
    )

    print(
        "REALTIME TRIP STATION ROWS:",
        len(
            trip_station_rows
        ),
    )

    trip_sheet_result = None

    station_sheet_result = None

    if trip_rows:
        trip_sheet_result = (
            push_trip_rows(
                trip_rows
            )
        )

    if trip_station_rows:
        station_sheet_result = (
            push_trip_station_rows(
                trip_station_rows
            )
        )

    print()
    print("=" * 90)
    print(
        "REALTIME VEHICLE SYNC COMPLETE"
    )
    print(
        "TRIPS:",
        len(
            trips
        ),
    )
    print(
        "FAILED:",
        len(
            built[
                "failed"
            ]
        ),
    )
    print("=" * 90)

    return {
        "success":
            True,

        "trip_count":
            len(
                trips
            ),

        "trip_rows":
            len(
                trip_rows
            ),

        "trip_station_rows":
            len(
                trip_station_rows
            ),

        "failed":
            built[
                "failed"
            ],

        "trip_sheet":
            trip_sheet_result,

        "trip_station_sheet":
            station_sheet_result,

        "range": {
            "from":
                range_info[
                    "query_start"
                ].isoformat(),

            "to":
                range_info[
                    "query_end"
                ].isoformat(),
        },
    }