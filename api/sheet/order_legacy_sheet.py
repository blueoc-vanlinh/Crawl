import json

from api.sheet.common import (
    SPREADSHEET_ID,
    convert_nested_times,
    flatten_dict,
    format_timestamp,
    get_sheet_name_by_gid,
    get_sheet_names,
    get_sheets_service,
    now_vn,
    read_sheet_range,
    unwrap_data,
    upsert_rows,
)


ORDER_GID = 1367050328
PUSH_ORDER_GID = 2082447880


def find_values_recursive(
    data,
    wanted_keys,
):
    found = []

    wanted_keys = {
        str(
            key
        ).lower()
        for key
        in wanted_keys
    }

    if isinstance(
        data,
        dict,
    ):
        for (
            key,
            value
        ) in data.items():
            if (
                str(
                    key
                ).lower()
                in wanted_keys
            ):
                found.append(
                    (
                        key,
                        value,
                    )
                )

            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):
                found.extend(
                    find_values_recursive(
                        value,
                        wanted_keys,
                    )
                )

    elif isinstance(
        data,
        list,
    ):
        for item in data:
            found.extend(
                find_values_recursive(
                    item,
                    wanted_keys,
                )
            )

    return found


def get_event_timestamp(
    event,
):
    if not isinstance(
        event,
        dict,
    ):
        return 0

    possible_keys = (
        "event_time",
        "tracking_time",
        "status_time",
        "update_time",
        "updated_time",
        "ctime",
        "mtime",
        "create_time",
        "created_time",
        "scan_time",
        "operation_time",
        "time",
        "timestamp",
    )

    for key in possible_keys:
        if key not in event:
            continue

        value = event.get(
            key
        )

        if value in (
            None,
            "",
            0,
            "0",
        ):
            continue

        try:
            ts = float(
                value
            )

            if (
                ts
                > 10_000_000_000
            ):
                ts /= 1000

            if (
                ts
                > 946684800
            ):
                return ts

        except (
            ValueError,
            TypeError,
        ):
            pass

    return 0


def collect_dicts(
    data,
):
    items = []

    if isinstance(
        data,
        dict,
    ):
        items.append(
            data
        )

        for value in data.values():
            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):
                items.extend(
                    collect_dicts(
                        value
                    )
                )

    elif isinstance(
        data,
        list,
    ):
        for item in data:
            if isinstance(
                item,
                (
                    dict,
                    list,
                ),
            ):
                items.extend(
                    collect_dicts(
                        item
                    )
                )

    return items


def extract_latest_tracking(
    tracking_response,
):
    tracking = unwrap_data(
        tracking_response
    )

    result = {
        "current_status":
            "",

        "current_status_time":
            "",

        "latest_station":
            "",

        "latest_event":
            "",
    }

    if tracking is None:
        return result

    all_dicts = collect_dicts(
        tracking
    )

    timed_events = []

    for event in all_dicts:
        ts = get_event_timestamp(
            event
        )

        if ts:
            timed_events.append(
                (
                    ts,
                    event,
                )
            )

    latest_event = None
    latest_ts = 0

    if timed_events:
        timed_events.sort(
            key=lambda item:
                item[0],
            reverse=True,
        )

        (
            latest_ts,
            latest_event,
        ) = timed_events[0]

        result[
            "current_status_time"
        ] = format_timestamp(
            latest_ts
        )

    if latest_event:
        for key in (
            "status_name",
            "status",
            "order_status_name",
            "order_status",
            "tracking_status_name",
            "tracking_status",
            "event_name",
            "description",
            "message",
            "action",
            "operation",
        ):
            value = latest_event.get(
                key
            )

            if value not in (
                None,
                "",
            ):
                result[
                    "latest_event"
                ] = value

                result[
                    "current_status"
                ] = value

                break

        for key in (
            "station_name",
            "current_station_name",
            "location_name",
            "hub_name",
            "site_name",
            "operation_station_name",
        ):
            value = latest_event.get(
                key
            )

            if value not in (
                None,
                "",
            ):
                result[
                    "latest_station"
                ] = value

                break

    if not result[
        "current_status"
    ]:
        found = find_values_recursive(
            tracking,
            (
                "current_status_name",
                "current_status",
                "status_name",
                "order_status_name",
                "order_status",
                "tracking_status_name",
                "tracking_status",
                "shipment_status_name",
                "shipment_status",
                "status",
            ),
        )

        for (
            _,
            value
        ) in found:
            if value not in (
                None,
                "",
            ):
                result[
                    "current_status"
                ] = value

                break

    if not result[
        "latest_station"
    ]:
        found = find_values_recursive(
            tracking,
            (
                "current_station_name",
                "station_name",
                "location_name",
                "hub_name",
                "site_name",
            ),
        )

        for (
            _,
            value
        ) in found:
            if value not in (
                None,
                "",
            ):
                result[
                    "latest_station"
                ] = value

                break

    return result


def build_order_row(
    shipment_id,
    order_data,
):
    shipment_id = str(
        shipment_id or ""
    ).strip().upper()

    if not shipment_id:
        raise RuntimeError(
            "shipment_id rỗng"
        )

    if not isinstance(
        order_data,
        dict,
    ):
        order_data = {}

    row = {
        "_key":
            shipment_id,

        "shipment_id":
            shipment_id,
    }

    tracking = order_data.get(
        "tracking_info",
        {},
    )

    recipient = order_data.get(
        "recipient_info",
        {},
    )

    trade = order_data.get(
        "trade_info",
        {},
    )

    pickup = order_data.get(
        "pickup_switches",
        {},
    )

    latest = extract_latest_tracking(
        tracking
    )

    row[
        "current_status"
    ] = latest.get(
        "current_status",
        "",
    )

    row[
        "current_status_time"
    ] = latest.get(
        "current_status_time",
        "",
    )

    row[
        "latest_station"
    ] = latest.get(
        "latest_station",
        "",
    )

    row[
        "latest_event"
    ] = latest.get(
        "latest_event",
        "",
    )

    tracking_data = unwrap_data(
        tracking
    )

    if isinstance(
        tracking_data,
        dict,
    ):
        for (
            key,
            value
        ) in flatten_dict(
            tracking_data
        ).items():
            row[
                f"tracking.{key}"
            ] = value

    elif tracking_data is not None:
        row[
            "tracking.raw"
        ] = json.dumps(
            convert_nested_times(
                tracking_data
            ),
            ensure_ascii=False,
        )

    recipient_data = unwrap_data(
        recipient
    )

    if isinstance(
        recipient_data,
        dict,
    ):
        for (
            key,
            value
        ) in flatten_dict(
            recipient_data
        ).items():
            row[
                f"recipient.{key}"
            ] = value

    elif recipient_data is not None:
        row[
            "recipient.raw"
        ] = json.dumps(
            convert_nested_times(
                recipient_data
            ),
            ensure_ascii=False,
        )

    trade_data = unwrap_data(
        trade
    )

    if isinstance(
        trade_data,
        dict,
    ):
        for (
            key,
            value
        ) in flatten_dict(
            trade_data
        ).items():
            row[
                f"trade.{key}"
            ] = value

    elif trade_data is not None:
        row[
            "trade.raw"
        ] = json.dumps(
            convert_nested_times(
                trade_data
            ),
            ensure_ascii=False,
        )

    pickup_data = unwrap_data(
        pickup
    )

    if isinstance(
        pickup_data,
        dict,
    ):
        for (
            key,
            value
        ) in flatten_dict(
            pickup_data
        ).items():
            row[
                f"pickup.{key}"
            ] = value

    elif pickup_data not in (
        None,
        {},
        [],
    ):
        row[
            "pickup.raw"
        ] = json.dumps(
            convert_nested_times(
                pickup_data
            ),
            ensure_ascii=False,
        )

    row[
        "sync_time"
    ] = now_vn()

    return row


def get_push_order_ids(
    service=None,
):
    if service is None:
        service = get_sheets_service()

    sheet_names = get_sheet_names(
        service
    )

    push_sheet = sheet_names.get(
        PUSH_ORDER_GID
    )

    if not push_sheet:
        raise RuntimeError(
            f"Không tìm thấy sheet "
            f"gid={PUSH_ORDER_GID}"
        )

    values = read_sheet_range(
        service=
            service,

        sheet_name=
            push_sheet,

        cell_range=
            "A2:A",
    )

    shipment_ids = []

    seen = set()

    for row in values:
        if not row:
            continue

        value = str(
            row[0]
            or ""
        ).strip().upper()

        if not value:
            continue

        if not value.startswith(
            "SPXVN"
        ):
            continue

        if value in seen:
            continue

        seen.add(
            value
        )

        shipment_ids.append(
            value
        )

    return shipment_ids


def push_order_rows(
    rows,
    service=None,
):
    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
        }

    if service is None:
        service = get_sheets_service()

    order_sheet = get_sheet_name_by_gid(
        gid=
            ORDER_GID,

        service=
            service,
    )

    return upsert_rows(
        service=
            service,

        sheet_name=
            order_sheet,

        rows=
            rows,

        merge_non_empty=
            True,
    )


def push_order(
    shipment_id,
    order_data,
    service=None,
):
    row = build_order_row(
        shipment_id=
            shipment_id,

        order_data=
            order_data,
    )

    result = push_order_rows(
        rows=[
            row
        ],

        service=
            service,
    )

    return {
        "row":
            row,

        "sheet":
            result,
    }