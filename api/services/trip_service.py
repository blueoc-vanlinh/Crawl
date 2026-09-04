from __future__ import annotations

import time

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

from config import BASE_URL

from core.spx_request import (
    spx_get,
)

from api.order.daily_trip_sync import (
    sync_two_day_trips,
)

from api.sheet.trip_sheet import (
    build_trip_row,
    push_trip_rows,
)

from api.sheet.to_sheet import (
    build_to_rows,
    push_to_rows,
)


VN_TZ = timezone(
    timedelta(
        hours=7,
    )
)


TRIP_HISTORY_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/list"
)


def extract_list(
    data,
):
    if not isinstance(
        data,
        dict,
    ):
        return []

    payload = data.get(
        "data"
    )

    if isinstance(
        payload,
        list,
    ):
        return payload

    if isinstance(
        payload,
        dict,
    ):
        for key in (
            "list",
            "items",
            "rows",
            "records",
        ):
            value = payload.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return value

    for key in (
        "list",
        "items",
        "rows",
        "records",
    ):
        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return value

    return []


def _extract_rows_total(
    data,
):
    if not isinstance(
        data,
        dict,
    ):
        return (
            [],
            0,
        )

    payload = (
        data.get(
            "data"
        )
        or {}
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            [],
            0,
        )

    rows = (
        payload.get(
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
            payload.get(
                "total"
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


def get_completed_trip_page(
    mtime_start,
    mtime_end,
    page=1,
    count=100,
):
    try:
        page = int(
            page
        )

    except (
        TypeError,
        ValueError,
    ):
        page = 1

    if page < 1:
        page = 1

    try:
        count = int(
            count
        )

    except (
        TypeError,
        ValueError,
    ):
        count = 100

    count = max(
        1,
        min(
            count,
            100,
        ),
    )

    params = {
        "trip_station_status":
            90,

        "mtime":
            (
                f"{int(mtime_start)},"
                f"{int(mtime_end)}"
            ),

        "pageno":
            page,

        "count":
            count,
    }

    response = spx_get(
        TRIP_HISTORY_API,
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
            "SPX Trip History trả dữ liệu không hợp lệ"
        )

    retcode = payload.get(
        "retcode"
    )

    if retcode not in (
        None,
        0,
        "0",
    ):
        raise RuntimeError(
            payload.get(
                "message"
            )
            or (
                "SPX Trip History "
                f"retcode={retcode}"
            )
        )

    return payload


def get_all_completed_trips(
    mtime_start,
    mtime_end,
    count=100,
    max_workers=5,
):
    try:
        count = int(
            count
        )

    except (
        TypeError,
        ValueError,
    ):
        count = 100

    count = max(
        1,
        min(
            count,
            100,
        ),
    )

    try:
        max_workers = int(
            max_workers
        )

    except (
        TypeError,
        ValueError,
    ):
        max_workers = 5

    max_workers = max(
        1,
        min(
            max_workers,
            5,
        ),
    )

    first_data = (
        get_completed_trip_page(
            mtime_start=
                mtime_start,

            mtime_end=
                mtime_end,

            page=
                1,

            count=
                count,
        )
    )

    (
        first_rows,
        total,
    ) = _extract_rows_total(
        first_data
    )

    print(
        "[TRIP HISTORY COMPLETED] "
        f"page=1 "
        f"rows={len(first_rows)} "
        f"total={total}"
    )

    if not first_rows:
        print(
            "[TRIP HISTORY COMPLETED DONE] "
            "pages=1 "
            "received=0 "
            "unique=0 "
            f"total={total}"
        )

        return []

    if total > 0:
        total_pages = (
            total
            + count
            - 1
        ) // count

    else:
        total_pages = 1

    page_results = {
        1:
            first_rows,
    }

    if total_pages > 1:
        worker_count = min(
            max_workers,
            total_pages - 1,
        )

        print(
            "[TRIP HISTORY COMPLETED] "
            f"pages={total_pages} "
            f"workers={worker_count}"
        )

        with ThreadPoolExecutor(
            max_workers=
                worker_count
        ) as executor:

            future_map = {
                executor.submit(
                    get_completed_trip_page,
                    mtime_start,
                    mtime_end,
                    page,
                    count,
                ):
                    page

                for page in range(
                    2,
                    total_pages + 1,
                )
            }

            for future in as_completed(
                future_map
            ):
                page = future_map[
                    future
                ]

                data = (
                    future.result()
                )

                (
                    rows,
                    current_total,
                ) = _extract_rows_total(
                    data
                )

                if (
                    current_total
                    > total
                ):
                    total = (
                        current_total
                    )

                page_results[
                    page
                ] = rows

                print(
                    "[TRIP HISTORY COMPLETED] "
                    f"page={page} "
                    f"rows={len(rows)}"
                )

    result = []

    seen_trip_keys = set()
    seen_page_signatures = set()

    received = 0

    for page in sorted(
        page_results
    ):
        rows = (
            page_results[
                page
            ]
        )

        received += len(
            rows
        )

        page_signature = tuple(
            (
                str(
                    item.get(
                        "id"
                    )
                    or item.get(
                        "trip_id"
                    )
                    or ""
                ),
                str(
                    item.get(
                        "trip_number"
                    )
                    or ""
                ),
            )
            for item in rows
            if isinstance(
                item,
                dict,
            )
        )

        if (
            page_signature
            in seen_page_signatures
        ):
            print(
                "[TRIP HISTORY COMPLETED] "
                f"page={page} "
                "repeated page skipped"
            )

            continue

        seen_page_signatures.add(
            page_signature
        )

        for item in rows:
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

            trip_number = str(
                item.get(
                    "trip_number",
                    "",
                )
                or ""
            ).strip().upper()

            if trip_id:
                trip_key = (
                    f"ID:{trip_id}"
                )

            elif trip_number:
                trip_key = (
                    f"NUMBER:{trip_number}"
                )

            else:
                continue

            if (
                trip_key
                in seen_trip_keys
            ):
                continue

            seen_trip_keys.add(
                trip_key
            )

            row = dict(
                item
            )

            row[
                "_trip_source"
            ] = (
                "HISTORY_COMPLETED"
            )

            result.append(
                row
            )

    print(
        "[TRIP HISTORY COMPLETED DONE] "
        f"pages={len(page_results)} "
        f"received={received} "
        f"unique={len(result)} "
        f"total={total}"
    )

    return result


def get_crawl_range(
    target_date=None,
):
    if target_date is None:
        target = (
            datetime.now(
                VN_TZ
            ).date()
        )

    elif isinstance(
        target_date,
        datetime,
    ):
        if (
            target_date.tzinfo
            is None
        ):
            target_date = (
                target_date.replace(
                    tzinfo=
                        VN_TZ
                )
            )

        target = (
            target_date
            .astimezone(
                VN_TZ
            )
            .date()
        )

    elif isinstance(
        target_date,
        date,
    ):
        target = (
            target_date
        )

    else:
        target = (
            datetime.strptime(
                str(
                    target_date
                ).strip(),
                "%Y-%m-%d",
            ).date()
        )

    start_date = (
        target
        - timedelta(
            days=3
        )
    )

    start_datetime = datetime(
        start_date.year,
        start_date.month,
        start_date.day,
        0,
        0,
        0,
        tzinfo=
            VN_TZ,
    )

    end_datetime = datetime(
        target.year,
        target.month,
        target.day,
        23,
        59,
        59,
        tzinfo=
            VN_TZ,
    )

    return {
        "target_date":
            target,

        "start_date":
            start_date,

        "start_datetime":
            start_datetime,

        "end_datetime":
            end_datetime,

        "start_ts":
            int(
                start_datetime
                .timestamp()
            ),

        "end_ts":
            int(
                end_datetime
                .timestamp()
            ),
    }


def crawl_trip_by_date(
    target_date=None,
    max_workers=5,
):
    range_info = (
        get_crawl_range(
            target_date
        )
    )

    try:
        max_workers = int(
            max_workers
        )

    except (
        TypeError,
        ValueError,
    ):
        max_workers = 5

    max_workers = max(
        1,
        min(
            max_workers,
            5,
        ),
    )

    print()
    print(
        "=" * 90
    )

    print(
        "CRAWL TRIP HISTORY COMPLETED"
    )

    print(
        "TARGET:",
        range_info[
            "target_date"
        ].isoformat(),
    )

    print(
        "FROM:",
        range_info[
            "start_datetime"
        ].isoformat(),
    )

    print(
        "TO:",
        range_info[
            "end_datetime"
        ].isoformat(),
    )

    print(
        "FILTER:",
        "trip_station_status=90",
    )

    print(
        "WORKERS:",
        max_workers,
    )

    print(
        "=" * 90
    )

    trips = (
        get_all_completed_trips(
            mtime_start=
                range_info[
                    "start_ts"
                ],

            mtime_end=
                range_info[
                    "end_ts"
                ],

            count=
                100,

            max_workers=
                max_workers,
        )
    )

    return {
        "success":
            True,

        "date":
            range_info[
                "target_date"
            ].isoformat(),

        "from":
            range_info[
                "start_datetime"
            ].isoformat(),

        "to":
            range_info[
                "end_datetime"
            ].isoformat(),

        "total":
            len(
                trips
            ),

        "trips":
            trips,
    }


def resolve_trip_number_to_id(
    trip_number,
):
    trip_number = str(
        trip_number
        or ""
    ).strip().upper()

    if not trip_number:
        raise RuntimeError(
            "Trip number rỗng"
        )

    if trip_number.isdigit():
        return int(
            trip_number
        )

    if not trip_number.startswith(
        "LT"
    ):
        raise RuntimeError(
            f"Trip không hợp lệ: "
            f"{trip_number}"
        )

    end_ts = int(
        time.time()
    )

    start_ts = (
        end_ts
        - (
            90
            * 24
            * 60
            * 60
        )
    )

    params = {
        "trip_number":
            trip_number,

        "mtime":
            (
                f"{start_ts},"
                f"{end_ts}"
            ),

        "pageno":
            1,

        "count":
            100,
    }

    response = spx_get(
        TRIP_HISTORY_API,
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
            "Trip history trả dữ liệu không hợp lệ"
        )

    retcode = payload.get(
        "retcode"
    )

    if retcode not in (
        None,
        0,
        "0",
    ):
        raise RuntimeError(
            payload.get(
                "message"
            )
            or (
                "Trip history "
                f"retcode={retcode}"
            )
        )

    data = (
        payload.get(
            "data"
        )
        or {}
    )

    if not isinstance(
        data,
        dict,
    ):
        data = {}

    items = (
        data.get(
            "list"
        )
        or []
    )

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        item_trip_number = str(
            item.get(
                "trip_number",
                "",
            )
            or ""
        ).strip().upper()

        if (
            item_trip_number
            != trip_number
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

        if trip_id:
            try:
                return int(
                    trip_id
                )

            except (
                TypeError,
                ValueError,
            ):
                return trip_id

    raise RuntimeError(
        f"Không tìm thấy trip_id "
        f"cho {trip_number}"
    )


def resolve_trip_identifier(
    value,
):
    value = str(
        value
        or ""
    ).strip().upper()

    if not value:
        raise RuntimeError(
            "Trip ID / Trip number rỗng"
        )

    if value.isdigit():
        return int(
            value
        )

    return (
        resolve_trip_number_to_id(
            value
        )
    )


def get_trip_detail_data(
    trip_id,
):
    trip_id = (
        resolve_trip_identifier(
            trip_id
        )
    )

    endpoints = [
        (
            BASE_URL
            + "/api/admin/transportation/trip/history/detail",
            {
                "trip_id":
                    trip_id,

                "new_process_switch":
                    "false",
            },
        ),
        (
            BASE_URL
            + "/api/admin/transportation/trip/detail_v2",
            {
                "trip_id":
                    trip_id,

                "new_process_switch":
                    "false",
            },
        ),
    ]

    last_error = None

    for (
        url,
        params,
    ) in endpoints:

        try:
            response = spx_get(
                url,
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
                    "Trip detail trả dữ liệu không hợp lệ"
                )

            retcode = payload.get(
                "retcode"
            )

            if retcode not in (
                None,
                0,
                "0",
            ):
                raise RuntimeError(
                    payload.get(
                        "message"
                    )
                    or (
                        "Trip detail "
                        f"retcode={retcode}"
                    )
                )

            return payload

        except Exception as e:
            last_error = e

    raise RuntimeError(
        "Không lấy được Trip Detail: "
        f"{last_error}"
    )


def get_trip_loading_data(
    trip_id,
    direction="outbound",
    sequence=1,
):
    trip_id = (
        resolve_trip_identifier(
            trip_id
        )
    )

    direction = str(
        direction
        or "outbound"
    ).strip().lower()

    if direction not in (
        "outbound",
        "inbound",
    ):
        raise ValueError(
            "direction phải là "
            "outbound hoặc inbound"
        )

    try:
        sequence = int(
            sequence
        )

    except (
        TypeError,
        ValueError,
    ):
        sequence = 1

    if sequence < 1:
        sequence = 1

    url = (
        BASE_URL
        + "/api/admin/transportation/trip/history/loading/list"
    )

    all_items = []

    page = 1
    count = 2000

    seen_page_signatures = set()

    while True:
        params = {
            "trip_id":
                trip_id,

            "pageno":
                page,

            "count":
                count,

            "type":
                direction,
        }

        if (
            direction
            == "outbound"
        ):
            params[
                "loaded_sequence_number"
            ] = (
                sequence
            )

        else:
            params[
                "actual_unloaded_sequence_number"
            ] = (
                sequence
            )

        response = spx_get(
            url,
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
                "Trip loading trả dữ liệu không hợp lệ"
            )

        retcode = payload.get(
            "retcode"
        )

        if retcode not in (
            None,
            0,
            "0",
        ):
            raise RuntimeError(
                payload.get(
                    "message"
                )
                or (
                    "Trip loading "
                    f"retcode={retcode}"
                )
            )

        data = (
            payload.get(
                "data"
            )
            or {}
        )

        if not isinstance(
            data,
            dict,
        ):
            break

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
                    "total"
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            total = 0

        if not rows:
            break

        signature = tuple(
            str(
                item.get(
                    "scan_number"
                )
                or item.get(
                    "to_number"
                )
                or item.get(
                    "shipment_id"
                )
                or item.get(
                    "id"
                )
                or ""
            )
            for item in rows
            if isinstance(
                item,
                dict,
            )
        )

        if (
            signature
            in seen_page_signatures
        ):
            print(
                "[TRIP LOADING] "
                f"page={page} "
                "repeated skipped"
            )

            break

        seen_page_signatures.add(
            signature
        )

        all_items.extend(
            rows
        )

        if (
            total > 0
            and len(
                all_items
            ) >= total
        ):
            break

        if (
            len(
                rows
            ) < count
            and total <= 0
        ):
            break

        page += 1

    return {
        "retcode":
            0,

        "data": {
            "list":
                all_items,

            "total":
                len(
                    all_items
                ),
        },
    }


def get_trip_editing_data(
    trip_id,
):
    trip_id = (
        resolve_trip_identifier(
            trip_id
        )
    )

    endpoints = [
        (
            BASE_URL
            + "/api/admin/transportation/trip/editing/detail",
            {
                "trip_id":
                    trip_id,
            },
        ),
        (
            BASE_URL
            + "/api/admin/transportation/trip/edit/detail",
            {
                "trip_id":
                    trip_id,
            },
        ),
    ]

    last_error = None

    for (
        url,
        params,
    ) in endpoints:

        try:
            response = spx_get(
                url,
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
                    "Trip editing trả dữ liệu không hợp lệ"
                )

            retcode = payload.get(
                "retcode"
            )

            if retcode not in (
                None,
                0,
                "0",
            ):
                raise RuntimeError(
                    payload.get(
                        "message"
                    )
                    or (
                        "Trip editing "
                        f"retcode={retcode}"
                    )
                )

            return payload

        except Exception as e:
            last_error = e

    raise RuntimeError(
        "Không lấy được Trip Editing: "
        f"{last_error}"
    )


def get_trip_seal_data(
    trip_id,
):
    trip_id = (
        resolve_trip_identifier(
            trip_id
        )
    )

    endpoints = [
        (
            BASE_URL
            + "/api/admin/transportation/trip/seal/detail",
            {
                "trip_id":
                    trip_id,
            },
        ),
        (
            BASE_URL
            + "/api/admin/transportation/trip/seal/report/detail",
            {
                "trip_id":
                    trip_id,
            },
        ),
    ]

    last_error = None

    for (
        url,
        params,
    ) in endpoints:

        try:
            response = spx_get(
                url,
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
                    "Trip seal trả dữ liệu không hợp lệ"
                )

            retcode = payload.get(
                "retcode"
            )

            if retcode not in (
                None,
                0,
                "0",
            ):
                raise RuntimeError(
                    payload.get(
                        "message"
                    )
                    or (
                        "Trip seal "
                        f"retcode={retcode}"
                    )
                )

            return payload

        except Exception as e:
            last_error = e

    raise RuntimeError(
        "Không lấy được Trip Seal: "
        f"{last_error}"
    )


def push_to_sheet(
    trip_rows=None,
    to_rows=None,
):
    trip_rows = (
        trip_rows
        or []
    )

    to_rows = (
        to_rows
        or []
    )

    trip_result = {
        "inserted":
            0,

        "updated":
            0,

        "unchanged":
            0,

        "skipped":
            0,
    }

    to_result = {
        "inserted":
            0,

        "updated":
            0,

        "unchanged":
            0,

        "skipped":
            0,
    }

    if trip_rows:
        trip_result = (
            push_trip_rows(
                trip_rows
            )
        )

    if to_rows:
        to_result = (
            push_to_rows(
                to_rows
            )
        )

    return {
        "trip":
            trip_result,

        "to":
            to_result,
    }


def sync_trips(
    target_date=None,
    trip_wait_seconds=0,
    max_workers=5,
):
    try:
        max_workers = int(
            max_workers
        )

    except (
        TypeError,
        ValueError,
    ):
        max_workers = 5

    max_workers = max(
        1,
        min(
            max_workers,
            5,
        ),
    )

    return (
        sync_two_day_trips(
            target_date=
                target_date,

            trip_wait_seconds=
                trip_wait_seconds,

            max_workers=
                max_workers,
        )
    )