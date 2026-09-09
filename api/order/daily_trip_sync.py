from __future__ import annotations

import threading
import time
import traceback

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

from typing import Any

from config import BASE_URL
from core.spx_request import spx_get

from api.to.scanto import (
    scan_to_orders,
)

from api.sheet.trip_sheet import (
    build_trip_row,
    push_trip_rows,
)

from api.sheet.trip_station_sheet import (
    build_trip_station_rows,
    push_trip_station_rows,
)

from api.sheet.to_sheet import (
    build_to_rows,
    push_to_rows,
)

from api.sheet.to_order_sheet import (
    build_to_order_rows_from_scan,
    get_shipment_ids_from_to_order_rows,
    push_to_order_rows,
)


VN_TZ = timezone(
    timedelta(
        hours=7
    )
)


TO_CACHE = {}
TO_CACHE_LOCK = threading.Lock()
TO_INFLIGHT = {}

TRIP_BATCH_SIZE = 2000
TRIP_BATCH_SLEEP = 10
TO_BATCH_SIZE = 2000
TO_BATCH_SLEEP = 10
ORDER_ROW_BATCH_SIZE = 2000
ORDER_ROW_BATCH_SLEEP = 20

SCAN_TO_RATE_LOCK = threading.Lock()
SCAN_TO_API_STARTED = 0
ORDER_ROW_RATE_LOCK = threading.Lock()
ORDER_ROWS_EMITTED = 0


def reset_to_cache():
    global TO_CACHE
    global TO_INFLIGHT
    global SCAN_TO_API_STARTED
    global ORDER_ROWS_EMITTED

    with TO_CACHE_LOCK:
        TO_CACHE = {}
        TO_INFLIGHT = {}

    with SCAN_TO_RATE_LOCK:
        SCAN_TO_API_STARTED = 0

    with ORDER_ROW_RATE_LOCK:
        ORDER_ROWS_EMITTED = 0


def extract_list(
    data: Any,
) -> list[dict]:
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
        return [
            item
            for item in payload
            if isinstance(
                item,
                dict,
            )
        ]

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
                return [
                    item
                    for item in value
                    if isinstance(
                        item,
                        dict,
                    )
                ]

    return []



def get_trip_detail_data(
    trip_id: int,
    trip_source: str = "",
) -> dict:
    source = str(
        trip_source
        or ""
    ).strip().upper()

    history_endpoint = (
        "/api/admin/transportation/"
        "trip/history/detail"
    )

    handover_endpoint = (
        "/api/admin/transportation/"
        "trip/detail_v2"
    )

    if "HANDOVER" in source:
        endpoints = [
            (
                "DETAIL_V2",
                handover_endpoint,
            ),
            (
                "HISTORY_DETAIL",
                history_endpoint,
            ),
        ]
    else:
        endpoints = [
            (
                "HISTORY_DETAIL",
                history_endpoint,
            ),
            (
                "DETAIL_V2",
                handover_endpoint,
            ),
        ]

    errors = []

    for (
        endpoint_name,
        endpoint,
    ) in endpoints:
        url = (
            BASE_URL
            + endpoint
        )

        try:
            response = spx_get(
                url,
                params={
                    "trip_id":
                        trip_id,

                    "new_process_switch":
                        "false",
                },
                timeout=30,
            )

            payload = (
                response.json()
            )

            if not isinstance(
                payload,
                dict,
            ):
                errors.append(
                    f"{endpoint_name}: "
                    f"response không phải dict"
                )
                continue

            retcode = payload.get(
                "retcode"
            )

            data = payload.get(
                "data"
            )

            if (
                retcode
                not in (
                    None,
                    0,
                )
            ):
                errors.append(
                    f"{endpoint_name}: "
                    f"{payload.get('message') or 'SPX error'}"
                )
                continue

            if not isinstance(
                data,
                dict,
            ):
                errors.append(
                    f"{endpoint_name}: "
                    f"data rỗng"
                )
                continue

            if not (
                data.get("id")
                or data.get("trip_id")
                or data.get("trip_number")
                or data.get("trip_station")
            ):
                errors.append(
                    f"{endpoint_name}: "
                    f"không có trip data"
                )
                continue

            result = dict(
                payload
            )

            result[
                "_detail_endpoint"
            ] = endpoint_name

            print(
                f"[Trip {trip_id}] "
                f"DETAIL OK: "
                f"{endpoint_name}"
            )

            return result

        except Exception as e:
            errors.append(
                f"{endpoint_name}: "
                f"{e}"
            )

    raise RuntimeError(
        f"Trip {trip_id} "
        f"không lấy được detail | "
        + " | ".join(
            errors
        )
    )



def get_trip_loading_data(
    trip_id: int,
    direction: str = "outbound",
    sequence: int = 1,
) -> dict:
    direction = str(
        direction
        or ""
    ).strip().lower()

    if direction not in (
        "outbound",
        "inbound",
    ):
        raise RuntimeError(
            f"direction không hợp lệ: "
            f"{direction}"
        )

    try:
        sequence = int(
            sequence
        )
    except (
        TypeError,
        ValueError,
    ):
        raise RuntimeError(
            f"sequence không hợp lệ: "
            f"{sequence}"
        )

    all_items = []
    page_no = 1
    count = 2000

    while True:
        params = {
            "trip_id":
                trip_id,

            "pageno":
                page_no,

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
            ] = sequence

        else:
            params[
                "actual_unloaded_sequence_number"
            ] = sequence

        url = (
            BASE_URL
            + "/api/admin/transportation/"
            "trip/history/loading/list"
        )

        response = spx_get(
            url,
            params=params,
            timeout=60,
        )

        data = response.json()

        if (
            data.get(
                "retcode"
            )
            != 0
        ):
            raise RuntimeError(
                data.get(
                    "message",
                    "Trip loading error",
                )
            )

        payload = data.get(
            "data",
            {},
        )

        rows = (
            payload.get(
                "list",
                [],
            )
            if isinstance(
                payload,
                dict,
            )
            else []
        )

        total = int(
            payload.get(
                "total",
                0,
            )
            or 0
        )

        if not rows:
            break

        all_items.extend(
            rows
        )

        print(
            f"[Trip {trip_id}] "
            f"{direction.upper()} "
            f"sequence={sequence} "
            f"page={page_no} "
            f"received={len(rows)} "
            f"collected={len(all_items)} "
            f"total={total}"
        )

        if (
            total > 0
            and len(
                all_items
            )
            >= total
        ):
            break

        if (
            len(
                rows
            )
            < count
        ):
            break

        page_no += 1

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


def get_trip_station_sequence(
    trip_detail: dict,
    station_id: int = 3909,
) -> int | None:
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
            or (
                station.get(
                    "station_info",
                    {},
                ).get(
                    "id"
                )
                if isinstance(
                    station.get(
                        "station_info"
                    ),
                    dict,
                )
                else ""
            )
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


def get_auto_loading_context(
    trip_detail: dict,
    fallback_direction: str = "outbound",
    fallback_sequence: int = 1,
    station_id: int = 3909,
) -> tuple[str, int]:
    sequence = (
        get_trip_station_sequence(
            trip_detail=
                trip_detail,

            station_id=
                station_id,
        )
    )

    if sequence is None:
        return (
            fallback_direction,
            fallback_sequence,
        )

    if sequence <= 1:
        return (
            "outbound",
            sequence,
        )

    return (
        "inbound",
        sequence,
    )


def get_one_day_range(
    target_date=None,
):
    if target_date is None:
        target_date = (
            datetime.now(VN_TZ)
            .date()
        )

    elif isinstance(
        target_date,
        str,
    ):
        target_date = (
            datetime.strptime(
                target_date,
                "%Y-%m-%d",
            )
            .date()
        )

    start_datetime = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        0,
        0,
        0,
        tzinfo=VN_TZ,
    )

    end_datetime = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        23,
        59,
        59,
        tzinfo=VN_TZ,
    )

    return {
        "target_date":
            target_date,

        "previous_date":
            target_date,

        "start_date":
            target_date,

        "start_datetime":
            start_datetime,

        "end_datetime":
            end_datetime,

        "start_ts":
            int(
                start_datetime.timestamp()
            ),

        "end_ts":
            int(
                end_datetime.timestamp()
            ),
    }



def get_two_day_range(
    target_date=None,
):
    return get_one_day_range(
        target_date
    )


def get_four_day_range(
    target_date=None,
):
    if target_date is None:
        target_date = (
            datetime.now(VN_TZ)
            .date()
        )

    elif isinstance(
        target_date,
        str,
    ):
        target_date = (
            datetime.strptime(
                target_date,
                "%Y-%m-%d",
            )
            .date()
        )

    elif not isinstance(
        target_date,
        date,
    ):
        raise ValueError(
            "target_date không hợp lệ"
        )

    start_date = (
        target_date
        - timedelta(days=3)
    )

    start_datetime = datetime(
        start_date.year,
        start_date.month,
        start_date.day,
        0,
        0,
        0,
        tzinfo=VN_TZ,
    )

    end_datetime = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        23,
        59,
        59,
        tzinfo=VN_TZ,
    )

    return {
        "target_date":
            target_date,
        "start_date":
            start_date,
        "start_datetime":
            start_datetime,
        "end_datetime":
            end_datetime,
        "start_ts":
            int(
                start_datetime.timestamp()
            ),
        "end_ts":
            int(
                end_datetime.timestamp()
            ),
    }


def get_trip_key(
    item: dict,
) -> str:
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
        return (
            f"ID:{trip_id}"
        )

    if trip_number:
        return (
            f"NUMBER:{trip_number}"
        )

    return ""



def crawl_trip_endpoint(
    endpoint: str,
    loading_start_ts: int | None = None,
    loading_end_ts: int | None = None,
    mtime_start_ts: int | None = None,
    mtime_end_ts: int | None = None,
    query_type: int | None = None,
    count: int = 100,
    source_name: str = "",
) -> list[dict]:
    url = (
        BASE_URL
        + endpoint
    )

    page_no = 1
    all_trips = []
    seen = set()
    seen_page_signatures = set()
    raw_received = 0
    server_total = 0

    try:
        count = int(
            count
        )
    except (
        TypeError,
        ValueError,
    ):
        count = 100

    if count < 1:
        count = 100

    while True:
        params = {
            "pageno":
                page_no,

            "count":
                count,
        }

        if (
            loading_start_ts
            is not None
            and loading_end_ts
            is not None
        ):
            params[
                "loading_time"
            ] = (
                f"{loading_start_ts},"
                f"{loading_end_ts}"
            )

        if (
            mtime_start_ts
            is not None
            and mtime_end_ts
            is not None
        ):
            params[
                "mtime"
            ] = (
                f"{mtime_start_ts},"
                f"{mtime_end_ts}"
            )

        if query_type is not None:
            params[
                "query_type"
            ] = query_type

        print(
            f"{source_name} PAGE: "
            f"{page_no} | "
            f"PARAMS: {params}"
        )

        response = spx_get(
            url,
            params=params,
            timeout=60,
        )

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                f"{source_name}: "
                f"response không phải dict"
            )

        if (
            payload.get(
                "retcode"
            )
            not in (
                None,
                0,
                "0",
            )
        ):
            raise RuntimeError(
                payload.get(
                    "message",
                    f"{source_name} error",
                )
            )

        data = payload.get(
            "data",
            {},
        )

        if isinstance(
            data,
            list,
        ):
            rows = data
            total = 0

        elif isinstance(
            data,
            dict,
        ):
            rows = (
                data.get(
                    "list"
                )
                or data.get(
                    "items"
                )
                or data.get(
                    "rows"
                )
                or data.get(
                    "records"
                )
                or []
            )

            try:
                total = int(
                    data.get(
                        "total",
                        0,
                    )
                    or data.get(
                        "total_count",
                        0,
                    )
                    or 0
                )
            except (
                TypeError,
                ValueError,
            ):
                total = 0

        else:
            rows = []
            total = 0

        if not isinstance(
            rows,
            list,
        ):
            rows = []

        if total > 0:
            server_total = max(
                server_total,
                total,
            )

        if not rows:
            print(
                f"{source_name} PAGE "
                f"{page_no}: EMPTY"
            )
            break

        raw_received += len(
            rows
        )

        signature = tuple(
            get_trip_key(
                item
            )
            for item in rows
            if isinstance(
                item,
                dict,
            )
            and get_trip_key(
                item
            )
        )

        if (
            signature
            and signature
            in seen_page_signatures
        ):
            print(
                f"{source_name} PAGE "
                f"{page_no}: "
                f"REPEATED PAGE => STOP"
            )
            break

        if signature:
            seen_page_signatures.add(
                signature
            )

        new_count = 0

        for item in rows:
            if not isinstance(
                item,
                dict,
            ):
                continue

            key = get_trip_key(
                item
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(
                key
            )

            row = dict(
                item
            )

            row[
                "_trip_source"
            ] = source_name

            all_trips.append(
                row
            )

            new_count += 1

        print(
            f"{source_name} PAGE "
            f"{page_no}: "
            f"RAW={len(rows)} | "
            f"NEW={new_count} | "
            f"UNIQUE={len(all_trips)} | "
            f"RAW_RECEIVED={raw_received} | "
            f"SERVER_TOTAL={server_total}"
        )

        if (
            server_total > 0
            and raw_received
            >= server_total
        ):
            break

        page_no += 1

        if page_no > 10000:
            raise RuntimeError(
                f"{source_name}: "
                f"pagination vượt 10000 page"
            )

    return all_trips



def _history_page(
    mtime_start_ts: int,
    mtime_end_ts: int,
    page_no: int,
    count: int = 100,
) -> dict:
    url = (
        BASE_URL
        + "/api/admin/transportation/"
        "trip/history/list"
    )

    params = {
        "trip_station_status":
            90,

        "mtime":
            f"{mtime_start_ts},"
            f"{mtime_end_ts}",

        "pageno":
            page_no,

        "count":
            count,
    }

    response = spx_get(
        url,
        params=params,
        timeout=60,
    )

    payload = response.json()

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "HISTORY_COMPLETED response "
            "không phải dict"
        )

    if (
        payload.get("retcode")
        not in (
            None,
            0,
            "0",
        )
    ):
        raise RuntimeError(
            payload.get(
                "message",
                "HISTORY_COMPLETED error",
            )
        )

    return payload


def _extract_history_rows_total(
    payload: dict,
) -> tuple[list[dict], int]:
    data = (
        payload.get("data")
        or {}
    )

    rows = (
        data.get("list")
        or []
        if isinstance(
            data,
            dict,
        )
        else []
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = []

    try:
        total = int(
            data.get("total")
            or 0
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        total = 0

    return (
        rows,
        total,
    )


def crawl_history_mtime_day(
    day_start_ts: int,
    day_end_ts: int,
    source_name: str,
    count: int = 100,
    max_workers: int = 5,
) -> list[dict]:
    try:
        count = int(
            count
        )
    except (
        TypeError,
        ValueError,
    ):
        count = 100

    if count < 1:
        count = 100

    max_workers = max(
        1,
        min(
            int(max_workers),
            5,
        ),
    )

    first_payload = _history_page(
        mtime_start_ts=
            day_start_ts,

        mtime_end_ts=
            day_end_ts,

        page_no=
            1,

        count=
            count,
    )

    (
        first_rows,
        total,
    ) = _extract_history_rows_total(
        first_payload
    )

    print(
        f"{source_name} "
        f"PAGE 1 | "
        f"ROWS={len(first_rows)} | "
        f"TOTAL={total}"
    )

    if not first_rows:
        return []

    page_results = {
        1: first_rows,
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
            max_workers,
            total_pages - 1,
        )

        print(
            f"{source_name} "
            f"WORKERS={worker_count} | "
            f"PAGES={total_pages}"
        )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:
            future_map = {
                executor.submit(
                    _history_page,
                    day_start_ts,
                    day_end_ts,
                    page_no,
                    count,
                ): page_no

                for page_no in range(
                    2,
                    total_pages + 1,
                )
            }

            for future in as_completed(
                future_map
            ):
                page_no = future_map[
                    future
                ]

                payload = future.result()

                (
                    rows,
                    current_total,
                ) = _extract_history_rows_total(
                    payload
                )

                if current_total > total:
                    total = current_total

                page_results[
                    page_no
                ] = rows

                print(
                    f"{source_name} "
                    f"PAGE {page_no} | "
                    f"ROWS={len(rows)} | DONE"
                )

    result = []
    seen_trips = set()
    seen_pages = set()
    raw_received = 0

    for page_no in sorted(
        page_results
    ):
        rows = page_results[
            page_no
        ]

        raw_received += len(
            rows
        )

        signature = tuple(
            get_trip_key(
                item
            )
            for item in rows
            if isinstance(
                item,
                dict,
            )
            and get_trip_key(
                item
            )
        )

        if (
            signature
            and signature
            in seen_pages
        ):
            print(
                f"{source_name} "
                f"PAGE {page_no} "
                f"REPEATED => SKIP"
            )
            continue

        if signature:
            seen_pages.add(
                signature
            )

        for item in rows:
            if not isinstance(
                item,
                dict,
            ):
                continue

            key = get_trip_key(
                item
            )

            if not key:
                continue

            if key in seen_trips:
                continue

            seen_trips.add(
                key
            )

            row = dict(
                item
            )

            row[
                "_trip_source"
            ] = source_name

            result.append(
                row
            )

    print(
        f"{source_name} DONE | "
        f"RAW={raw_received} | "
        f"UNIQUE={len(result)} | "
        f"TOTAL={total}"
    )

    return result


def crawl_trip_list(
    start_ts: int,
    end_ts: int,
    count: int = 100,
    max_workers: int = 5,
) -> list[dict]:
    start_datetime = (
        datetime.fromtimestamp(
            start_ts,
            VN_TZ,
        )
    )

    end_datetime = (
        datetime.fromtimestamp(
            end_ts,
            VN_TZ,
        )
    )

    print()
    print("=" * 100)
    print(
        "CRAWL TRIPS - COMPLETED ONLY"
    )
    print(
        "TRIP_STATION_STATUS:",
        90,
    )
    print(
        "MTIME FROM:",
        start_datetime.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )
    print(
        "MTIME TO:",
        end_datetime.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )
    print(
        "COUNT:",
        count,
    )
    print(
        "WORKERS:",
        max_workers,
    )
    print("=" * 100)

    items = crawl_history_mtime_day(
        day_start_ts=
            start_ts,

        day_end_ts=
            end_ts,

        source_name=
            "HISTORY_COMPLETED_4D",

        count=
            count,

        max_workers=
            max_workers,
    )

    print()
    print("=" * 100)
    print(
        "TRIP DISCOVERY COMPLETE"
    )
    print(
        f"UNIQUE COMPLETED TRIPS: "
        f"{len(items)}"
    )
    print("=" * 100)

    return items


def get_trip_identity(
    trip_item: dict,
) -> tuple[int, str]:
    trip_id = (
        trip_item.get(
            "id"
        )
        or trip_item.get(
            "trip_id"
        )
    )

    trip_number = str(
        trip_item.get(
            "trip_number",
            "",
        )
        or ""
    ).strip().upper()

    if not trip_id:
        raise RuntimeError(
            f"Trip không có id: "
            f"{trip_number}"
        )

    return (
        int(
            trip_id
        ),
        trip_number,
    )


def classify_loading(
    loading_items: list[dict],
) -> dict:
    to_numbers = []
    bulky_ids = []
    unknown = []

    to_seen = set()
    bulky_seen = set()
    unknown_seen = set()

    for item in loading_items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        scan_number = str(
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
                "fleet_order_id"
            )
            or ""
        ).strip().upper()

        if not scan_number:
            continue

        if scan_number.startswith(
            "TO"
        ):
            if (
                scan_number
                not in to_seen
            ):
                to_seen.add(
                    scan_number
                )

                to_numbers.append(
                    scan_number
                )

            continue

        if scan_number.startswith(
            "SPXVN"
        ):
            if (
                scan_number
                not in bulky_seen
            ):
                bulky_seen.add(
                    scan_number
                )

                bulky_ids.append(
                    scan_number
                )

            continue

        if (
            scan_number
            not in unknown_seen
        ):
            unknown_seen.add(
                scan_number
            )

            unknown.append(
                scan_number
            )

    return {
        "to_numbers":
            to_numbers,

        "bulky_ids":
            bulky_ids,

        "unknown":
            unknown,
    }



def before_scan_to_api_call():
    global SCAN_TO_API_STARTED

    with SCAN_TO_RATE_LOCK:
        if (
            SCAN_TO_API_STARTED > 0
            and SCAN_TO_API_STARTED
            % TO_BATCH_SIZE == 0
        ):
            print()
            print("=" * 90)
            print(
                f"[TO HOLD] "
                f"{SCAN_TO_API_STARTED} TO API calls "
                f"=> sleep {TO_BATCH_SLEEP}s"
            )
            print("=" * 90)
            print()

            time.sleep(
                TO_BATCH_SLEEP
            )

        SCAN_TO_API_STARTED += 1

        current_call = (
            SCAN_TO_API_STARTED
        )

    return current_call


def after_scan_to_order_rows(
    row_count: int,
):
    global ORDER_ROWS_EMITTED

    try:
        row_count = int(
            row_count
        )
    except (
        TypeError,
        ValueError,
    ):
        row_count = 0

    if row_count <= 0:
        return

    with ORDER_ROW_RATE_LOCK:
        previous_total = (
            ORDER_ROWS_EMITTED
        )

        ORDER_ROWS_EMITTED += (
            row_count
        )

        previous_bucket = (
            previous_total
            // ORDER_ROW_BATCH_SIZE
        )

        current_bucket = (
            ORDER_ROWS_EMITTED
            // ORDER_ROW_BATCH_SIZE
        )

        if current_bucket > previous_bucket:
            print()
            print("=" * 90)
            print(
                f"[ORDER ROW HOLD] "
                f"rows={ORDER_ROWS_EMITTED} "
                f"=> sleep {ORDER_ROW_BATCH_SLEEP}s"
            )
            print("=" * 90)
            print()

            time.sleep(
                ORDER_ROW_BATCH_SLEEP
            )



def get_or_scan_to(
    to_number: str,
) -> tuple[dict, bool]:
    to_number = str(
        to_number
        or ""
    ).strip().upper()

    should_scan = False
    wait_event = None

    with TO_CACHE_LOCK:
        if (
            to_number
            in TO_CACHE
        ):
            return (
                TO_CACHE[
                    to_number
                ],
                True,
            )

        if (
            to_number
            in TO_INFLIGHT
        ):
            wait_event = (
                TO_INFLIGHT[
                    to_number
                ]
            )

        else:
            wait_event = (
                threading.Event()
            )

            TO_INFLIGHT[
                to_number
            ] = wait_event

            should_scan = True

    if should_scan:
        try:
            global_call_number = (
                before_scan_to_api_call()
            )

            print(
                f"TO API CALL "
                f"#{global_call_number}: "
                f"{to_number}"
            )

            result = (
                scan_to_orders(
                    to_number=
                        to_number,

                    count=
                        10000,
                )
            )

            with TO_CACHE_LOCK:
                TO_CACHE[
                    to_number
                ] = result

            return (
                result,
                False,
            )

        finally:
            with TO_CACHE_LOCK:
                event = (
                    TO_INFLIGHT.pop(
                        to_number,
                        None,
                    )
                )

                if event is not None:
                    event.set()

    print(
        f"TO WAIT: "
        f"{to_number}"
    )

    wait_event.wait()

    with TO_CACHE_LOCK:
        if (
            to_number
            not in TO_CACHE
        ):
            raise RuntimeError(
                f"TO scan failed: "
                f"{to_number}"
            )

        return (
            TO_CACHE[
                to_number
            ],
            True,
        )


def scan_all_tos(
    trip_id: int,
    to_numbers: list[str],
    wait_seconds: float = 0.15,
) -> dict:
    rows = []
    shipment_ids = []
    shipment_seen = set()

    failed = []

    success_count = 0
    cached_count = 0
    api_call_count = 0

    total = len(
        to_numbers
    )

    for (
        index,
        to_number
    ) in enumerate(
        to_numbers,
        start=1,
    ):
        print(
            f"[SCAN TO "
            f"{index}/{total}] "
            f"{to_number}"
        )

        try:
            (
                scan_result,
                from_cache,
            ) = get_or_scan_to(
                to_number
            )

            if from_cache:
                cached_count += 1

                print(
                    f"TO CACHE: "
                    f"{to_number}"
                )

            else:
                api_call_count += 1

                if (
                    wait_seconds > 0
                ):
                    time.sleep(
                        wait_seconds
                    )

            current_rows = (
                build_to_order_rows_from_scan(
                    trip_id=
                        trip_id,

                    scan_result=
                        scan_result,
                )
            )

            after_scan_to_order_rows(
                len(
                    current_rows
                )
            )

            rows.extend(
                current_rows
            )

            current_ids = (
                get_shipment_ids_from_to_order_rows(
                    current_rows
                )
            )

            for shipment_id in current_ids:
                shipment_id = str(
                    shipment_id
                    or ""
                ).strip().upper()

                if not shipment_id:
                    continue

                if (
                    shipment_id
                    in shipment_seen
                ):
                    continue

                shipment_seen.add(
                    shipment_id
                )

                shipment_ids.append(
                    shipment_id
                )

            success_count += 1

            print(
                f"TO OK: "
                f"{to_number} "
                f"=> "
                f"{len(current_rows)} "
                f"orders"
            )

        except Exception as e:
            failed.append({
                "to_number":
                    to_number,

                "error":
                    str(e),
            })

            print(
                f"TO ERROR: "
                f"{to_number} "
                f"=> "
                f"{e}"
            )

    return {
        "rows":
            rows,

        "shipment_ids":
            shipment_ids,

        "success":
            success_count,

        "cached":
            cached_count,

        "api_calls":
            api_call_count,

        "failed_count":
            len(
                failed
            ),

        "failed":
            failed,
    }



def sync_one_trip(
    trip_item: dict,
    direction: str = "auto",
    sequence: int | None = None,
    scan_to: bool = True,
) -> dict:
    (
        trip_id,
        trip_number,
    ) = get_trip_identity(
        trip_item
    )

    trip_source = str(
        trip_item.get(
            "_trip_source",
            "",
        )
        or ""
    )

    print()
    print("=" * 90)
    print(
        f"TRIP: "
        f"{trip_number or trip_id}"
    )
    print(
        f"TRIP ID: "
        f"{trip_id}"
    )
    print(
        f"SOURCE: "
        f"{trip_source}"
    )
    print("=" * 90)

    print(
        "[1/6] TRIP DETAIL"
    )

    trip_detail = (
        get_trip_detail_data(
            trip_id=
                trip_id,

            trip_source=
                trip_source,
        )
    )

    detail_endpoint = str(
        trip_detail.get(
            "_detail_endpoint",
            "",
        )
        or ""
    )

    print(
        f"DETAIL SOURCE: "
        f"{detail_endpoint}"
    )

    print(
        "[2/6] BUILD TRIP"
    )

    trip_row = (
        build_trip_row(
            trip_id=
                trip_id,

            trip_detail=
                trip_detail,
        )
    )

    print(
        "[3/6] BUILD TRIP STATION"
    )

    trip_station_rows = (
        build_trip_station_rows(
            trip_id=
                trip_id,

            trip_detail=
                trip_detail,
        )
    )

    print(
        "[4/6] GET LOADING"
    )

    requested_direction = str(
        direction
        or "auto"
    ).strip().lower()

    if (
        requested_direction
        == "auto"
    ):
        (
            loading_direction,
            loading_sequence,
        ) = get_auto_loading_context(
            trip_detail=
                trip_detail,

            fallback_direction=
                "outbound",

            fallback_sequence=
                1,

            station_id=
                3909,
        )

    else:
        loading_direction = (
            requested_direction
        )

        loading_sequence = (
            sequence
            if sequence is not None
            else 1
        )

    print(
        f"LOADING MODE: "
        f"{loading_direction} "
        f"| sequence="
        f"{loading_sequence}"
    )

    loading_data = (
        get_trip_loading_data(
            trip_id=
                trip_id,

            direction=
                loading_direction,

            sequence=
                loading_sequence,
        )
    )

    loading_items = (
        extract_list(
            loading_data
        )
    )

    print(
        f"LOADING ITEMS: "
        f"{len(loading_items)}"
    )

    print(
        "[5/6] BUILD TO"
    )

    to_rows = (
        build_to_rows(
            trip_id=
                trip_id,

            items=
                loading_items,

            direction=
                loading_direction,

            sequence=
                loading_sequence,
        )
    )

    classified = (
        classify_loading(
            loading_items
        )
    )

    to_numbers = (
        classified[
            "to_numbers"
        ]
    )

    bulky_ids = (
        classified[
            "bulky_ids"
        ]
    )

    unknown = (
        classified[
            "unknown"
        ]
    )

    print(
        f"TO UNIQUE: "
        f"{len(to_numbers)}"
    )

    print(
        f"BULKY: "
        f"{len(bulky_ids)}"
    )

    print(
        f"UNKNOWN: "
        f"{len(unknown)}"
    )

    print(
        "[6/6] SCAN TO"
    )

    if scan_to:
        scan_result = (
            scan_all_tos(
                trip_id=
                    trip_id,

                to_numbers=
                    to_numbers,

                wait_seconds=
                    0.15,
            )
        )
    else:
        scan_result = {
            "rows": [],
            "shipment_ids": [],
            "success": 0,
            "cached": 0,
            "api_calls": 0,
            "failed_count": 0,
            "failed": [],
        }

    to_order_rows = (
        scan_result[
            "rows"
        ]
    )

    order_candidates = set(
        scan_result[
            "shipment_ids"
        ]
    )

    for bulky_id in bulky_ids:
        order_candidates.add(
            bulky_id
        )

    print()
    print(
        f"CRAWL COMPLETE: "
        f"{trip_number or trip_id}"
    )

    print(
        f"TO: "
        f"{len(to_numbers)}"
    )

    print(
        f"BULKY: "
        f"{len(bulky_ids)}"
    )

    print(
        f"TO ORDER ROWS: "
        f"{len(to_order_rows)}"
    )

    print(
        f"TO API CALLS: "
        f"{scan_result['api_calls']}"
    )

    print(
        f"TO CACHE HITS: "
        f"{scan_result['cached']}"
    )

    print(
        "SHEET WRITE: QUEUED"
    )

    print(
        "ORDER DETAIL: DISABLED"
    )

    return {
        "success":
            True,

        "trip_id":
            trip_id,

        "trip_number":
            trip_number,

        "source":
            trip_source,

        "detail_endpoint":
            detail_endpoint,

        "loading_direction":
            loading_direction,

        "loading_sequence":
            loading_sequence,

        "trip_row":
            trip_row,

        "trip_station_rows":
            trip_station_rows,

        "to_rows":
            to_rows,

        "to_order_rows":
            to_order_rows,

        "loading_count":
            len(
                loading_items
            ),

        "trip_station_count":
            len(
                trip_station_rows
            ),

        "to_rows_count":
            len(
                to_rows
            ),

        "to_unique":
            len(
                to_numbers
            ),

        "bulky":
            len(
                bulky_ids
            ),

        "bulky_ids":
            bulky_ids,

        "unknown":
            len(
                unknown
            ),

        "scan_to_rows":
            len(
                to_order_rows
            ),

        "scan_to_success":
            scan_result[
                "success"
            ],

        "scan_to_cached":
            scan_result[
                "cached"
            ],

        "scan_to_api_calls":
            scan_result[
                "api_calls"
            ],

        "scan_to_failed":
            scan_result[
                "failed_count"
            ],

        "failed_tos":
            scan_result[
                "failed"
            ],

        "order_candidates":
            len(
                order_candidates
            ),

        "order_crawl":
            False,
    }



CANCEL_TRIP_STATUSES = {
    100,
}


def parse_trip_date_value(
    value,
) -> date | None:
    if value in (
        None,
        "",
        0,
        "0",
    ):
        return None

    if isinstance(
        value,
        datetime,
    ):
        if value.tzinfo is None:
            value = value.replace(
                tzinfo=VN_TZ
            )
        else:
            value = value.astimezone(
                VN_TZ
            )

        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    try:
        number = float(
            value
        )

        while (
            number
            > 10_000_000_000
        ):
            number /= 1000

        return datetime.fromtimestamp(
            number,
            tz=VN_TZ,
        ).date()

    except (
        TypeError,
        ValueError,
        OSError,
        OverflowError,
    ):
        pass

    text = str(
        value
    ).strip()

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def get_trip_status_value(
    trip: dict,
) -> int | None:
    value = trip.get(
        "trip_status"
    )

    if value in (
        None,
        "",
    ):
        return None

    try:
        return int(
            float(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def is_cancelled_trip(
    trip: dict,
) -> bool:
    trip_status = (
        get_trip_status_value(
            trip
        )
    )

    if (
        trip_status
        in CANCEL_TRIP_STATUSES
    ):
        return True

    status_text = " ".join(
        [
            str(
                trip.get(
                    "trip_status_name",
                    "",
                )
                or ""
            ),
            str(
                trip.get(
                    "status_name",
                    "",
                )
                or ""
            ),
            str(
                trip.get(
                    "status",
                    "",
                )
                or ""
            ),
        ]
    ).strip().upper()

    return (
        "CANCEL"
        in status_text
    )


def filter_trips_for_processing(
    trips: list[dict],
    reference_date: str | date | None = None,
    days: int = 4,
) -> list[dict]:
    if reference_date is None:
        current_date = (
            datetime.now(
                VN_TZ
            ).date()
        )

    elif isinstance(
        reference_date,
        str,
    ):
        current_date = (
            datetime.strptime(
                reference_date,
                "%Y-%m-%d",
            ).date()
        )

    elif isinstance(
        reference_date,
        date,
    ):
        current_date = reference_date

    else:
        raise ValueError(
            "reference_date không hợp lệ"
        )

    try:
        days = int(
            days
        )
    except (
        TypeError,
        ValueError,
    ):
        days = 4

    if days < 1:
        days = 1

    oldest_date = (
        current_date
        - timedelta(
            days=days - 1
        )
    )

    result = []
    skipped_old = 0
    skipped_future = 0
    skipped_cancel = 0
    skipped_no_trip_date = 0
    status_found = {}

    for trip in trips:
        if not isinstance(
            trip,
            dict,
        ):
            continue

        status_value = (
            get_trip_status_value(
                trip
            )
        )

        status_found[
            status_value
        ] = (
            status_found.get(
                status_value,
                0,
            )
            + 1
        )

        trip_date = (
            parse_trip_date_value(
                trip.get(
                    "trip_date"
                )
            )
        )

        if trip_date is None:
            skipped_no_trip_date += 1
            continue

        if trip_date < oldest_date:
            skipped_old += 1
            continue

        if trip_date > current_date:
            skipped_future += 1
            continue

        if is_cancelled_trip(
            trip
        ):
            skipped_cancel += 1
            continue

        result.append(
            trip
        )

    print()
    print("=" * 90)
    print("TRIP PROCESS FILTER")
    print(
        "DATE FROM:",
        oldest_date.strftime(
            "%d/%m/%Y"
        ),
    )
    print(
        "DATE TO:",
        current_date.strftime(
            "%d/%m/%Y"
        ),
    )
    print(
        "INPUT:",
        len(trips),
    )
    print(
        "SKIP OLD:",
        skipped_old,
    )
    print(
        "SKIP FUTURE:",
        skipped_future,
    )
    print(
        "SKIP CANCEL:",
        skipped_cancel,
    )
    print(
        "SKIP NO TRIP_DATE:",
        skipped_no_trip_date,
    )
    print(
        "STATUS FOUND:",
        status_found,
    )
    print(
        "TO PROCESS:",
        len(result),
    )
    print("=" * 90)

    return result


def sync_two_day_trips(
    target_date: str | date | None = None,
    trip_wait_seconds: float = 0.0,
    max_workers: int = 5,
    trip_limit: int | None = None,
    scan_to: bool = True,
) -> dict:
    started_at = time.time()

    try:
        max_workers = int(max_workers)
    except (TypeError, ValueError):
        max_workers = 5

    if max_workers < 1:
        max_workers = 1

    if max_workers > 5:
        max_workers = 5

    if trip_limit is not None:
        try:
            trip_limit = int(trip_limit)
        except (TypeError, ValueError):
            trip_limit = None

        if trip_limit <= 0:
            trip_limit = None

    range_info = get_one_day_range(
        target_date
    )
    start_datetime = range_info["start_datetime"]
    end_datetime = range_info["end_datetime"]
    reference_date = range_info["target_date"]

    print()
    print("=" * 90)
    print("DAILY TRIP SYNC - COMPLETED 1 DAYS DIRECT TO SHEET")
    print(
        "MTIME FROM:",
        start_datetime.strftime("%d/%m/%Y %H:%M:%S"),
    )
    print(
        "MTIME TO:",
        end_datetime.strftime("%d/%m/%Y %H:%M:%S"),
    )
    print(
        "MTIME DATE FROM:",
        range_info[
            "start_date"
        ].strftime("%d/%m/%Y"),
    )
    print(
        "MTIME DATE TO:",
        reference_date.strftime("%d/%m/%Y"),
    )
    print("TRIP_STATION_STATUS: 90")
    print("TRIP_DATE FILTER: DISABLED")
    print(f"LIST WORKERS: {max_workers}")
    print(f"TRIP LIMIT: {trip_limit if trip_limit else 'ALL'}")
    print("DETAIL API: DISABLED")
    print("LOADING API: DISABLED")
    print("SCAN TO: DISABLED")
    print("SHEET: TRIP + TRIP STATION")
    print("=" * 90)

    trips_discovered = crawl_trip_list(
        start_ts=range_info["start_ts"],
        end_ts=range_info["end_ts"],
        count=100,
        max_workers=max_workers,
    )

    print()
    print(
        "TOTAL COMPLETED TRIPS DISCOVERED:",
        len(trips_discovered),
    )

    trips = list(
        trips_discovered
    )

    trips = sorted(
        trips,
        key=lambda item: (
            int(
                item.get(
                    "trip_date",
                    0,
                )
                or 0
            ),
            int(
                item.get(
                    "mtime",
                    0,
                )
                or 0
            ),
        ),
        reverse=True,
    )

    if trip_limit:
        trips = trips[:trip_limit]

    total = len(trips)

    print()
    print(
        "TOTAL TRIPS TO SHEET:",
        total,
    )

    if total == 0:
        elapsed = round(
            time.time()
            - started_at,
            2,
        )

        return {
            "success": True,
            "range": {
                "from":
                    start_datetime.isoformat(),
                "to":
                    end_datetime.isoformat(),
            },
            "trip_date_filter":
                False,
            "mtime_date_range": {
                "from":
                    range_info[
                        "start_date"
                    ].isoformat(),
                "to":
                    reference_date.isoformat(),
            },
            "discovered_count":
                len(trips_discovered),
            "total_trips":
                0,
            "success_count":
                0,
            "failed_count":
                0,
            "loading_count":
                0,
            "to_count":
                0,
            "bulky_count":
                0,
            "scan_to_rows":
                0,
            "scan_to_api_calls":
                0,
            "scan_to_cache_hits":
                0,
            "scan_to_cache_size":
                0,
            "order_candidates":
                0,
            "order_crawl":
                False,
            "max_workers":
                max_workers,
            "trip_limit":
                trip_limit,
            "scan_to":
                False,
            "sheet_writer":
                1,
            "sheet_rows": {
                "trip": 0,
                "trip_station": 0,
                "to": 0,
                "to_order": 0,
            },
            "sheet_results": {
                "trip": None,
                "trip_station": None,
                "to": None,
                "to_order": None,
            },
            "sheet_errors":
                [],
            "elapsed_seconds":
                elapsed,
            "results":
                [],
            "failed":
                [],
        }

    success_results = []
    failed_results = []

    all_trip_rows = []
    all_trip_station_rows = []

    print()
    print("=" * 90)
    print("BUILD ROWS DIRECTLY FROM HISTORY LIST")
    print("=" * 90)

    for index, trip_item in enumerate(
        trips,
        start=1,
    ):
        trip_id = (
            trip_item.get("id")
            or trip_item.get("trip_id")
        )

        trip_number = str(
            trip_item.get(
                "trip_number",
                "",
            )
            or ""
        ).strip().upper()

        try:
            if not trip_id:
                raise RuntimeError(
                    f"Trip không có id: {trip_number}"
                )

            list_payload = {
                "retcode": 0,
                "message": "",
                "data": dict(
                    trip_item
                ),
                "_detail_endpoint":
                    "HISTORY_LIST",
            }

            trip_row = build_trip_row(
                trip_id=int(
                    trip_id
                ),
                trip_detail=list_payload,
            )

            trip_station_rows = (
                build_trip_station_rows(
                    trip_id=int(
                        trip_id
                    ),
                    trip_detail=list_payload,
                )
            )

            if isinstance(
                trip_row,
                dict,
            ):
                all_trip_rows.append(
                    trip_row
                )

            if isinstance(
                trip_station_rows,
                list,
            ):
                all_trip_station_rows.extend(
                    trip_station_rows
                )

            success_results.append({
                "trip_id":
                    int(trip_id),
                "trip_number":
                    trip_number,
                "source":
                    trip_item.get(
                        "_trip_source",
                        "",
                    ),
                "detail_endpoint":
                    "HISTORY_LIST",
                "trip_station_count":
                    len(
                        trip_station_rows
                    )
                    if isinstance(
                        trip_station_rows,
                        list,
                    )
                    else 0,
                "loading_count":
                    0,
                "to_rows_count":
                    0,
                "to_unique":
                    0,
                "bulky":
                    0,
                "scan_to_rows":
                    0,
                "scan_to_api_calls":
                    0,
                "scan_to_failed":
                    0,
                "order_candidates":
                    0,
            })

            print(
                f"[{index}/{total}] "
                f"BUILD OK "
                f"{trip_number or trip_id} "
                f"| stations="
                f"{len(trip_station_rows) if isinstance(trip_station_rows, list) else 0}"
            )

        except Exception as e:
            failed_results.append({
                "trip_id":
                    trip_id,
                "trip_number":
                    trip_number,
                "source":
                    trip_item.get(
                        "_trip_source",
                        "",
                    ),
                "error":
                    str(e),
            })

            print(
                f"[{index}/{total}] "
                f"BUILD FAILED "
                f"{trip_number or trip_id} "
                f"=> {e}"
            )

            print(
                traceback.format_exc()
            )

        if trip_wait_seconds > 0:
            time.sleep(
                trip_wait_seconds
            )

    print()
    print("=" * 90)
    print("BUILD COMPLETE")
    print(
        "TRIP ROWS:",
        len(all_trip_rows),
    )
    print(
        "TRIP STATION ROWS:",
        len(
            all_trip_station_rows
        ),
    )
    print("=" * 90)

    sheet_results = {
        "trip": None,
        "trip_station": None,
        "to": None,
        "to_order": None,
    }

    sheet_errors = []

    print()
    print("=" * 90)
    print("START GOOGLE SHEET WRITE")
    print("=" * 90)

    if all_trip_rows:
        try:
            print(
                f"[SHEET 1/2] TRIP "
                f"rows={len(all_trip_rows)}"
            )

            sheet_results["trip"] = (
                push_trip_rows(
                    all_trip_rows
                )
            )

            print(
                f"[SHEET 1/2] TRIP OK: "
                f"{sheet_results['trip']}"
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "trip",
                "error":
                    str(e),
            })

            print(
                f"[SHEET 1/2] "
                f"TRIP ERROR: {e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 1/2] "
            "TRIP SKIP - 0 ROW"
        )

    if all_trip_station_rows:
        try:
            print(
                f"[SHEET 2/2] "
                f"TRIP STATION "
                f"rows="
                f"{len(all_trip_station_rows)}"
            )

            sheet_results[
                "trip_station"
            ] = (
                push_trip_station_rows(
                    all_trip_station_rows
                )
            )

            print(
                f"[SHEET 2/2] "
                f"TRIP STATION OK: "
                f"{sheet_results['trip_station']}"
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "trip_station",
                "error":
                    str(e),
            })

            print(
                f"[SHEET 2/2] "
                f"TRIP STATION ERROR: {e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 2/2] "
            "TRIP STATION SKIP - 0 ROW"
        )

    elapsed = round(
        time.time()
        - started_at,
        2,
    )

    print()
    print("=" * 90)
    print("DAILY TRIP SYNC COMPLETE")
    print(
        f"COMPLETED DISCOVERED: "
        f"{len(trips_discovered)}"
    )
    print(
        f"TOTAL TO SHEET: "
        f"{total}"
    )
    print(
        f"SUCCESS: "
        f"{len(success_results)}"
    )
    print(
        f"FAILED: "
        f"{len(failed_results)}"
    )
    print(
        f"TRIP ROWS: "
        f"{len(all_trip_rows)}"
    )
    print(
        f"TRIP STATION ROWS: "
        f"{len(all_trip_station_rows)}"
    )
    print(
        f"SHEET ERRORS: "
        f"{len(sheet_errors)}"
    )
    print("DETAIL API CALLS: 0")
    print("LOADING API CALLS: 0")
    print("TO API CALLS: 0")
    print(
        f"ELAPSED: "
        f"{elapsed}s"
    )
    print("=" * 90)

    return {
        "success":
            (
                len(failed_results)
                == 0
                and len(sheet_errors)
                == 0
            ),
        "range": {
            "from":
                start_datetime.isoformat(),
            "to":
                end_datetime.isoformat(),
        },
        "trip_date_filter":
            False,
        "mtime_date_range": {
            "from":
                range_info[
                    "start_date"
                ].isoformat(),
            "to":
                reference_date.isoformat(),
        },
        "discovered_count":
            len(trips_discovered),
        "total_trips":
            total,
        "success_count":
            len(success_results),
        "failed_count":
            len(failed_results),
        "loading_count":
            0,
        "to_count":
            0,
        "bulky_count":
            0,
        "scan_to_rows":
            0,
        "scan_to_api_calls":
            0,
        "scan_to_cache_hits":
            0,
        "scan_to_cache_size":
            0,
        "order_candidates":
            0,
        "order_crawl":
            False,
        "max_workers":
            max_workers,
        "trip_limit":
            trip_limit,
        "scan_to":
            False,
        "sheet_writer":
            1,
        "sheet_rows": {
            "trip":
                len(
                    all_trip_rows
                ),
            "trip_station":
                len(
                    all_trip_station_rows
                ),
            "to":
                0,
            "to_order":
                0,
        },
        "sheet_results":
            sheet_results,
        "sheet_errors":
            sheet_errors,
        "elapsed_seconds":
            elapsed,
        "results":
            success_results,
        "failed":
            failed_results,
    }


if __name__ == "__main__":
    try:
        result = sync_two_day_trips(
            target_date=None,
            trip_wait_seconds=0,
            max_workers=5,
            trip_limit=None,
            scan_to=True,
        )

        print()
        print(
            result
        )

    except Exception:
        print(
            traceback.format_exc()
        )

        raise
