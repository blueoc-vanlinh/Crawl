import json
import os
from datetime import datetime, timezone, timedelta

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SPREADSHEET_ID = "1YfRPJd99ipWnUqPqXCFDlQzHj8ADxdP_UE1363KqLS8"

TRIP_GID = 0
TO_GID = 91531087
ORDER_GID = 1367050328
PUSH_ORDER_GID = 2082447880
TRIP_STATION_GID = 1157738563

SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "service_account.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

VN_TZ = timezone(
    timedelta(hours=7)
)


def get_sheets_service():
    if not os.path.exists(
        SERVICE_ACCOUNT_FILE
    ):
        raise RuntimeError(
            "Không tìm thấy service_account.json tại: "
            f"{SERVICE_ACCOUNT_FILE}"
        )

    credentials = (
        Credentials
        .from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False
    )


def get_sheet_names(
    service=None
):
    if service is None:
        service = (
            get_sheets_service()
        )

    result = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            fields=
                "sheets.properties"
        )
        .execute()
    )

    mapping = {}

    for sheet in result.get(
        "sheets",
        []
    ):
        props = sheet.get(
            "properties",
            {}
        )

        sheet_id = props.get(
            "sheetId"
        )

        title = props.get(
            "title"
        )

        if (
            sheet_id is not None
            and title
        ):
            mapping[
                int(sheet_id)
            ] = title

    return mapping


def is_time_field(
    key
):
    key = str(
        key
    ).strip().lower()

    exact_fields = {
        "ctime",
        "mtime",
        "ata",
        "atd",
        "sta",
        "std",
        "eta",
        "etd",
        "trip_date",
        "created_at",
        "updated_at",
        "deleted_at",
        "create_at",
        "update_at",
        "start_at",
        "end_at",
        "created_time",
        "updated_time",
        "deleted_time",
        "time",
        "timestamp",
    }

    if key in exact_fields:
        return True

    return key.endswith(
        (
            "_time",
            "_timestamp",
            "_datetime",
            "_date_time",
            "_date",
        )
    )


def format_timestamp(
    value
):
    if value in (
        None,
        "",
        0,
        "0",
    ):
        return ""

    if isinstance(
        value,
        str
    ):
        stripped = (
            value.strip()
        )

        if not stripped:
            return ""

        try:
            float(stripped)
        except ValueError:
            return value

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
            < 946684800
        ):
            return value

        dt = (
            datetime
            .fromtimestamp(
                ts,
                tz=timezone.utc
            )
            .astimezone(
                VN_TZ
            )
        )

        return dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
        OSError,
    ):
        return value


def convert_nested_times(
    data
):
    if isinstance(
        data,
        dict
    ):
        result = {}

        for (
            key,
            value
        ) in data.items():
            if isinstance(
                value,
                (
                    dict,
                    list,
                )
            ):
                result[
                    key
                ] = (
                    convert_nested_times(
                        value
                    )
                )

            elif is_time_field(
                key
            ):
                result[
                    key
                ] = (
                    format_timestamp(
                        value
                    )
                )

            else:
                result[
                    key
                ] = value

        return result

    if isinstance(
        data,
        list
    ):
        return [
            convert_nested_times(
                item
            )
            for item
            in data
        ]

    return data


def flatten_dict(
    data,
    parent_key=""
):
    result = {}

    if not isinstance(
        data,
        dict
    ):
        return result

    for (
        key,
        value
    ) in data.items():
        new_key = (
            f"{parent_key}.{key}"
            if parent_key
            else key
        )

        if isinstance(
            value,
            dict
        ):
            result.update(
                flatten_dict(
                    value,
                    new_key
                )
            )

        elif isinstance(
            value,
            list
        ):
            if key in (
                "inbound_dock_infos",
                "outbound_dock_infos",
            ):
                dock_values = []

                for item in value:
                    if not isinstance(
                        item,
                        dict
                    ):
                        continue

                    dock_number = str(
                        item.get(
                            "dock_number",
                            ""
                        )
                        or ""
                    ).strip()

                    dock_name = str(
                        item.get(
                            "dock_name",
                            ""
                        )
                        or ""
                    ).strip()

                    if (
                        not dock_number
                        and not dock_name
                    ):
                        continue

                    dock_values.append({
                        "dock_number":
                            dock_number,
                        "dock_name":
                            dock_name,
                    })

                result[
                    new_key
                ] = json.dumps(
                    dock_values,
                    ensure_ascii=False
                )

            else:
                converted = (
                    convert_nested_times(
                        value
                    )
                )

                result[
                    new_key
                ] = json.dumps(
                    converted,
                    ensure_ascii=False
                )

        else:
            if is_time_field(
                key
            ):
                result[
                    new_key
                ] = (
                    format_timestamp(
                        value
                    )
                )

            else:
                result[
                    new_key
                ] = value

    return result


def normalize_spx_data(
    response
):
    if (
        isinstance(
            response,
            dict
        )
        and isinstance(
            response.get(
                "data"
            ),
            dict
        )
    ):
        return response[
            "data"
        ]

    return response


def unwrap_data(
    data
):
    if (
        isinstance(
            data,
            dict
        )
        and "data"
        in data
    ):
        return data.get(
            "data"
        )

    return data


def build_trip_row(
    trip_id,
    trip_detail
):
    detail = (
        normalize_spx_data(
            trip_detail
        )
    )

    row = {
        "_key":
            str(
                trip_id
            ),

        "trip_id":
            trip_id,
    }

    if isinstance(
        detail,
        dict
    ):
        row.update(
            flatten_dict(
                detail
            )
        )

    row[
        "sync_time"
    ] = datetime.now(
        VN_TZ
    ).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    return row

def build_trip_station_rows(
    trip_id,
    trip_detail
):
    detail = normalize_spx_data(
        trip_detail
    )

    rows = []

    sync_time = datetime.now(
        VN_TZ
    ).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    candidate_keys = {
        "station_list",
        "stations",
        "station_infos",
        "station_info_list",
        "trip_station_list",
        "trip_stations",
        "route_station_list",
        "route_stations",
        "trip_station",
    }

    found_items = []

    def walk(data):
        if isinstance(
            data,
            dict
        ):
            for key, value in data.items():
                key_lower = str(
                    key
                ).strip().lower()

                if (
                    key_lower
                    in candidate_keys
                    and isinstance(
                        value,
                        list
                    )
                ):
                    for item in value:
                        if isinstance(
                            item,
                            dict
                        ):
                            found_items.append(
                                item
                            )

                walk(
                    value
                )

        elif isinstance(
            data,
            list
        ):
            for item in data:
                walk(
                    item
                )

    walk(
        detail
    )

    if not found_items:
        all_dicts = []

        def collect(data):
            if isinstance(
                data,
                dict
            ):
                all_dicts.append(
                    data
                )

                for value in data.values():
                    collect(
                        value
                    )

            elif isinstance(
                data,
                list
            ):
                for item in data:
                    collect(
                        item
                    )

        collect(
            detail
        )

        for item in all_dicts:
            has_station = any(
                key in item
                for key in (
                    "station_id",
                    "station_name",
                    "station",
                    "station_code",
                )
            )

            has_sequence = any(
                key in item
                for key in (
                    "sequence_number",
                    "sequence",
                    "station_sequence",
                    "unloaded_sequence_number",
                    "loaded_sequence_number",
                )
            )

            if (
                has_station
                and has_sequence
            ):
                found_items.append(
                    item
                )

    seen = set()

    for index, item in enumerate(
        found_items,
        start=1
    ):
        station_id = (
            item.get(
                "station_id"
            )
            or item.get(
                "id"
            )
            or item.get(
                "station"
            )
            or ""
        )

        station_name = (
            item.get(
                "station_name"
            )
            or item.get(
                "name"
            )
            or item.get(
                "station"
            )
            or ""
        )

        sequence = (
            item.get(
                "sequence_number"
            )
            or item.get(
                "sequence"
            )
            or item.get(
                "station_sequence"
            )
            or item.get(
                "unloaded_sequence_number"
            )
            or item.get(
                "loaded_sequence_number"
            )
            or index
        )

        key = (
            f"{trip_id}|"
            f"{sequence}|"
            f"{station_id}|"
            f"{station_name}"
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        row = {
            "_key":
                key,

            "trip_id":
                trip_id,

            "sequence_number":
                sequence,

            "station_id":
                station_id,

            "station_name":
                station_name,
        }

        row.update(
            flatten_dict(
                item
            )
        )

        row[
            "sync_time"
        ] = sync_time

        rows.append(
            row
        )

    return rows
def _first_not_empty(
    mapping,
    keys
):
    if not isinstance(
        mapping,
        dict
    ):
        return ""

    for key in keys:
        value = mapping.get(
            key
        )

        if value not in (
            None,
            "",
            0,
            "0",
        ):
            return value

    return ""


def get_to_identity_parts(
    item
):
    """
    Lấy ID ổn định của TO.

    Ưu tiên:
    - TO ID / record ID
    - station ID đã load

    Mục tiêu:
    cùng một Trip + TO + Station luôn sinh cùng một _key,
    dù dữ liệu SPX được bổ sung ở lần crawl sau.
    """

    to_id = _first_not_empty(
        item,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        )
    )

    station_id = _first_not_empty(
        item,
        (
            "station_id",
            "loaded_station_id",
            "actual_loaded_station_id",
            "unloaded_station_id",
            "actual_unloaded_station_id",
            "current_station_id",
        )
    )

    return (
        str(
            to_id or ""
        ).strip(),
        str(
            station_id or ""
        ).strip(),
    )


def make_to_key(
    trip_id,
    item,
    direction="outbound",
    sequence=1
):
    to_id, station_id = (
        get_to_identity_parts(
            item
        )
    )

    return (
        f"{trip_id}|"
        f"{direction}|"
        f"{sequence}|"
        f"{station_id}|"
        f"{to_id}"
    )


def is_to_complete(
    row
):
    """
    TO được coi là hoàn tất khi đã có đủ thông tin:
    - nhận diện TO
    - thời gian + station load
    - thời gian + station unload

    TO chưa đủ sẽ được cho phép update ở lần sync sau.
    """

    if not isinstance(
        row,
        dict
    ):
        return False

    to_id = _first_not_empty(
        row,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        )
    )

    loaded_time = _first_not_empty(
        row,
        (
            "loaded_time",
            "to_scan_time",
            "actual_loaded_time",
        )
    )

    loaded_station = _first_not_empty(
        row,
        (
            "loaded_station_id",
            "loaded_station_name",
            "loaded_station",
            "actual_loaded_station_id",
            "actual_loaded_station_name",
            "to_scan_station",
        )
    )

    unloaded_time = _first_not_empty(
        row,
        (
            "unloaded_time",
            "actual_unloaded_time",
            "to_unload_time",
        )
    )

    unloaded_station = _first_not_empty(
        row,
        (
            "actual_unloaded_station_id",
            "actual_unloaded_station_name",
            "unloaded_station_id",
            "unloaded_station_name",
            "actual_unloaded_station",
            "unloaded_station",
            "to_unload_station",
        )
    )

    return bool(
        to_id
        and loaded_time
        and loaded_station
        and unloaded_time
        and unloaded_station
    )


def build_to_rows(
    trip_id,
    items,
    direction="outbound",
    sequence=1
):
    rows = []

    sync_time = (
        datetime.now(
            VN_TZ
        ).strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    for item in items:
        if not isinstance(
            item,
            dict
        ):
            continue

        to_id, station_id = (
            get_to_identity_parts(
                item
            )
        )

        key = make_to_key(
            trip_id=trip_id,
            item=item,
            direction=direction,
            sequence=sequence,
        )

        row = {
            "_key":
                key,

            "trip_id":
                trip_id,

            "to_id":
                to_id,

            "station_id":
                station_id,

            "direction":
                direction,

            "sequence_number":
                sequence,
        }

        row.update(
            flatten_dict(
                item
            )
        )

        row[
            "to_scan_time"
        ] = format_timestamp(
            item.get(
                "loaded_time"
            )
        )

        row[
            "to_scan_station"
        ] = (
            item.get(
                "loaded_station_name"
            )
            or item.get(
                "loaded_station"
            )
            or ""
        )

        row[
            "to_unload_time"
        ] = format_timestamp(
            item.get(
                "unloaded_time"
            )
        )

        row[
            "to_unload_station"
        ] = (
            item.get(
                "actual_unloaded_station_name"
            )
            or item.get(
                "unloaded_station_name"
            )
            or item.get(
                "actual_unloaded_station"
            )
            or item.get(
                "unloaded_station"
            )
            or ""
        )

        row[
            "is_complete"
        ] = (
            "YES"
            if is_to_complete(
                row
            )
            else "NO"
        )

        row[
            "sync_time"
        ] = sync_time

        rows.append(
            row
        )

    return rows

def find_values_recursive(
    data,
    wanted_keys
):
    found = []

    wanted_keys = {
        str(x).lower()
        for x
        in wanted_keys
    }

    if isinstance(
        data,
        dict
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
                        value
                    )
                )

            if isinstance(
                value,
                (
                    dict,
                    list,
                )
            ):
                found.extend(
                    find_values_recursive(
                        value,
                        wanted_keys
                    )
                )

    elif isinstance(
        data,
        list
    ):
        for item in data:
            found.extend(
                find_values_recursive(
                    item,
                    wanted_keys
                )
            )

    return found


def get_event_timestamp(
    event
):
    if not isinstance(
        event,
        dict
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
    data
):
    items = []

    if isinstance(
        data,
        dict
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
                )
            ):
                items.extend(
                    collect_dicts(
                        value
                    )
                )

    elif isinstance(
        data,
        list
    ):
        for item in data:
            if isinstance(
                item,
                (
                    dict,
                    list,
                )
            ):
                items.extend(
                    collect_dicts(
                        item
                    )
                )

    return items


def extract_latest_tracking(
    tracking_response
):
    tracking = (
        unwrap_data(
            tracking_response
        )
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

    all_dicts = (
        collect_dicts(
            tracking
        )
    )

    timed_events = []

    for event in all_dicts:
        ts = (
            get_event_timestamp(
                event
            )
        )

        if ts:
            timed_events.append(
                (
                    ts,
                    event
                )
            )

    latest_event = None
    latest_ts = 0

    if timed_events:
        timed_events.sort(
            key=lambda x:
                x[0],
            reverse=True
        )

        (
            latest_ts,
            latest_event
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
            value = (
                latest_event.get(
                    key
                )
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
            value = (
                latest_event.get(
                    key
                )
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
        found = (
            find_values_recursive(
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
                )
            )
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
        found = (
            find_values_recursive(
                tracking,
                (
                    "current_station_name",
                    "station_name",
                    "location_name",
                    "hub_name",
                    "site_name",
                )
            )
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
    order_data
):
    row = {
        "_key":
            str(
                shipment_id
            ),

        "shipment_id":
            shipment_id,
    }

    tracking = order_data.get(
        "tracking_info",
        {}
    )

    recipient = order_data.get(
        "recipient_info",
        {}
    )

    trade = order_data.get(
        "trade_info",
        {}
    )

    pickup = order_data.get(
        "pickup_switches",
        {}
    )

    latest = (
        extract_latest_tracking(
            tracking
        )
    )

    row[
        "current_status"
    ] = latest.get(
        "current_status",
        ""
    )

    row[
        "current_status_time"
    ] = latest.get(
        "current_status_time",
        ""
    )

    row[
        "latest_station"
    ] = latest.get(
        "latest_station",
        ""
    )

    row[
        "latest_event"
    ] = latest.get(
        "latest_event",
        ""
    )

    tracking_data = (
        unwrap_data(
            tracking
        )
    )

    if isinstance(
        tracking_data,
        dict
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

    elif (
        tracking_data
        is not None
    ):
        row[
            "tracking.raw"
        ] = json.dumps(
            convert_nested_times(
                tracking_data
            ),
            ensure_ascii=False
        )

    recipient_data = (
        unwrap_data(
            recipient
        )
    )

    if isinstance(
        recipient_data,
        dict
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

    elif (
        recipient_data
        is not None
    ):
        row[
            "recipient.raw"
        ] = json.dumps(
            convert_nested_times(
                recipient_data
            ),
            ensure_ascii=False
        )

    trade_data = (
        unwrap_data(
            trade
        )
    )

    if isinstance(
        trade_data,
        dict
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

    elif (
        trade_data
        is not None
    ):
        row[
            "trade.raw"
        ] = json.dumps(
            convert_nested_times(
                trade_data
            ),
            ensure_ascii=False
        )

    pickup_data = (
        unwrap_data(
            pickup
        )
    )

    if isinstance(
        pickup_data,
        dict
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
            ensure_ascii=False
        )

    row[
        "sync_time"
    ] = datetime.now(
        VN_TZ
    ).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    return row


def get_push_order_ids():
    service = (
        get_sheets_service()
    )

    sheet_names = (
        get_sheet_names(
            service
        )
    )

    push_sheet = (
        sheet_names.get(
            PUSH_ORDER_GID
        )
    )

    if not push_sheet:
        raise RuntimeError(
            f"Không tìm thấy sheet "
            f"gid={PUSH_ORDER_GID}"
        )

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            range=
                f"'{push_sheet}'!A2:A"
        )
        .execute()
    )

    values = result.get(
        "values",
        []
    )

    shipment_ids = []

    for (
        index,
        row
    ) in enumerate(
        values,
        start=1
    ):
        if not row:
            continue

        value = str(
            row[0]
        ).strip()

        if not value:
            continue

        if (
            index == 1
            and value.lower()
            in {
                "push order",
                "shipment_id",
                "shipment id",
                "order",
            }
        ):
            continue

        if value.upper().startswith(
            "SPXVN"
        ):
            shipment_ids.append(
                value.upper()
            )

    return list(
        dict.fromkeys(
            shipment_ids
        )
    )


def column_letter(
    number
):
    result = ""

    while number:
        (
            number,
            remainder
        ) = divmod(
            number - 1,
            26
        )

        result = (
            chr(
                65 + remainder
            )
            + result
        )

    return result


def read_existing_data(
    service,
    sheet_name
):
    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            range=
                f"'{sheet_name}'"
        )
        .execute()
    )

    return result.get(
        "values",
        []
    )


def _ensure_headers(
    service,
    sheet_name,
    existing,
    rows
):
    if not existing:
        raise RuntimeError(
            f"Sheet '{sheet_name}' chưa có header ở dòng 1."
        )

    headers = [
        str(header).strip()
        for header
        in existing[0]
    ]

    if not any(headers):
        raise RuntimeError(
            f"Sheet '{sheet_name}' chưa có header ở dòng 1."
        )

    if "_key" not in headers:
        raise RuntimeError(
            f"Sheet '{sheet_name}' không có cột _key trong dòng 1."
        )

    return headers

def _row_to_dict(
    headers,
    values
):
    result = {}

    for index, header in enumerate(
        headers
    ):
        if not header:
            continue

        result[
            header
        ] = (
            values[index]
            if index < len(
                values
            )
            else ""
        )

    return result


def _last_used_row(
    existing
):
    last_row = 1

    for index, existing_row in enumerate(
        existing,
        start=1
    ):
        if any(
            str(
                cell
            ).strip()
            for cell
            in existing_row
        ):
            last_row = index

    return last_row


def upsert_rows(
    service,
    sheet_name,
    rows
):
    """
    Upsert chung theo _key.

    - Key đã có: UPDATE đúng dòng cũ.
    - Key chưa có: INSERT từ dòng 2 trở đi.
    - Dòng 1 luôn là HEADER.
    """

    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }

    existing = read_existing_data(
        service,
        sheet_name
    )

    headers = _ensure_headers(
        service,
        sheet_name,
        existing,
        rows,
    )

    key_index = headers.index(
        "_key"
    )

    existing_map = {}

    for index, existing_row in enumerate(
        existing[1:],
        start=2
    ):
        if key_index >= len(
            existing_row
        ):
            continue

        key = str(
            existing_row[
                key_index
            ]
        ).strip()

        if key:
            existing_map[
                key
            ] = index

    end_col = column_letter(
        len(
            headers
        )
    )

    updates = []
    inserts = []
    skipped_count = 0

    last_row = _last_used_row(
        existing
    )

    for row in rows:
        if not isinstance(
            row,
            dict
        ):
            skipped_count += 1
            continue

        key = str(
            row.get(
                "_key",
                ""
            )
        ).strip()

        if not key:
            skipped_count += 1
            continue

        values = [
            row.get(
                header,
                ""
            )
            for header
            in headers
        ]

        if key in existing_map:
            row_number = existing_map[
                key
            ]

            # Chặn cứng không cho data đè HEADER
            if row_number < 2:
                skipped_count += 1
                continue

            updates.append({
                "range": (
                    f"'{sheet_name}'!"
                    f"A{row_number}:"
                    f"{end_col}{row_number}"
                ),
                "values": [
                    values
                ]
            })

        else:
            inserts.append(
                values
            )

    if updates:
        (
            service
            .spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=
                    SPREADSHEET_ID,
                body={
                    "valueInputOption":
                        "RAW",
                    "data":
                        updates,
                }
            )
            .execute()
        )

    if inserts:
        start_row = max(
            2,
            last_row + 1
        )

        end_row = (
            start_row
            + len(
                inserts
            )
            - 1
        )

        (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=
                    SPREADSHEET_ID,
                range=(
                    f"'{sheet_name}'!"
                    f"A{start_row}:"
                    f"{end_col}{end_row}"
                ),
                valueInputOption=
                    "RAW",
                body={
                    "values":
                        inserts
                }
            )
            .execute()
        )

    return {
        "inserted":
            len(
                inserts
            ),
        "updated":
            len(
                updates
            ),
        "skipped":
            skipped_count,
    }


def _canonical_to_identity(
    row
):
    """
    Identity độc lập với _key cũ/mới.
    Dùng để migrate dữ liệu TO đã tồn tại mà không tạo duplicate.
    """

    if not isinstance(
        row,
        dict
    ):
        return ""

    trip_id = str(
        row.get(
            "trip_id",
            ""
        )
        or ""
    ).strip()

    direction = str(
        row.get(
            "direction",
            "outbound"
        )
        or "outbound"
    ).strip().lower()

    sequence = str(
        row.get(
            "sequence_number",
            row.get(
                "sequence",
                1
            )
        )
        or 1
    ).strip()

    to_id = _first_not_empty(
        row,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        )
    )

    station_id = _first_not_empty(
        row,
        (
            "station_id",
            "loaded_station_id",
            "actual_loaded_station_id",
            "unloaded_station_id",
            "actual_unloaded_station_id",
            "current_station_id",
        )
    )

    if not (
        trip_id
        and to_id
    ):
        return ""

    return (
        f"{trip_id}|"
        f"{direction}|"
        f"{sequence}|"
        f"{str(station_id or '').strip()}|"
        f"{str(to_id or '').strip()}"
    )


def get_existing_to_status():
    """
    Đọc TO Sheet và trả về trạng thái theo identity chuẩn.

    complete=True:
        TO đã đủ dữ liệu -> lần sync sau có thể SKIP.

    complete=False:
        TO còn thiếu -> lần sync sau UPDATE lại đúng dòng cũ.
    """

    service = get_sheets_service()

    sheet_names = get_sheet_names(
        service
    )

    to_sheet = sheet_names.get(
        TO_GID
    )

    if not to_sheet:
        raise RuntimeError(
            f"Không tìm thấy sheet gid={TO_GID}"
        )

    existing = read_existing_data(
        service,
        to_sheet
    )

    if not existing:
        return {}

    headers = [
        str(
            header
        ).strip()
        for header
        in existing[0]
    ]

    result = {}

    for row_number, values in enumerate(
        existing[1:],
        start=2
    ):
        row = _row_to_dict(
            headers,
            values
        )

        identity = _canonical_to_identity(
            row
        )

        if not identity:
            continue

        complete_value = str(
            row.get(
                "is_complete",
                ""
            )
            or ""
        ).strip().upper()

        if complete_value in (
            "YES",
            "TRUE",
            "1",
        ):
            complete = True
        elif complete_value in (
            "NO",
            "FALSE",
            "0",
        ):
            complete = False
        else:
            # Sheet cũ chưa có is_complete:
            # tự suy ra từ các cột hiện có.
            complete = is_to_complete(
                row
            )

        result[
            identity
        ] = {
            "row_number":
                row_number,
            "complete":
                complete,
            "row":
                row,
        }

    return result


def filter_to_rows_for_sync(
    rows
):
    """
    Lọc TO trước khi ghi Sheet.

    NEW:
        chưa có -> INSERT.

    INCOMPLETE:
        đã có nhưng chưa đủ -> UPDATE.

    COMPLETE:
        đã đủ -> SKIP, không ghi lại.
    """

    existing_status = (
        get_existing_to_status()
    )

    selected = []

    stats = {
        "total":
            len(
                rows
            ),
        "new":
            0,
        "incomplete":
            0,
        "complete_skipped":
            0,
    }

    for row in rows:
        identity = (
            _canonical_to_identity(
                row
            )
        )

        old = (
            existing_status.get(
                identity
            )
            if identity
            else None
        )

        if old is None:
            stats[
                "new"
            ] += 1

            selected.append(
                row
            )
            continue

        if old.get(
            "complete"
        ):
            stats[
                "complete_skipped"
            ] += 1

            continue

        stats[
            "incomplete"
        ] += 1

        selected.append(
            row
        )

    stats[
        "selected"
    ] = len(
        selected
    )

    return (
        selected,
        stats,
    )


def upsert_to_rows(
    service,
    sheet_name,
    rows
):
    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
        }

    existing = read_existing_data(
        service,
        sheet_name
    )

    headers = _ensure_headers(
        service,
        sheet_name,
        existing,
        rows,
    )

    direct_key_map = {}
    identity_map = {}

    for row_number, values in enumerate(
        existing[1:],
        start=2
    ):
        old_row = _row_to_dict(
            headers,
            values
        )

        old_key = str(
            old_row.get(
                "_key",
                ""
            )
            or ""
        ).strip()

        if old_key:
            direct_key_map[
                old_key
            ] = row_number

        identity = _canonical_to_identity(
            old_row
        )

        if (
            identity
            and identity not in identity_map
        ):
            identity_map[
                identity
            ] = row_number

    end_col = column_letter(
        len(headers)
    )

    updates = []
    inserts = []
    skipped_count = 0
    unchanged_count = 0

    last_row = _last_used_row(
        existing
    )

    for row in rows:
        if not isinstance(row, dict):
            skipped_count += 1
            continue

        key = str(
            row.get(
                "_key",
                ""
            )
            or ""
        ).strip()

        identity = _canonical_to_identity(
            row
        )

        if not key:
            skipped_count += 1
            continue

        row_number = direct_key_map.get(
            key
        )

        if (
            row_number is None
            and identity
        ):
            row_number = identity_map.get(
                identity
            )

        if row_number is None:
            values = [
                row.get(
                    header,
                    ""
                )
                for header
                in headers
            ]

            inserts.append(
                values
            )
            continue

        if row_number < 2:
            skipped_count += 1
            continue

        old_values = (
            existing[row_number - 1]
            if row_number - 1 < len(existing)
            else []
        )

        old_row = _row_to_dict(
            headers,
            old_values
        )

        merged_values = []
        changed = False

        for header in headers:
            old_value = old_row.get(
                header,
                ""
            )

            new_value = row.get(
                header,
                ""
            )

            if new_value not in (
                None,
                "",
            ):
                final_value = new_value
            else:
                final_value = old_value

            if str(final_value) != str(old_value):
                changed = True

            merged_values.append(
                final_value
            )

        if not changed:
            unchanged_count += 1
            continue

        updates.append({
            "range": (
                f"'{sheet_name}'!"
                f"A{row_number}:"
                f"{end_col}{row_number}"
            ),
            "values": [
                merged_values
            ]
        })

    if updates:
        (
            service
            .spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=
                    SPREADSHEET_ID,
                body={
                    "valueInputOption":
                        "RAW",
                    "data":
                        updates,
                }
            )
            .execute()
        )

    if inserts:
        start_row = max(
            2,
            last_row + 1
        )

        end_row = (
            start_row
            + len(inserts)
            - 1
        )

        (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=
                    SPREADSHEET_ID,
                range=(
                    f"'{sheet_name}'!"
                    f"A{start_row}:"
                    f"{end_col}{end_row}"
                ),
                valueInputOption=
                    "RAW",
                body={
                    "values":
                        inserts
                }
            )
            .execute()
        )

    return {
        "inserted":
            len(inserts),
        "updated":
            len(updates),
        "unchanged":
            unchanged_count,
        "skipped":
            skipped_count,
    }

def push_to_sheet(
    trip_rows=None,
    to_rows=None,
    order_rows=None,
    trip_station_rows=None,
):
    service = (
        get_sheets_service()
    )

    sheet_names = (
        get_sheet_names(
            service
        )
    )

    result = {
        "success": True
    }

    if trip_rows:
        trip_sheet = (
            sheet_names.get(
                TRIP_GID
            )
        )

        if not trip_sheet:
            raise RuntimeError(
                f"Không tìm thấy sheet "
                f"gid={TRIP_GID}"
            )

        result[
            "trip"
        ] = upsert_rows(
            service,
            trip_sheet,
            trip_rows
        )

    if trip_station_rows:
        trip_station_sheet = (
            sheet_names.get(
                TRIP_STATION_GID
            )
        )

        if not trip_station_sheet:
            raise RuntimeError(
                f"Không tìm thấy sheet "
                f"gid={TRIP_STATION_GID}"
            )

        result[
            "trip_station"
        ] = upsert_rows(
            service,
            trip_station_sheet,
            trip_station_rows
        )

    if to_rows:
        to_sheet = (
            sheet_names.get(
                TO_GID
            )
        )

        if not to_sheet:
            raise RuntimeError(
                f"Không tìm thấy sheet "
                f"gid={TO_GID}"
            )

        result[
            "to"
        ] = upsert_to_rows(
            service,
            to_sheet,
            to_rows
        )

    if order_rows:
        order_sheet = (
            sheet_names.get(
                ORDER_GID
            )
        )

        if not order_sheet:
            raise RuntimeError(
                f"Không tìm thấy sheet "
                f"gid={ORDER_GID}"
            )

        result[
            "order"
        ] = upsert_rows(
            service,
            order_sheet,
            order_rows
        )

    return result