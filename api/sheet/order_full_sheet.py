from api.order.data_order_deli import (
    build_order_row as build_business_order_row,
)

from api.sheet.common import (
    SPREADSHEET_ID,
    get_sheet_name_by_gid,
    get_sheets_service,
    now_vn,
)


ORDER_FULL_GID = 1479670208


ORDER_FULL_HEADERS = [
    "_key",
    "shipment_id",
    "next_station",
    "display_status",
    "latest_status",
    "latest_status_code",
    "latest_status_time",
    "latest_station",
    "lh_arrived_time",
    "lh_unloading_time",
    "lh_unloaded_time",
    "received_type",
    "received_time",
    "packing_time",
    "packed_time",
    "lh_transporting_time",
    "lh_transported_time",
    "assigning_time",
    "assigned_time",
    "delivering_time",
    "delivered_time",
    "cycle_type",
    "new_status",
    "new_status_time",
    "new_status_reason",
    "sync_time",
    "to_number",
    "trip_number",
    "hy_trip_time",
]


ORDER_FULL_END_COLUMN = "AC"


def normalize_shipment_id(
    shipment_id,
):
    return str(
        shipment_id or ""
    ).strip().upper()


def safe_value(
    row,
    key,
):
    if not isinstance(
        row,
        dict,
    ):
        return ""

    value = row.get(
        key,
        "",
    )

    if value is None:
        return ""

    return value


def build_full_order_row(
    shipment_id,
    order_data,
):
    shipment_id = (
        normalize_shipment_id(
            shipment_id
        )
    )

    if not shipment_id:
        raise RuntimeError(
            "shipment_id rỗng"
        )

    if not isinstance(
        order_data,
        dict,
    ):
        order_data = {}

    business_row = (
        build_business_order_row(
            shipment_id=
                shipment_id,

            order_data=
                order_data,
        )
    )

    if not isinstance(
        business_row,
        dict,
    ):
        business_row = {}

    return {
        "_key":
            shipment_id,

        "shipment_id":
            shipment_id,

        "next_station":
            safe_value(
                business_row,
                "next_station",
            ),

        "display_status":
            safe_value(
                business_row,
                "display_status",
            ),

        "latest_status":
            safe_value(
                business_row,
                "latest_status",
            ),

        "latest_status_code":
            safe_value(
                business_row,
                "latest_status_code",
            ),

        "latest_status_time":
            safe_value(
                business_row,
                "latest_status_time",
            ),

        "latest_station":
            safe_value(
                business_row,
                "latest_station",
            ),

        "lh_arrived_time":
            safe_value(
                business_row,
                "lh_arrived_time",
            ),

        "lh_unloading_time":
            safe_value(
                business_row,
                "lh_unloading_time",
            ),

        "lh_unloaded_time":
            safe_value(
                business_row,
                "lh_unloaded_time",
            ),

        "received_type":
            safe_value(
                business_row,
                "received_type",
            ),

        "received_time":
            safe_value(
                business_row,
                "received_time",
            ),

        "packing_time":
            safe_value(
                business_row,
                "packing_time",
            ),

        "packed_time":
            safe_value(
                business_row,
                "packed_time",
            ),

        "lh_transporting_time":
            safe_value(
                business_row,
                "lh_transporting_time",
            ),

        "lh_transported_time":
            safe_value(
                business_row,
                "lh_transported_time",
            ),

        "assigning_time":
            safe_value(
                business_row,
                "assigning_time",
            ),

        "assigned_time":
            safe_value(
                business_row,
                "assigned_time",
            ),

        "delivering_time":
            safe_value(
                business_row,
                "delivering_time",
            ),

        "delivered_time":
            safe_value(
                business_row,
                "delivered_time",
            ),

        "cycle_type":
            safe_value(
                business_row,
                "cycle_type",
            ),

        "new_status":
            safe_value(
                business_row,
                "new_status",
            ),

        "new_status_time":
            safe_value(
                business_row,
                "new_status_time",
            ),

        "new_status_reason":
            safe_value(
                business_row,
                "new_status_reason",
            ),

        "sync_time":
            safe_value(
                business_row,
                "sync_time",
            )
            or now_vn(),

        "to_number":
            safe_value(
                business_row,
                "to_number",
            ),

        "trip_number":
            safe_value(
                business_row,
                "trip_number",
            ),

        "hy_trip_time":
            safe_value(
                business_row,
                "hy_trip_time",
            ),
    }


def build_full_order_rows(
    items,
):
    if not isinstance(
        items,
        list,
    ):
        return []

    rows = []
    seen = set()

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        shipment_id = (
            normalize_shipment_id(
                item.get(
                    "shipment_id"
                )
                or item.get(
                    "fleet_order_id"
                )
            )
        )

        if not shipment_id:
            continue

        if shipment_id in seen:
            continue

        order_data = (
            item.get(
                "order_data"
            )
        )

        if not isinstance(
            order_data,
            dict,
        ):
            order_data = (
                item.get(
                    "data"
                )
            )

        if not isinstance(
            order_data,
            dict,
        ):
            order_data = {}

        seen.add(
            shipment_id
        )

        rows.append(
            build_full_order_row(
                shipment_id=
                    shipment_id,

                order_data=
                    order_data,
            )
        )

    return rows


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


def ensure_row_capacity(
    service,
    sheet_name,
    required_rows,
):
    props = (
        get_sheet_properties(
            service=
                service,

            sheet_name=
                sheet_name,
        )
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

    required_rows = int(
        required_rows
        or 0
    )

    if (
        required_rows
        <= current_rows
    ):
        return

    new_rows = max(
        required_rows,
        current_rows + 1000,
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

                                "gridProperties": {
                                    "rowCount":
                                        new_rows
                                },
                            },

                            "fields":
                                "gridProperties.rowCount",
                        }
                    }
                ]
            },
        )
        .execute()
    )


def read_order_sheet(
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

            range=(
                f"'{sheet_name}'!"
                f"A:AC"
            ),
        )
        .execute()
    )

    return result.get(
        "values",
        [],
    )


def validate_headers(
    existing,
    sheet_name,
):
    if not existing:
        raise RuntimeError(
            f"Sheet '{sheet_name}' chưa có header"
        )

    header_row = existing[0]

    headers = []

    for index in range(
        len(
            ORDER_FULL_HEADERS
        )
    ):
        value = (
            header_row[
                index
            ]
            if index
            < len(
                header_row
            )
            else ""
        )

        headers.append(
            str(
                value or ""
            ).strip()
        )

    if headers != ORDER_FULL_HEADERS:
        raise RuntimeError(
            "Header Order không đúng. "
            "Sheet phải đúng 29 cột A:AC."
        )


def build_sheet_values(
    row,
):
    return [
        row.get(
            header,
            "",
        )
        if row.get(
            header,
            "",
        ) is not None
        else ""
        for header
        in ORDER_FULL_HEADERS
    ]


def row_to_dict(
    values,
):
    result = {}

    for (
        index,
        header
    ) in enumerate(
        ORDER_FULL_HEADERS
    ):
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


def values_equal(
    left,
    right,
):
    left_value = (
        ""
        if left is None
        else str(
            left
        )
    )

    right_value = (
        ""
        if right is None
        else str(
            right
        )
    )

    return (
        left_value
        == right_value
    )


def merge_existing_row(
    old_values,
    new_row,
):
    old_row = (
        row_to_dict(
            old_values
        )
    )

    merged = []

    changed = False

    sync_index = (
        ORDER_FULL_HEADERS.index(
            "sync_time"
        )
    )

    for header in ORDER_FULL_HEADERS:
        old_value = old_row.get(
            header,
            "",
        )

        new_value = new_row.get(
            header,
            "",
        )

        if header == "sync_time":
            merged.append(
                old_value
            )

            continue

        if new_value not in (
            None,
            "",
        ):
            final_value = (
                new_value
            )

        else:
            final_value = (
                old_value
            )

        if not values_equal(
            final_value,
            old_value,
        ):
            changed = True

        merged.append(
            final_value
        )

    if changed:
        new_sync_time = new_row.get(
            "sync_time",
            "",
        )

        if new_sync_time:
            merged[
                sync_index
            ] = new_sync_time

    return (
        merged,
        changed,
    )


def execute_updates(
    service,
    updates,
    batch_size=200,
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


def execute_inserts(
    service,
    sheet_name,
    rows,
    start_row,
    batch_size=200,
):
    if not rows:
        return 0

    final_row = (
        start_row
        + len(
            rows
        )
        - 1
    )

    ensure_row_capacity(
        service=
            service,

        sheet_name=
            sheet_name,

        required_rows=
            final_row,
    )

    written = 0

    for start in range(
        0,
        len(
            rows
        ),
        batch_size,
    ):
        batch = rows[
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
                    f"{ORDER_FULL_END_COLUMN}"
                    f"{batch_end_row}"
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


def push_full_order_rows(
    rows,
    service=None,
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

    if service is None:
        service = (
            get_sheets_service()
        )

    sheet_name = (
        get_sheet_name_by_gid(
            gid=
                ORDER_FULL_GID,

            service=
                service,
        )
    )

    existing = (
        read_order_sheet(
            service=
                service,

            sheet_name=
                sheet_name,
        )
    )

    validate_headers(
        existing=
            existing,

        sheet_name=
            sheet_name,
    )

    existing_map = {}

    last_row = 1

    for (
        row_number,
        values
    ) in enumerate(
        existing[1:],
        start=2,
    ):
        if any(
            str(
                value
            ).strip()
            for value
            in values
        ):
            last_row = (
                row_number
            )

        key = (
            normalize_shipment_id(
                values[0]
                if values
                else ""
            )
        )

        if not key:
            continue

        existing_map[
            key
        ] = (
            row_number,
            values,
        )

    updates = []

    inserts = []

    unchanged = 0

    skipped = 0

    seen = set()

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            skipped += 1
            continue

        key = (
            normalize_shipment_id(
                row.get(
                    "_key"
                )
                or row.get(
                    "shipment_id"
                )
            )
        )

        if not key:
            skipped += 1
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        clean_row = {
            header:
                row.get(
                    header,
                    "",
                )
            for header
            in ORDER_FULL_HEADERS
        }

        clean_row[
            "_key"
        ] = key

        clean_row[
            "shipment_id"
        ] = key

        existing_item = (
            existing_map.get(
                key
            )
        )

        if existing_item is None:
            inserts.append(
                build_sheet_values(
                    clean_row
                )
            )

            continue

        (
            row_number,
            old_values,
        ) = existing_item

        (
            merged_values,
            changed,
        ) = (
            merge_existing_row(
                old_values=
                    old_values,

                new_row=
                    clean_row,
            )
        )

        if not changed:
            unchanged += 1
            continue

        updates.append({
            "range": (
                f"'{sheet_name}'!"
                f"A{row_number}:"
                f"{ORDER_FULL_END_COLUMN}"
                f"{row_number}"
            ),

            "values": [
                merged_values
            ],
        })

    updated = (
        execute_updates(
            service=
                service,

            updates=
                updates,
        )
    )

    inserted = 0

    if inserts:
        inserted = (
            execute_inserts(
                service=
                    service,

                sheet_name=
                    sheet_name,

                rows=
                    inserts,

                start_row=
                    max(
                        2,
                        last_row + 1,
                    ),
            )
        )

    return {
        "inserted":
            inserted,

        "updated":
            updated,

        "unchanged":
            unchanged,

        "skipped":
            skipped,
    }


def push_full_order(
    shipment_id,
    order_data,
    service=None,
):
    shipment_id = (
        normalize_shipment_id(
            shipment_id
        )
    )

    row = (
        build_full_order_row(
            shipment_id=
                shipment_id,

            order_data=
                order_data,
        )
    )

    sheet_result = (
        push_full_order_rows(
            rows=[
                row
            ],

            service=
                service,
        )
    )

    return {
        "shipment_id":
            shipment_id,

        "row":
            row,

        "sheet":
            sheet_result,
    }