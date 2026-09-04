from __future__ import annotations
import json

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

from api.sheet.common import (
    get_sheet_name_by_gid,
    get_sheets_service,
    read_existing_data,
)


VN_TZ = timezone(
    timedelta(hours=7)
)

TRIP_STATION_GID = 1157738563
VOLUME_GID = 81652235
HUNG_YEN_SOC_ID = 3909
HUNG_YEN_SOC_NAME = "Hung Yen SOC"


def normalize_text(
    value,
) -> str:
    return str(
        value
        or ""
    ).strip()


def safe_int(
    value,
    default=0,
) -> int:
    try:
        if value in (
            None,
            "",
        ):
            return default

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def parse_datetime_value(
    value,
) -> datetime | None:
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
            return value.replace(
                tzinfo=VN_TZ
            )

        return value.astimezone(
            VN_TZ
        )

    if isinstance(
        value,
        date,
    ):
        return datetime(
            value.year,
            value.month,
            value.day,
            0,
            0,
            0,
            tzinfo=VN_TZ,
        )

    text = normalize_text(
        value
    )

    if not text:
        return None

    try:
        number = float(
            text
        )

        while (
            number
            > 10_000_000_000
        ):
            number /= 1000

        if (
            946684800
            <= number
            <= 4102444799
        ):
            return datetime.fromtimestamp(
                number,
                tz=VN_TZ,
            )

    except (
        TypeError,
        ValueError,
        OSError,
        OverflowError,
    ):
        pass

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(
                text,
                fmt,
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=VN_TZ
                )

            return parsed.astimezone(
                VN_TZ
            )

        except ValueError:
            continue

    return None


def get_business_window(
    target_date:
        str
        | date
        | None
        = None,
) -> dict:
    now = datetime.now(
        VN_TZ
    )

    if target_date is None:
        business_date = now.date()

        today_6am = datetime(
            now.year,
            now.month,
            now.day,
            6,
            0,
            0,
            tzinfo=VN_TZ,
        )

        if now < today_6am:
            business_date = (
                business_date
                - timedelta(days=1)
            )

    elif isinstance(
        target_date,
        str,
    ):
        business_date = (
            datetime.strptime(
                target_date,
                "%Y-%m-%d",
            )
            .date()
        )

    elif isinstance(
        target_date,
        date,
    ):
        business_date = target_date

    else:
        raise ValueError(
            "date phải có định dạng YYYY-MM-DD"
        )

    start = datetime(
        business_date.year,
        business_date.month,
        business_date.day,
        6,
        0,
        0,
        tzinfo=VN_TZ,
    )

    end = (
        start
        + timedelta(days=1)
    )

    if now < start:
        cutoff = start

    elif now >= end:
        cutoff = end

    else:
        cutoff = now

    return {
        "date":
            business_date,

        "start":
            start,

        "end":
            end,

        "cutoff":
            cutoff,

        "now":
            now,
    }


def values_to_rows(
    values,
) -> list[dict]:
    if not values:
        return []

    headers = [
        normalize_text(
            value
        )
        for value
        in values[0]
    ]

    rows = []

    for row_index, raw_row in enumerate(
        values[1:],
        start=2,
    ):
        if not any(
            normalize_text(
                value
            )
            for value
            in raw_row
        ):
            continue

        row = {}

        for index, header in enumerate(
            headers
        ):
            if not header:
                continue

            if index < len(
                raw_row
            ):
                value = raw_row[
                    index
                ]

            else:
                value = ""

            row[
                header
            ] = value

        row[
            "_sheet_row"
        ] = row_index

        rows.append(
            row
        )

    return rows


def read_trip_station_rows(
) -> list[dict]:
    service = (
        get_sheets_service()
    )

    sheet_name = (
        get_sheet_name_by_gid(
            TRIP_STATION_GID,
            service=service,
        )
    )

    values = (
        read_existing_data(
            service,
            sheet_name,
        )
    )

    return values_to_rows(
        values
    )

def read_volume_rows(
) -> list[dict]:
    service = (
        get_sheets_service()
    )

    sheet_name = (
        get_sheet_name_by_gid(
            VOLUME_GID,
            service=service,
        )
    )

    values = (
        read_existing_data(
            service,
            sheet_name,
        )
    )

    return values_to_rows(
        values
    )


def normalize_date_value(
    value,
) -> date | None:
    if value in (
        None,
        "",
    ):
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    text = normalize_text(
        value
    )

    if not text:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()

        except ValueError:
            continue

    parsed = parse_datetime_value(
        text
    )

    if parsed is not None:
        return parsed.date()

    return None


def get_volume_summary(
    business_date: date,
) -> dict:
    rows = read_volume_rows()

    matched = {}

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        row_date = normalize_date_value(
            row.get(
                "Operational Date"
            )
            or row.get(
                "operational_date"
            )
            or row.get(
                "date"
            )
        )

        if row_date != business_date:
            continue

        key = normalize_text(
            row.get(
                "_key"
            )
            or row.get(
                "trip_id"
            )
            or row.get(
                "LH Trip Number"
            )
        )

        if not key:
            continue

        matched[
            key
        ] = row

    inbound_order = 0
    bulky = 0
    to_count = 0

    for row in matched.values():
        inbound_order += safe_int(
            row.get(
                "Inbound(order)"
            )
            or row.get(
                "Inbound Order"
            )
            or row.get(
                "inbound_order"
            )
        )

        bulky += safe_int(
            row.get(
                "Bulky"
            )
            or row.get(
                "bulky"
            )
        )

        to_count += safe_int(
            row.get(
                "TO Count"
            )
            or row.get(
                "to_count"
            )
        )

    return {
        "trip_count":
            len(
                matched
            ),

        "inbound_order":
            inbound_order,

        "bulky":
            bulky,

        "to_count":
            to_count,
    }
    
def get_volume_hourly(
    business_date: date,
    start: datetime,
    end: datetime,
    cutoff: datetime,
) -> list[dict]:
    rows = read_volume_rows()

    matched = {}

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        row_date = normalize_date_value(
            row.get(
                "Operational Date"
            )
            or row.get(
                "operational_date"
            )
            or row.get(
                "date"
            )
        )

        if row_date != business_date:
            continue

        key = normalize_text(
            row.get(
                "_key"
            )
            or row.get(
                "trip_id"
            )
            or row.get(
                "LH Trip Number"
            )
        )

        if not key:
            continue

        matched[
            key
        ] = row

    hourly = []

    for index in range(
        24
    ):
        hour_start = (
            start
            + timedelta(
                hours=index
            )
        )

        hour_end = (
            hour_start
            + timedelta(
                hours=1
            )
        )

        hourly.append({
            "hour":
                hour_start.strftime(
                    "%H:00"
                ),

            "from":
                hour_start.isoformat(),

            "to":
                hour_end.isoformat(),

            "volume":
                0,

            "bulky":
                0,

            "to_count":
                0,

            "trip_count":
                0,
        })

    for row in matched.values():
        arrive_time = parse_datetime_value(
            row.get(
                "Actual Arrival Time"
            )
            or row.get(
                "actual_arrival_time"
            )
            or row.get(
                "ata"
            )
        )

        if arrive_time is None:
            continue

        if not (
            start
            <= arrive_time
            < end
        ):
            continue

        if arrive_time > cutoff:
            continue

        index = int(
            (
                arrive_time
                - start
            ).total_seconds()
            // 3600
        )

        if not (
            0
            <= index
            < 24
        ):
            continue

        hourly[
            index
        ][
            "volume"
        ] += safe_int(
            row.get(
                "Inbound(order)"
            )
            or row.get(
                "Inbound Order"
            )
            or row.get(
                "inbound_order"
            )
        )

        hourly[
            index
        ][
            "bulky"
        ] += safe_int(
            row.get(
                "Bulky"
            )
            or row.get(
                "bulky"
            )
        )

        hourly[
            index
        ][
            "to_count"
        ] += safe_int(
            row.get(
                "TO Count"
            )
            or row.get(
                "to_count"
            )
        )

        hourly[
            index
        ][
            "trip_count"
        ] += 1

    return hourly    
def merge_volume_hourly(
    hourly: list[dict],
    volume_hourly: list[dict],
) -> list[dict]:
    volume_map = {
        item.get(
            "hour"
        ): item
        for item in volume_hourly
    }

    result = []

    for item in hourly:
        row = dict(
            item
        )

        volume_item = volume_map.get(
            row.get(
                "hour"
            ),
            {},
        )

        row[
            "volume"
        ] = safe_int(
            volume_item.get(
                "volume"
            )
        )

        row[
            "bulky"
        ] = safe_int(
            volume_item.get(
                "bulky"
            )
        )

        row[
            "to_count"
        ] = safe_int(
            volume_item.get(
                "to_count"
            )
        )

        row[
            "volume_trip_count"
        ] = safe_int(
            volume_item.get(
                "trip_count"
            )
        )

        result.append(
            row
        )

    return result
def get_trip_key(
    row: dict,
) -> str:
    trip_id = normalize_text(
        row.get(
            "trip_id"
        )
    )

    if trip_id:
        return trip_id

    return normalize_text(
        row.get(
            "trip_number"
        )
        or row.get(
            "id"
        )
    )


def get_station_id(
    row: dict,
) -> int:
    return safe_int(
        row.get(
            "station_id"
        )
        or row.get(
            "station"
        )
        or row.get(
            "station_info.id"
        )
        or 0
    )


def get_station_name(
    row: dict,
) -> str:
    return normalize_text(
        row.get(
            "station_name"
        )
        or row.get(
            "station_info.station_name"
        )
    )


def get_sequence_number(
    row: dict,
) -> int:
    return safe_int(
        row.get(
            "sequence_number"
        )
        or row.get(
            "sequence"
        )
        or row.get(
            "station_sequence"
        )
        or 0
    )


def is_hung_yen_row(
    row: dict,
) -> bool:
    station_id = get_station_id(
        row
    )

    if (
        station_id
        == HUNG_YEN_SOC_ID
    ):
        return True

    station_name = (
        get_station_name(
            row
        )
        .lower()
    )

    return (
        station_name
        == HUNG_YEN_SOC_NAME.lower()
    )


def is_inbound_hung_yen_row(
    row: dict,
) -> bool:
    if not is_hung_yen_row(
        row
    ):
        return False

    sequence_number = (
        get_sequence_number(
            row
        )
    )

    return (
        sequence_number
        > 1
    )


def get_sync_time(
    row: dict,
) -> datetime | None:
    return parse_datetime_value(
        row.get(
            "sync_time"
        )
        or row.get(
            "mtime"
        )
        or row.get(
            "update_time"
        )
    )


def get_loaded_time(
    row: dict,
) -> datetime | None:
    return parse_datetime_value(
        row.get(
            "loaded_time"
        )
    )


def get_arrive_time(
    row: dict,
) -> datetime | None:
    return parse_datetime_value(
        row.get(
            "ata"
        )
        or row.get(
            "arrive_time"
        )
        or row.get(
            "actual_arrival_time"
        )
    )


def get_unseal_time(
    row: dict,
) -> datetime | None:
    return parse_datetime_value(
        row.get(
            "unseal_time"
        )
        or row.get(
            "unsealed_time"
        )
    )


def get_unloaded_time(
    row: dict,
) -> datetime | None:
    return parse_datetime_value(
        row.get(
            "unloaded_time"
        )
    )


def get_station_key(
    row: dict,
) -> tuple:
    return (
        get_trip_key(
            row
        ),
        get_sequence_number(
            row
        ),
        get_station_id(
            row
        ),
    )


def row_is_newer(
    new_row: dict,
    old_row: dict,
) -> bool:
    new_sync = get_sync_time(
        new_row
    )

    old_sync = get_sync_time(
        old_row
    )

    if (
        new_sync is not None
        and old_sync is not None
    ):
        if new_sync != old_sync:
            return (
                new_sync
                > old_sync
            )

    elif (
        new_sync is not None
        and old_sync is None
    ):
        return True

    elif (
        new_sync is None
        and old_sync is not None
    ):
        return False

    new_sheet_row = safe_int(
        new_row.get(
            "_sheet_row"
        )
    )

    old_sheet_row = safe_int(
        old_row.get(
            "_sheet_row"
        )
    )

    return (
        new_sheet_row
        >= old_sheet_row
    )


def dedupe_station_rows(
    rows: list[dict],
) -> list[dict]:
    latest = {}

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        trip_key = get_trip_key(
            row
        )

        if not trip_key:
            continue

        station_key = (
            get_station_key(
                row
            )
        )

        current = latest.get(
            station_key
        )

        if (
            current is None
            or row_is_newer(
                row,
                current,
            )
        ):
            latest[
                station_key
            ] = row

    return list(
        latest.values()
    )


def build_trip_states(
    rows: list[dict],
) -> tuple[
    dict,
    set,
    set,
]:
    trip_rows = {}

    hung_yen_seen = set()
    inbound_seen = set()

    for row in rows:
        trip_key = get_trip_key(
            row
        )

        if not trip_key:
            continue

        trip_rows.setdefault(
            trip_key,
            []
        ).append(
            row
        )

        if is_hung_yen_row(
            row
        ):
            hung_yen_seen.add(
                trip_key
            )

    trip_states = {}

    for (
        trip_key,
        station_rows,
    ) in trip_rows.items():
        hung_yen_rows = [
            row
            for row
            in station_rows
            if is_inbound_hung_yen_row(
                row
            )
        ]

        if not hung_yen_rows:
            continue

        hung_yen_row = max(
            hung_yen_rows,
            key=lambda row: (
                get_sequence_number(
                    row
                ),
                safe_int(
                    row.get(
                        "_sheet_row"
                    )
                ),
            ),
        )

        inbound_seen.add(
            trip_key
        )

        hy_sequence = (
            get_sequence_number(
                hung_yen_row
            )
        )

        arrive_time = (
            get_arrive_time(
                hung_yen_row
            )
        )

        unseal_time = (
            get_unseal_time(
                hung_yen_row
            )
        )

        unloaded_time = (
            get_unloaded_time(
                hung_yen_row
            )
        )

        loaded_candidates = []

        for row in station_rows:
            sequence_number = (
                get_sequence_number(
                    row
                )
            )

            if (
                sequence_number
                >= hy_sequence
            ):
                continue

            loaded_time = (
                get_loaded_time(
                    row
                )
            )

            if loaded_time is None:
                continue

            if (
                arrive_time is not None
                and loaded_time
                > arrive_time
            ):
                continue

            loaded_candidates.append(
                loaded_time
            )

        loaded_time = (
            max(
                loaded_candidates
            )
            if loaded_candidates
            else None
        )

        trip_states[
            trip_key
        ] = {
            "trip_id":
                trip_key,

            "hung_yen_sequence":
                hy_sequence,

            "loaded_time":
                loaded_time,

            "arrive_time":
                arrive_time,

            "unseal_time":
                unseal_time,

            "unloaded_time":
                unloaded_time,
        }

    return (
        trip_states,
        hung_yen_seen,
        inbound_seen,
    )


def is_event_in_window(
    event_time: datetime | None,
    start: datetime,
    end: datetime,
    cutoff: datetime,
) -> bool:
    if event_time is None:
        return False

    return (
        start
        <= event_time
        < end
        and event_time
        <= cutoff
    )


def get_hour_index(
    event_time: datetime | None,
    start: datetime,
) -> int | None:
    if event_time is None:
        return None

    seconds = (
        event_time
        - start
    ).total_seconds()

    index = int(
        seconds
        // 3600
    )

    if (
        0
        <= index
        < 24
    ):
        return index

    return None


def is_waiting_at(
    state: dict,
    snapshot_time: datetime,
    start: datetime | None = None,
    end: datetime | None = None,
) -> bool:
    arrive_time = state.get(
        "arrive_time"
    )

    unseal_time = state.get(
        "unseal_time"
    )

    if arrive_time is None:
        return False

    if (
        start is not None
        and arrive_time < start
    ):
        return False

    if (
        end is not None
        and arrive_time >= end
    ):
        return False

    if (
        arrive_time
        >= snapshot_time
    ):
        return False

    if (
        unseal_time is not None
        and unseal_time
        <= snapshot_time
    ):
        return False

    return True

def get_current_status(
    state: dict,
    cutoff: datetime,
    start: datetime | None = None,
    end: datetime | None = None,
) -> str:
    loaded_time = state.get(
        "loaded_time"
    )

    arrive_time = state.get(
        "arrive_time"
    )

    unseal_time = state.get(
        "unseal_time"
    )

    unloaded_time = state.get(
        "unloaded_time"
    )

    if (
        unloaded_time is not None
        and unloaded_time <= cutoff
        and (
            start is None
            or unloaded_time >= start
        )
        and (
            end is None
            or unloaded_time < end
        )
    ):
        return "UNLOADED"

    if (
        unseal_time is not None
        and unseal_time <= cutoff
        and (
            start is None
            or unseal_time >= start
        )
        and (
            end is None
            or unseal_time < end
        )
    ):
        return "UNSEAL"

    if (
        arrive_time is not None
        and arrive_time <= cutoff
        and (
            start is None
            or arrive_time >= start
        )
        and (
            end is None
            or arrive_time < end
        )
    ):
        return "WAITING"

    if (
        loaded_time is not None
        and loaded_time <= cutoff
        and (
            start is None
            or loaded_time >= start
        )
        and (
            end is None
            or loaded_time < end
        )
    ):
        return "LOADED"

    return "NOT_ARRIVED"


def build_hourly(
    trip_states: dict,
    start: datetime,
    end: datetime,
    cutoff: datetime,
) -> list[dict]:
    hourly = []

    for index in range(
        24
    ):
        hour_start = (
            start
            + timedelta(
                hours=index
            )
        )

        hour_end = (
            hour_start
            + timedelta(
                hours=1
            )
        )

        item = {
            "hour":
                hour_start.strftime(
                    "%H:00"
                ),

            "label":
                (
                    f"{hour_start.strftime('%H:00')}"
                    "-"
                    f"{(hour_end - timedelta(seconds=1)).strftime('%H:59')}"
                ),

            "from":
                hour_start.isoformat(),

            "to":
                hour_end.isoformat(),

            "loaded":
                0,

            "arrived":
                0,

            "unseal":
                0,

            "unloaded":
                0,

            "waiting":
                0,
        }

        if (
            hour_start
            >= cutoff
        ):
            hourly.append(
                item
            )
            continue

        loaded_seen = set()
        arrived_seen = set()
        unseal_seen = set()
        unloaded_seen = set()
        waiting_seen = set()

        for (
            trip_key,
            state,
        ) in trip_states.items():
            loaded_time = state.get(
                "loaded_time"
            )

            arrive_time = state.get(
                "arrive_time"
            )

            unseal_time = state.get(
                "unseal_time"
            )

            unloaded_time = state.get(
                "unloaded_time"
            )

            if (
                loaded_time is not None
                and hour_start
                <= loaded_time
                < hour_end
                and loaded_time
                <= cutoff
            ):
                loaded_seen.add(
                    trip_key
                )

            if (
                arrive_time is not None
                and hour_start
                <= arrive_time
                < hour_end
                and arrive_time
                <= cutoff
            ):
                arrived_seen.add(
                    trip_key
                )

            if (
                unseal_time is not None
                and hour_start
                <= unseal_time
                < hour_end
                and unseal_time
                <= cutoff
            ):
                unseal_seen.add(
                    trip_key
                )

            if (
                unloaded_time is not None
                and hour_start
                <= unloaded_time
                < hour_end
                and unloaded_time
                <= cutoff
            ):
                unloaded_seen.add(
                    trip_key
                )

            snapshot_time = min(
                hour_end,
                cutoff,
            )

            if is_waiting_at(
                state,
                snapshot_time,
                start=start,
                end=end,
            ):
                waiting_seen.add(
                    trip_key
                )

        item[
            "loaded"
        ] = len(
            loaded_seen
        )

        item[
            "arrived"
        ] = len(
            arrived_seen
        )

        item[
            "unseal"
        ] = len(
            unseal_seen
        )

        item[
            "unloaded"
        ] = len(
            unloaded_seen
        )

        item[
            "waiting"
        ] = len(
            waiting_seen
        )

        hourly.append(
            item
        )

    return hourly


def build_total(
    trip_states: dict,
    start: datetime,
    end: datetime,
    cutoff: datetime,
) -> dict:
    loaded_seen = set()
    arrived_seen = set()
    unseal_seen = set()
    unloaded_seen = set()
    waiting_seen = set()

    status_counts = {
        "loaded":
            0,

        "waiting":
            0,

        "unseal":
            0,

        "unloaded":
            0,

        "not_arrived":
            0,
    }

    for (
        trip_key,
        state,
    ) in trip_states.items():
        loaded_time = state.get(
            "loaded_time"
        )

        arrive_time = state.get(
            "arrive_time"
        )

        unseal_time = state.get(
            "unseal_time"
        )

        unloaded_time = state.get(
            "unloaded_time"
        )

        if is_event_in_window(
            loaded_time,
            start,
            end,
            cutoff,
        ):
            loaded_seen.add(
                trip_key
            )

        if is_event_in_window(
            arrive_time,
            start,
            end,
            cutoff,
        ):
            arrived_seen.add(
                trip_key
            )

        if is_event_in_window(
            unseal_time,
            start,
            end,
            cutoff,
        ):
            unseal_seen.add(
                trip_key
            )

        if is_event_in_window(
            unloaded_time,
            start,
            end,
            cutoff,
        ):
            unloaded_seen.add(
                trip_key
            )

        if is_waiting_at(
            state,
            cutoff,
            start=start,
            end=end,
        ):
            waiting_seen.add(
                trip_key
            )

        status = get_current_status(
            state,
            cutoff,
        )

        if status == "LOADED":
            status_counts[
                "loaded"
            ] += 1

        elif status == "WAITING":
            status_counts[
                "waiting"
            ] += 1

        elif status == "UNSEAL":
            status_counts[
                "unseal"
            ] += 1

        elif status == "UNLOADED":
            status_counts[
                "unloaded"
            ] += 1

        else:
            status_counts[
                "not_arrived"
            ] += 1

    return {
        "loaded":
            len(
                loaded_seen
            ),

        "arrived":
            len(
                arrived_seen
            ),

        "unseal":
            len(
                unseal_seen
            ),

        "unloaded":
            len(
                unloaded_seen
            ),

        "waiting":
            len(
                waiting_seen
            ),

        "status":
            status_counts,
    }


def get_vehicle_status(
    target_date:
        str
        | date
        | None
        = None,
) -> dict:
    window = get_business_window(
        target_date
    )

    start = window[
        "start"
    ]

    end = window[
        "end"
    ]

    cutoff = window[
        "cutoff"
    ]

    source_rows = (
        read_trip_station_rows()
    )

    latest_rows = (
        dedupe_station_rows(
            source_rows
        )
    )

    (
        trip_states,
        hung_yen_seen,
        inbound_seen,
    ) = build_trip_states(
        latest_rows
    )

    hourly = build_hourly(
        trip_states,
        start,
        end,
        cutoff,
    )

    volume_hourly = get_volume_hourly(
        business_date=
            window[
                "date"
            ],

        start=
            start,

        end=
            end,

        cutoff=
            cutoff,
    )

    hourly = merge_volume_hourly(
        hourly=
            hourly,

        volume_hourly=
            volume_hourly,
    )

    total = build_total(
        trip_states,
        start,
        end,
        cutoff,
    )

    volume = get_volume_summary(
        window[
            "date"
        ]
    )
    return {
        "success":
            True,

        "date":
            window[
                "date"
            ].isoformat(),

        "from":
            start.isoformat(),

        "to":
            end.isoformat(),

        "cutoff":
            cutoff.isoformat(),

        "source_rows":
            len(
                source_rows
            ),

        "latest_rows":
            len(
                latest_rows
            ),

        "hung_yen":
            len(
                hung_yen_seen
            ),

        "inbound":
            len(
                inbound_seen
            ),

        "hourly":
            hourly,
        "volume":
            volume,
        "total":
            total,
            
    }


def main():
    result = get_vehicle_status(
        target_date=None
    )

    print()

    print(
        "NGAY KHO:",
        result[
            "date"
        ],
    )

    print(
        "FROM:",
        result[
            "from"
        ],
    )

    print(
        "TO:",
        result[
            "to"
        ],
    )

    print(
        "CUTOFF:",
        result[
            "cutoff"
        ],
    )

    print()

    print(
        f"{'GIO':<15}"
        f"{'LOADED':>9}"
        f"{'ARRIVED':>10}"
        f"{'UNSEAL':>9}"
        f"{'UNLOADED':>11}"
        f"{'WAITING':>10}"
    )

    print(
        "-" * 64
    )

    for item in result[
        "hourly"
    ]:
        print(
            f"{item['label']:<15}"
            f"{item['loaded']:>9}"
            f"{item['arrived']:>10}"
            f"{item['unseal']:>9}"
            f"{item['unloaded']:>11}"
            f"{item['waiting']:>10}"
        )

    print(
        "-" * 64
    )

    total = result[
        "total"
    ]

    print(
        f"{'TOTAL':<15}"
        f"{total['loaded']:>9}"
        f"{total['arrived']:>10}"
        f"{total['unseal']:>9}"
        f"{total['unloaded']:>11}"
        f"{total['waiting']:>10}"
    )

    print()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()