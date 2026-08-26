import json
import os
from datetime import (
    datetime,
    timezone,
    timedelta,
)

from google.oauth2.service_account import (
    Credentials,
)

from googleapiclient.discovery import (
    build,
)


SPREADSHEET_ID = (
    "1YfRPJd99ipWnUqPqXCFDlQzHj8ADxdP_UE1363KqLS8"
)

SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                __file__
            )
        )
    ),
    "service_account.json",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

VN_TZ = timezone(
    timedelta(
        hours=7
    )
)

SHEET_INSERT_BATCH_SIZE = 1000
SHEET_UPDATE_BATCH_SIZE = 500


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
            scopes=SCOPES,
        )
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


def get_sheet_names(
    service=None,
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
                "sheets.properties",
        )
        .execute()
    )

    mapping = {}

    for sheet in result.get(
        "sheets",
        [],
    ):
        props = sheet.get(
            "properties",
            {},
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
                int(
                    sheet_id
                )
            ] = title

    return mapping


def get_sheet_name_by_gid(
    gid,
    service=None,
):
    if service is None:
        service = (
            get_sheets_service()
        )

    try:
        gid = int(
            gid
        )

    except (
        TypeError,
        ValueError,
    ):
        raise RuntimeError(
            f"GID không hợp lệ: {gid}"
        )

    sheet_names = (
        get_sheet_names(
            service
        )
    )

    sheet_name = (
        sheet_names.get(
            gid
        )
    )

    if not sheet_name:
        raise RuntimeError(
            f"Không tìm thấy sheet gid={gid}"
        )

    return sheet_name


def get_sheet_properties(
    service,
    sheet_name,
):
    result = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,

            fields=
                "sheets.properties",
        )
        .execute()
    )

    for sheet in result.get(
        "sheets",
        [],
    ):
        props = sheet.get(
            "properties",
            {},
        )

        if props.get(
            "title"
        ) == sheet_name:
            return props

    raise RuntimeError(
        f"Không tìm thấy sheet '{sheet_name}'"
    )


def ensure_sheet_capacity(
    service,
    sheet_name,
    required_rows=None,
    required_columns=None,
):
    props = get_sheet_properties(
        service=
            service,

        sheet_name=
            sheet_name,
    )

    sheet_id = props.get(
        "sheetId"
    )

    grid = props.get(
        "gridProperties",
        {},
    )

    current_rows = int(
        grid.get(
            "rowCount",
            0,
        )
        or 0
    )

    current_columns = int(
        grid.get(
            "columnCount",
            0,
        )
        or 0
    )

    new_rows = current_rows
    new_columns = current_columns

    if required_rows is not None:
        try:
            required_rows = max(
                1,
                int(
                    required_rows
                ),
            )
        except (
            TypeError,
            ValueError,
        ):
            required_rows = current_rows

        if required_rows > current_rows:
            new_rows = required_rows

    if required_columns is not None:
        try:
            required_columns = max(
                1,
                int(
                    required_columns
                ),
            )
        except (
            TypeError,
            ValueError,
        ):
            required_columns = (
                current_columns
            )

        if (
            required_columns
            > current_columns
        ):
            new_columns = required_columns

    if (
        new_rows == current_rows
        and new_columns
        == current_columns
    ):
        return {
            "changed":
                False,

            "rows_before":
                current_rows,

            "rows_after":
                current_rows,

            "columns_before":
                current_columns,

            "columns_after":
                current_columns,
        }

    grid_properties = {}

    fields = []

    if new_rows != current_rows:
        grid_properties[
            "rowCount"
        ] = new_rows

        fields.append(
            "gridProperties.rowCount"
        )

    if (
        new_columns
        != current_columns
    ):
        grid_properties[
            "columnCount"
        ] = new_columns

        fields.append(
            "gridProperties.columnCount"
        )

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=
                SPREADSHEET_ID,

            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId":
                                    sheet_id,

                                "gridProperties":
                                    grid_properties,
                            },

                            "fields":
                                ",".join(
                                    fields
                                ),
                        }
                    }
                ]
            },
        )
        .execute()
    )

    return {
        "changed":
            True,

        "rows_before":
            current_rows,

        "rows_after":
            new_rows,

        "columns_before":
            current_columns,

        "columns_after":
            new_columns,
    }


def ensure_sheet_row_capacity(
    service,
    sheet_name,
    required_rows,
):
    return ensure_sheet_capacity(
        service=
            service,

        sheet_name=
            sheet_name,

        required_rows=
            required_rows,
    )


def ensure_sheet_column_capacity(
    service,
    sheet_name,
    required_columns,
):
    return ensure_sheet_capacity(
        service=
            service,

        sheet_name=
            sheet_name,

        required_columns=
            required_columns,
    )


def is_time_field(
    key,
):
    key = str(
        key
        or ""
    ).strip().lower()

    if not key:
        return False

    leaf_key = (
        key
        .replace(
            "]",
            ""
        )
        .split(".")[-1]
        .split("[")[0]
        .strip()
        .lower()
    )

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
        "complete_time",
        "completed_time",
        "receive_time",
        "received_time",
        "pickup_time",
        "picked_time",
        "packing_time",
        "packed_time",
        "loaded_time",
        "unloaded_time",
        "actual_loaded_time",
        "actual_unloaded_time",
        "arrived_time",
        "arrival_time",
        "departed_time",
        "departure_time",
        "transporting_time",
        "transported_time",
        "assigning_time",
        "assigned_time",
        "delivering_time",
        "delivered_time",
        "scan_time",
        "operation_time",
        "event_time",
        "tracking_time",
        "status_time",
        "latest_status_time",
        "new_status_time",
        "lh_arrived_time",
        "lh_unloading_time",
        "lh_unloaded_time",
        "lh_transporting_time",
        "lh_transported_time",
        "hy_trip_time",
        "sync_time",
        "time",
        "timestamp",
    }

    if (
        key in exact_fields
        or leaf_key in exact_fields
    ):
        return True

    suffixes = (
        "_time",
        "_timestamp",
        "_datetime",
        "_date_time",
        "_date",
    )

    return (
        key.endswith(
            suffixes
        )
        or leaf_key.endswith(
            suffixes
        )
    )


def format_timestamp(
    value,
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
        bool,
    ):
        return value

    if isinstance(
        value,
        datetime,
    ):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=VN_TZ
            )
        else:
            dt = dt.astimezone(
                VN_TZ
            )

        return dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    if isinstance(
        value,
        str,
    ):
        stripped = value.strip()

        if not stripped:
            return ""

        try:
            ts = float(
                stripped
            )
        except ValueError:
            return value

    else:
        try:
            ts = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return value

    try:
        while (
            abs(
                ts
            )
            > 10_000_000_000
        ):
            ts /= 1000

        if (
            ts < 946684800
            or ts > 4102444799
        ):
            return value

        dt = (
            datetime
            .fromtimestamp(
                ts,
                tz=timezone.utc,
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


def normalize_sheet_value(
    field_name,
    value,
):
    if value in (
        None,
        "",
    ):
        return ""

    if is_time_field(
        field_name
    ):
        return format_timestamp(
            value
        )

    return value


def now_vn():
    return (
        datetime
        .now(
            VN_TZ
        )
        .strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )


def convert_nested_times(
    data,
    parent_key="",
):
    if isinstance(
        data,
        dict,
    ):
        result = {}

        for key, value in data.items():
            new_key = (
                f"{parent_key}.{key}"
                if parent_key
                else str(
                    key
                )
            )

            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):
                result[
                    key
                ] = convert_nested_times(
                    value,
                    new_key,
                )

            else:
                result[
                    key
                ] = normalize_sheet_value(
                    new_key,
                    value,
                )

        return result

    if isinstance(
        data,
        list,
    ):
        result = []

        for index, item in enumerate(
            data
        ):
            new_key = (
                f"{parent_key}"
                f"[{index}]"
            )

            if isinstance(
                item,
                (
                    dict,
                    list,
                ),
            ):
                result.append(
                    convert_nested_times(
                        item,
                        new_key,
                    )
                )

            else:
                result.append(
                    normalize_sheet_value(
                        new_key,
                        item,
                    )
                )

        return result

    return normalize_sheet_value(
        parent_key,
        data,
    )


def format_dock_infos(
    value,
):
    if not isinstance(
        value,
        list,
    ):
        return []

    result = []

    for item in value:
        if not isinstance(
            item,
            dict,
        ):
            continue

        dock_number = str(
            item.get(
                "dock_number",
                "",
            )
            or ""
        ).strip()

        dock_name = str(
            item.get(
                "dock_name",
                "",
            )
            or ""
        ).strip()

        if (
            not dock_number
            and not dock_name
        ):
            continue

        result.append({
            "dock_number":
                dock_number,

            "dock_name":
                dock_name,
        })

    return result


def flatten_dict(
    value,
    parent_key="",
):
    result = {}

    if isinstance(
        value,
        dict,
    ):
        for key, item in value.items():
            new_key = (
                f"{parent_key}.{key}"
                if parent_key
                else str(
                    key
                )
            )

            result.update(
                flatten_dict(
                    item,
                    new_key,
                )
            )

        return result

    if isinstance(
        value,
        list,
    ):
        if not value:
            result[
                parent_key
            ] = ""

            return result

        for index, item in enumerate(
            value
        ):
            new_key = (
                f"{parent_key}"
                f"[{index}]"
            )

            result.update(
                flatten_dict(
                    item,
                    new_key,
                )
            )

        return result

    result[
        parent_key
    ] = normalize_sheet_value(
        parent_key,
        value,
    )

    return result


def normalize_spx_data(
    response,
):
    if (
        isinstance(
            response,
            dict,
        )
        and isinstance(
            response.get(
                "data"
            ),
            dict,
        )
    ):
        return response[
            "data"
        ]

    return response


def unwrap_data(
    data,
):
    if (
        isinstance(
            data,
            dict,
        )
        and "data" in data
    ):
        return data.get(
            "data"
        )

    return data


def first_not_empty(
    mapping,
    keys,
):
    if not isinstance(
        mapping,
        dict,
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


def column_letter(
    number,
):
    try:
        number = int(
            number
        )

    except (
        TypeError,
        ValueError,
    ):
        return ""

    if number <= 0:
        return ""

    result = ""

    while number:
        (
            number,
            remainder
        ) = divmod(
            number - 1,
            26,
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
    sheet_name,
):
    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,

            range=
                f"'{sheet_name}'",
        )
        .execute()
    )

    return result.get(
        "values",
        [],
    )


def read_sheet_range(
    service,
    sheet_name,
    cell_range,
):
    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,

            range=(
                f"'{sheet_name}'!"
                f"{cell_range}"
            ),
        )
        .execute()
    )

    return result.get(
        "values",
        [],
    )


def get_headers(
    existing,
    sheet_name="",
    require_key=True,
):
    if not existing:
        raise RuntimeError(
            f"Sheet '{sheet_name}' "
            f"chưa có header ở dòng 1."
        )

    headers = [
        str(
            header
        ).strip()
        for header
        in existing[0]
    ]

    if not any(
        headers
    ):
        raise RuntimeError(
            f"Sheet '{sheet_name}' "
            f"chưa có header ở dòng 1."
        )

    if (
        require_key
        and "_key" not in headers
    ):
        raise RuntimeError(
            f"Sheet '{sheet_name}' "
            f"không có cột _key trong dòng 1."
        )

    return headers


def ensure_headers(
    service,
    sheet_name,
    existing,
    rows=None,
    require_key=True,
):
    return get_headers(
        existing=
            existing,

        sheet_name=
            sheet_name,

        require_key=
            require_key,
    )


def row_to_dict(
    headers,
    values,
):
    result = {}

    for (
        index,
        header
    ) in enumerate(
        headers
    ):
        if not header:
            continue

        result[
            header
        ] = (
            values[
                index
            ]
            if index
            < len(
                values
            )
            else ""
        )

    return result


def last_used_row(
    existing,
):
    last_row = 1

    for (
        index,
        existing_row
    ) in enumerate(
        existing,
        start=1,
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


def build_values_from_row(
    headers,
    row,
):
    values = []

    for header in headers:
        value = row.get(
            header,
            "",
        )

        value = normalize_sheet_value(
            header,
            value,
        )

        values.append(
            value
        )

    return values


def values_equal(
    left,
    right,
):
    return str(
        left
    ) == str(
        right
    )


def merge_row_non_empty(
    headers,
    old_row,
    new_row,
):
    merged_values = []

    data_changed = False
    sync_index = None

    for (
        index,
        header
    ) in enumerate(
        headers
    ):
        old_value = old_row.get(
            header,
            "",
        )

        incoming_value = (
            new_row.get(
                header,
                "",
            )
        )

        new_value = normalize_sheet_value(
            header,
            incoming_value,
        )

        if header == "sync_time":
            sync_index = index

            merged_values.append(
                old_value
            )

            continue

        if new_value not in (
            None,
            "",
        ):
            final_value = new_value

        else:
            final_value = old_value

        if not values_equal(
            final_value,
            old_value,
        ):
            data_changed = True

        merged_values.append(
            final_value
        )

    if (
        data_changed
        and sync_index is not None
    ):
        incoming_sync = normalize_sheet_value(
            "sync_time",
            new_row.get(
                "sync_time",
                "",
            ),
        )

        if incoming_sync not in (
            None,
            "",
        ):
            merged_values[
                sync_index
            ] = incoming_sync

    return (
        merged_values,
        data_changed,
    )


def build_replace_values(
    headers,
    old_row,
    new_row,
):
    values = []

    data_changed = False
    sync_index = None

    for (
        index,
        header
    ) in enumerate(
        headers
    ):
        old_value = old_row.get(
            header,
            "",
        )

        if header == "sync_time":
            sync_index = index

            values.append(
                old_value
            )

            continue

        new_value = normalize_sheet_value(
            header,
            new_row.get(
                header,
                "",
            ),
        )

        if not values_equal(
            new_value,
            old_value,
        ):
            data_changed = True

        values.append(
            new_value
        )

    if (
        data_changed
        and sync_index is not None
    ):
        incoming_sync = normalize_sheet_value(
            "sync_time",
            new_row.get(
                "sync_time",
                "",
            ),
        )

        if incoming_sync not in (
            None,
            "",
        ):
            values[
                sync_index
            ] = incoming_sync

    return (
        values,
        data_changed,
    )


def execute_update_batches(
    service,
    updates,
    batch_size=
        SHEET_UPDATE_BATCH_SIZE,
):
    if not updates:
        return 0

    total = 0

    for start in range(
        0,
        len(
            updates
        ),
        batch_size,
    ):
        batch = updates[
            start:
            start + batch_size
        ]

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
                        batch,
                },
            )
            .execute()
        )

        total += len(
            batch
        )

    return total


def execute_insert_batches(
    service,
    sheet_name,
    headers,
    inserts,
    start_row,
    batch_size=
        SHEET_INSERT_BATCH_SIZE,
):
    if not inserts:
        return 0

    end_col = column_letter(
        len(
            headers
        )
    )

    total_rows = len(
        inserts
    )

    final_row = (
        start_row
        + total_rows
        - 1
    )

    ensure_sheet_capacity(
        service=
            service,

        sheet_name=
            sheet_name,

        required_rows=
            final_row,

        required_columns=
            len(
                headers
            ),
    )

    written = 0

    for start in range(
        0,
        total_rows,
        batch_size,
    ):
        batch = inserts[
            start:
            start + batch_size
        ]

        batch_start_row = (
            start_row
            + start
        )

        batch_end_row = (
            batch_start_row
            + len(
                batch
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
                    f"A{batch_start_row}:"
                    f"{end_col}{batch_end_row}"
                ),

                valueInputOption=
                    "RAW",

                body={
                    "values":
                        batch
                },
            )
            .execute()
        )

        written += len(
            batch
        )

    return written


def upsert_rows(
    service,
    sheet_name,
    rows,
    merge_non_empty=False,
):
    if not rows:
        return {
            "inserted":
                0,

            "updated":
                0,

            "unchanged":
                0,

            "skipped":
                0,
        }

    existing = (
        read_existing_data(
            service,
            sheet_name,
        )
    )

    headers = (
        ensure_headers(
            service=
                service,

            sheet_name=
                sheet_name,

            existing=
                existing,

            rows=
                rows,

            require_key=
                True,
        )
    )

    ensure_sheet_column_capacity(
        service=
            service,

        sheet_name=
            sheet_name,

        required_columns=
            len(
                headers
            ),
    )

    key_index = headers.index(
        "_key"
    )

    existing_map = {}

    for (
        row_number,
        values
    ) in enumerate(
        existing[1:],
        start=2,
    ):
        if (
            key_index
            >= len(
                values
            )
        ):
            continue

        key = str(
            values[
                key_index
            ]
            or ""
        ).strip()

        if not key:
            continue

        existing_map[
            key
        ] = row_number

    end_col = column_letter(
        len(
            headers
        )
    )

    updates = []
    inserts = []

    skipped_count = 0
    unchanged_count = 0

    last_row = last_used_row(
        existing
    )

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            skipped_count += 1
            continue

        key = str(
            row.get(
                "_key",
                "",
            )
            or ""
        ).strip()

        if not key:
            skipped_count += 1
            continue

        row_number = (
            existing_map.get(
                key
            )
        )

        if row_number is None:
            values = (
                build_values_from_row(
                    headers,
                    row,
                )
            )

            inserts.append(
                values
            )

            continue

        if row_number < 2:
            skipped_count += 1
            continue

        old_values = (
            existing[
                row_number - 1
            ]
            if (
                row_number - 1
                < len(
                    existing
                )
            )
            else []
        )

        old_row = row_to_dict(
            headers,
            old_values,
        )

        if merge_non_empty:
            (
                values,
                changed,
            ) = merge_row_non_empty(
                headers=
                    headers,

                old_row=
                    old_row,

                new_row=
                    row,
            )

        else:
            (
                values,
                changed,
            ) = build_replace_values(
                headers=
                    headers,

                old_row=
                    old_row,

                new_row=
                    row,
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
                values
            ],
        })

    updated_count = (
        execute_update_batches(
            service=
                service,

            updates=
                updates,
        )
    )

    inserted_count = 0

    if inserts:
        start_row = max(
            2,
            last_row + 1,
        )

        inserted_count = (
            execute_insert_batches(
                service=
                    service,

                sheet_name=
                    sheet_name,

                headers=
                    headers,

                inserts=
                    inserts,

                start_row=
                    start_row,
            )
        )

    return {
        "inserted":
            inserted_count,

        "updated":
            updated_count,

        "unchanged":
            unchanged_count,

        "skipped":
            skipped_count,
    }


def upsert_rows_by_gid(
    gid,
    rows,
    merge_non_empty=False,
    service=None,
):
    if service is None:
        service = (
            get_sheets_service()
        )

    sheet_name = (
        get_sheet_name_by_gid(
            gid=
                gid,

            service=
                service,
        )
    )

    return upsert_rows(
        service=
            service,

        sheet_name=
            sheet_name,

        rows=
            rows,

        merge_non_empty=
            merge_non_empty,
    )