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

from googleapiclient.errors import HttpError

from config import BASE_URL
from core.spx_request import spx_get

from api.scanto import (
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



def dedupe_rows_by_key(
    rows: list[dict],
) -> list[dict]:
    result = []
    seen = set()

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        key = str(
            row.get(
                "_key",
                "",
            )
            or ""
        ).strip()

        if key:
            if key in seen:
                continue

            seen.add(
                key
            )

        result.append(
            row
        )

    return result


def is_google_rate_limit_error(
    error: Exception,
) -> bool:
    if isinstance(
        error,
        HttpError,
    ):
        status = getattr(
            getattr(
                error,
                "resp",
                None,
            ),
            "status",
            None,
        )

        if status == 429:
            return True

    message = str(
        error
    ).upper()

    return (
        "429" in message
        or "RATE_LIMIT_EXCEEDED" in message
        or "QUOTA EXCEEDED" in message
    )


def push_sheet_with_retry(
    label: str,
    push_func,
    rows: list[dict],
    max_attempts: int = 5,
):
    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
        }

    attempt = 0

    while True:
        attempt += 1

        try:
            print(
                f"{label}: "
                f"PUSH ATTEMPT "
                f"{attempt}/"
                f"{max_attempts}"
            )

            return push_func(
                rows
            )

        except Exception as e:
            if (
                not is_google_rate_limit_error(
                    e
                )
                or attempt
                >= max_attempts
            ):
                raise

            wait_seconds = 65

            print(
                f"{label}: "
                f"GOOGLE 429, "
                f"WAIT "
                f"{wait_seconds}s "
                f"THEN RETRY"
            )

            time.sleep(
                wait_seconds
            )

def reset_to_cache():
    global TO_CACHE
    global TO_INFLIGHT

    with TO_CACHE_LOCK:
        TO_CACHE = {}
        TO_INFLIGHT = {}


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
) -> dict:
    url = (
        BASE_URL
        + "/api/admin/transportation/"
        "trip/history/detail"
    )

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

    data = response.json()

    if (
        data.get(
            "retcode"
        )
        not in (
            None,
            0,
        )
    ):
        raise RuntimeError(
            data.get(
                "message",
                "Trip Detail error",
            )
        )

    return data


def get_trip_loading_data(
    trip_id: int,
    direction: str = "outbound",
    sequence: int = 1,
) -> dict:
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
                "unloaded_sequence_number"
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


def get_two_day_range(
    target_date: str | date | None = None,
) -> dict:
    if target_date is None:
        current_date = (
            datetime.now(
                VN_TZ
            )
            .date()
        )

    elif isinstance(
        target_date,
        str,
    ):
        current_date = (
            datetime.strptime(
                target_date,
                "%Y-%m-%d",
            )
            .date()
        )

    else:
        current_date = target_date

    previous_date = (
        current_date
        - timedelta(
            days=1
        )
    )

    start_datetime = datetime(
        previous_date.year,
        previous_date.month,
        previous_date.day,
        0,
        0,
        0,
        tzinfo=VN_TZ,
    )

    end_datetime = datetime(
        current_date.year,
        current_date.month,
        current_date.day,
        23,
        59,
        59,
        tzinfo=VN_TZ,
    )

    return {
        "target_date":
            current_date,

        "previous_date":
            previous_date,

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
    loading_start_ts: int,
    loading_end_ts: int,
    mtime_start_ts: int,
    mtime_end_ts: int,
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

    while True:
        params = {
            "loading_time":
                (
                    f"{loading_start_ts},"
                    f"{loading_end_ts}"
                ),

            "mtime":
                (
                    f"{mtime_start_ts},"
                    f"{mtime_end_ts}"
                ),

            "pageno":
                page_no,

            "count":
                count,
        }

        if query_type is not None:
            params[
                "query_type"
            ] = query_type

        print(
            f"{source_name} PAGE: "
            f"{page_no}"
        )

        response = spx_get(
            url,
            params=params,
            timeout=60,
        )

        payload = response.json()

        if (
            payload.get(
                "retcode"
            )
            not in (
                None,
                0,
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

        if not isinstance(
            data,
            dict,
        ):
            break

        rows = data.get(
            "list",
            [],
        )

        if not isinstance(
            rows,
            list,
        ):
            rows = []

        total = int(
            data.get(
                "total",
                0,
            )
            or 0
        )

        if not rows:
            print(
                f"{source_name} PAGE "
                f"{page_no}: EMPTY"
            )

            break

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
            f"{len(rows)} rows | "
            f"NEW: {new_count} | "
            f"COLLECTED: "
            f"{len(all_trips)} | "
            f"SERVER TOTAL: "
            f"{total}"
        )

        if (
            total > 0
            and len(
                all_trips
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

    return all_trips


def crawl_trip_list(
    start_ts: int,
    end_ts: int,
    count: int = 100,
) -> list[dict]:
    history_mtime_start = (
        start_ts
        - (
            29
            * 24
            * 60
            * 60
        )
    )

    history_mtime_end = (
        end_ts
    )

    handover_mtime_start = (
        start_ts
        - (
            1
            * 24
            * 60
            * 60
        )
    )

    handover_mtime_end = (
        end_ts
    )

    print()
    print(
        "=" * 90
    )

    print(
        "CRAWL TRIP HISTORY"
    )

    print(
        "LOADING_TIME:",
        f"{start_ts},{end_ts}",
    )

    print(
        "MTIME:",
        (
            f"{history_mtime_start},"
            f"{history_mtime_end}"
        ),
    )

    print(
        "=" * 90
    )

    history_trips = (
        crawl_trip_endpoint(
            endpoint=(
                "/api/admin/"
                "transportation/"
                "trip/history/list"
            ),

            loading_start_ts=
                start_ts,

            loading_end_ts=
                end_ts,

            mtime_start_ts=
                history_mtime_start,

            mtime_end_ts=
                history_mtime_end,

            query_type=
                None,

            count=
                count,

            source_name=
                "HISTORY",
        )
    )

    print()
    print(
        "=" * 90
    )

    print(
        "CRAWL HANDOVER"
    )

    print(
        "LOADING_TIME:",
        f"{start_ts},{end_ts}",
    )

    print(
        "MTIME:",
        (
            f"{handover_mtime_start},"
            f"{handover_mtime_end}"
        ),
    )

    print(
        "QUERY_TYPE: 2"
    )

    print(
        "=" * 90
    )

    handover_trips = (
        crawl_trip_endpoint(
            endpoint=(
                "/api/admin/"
                "transportation/"
                "trip/list"
            ),

            loading_start_ts=
                start_ts,

            loading_end_ts=
                end_ts,

            mtime_start_ts=
                handover_mtime_start,

            mtime_end_ts=
                handover_mtime_end,

            query_type=
                2,

            count=
                count,

            source_name=
                "HANDOVER",
        )
    )

    merged = []
    merged_index = {}

    for item in (
        history_trips
        + handover_trips
    ):
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
            key = (
                f"ID:{trip_id}"
            )

        elif trip_number:
            key = (
                f"NUMBER:{trip_number}"
            )

        else:
            continue

        if key not in merged_index:
            merged_index[
                key
            ] = len(
                merged
            )

            merged.append(
                dict(
                    item
                )
            )

            continue

        current_index = (
            merged_index[
                key
            ]
        )

        current = (
            merged[
                current_index
            ]
        )

        current_source = str(
            current.get(
                "_trip_source",
                "",
            )
            or ""
        )

        incoming_source = str(
            item.get(
                "_trip_source",
                "",
            )
            or ""
        )

        if (
            current_source
            != incoming_source
        ):
            sources = []

            for source in (
                current_source.split(
                    "+"
                )
                + incoming_source.split(
                    "+"
                )
            ):
                source = (
                    source.strip()
                )

                if (
                    source
                    and source
                    not in sources
                ):
                    sources.append(
                        source
                    )

            current[
                "_trip_source"
            ] = "+".join(
                sources
            )

        for (
            field,
            value
        ) in item.items():
            if (
                field
                == "_trip_source"
            ):
                continue

            if (
                value is None
                or value == ""
            ):
                continue

            current[
                field
            ] = value

    print()
    print(
        "=" * 90
    )

    print(
        f"HISTORY: "
        f"{len(history_trips)}"
    )

    print(
        f"HANDOVER: "
        f"{len(handover_trips)}"
    )

    print(
        f"MERGED UNIQUE: "
        f"{len(merged)}"
    )

    print(
        "=" * 90
    )

    return merged


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
            print(
                f"TO API CALL: "
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
    direction: str = "outbound",
    sequence: int = 1,
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
            trip_id
        )
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

    loading_data = (
        get_trip_loading_data(
            trip_id=
                trip_id,

            direction=
                direction,

            sequence=
                sequence,
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
                direction,

            sequence=
                sequence,
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


def sync_two_day_trips(
    target_date: str | date | None = None,
    trip_wait_seconds: float = 0.0,
    max_workers: int = 5,
) -> dict:
    started_at = time.time()

    reset_to_cache()

    try:
        max_workers = int(max_workers)
    except (TypeError, ValueError):
        max_workers = 5

    if max_workers < 1:
        max_workers = 1

    if max_workers > 5:
        max_workers = 5

    range_info = get_two_day_range(
        target_date
    )

    start_datetime = range_info[
        "start_datetime"
    ]

    end_datetime = range_info[
        "end_datetime"
    ]

    print()
    print("=" * 90)
    print("DAILY TRIP SYNC")

    print(
        "FROM:",
        start_datetime.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )

    print(
        "TO:",
        end_datetime.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )

    print(
        f"SPX WORKERS: "
        f"{max_workers}"
    )

    print(
        "SHEET WRITER: 1"
    )

    print(
        "ORDER DETAIL CRAWL: DISABLED"
    )

    print("=" * 90)

    trips = crawl_trip_list(
        start_ts=
            range_info[
                "start_ts"
            ],
        end_ts=
            range_info[
                "end_ts"
            ],
        count=100,
    )

    total = len(
        trips
    )

    print()
    print(
        f"TOTAL TRIPS FOUND: "
        f"{total}"
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
            "total_trips": 0,
            "success_count": 0,
            "failed_count": 0,
            "loading_count": 0,
            "to_count": 0,
            "bulky_count": 0,
            "scan_to_rows": 0,
            "scan_to_api_calls": 0,
            "scan_to_cache_hits": 0,
            "scan_to_cache_size": 0,
            "order_candidates": 0,
            "order_crawl": False,
            "max_workers":
                max_workers,
            "sheet_writer": 1,
            "sheet_results": {},
            "sheet_errors": [],
            "elapsed_seconds":
                elapsed,
            "results": [],
            "failed": [],
        }

    success_results = []
    failed_results = []

    all_trip_rows = []
    all_trip_station_rows = []
    all_to_rows = []
    all_to_order_rows = []

    total_loading = 0
    total_to = 0
    total_bulky = 0
    total_scan_to_rows = 0
    total_scan_to_api_calls = 0
    total_scan_to_cached = 0
    total_order_candidates = 0

    future_map = {}

    print()
    print("=" * 90)
    print("START SPX CRAWL")
    print(
        f"WORKERS: "
        f"{max_workers}"
    )
    print("=" * 90)

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        for trip_item in trips:
            future = executor.submit(
                sync_one_trip,
                trip_item,
                "outbound",
                1,
            )

            future_map[
                future
            ] = trip_item

        completed = 0

        for future in as_completed(
            future_map
        ):
            completed += 1

            trip_item = future_map[
                future
            ]

            trip_number = str(
                trip_item.get(
                    "trip_number",
                    "",
                )
                or ""
            ).strip().upper()

            trip_id = (
                trip_item.get(
                    "id"
                )
                or trip_item.get(
                    "trip_id"
                )
            )

            trip_source = str(
                trip_item.get(
                    "_trip_source",
                    "",
                )
                or ""
            )

            try:
                result = (
                    future.result()
                )

                success_results.append(
                    result
                )

                trip_row = result.get(
                    "trip_row"
                )

                if isinstance(
                    trip_row,
                    dict,
                ):
                    all_trip_rows.append(
                        trip_row
                    )

                trip_station_rows = (
                    result.get(
                        "trip_station_rows",
                        [],
                    )
                    or []
                )

                if isinstance(
                    trip_station_rows,
                    list,
                ):
                    all_trip_station_rows.extend(
                        trip_station_rows
                    )

                to_rows = (
                    result.get(
                        "to_rows",
                        [],
                    )
                    or []
                )

                if isinstance(
                    to_rows,
                    list,
                ):
                    all_to_rows.extend(
                        to_rows
                    )

                to_order_rows = (
                    result.get(
                        "to_order_rows",
                        [],
                    )
                    or []
                )

                if isinstance(
                    to_order_rows,
                    list,
                ):
                    all_to_order_rows.extend(
                        to_order_rows
                    )

                total_loading += int(
                    result.get(
                        "loading_count",
                        0,
                    )
                    or 0
                )

                total_to += int(
                    result.get(
                        "to_unique",
                        0,
                    )
                    or 0
                )

                total_bulky += int(
                    result.get(
                        "bulky",
                        0,
                    )
                    or 0
                )

                total_scan_to_rows += int(
                    result.get(
                        "scan_to_rows",
                        0,
                    )
                    or 0
                )

                total_scan_to_api_calls += int(
                    result.get(
                        "scan_to_api_calls",
                        0,
                    )
                    or 0
                )

                total_scan_to_cached += int(
                    result.get(
                        "scan_to_cached",
                        0,
                    )
                    or 0
                )

                total_order_candidates += int(
                    result.get(
                        "order_candidates",
                        0,
                    )
                    or 0
                )

                print(
                    f"[{completed}/{total}] "
                    f"CRAWL OK "
                    f"{trip_number or trip_id}"
                )

            except Exception as e:
                failed_results.append({
                    "trip_id":
                        trip_id,
                    "trip_number":
                        trip_number,
                    "source":
                        trip_source,
                    "error":
                        str(e),
                })

                print(
                    f"[{completed}/{total}] "
                    f"CRAWL FAILED "
                    f"{trip_number or trip_id} "
                    f"=> {e}"
                )

                print(
                    traceback.format_exc()
                )

            if (
                trip_wait_seconds > 0
            ):
                time.sleep(
                    trip_wait_seconds
                )

    all_trip_rows = dedupe_rows_by_key(
        all_trip_rows
    )

    all_trip_station_rows = dedupe_rows_by_key(
        all_trip_station_rows
    )

    all_to_rows = dedupe_rows_by_key(
        all_to_rows
    )

    all_to_order_rows = dedupe_rows_by_key(
        all_to_order_rows
    )

    print()
    print("=" * 90)
    print(
        "SPX CRAWL COMPLETE"
    )

    print(
        f"TRIP ROWS QUEUED: "
        f"{len(all_trip_rows)}"
    )

    print(
        f"TRIP STATION ROWS QUEUED: "
        f"{len(all_trip_station_rows)}"
    )

    print(
        f"TO ROWS QUEUED: "
        f"{len(all_to_rows)}"
    )

    print(
        f"TO ORDER ROWS QUEUED: "
        f"{len(all_to_order_rows)}"
    )

    print("=" * 90)

    sheet_results = {
        "trip": {},
        "trip_station": {},
        "to": {},
        "to_order": {},
    }

    sheet_errors = []

    print()
    print("=" * 90)
    print(
        "START GOOGLE SHEET WRITER"
    )
    print(
        "WRITER: 1"
    )
    print("=" * 90)

    if all_trip_rows:
        try:
            print(
                f"[SHEET 1/4] "
                f"TRIP "
                f"{len(all_trip_rows)} rows"
            )

            sheet_results[
                "trip"
            ] = push_sheet_with_retry(
                label="TRIP",
                push_func=push_trip_rows,
                rows=all_trip_rows,
            )

            print(
                "TRIP SHEET OK:",
                sheet_results[
                    "trip"
                ],
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "trip",
                "error":
                    str(e),
            })

            print(
                f"TRIP SHEET ERROR: "
                f"{e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 1/4] "
            "TRIP: NO ROWS"
        )

    if all_trip_station_rows:
        try:
            print(
                f"[SHEET 2/4] "
                f"TRIP STATION "
                f"{len(all_trip_station_rows)} rows"
            )

            sheet_results[
                "trip_station"
            ] = push_sheet_with_retry(
                label="TRIP STATION",
                push_func=push_trip_station_rows,
                rows=all_trip_station_rows,
            )

            print(
                "TRIP STATION SHEET OK:",
                sheet_results[
                    "trip_station"
                ],
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "trip_station",
                "error":
                    str(e),
            })

            print(
                f"TRIP STATION SHEET ERROR: "
                f"{e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 2/4] "
            "TRIP STATION: NO ROWS"
        )

    if all_to_rows:
        try:
            print(
                f"[SHEET 3/4] "
                f"TO "
                f"{len(all_to_rows)} rows"
            )

            sheet_results[
                "to"
            ] = push_sheet_with_retry(
                label="TO",
                push_func=push_to_rows,
                rows=all_to_rows,
            )

            print(
                "TO SHEET OK:",
                sheet_results[
                    "to"
                ],
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "to",
                "error":
                    str(e),
            })

            print(
                f"TO SHEET ERROR: "
                f"{e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 3/4] "
            "TO: NO ROWS"
        )

    if all_to_order_rows:
        try:
            print(
                f"[SHEET 4/4] "
                f"SCAN TO / TO ORDER "
                f"{len(all_to_order_rows)} rows"
            )

            sheet_results[
                "to_order"
            ] = push_sheet_with_retry(
                label="SCAN TO / TO ORDER",
                push_func=push_to_order_rows,
                rows=all_to_order_rows,
            )

            print(
                "SCAN TO / TO ORDER SHEET OK:",
                sheet_results[
                    "to_order"
                ],
            )

        except Exception as e:
            sheet_errors.append({
                "sheet":
                    "to_order",
                "error":
                    str(e),
            })

            print(
                f"SCAN TO / TO ORDER SHEET ERROR: "
                f"{e}"
            )

            print(
                traceback.format_exc()
            )

    else:
        print(
            "[SHEET 4/4] "
            "SCAN TO / TO ORDER: NO ROWS"
        )

    print()
    print("=" * 90)
    print(
        "GOOGLE SHEET WRITER COMPLETE"
    )

    print(
        f"SHEET ERRORS: "
        f"{len(sheet_errors)}"
    )

    print("=" * 90)

    elapsed = round(
        time.time()
        - started_at,
        2,
    )

    with TO_CACHE_LOCK:
        cache_size = len(
            TO_CACHE
        )

    final_success = (
        len(
            failed_results
        )
        == 0
        and len(
            sheet_errors
        )
        == 0
    )

    print()
    print("=" * 90)
    print(
        "DAILY TRIP SYNC COMPLETE"
    )

    print(
        f"TOTAL TRIPS: "
        f"{total}"
    )

    print(
        f"CRAWL SUCCESS: "
        f"{len(success_results)}"
    )

    print(
        f"CRAWL FAILED: "
        f"{len(failed_results)}"
    )

    print(
        f"SHEET ERRORS: "
        f"{len(sheet_errors)}"
    )

    print(
        f"LOADING: "
        f"{total_loading}"
    )

    print(
        f"TO UNIQUE BY TRIP: "
        f"{total_to}"
    )

    print(
        f"BULKY: "
        f"{total_bulky}"
    )

    print(
        f"SCAN TO ROWS: "
        f"{total_scan_to_rows}"
    )

    print(
        f"TO API CALLS: "
        f"{total_scan_to_api_calls}"
    )

    print(
        f"TO CACHE HITS: "
        f"{total_scan_to_cached}"
    )

    print(
        f"TO UNIQUE GLOBAL: "
        f"{cache_size}"
    )

    print(
        f"ORDER CANDIDATES: "
        f"{total_order_candidates}"
    )

    print(
        f"SPX WORKERS: "
        f"{max_workers}"
    )

    print(
        "SHEET WRITER: 1"
    )

    print(
        "ORDER DETAIL CRAWL: DISABLED"
    )

    print(
        f"ELAPSED: "
        f"{elapsed}s"
    )

    print("=" * 90)

    return {
        "success":
            final_success,

        "range": {
            "from":
                start_datetime.isoformat(),
            "to":
                end_datetime.isoformat(),
        },

        "total_trips":
            total,

        "success_count":
            len(
                success_results
            ),

        "failed_count":
            len(
                failed_results
            ),

        "loading_count":
            total_loading,

        "to_count":
            total_to,

        "bulky_count":
            total_bulky,

        "scan_to_rows":
            total_scan_to_rows,

        "scan_to_api_calls":
            total_scan_to_api_calls,

        "scan_to_cache_hits":
            total_scan_to_cached,

        "scan_to_cache_size":
            cache_size,

        "order_candidates":
            total_order_candidates,

        "order_crawl":
            False,

        "max_workers":
            max_workers,

        "sheet_writer":
            1,

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
        result = (
            sync_two_day_trips(
                target_date=None,
                trip_wait_seconds=0,
                max_workers=5,
            )
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