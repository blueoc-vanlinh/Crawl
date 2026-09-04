from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from config import BASE_URL
from core.spx_request import spx_get


TRIP_HISTORY_API = (
    BASE_URL
    + "/api/admin/transportation/trip/history/list"
)

TRIP_HANDOVER_API = (
    BASE_URL
    + "/api/admin/transportation/trip/list"
)


def _is_empty(
    value,
):
    return value in (
        None,
        "",
        [],
        {},
    )


def _trip_identity(
    item,
):
    if not isinstance(
        item,
        dict,
    ):
        return ""

    trip_id = (
        item.get("id")
        or item.get("trip_id")
    )

    if trip_id not in (
        None,
        "",
    ):
        return (
            "ID:"
            + str(
                trip_id
            ).strip()
        )

    trip_number = str(
        item.get(
            "trip_number",
            "",
        )
        or ""
    ).strip().upper()

    if trip_number:
        return (
            "NUMBER:"
            + trip_number
        )

    return ""


def _extract_rows_total(
    data,
):
    if not isinstance(
        data,
        dict,
    ):
        return [], 0

    payload = (
        data.get(
            "data"
        )
        or {}
    )

    if isinstance(
        payload,
        list,
    ):
        return (
            payload,
            len(
                payload
            ),
        )

    if not isinstance(
        payload,
        dict,
    ):
        return [], 0

    rows = (
        payload.get(
            "list"
        )
        or payload.get(
            "items"
        )
        or payload.get(
            "rows"
        )
        or payload.get(
            "records"
        )
        or []
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = []

    total = 0

    for key in (
        "total",
        "total_count",
        "count",
    ):
        try:
            value = int(
                payload.get(
                    key
                )
                or 0
            )

            if value > 0:
                total = value
                break

        except (
            TypeError,
            ValueError,
        ):
            pass

    return (
        rows,
        total,
    )


def get_history_trip(
    mtime_start,
    mtime_end,
    page=1,
    count=100,
):
    params = {
        "trip_station_status":
            90,

        "mtime":
            f"{mtime_start},{mtime_end}",

        "pageno":
            page,

        "count":
            count,
    }

    response = spx_get(
        TRIP_HISTORY_API,
        params=
            params,
        timeout=
            60,
    )

    data = (
        response.json()
    )

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
                "SPX trip history error",
            )
        )

    return data


def get_handover_trip(
    mtime_start,
    mtime_end,
    page=1,
    count=100,
):
    params = {
        "trip_station_status":
            40,

        "mtime":
            f"{mtime_start},{mtime_end}",

        "pageno":
            page,

        "count":
            count,

        "query_type":
            2,
    }

    response = spx_get(
        TRIP_HANDOVER_API,
        params=
            params,
        timeout=
            60,
    )

    data = (
        response.json()
    )

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
                "SPX trip handover error",
            )
        )

    return data


def _crawl_source(
    source_name,
    request_func,
    mtime_start,
    mtime_end,
    count=100,
    max_workers=5,
):
    count = max(
        1,
        int(
            count
        ),
    )

    max_workers = max(
        1,
        min(
            int(
                max_workers
            ),
            5,
        ),
    )

    first_data = request_func(
        mtime_start=
            mtime_start,

        mtime_end=
            mtime_end,

        page=
            1,

        count=
            count,
    )

    (
        first_rows,
        total,
    ) = (
        _extract_rows_total(
            first_data
        )
    )

    print(
        f"[{source_name}] "
        f"PAGE 1 "
        f"| ROWS={len(first_rows)} "
        f"| TOTAL={total}"
    )

    if not first_rows:
        print(
            f"[{source_name}] "
            "DONE "
            "| RAW=0 "
            "| UNIQUE=0 "
            f"| TOTAL={total}"
        )

        return []

    page_results = {
        1:
            first_rows
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
            f"[{source_name}] "
            f"WORKERS={worker_count} "
            f"| PAGES={total_pages}"
        )

        with ThreadPoolExecutor(
            max_workers=
                worker_count
        ) as executor:

            future_map = {}

            for page in range(
                2,
                total_pages + 1,
            ):
                future = (
                    executor.submit(
                        request_func,
                        mtime_start,
                        mtime_end,
                        page,
                        count,
                    )
                )

                future_map[
                    future
                ] = page

            for future in as_completed(
                future_map
            ):
                page = (
                    future_map[
                        future
                    ]
                )

                try:
                    data = (
                        future.result()
                    )

                    (
                        rows,
                        current_total,
                    ) = (
                        _extract_rows_total(
                            data
                        )
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
                        f"[{source_name}] "
                        f"PAGE {page} "
                        f"| ROWS={len(rows)} "
                        "| DONE"
                    )

                except Exception as exc:
                    print(
                        f"[{source_name}] "
                        f"PAGE {page} "
                        f"| ERROR={exc}"
                    )

                    raise

    result = []

    seen = set()

    seen_pages = set()

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
                item.get(
                    "id"
                ),
                item.get(
                    "trip_id"
                ),
                item.get(
                    "trip_number"
                ),
            )
            for item
            in rows
            if isinstance(
                item,
                dict,
            )
        )

        if (
            page_signature
            in seen_pages
        ):
            print(
                f"[{source_name}] "
                f"PAGE {page} "
                "| REPEATED SKIPPED"
            )

            continue

        seen_pages.add(
            page_signature
        )

        for item in rows:
            if not isinstance(
                item,
                dict,
            ):
                continue

            key = (
                _trip_identity(
                    item
                )
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

            result.append(
                row
            )

    print(
        f"[{source_name}] "
        "DONE "
        f"| RAW={received} "
        f"| UNIQUE={len(result)} "
        f"| TOTAL={total}"
    )

    return result


def get_all_history_trip(
    mtime_start,
    mtime_end,
    count=100,
    max_workers=5,
):
    return _crawl_source(
        source_name=
            "HISTORY_COMPLETED",

        request_func=
            get_history_trip,

        mtime_start=
            mtime_start,

        mtime_end=
            mtime_end,

        count=
            count,

        max_workers=
            max_workers,
    )


def get_all_handover_trip(
    mtime_start,
    mtime_end,
    count=100,
    max_workers=5,
):
    return _crawl_source(
        source_name=
            "HANDOVER",

        request_func=
            get_handover_trip,

        mtime_start=
            mtime_start,

        mtime_end=
            mtime_end,

        count=
            count,

        max_workers=
            max_workers,
    )


def _merge_trip_rows(
    old,
    new,
):
    if not isinstance(
        old,
        dict,
    ):
        return dict(
            new
        )

    if not isinstance(
        new,
        dict,
    ):
        return dict(
            old
        )

    merged = dict(
        old
    )

    for (
        key,
        value,
    ) in new.items():

        if (
            key
            == "_trip_source"
        ):
            continue

        if not _is_empty(
            value
        ):
            merged[
                key
            ] = value

    old_source = str(
        old.get(
            "_trip_source",
            "",
        )
        or ""
    ).strip()

    new_source = str(
        new.get(
            "_trip_source",
            "",
        )
        or ""
    ).strip()

    sources = []

    for source in (
        old_source,
        new_source,
    ):
        for part in source.split(
            "+"
        ):
            part = (
                part.strip()
            )

            if (
                part
                and part
                not in sources
            ):
                sources.append(
                    part
                )

    merged[
        "_trip_source"
    ] = "+".join(
        sources
    )

    return merged


def merge_history_handover(
    history_rows,
    handover_rows,
):
    merged_map = {}

    history_keys = set()

    handover_keys = set()

    for item in (
        handover_rows
        or []
    ):
        key = (
            _trip_identity(
                item
            )
        )

        if not key:
            continue

        handover_keys.add(
            key
        )

        merged_map[
            key
        ] = dict(
            item
        )

    for item in (
        history_rows
        or []
    ):
        key = (
            _trip_identity(
                item
            )
        )

        if not key:
            continue

        history_keys.add(
            key
        )

        if (
            key
            in merged_map
        ):
            merged_map[
                key
            ] = (
                _merge_trip_rows(
                    merged_map[
                        key
                    ],
                    item,
                )
            )

        else:
            merged_map[
                key
            ] = dict(
                item
            )

    overlap = len(
        history_keys
        & handover_keys
    )

    handover_only = len(
        handover_keys
        - history_keys
    )

    history_only = len(
        history_keys
        - handover_keys
    )

    result = list(
        merged_map.values()
    )

    print()
    print(
        "=" * 90
    )

    print(
        "TRIP SOURCES MERGED"
    )

    print(
        f"HISTORY COMPLETED: "
        f"{len(history_rows)}"
    )

    print(
        f"HANDOVER: "
        f"{len(handover_rows)}"
    )

    print(
        f"OVERLAP: "
        f"{overlap}"
    )

    print(
        f"HISTORY ONLY: "
        f"{history_only}"
    )

    print(
        f"HANDOVER ONLY: "
        f"{handover_only}"
    )

    print(
        f"UNIQUE FINAL: "
        f"{len(result)}"
    )

    print(
        "=" * 90
    )
    print()

    return result


def get_all_trip(
    mtime_start,
    mtime_end,
    count=100,
    max_workers=5,
):
    max_workers = max(
        1,
        min(
            int(
                max_workers
            ),
            5,
        ),
    )

    print()
    print(
        "=" * 100
    )

    print(
        "CRAWL TRIPS - HISTORY + HANDOVER"
    )

    print(
        f"MTIME: "
        f"{mtime_start},{mtime_end}"
    )

    print(
        "HISTORY STATUS: 90"
    )

    print(
        "HANDOVER STATUS: 40"
    )

    print(
        "HANDOVER QUERY_TYPE: 2"
    )

    print(
        f"COUNT: {count}"
    )

    print(
        f"WORKERS: {max_workers}"
    )

    print(
        "=" * 100
    )

    with ThreadPoolExecutor(
        max_workers=
            2
    ) as executor:

        history_future = (
            executor.submit(
                get_all_history_trip,
                mtime_start,
                mtime_end,
                count,
                max_workers,
            )
        )

        handover_future = (
            executor.submit(
                get_all_handover_trip,
                mtime_start,
                mtime_end,
                count,
                max_workers,
            )
        )

        history_rows = (
            history_future.result()
        )

        handover_rows = (
            handover_future.result()
        )

    return (
        merge_history_handover(
            history_rows=
                history_rows,

            handover_rows=
                handover_rows,
        )
    )