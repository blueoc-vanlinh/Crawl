from api.sheet.common import (
    SPREADSHEET_ID,
    column_letter,
    ensure_headers,
    flatten_dict,
    get_sheet_name_by_gid,
    get_sheets_service,
    last_used_row,
    normalize_spx_data,
    now_vn,
    read_existing_data,
    row_to_dict,
)


TRIP_GID = 0

def ensure_trip_grid(
    service,
    required_rows,
    required_columns,
):
    spreadsheet = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,

            fields=(
                "sheets.properties("
                "sheetId,"
                "title,"
                "gridProperties"
                ")"
            ),
        )
        .execute()
    )

    target = None

    for sheet in spreadsheet.get(
        "sheets",
        [],
    ):
        properties = sheet.get(
            "properties",
            {},
        )

        if int(
            properties.get(
                "sheetId",
                -1,
            )
        ) == int(
            TRIP_GID
        ):
            target = properties
            break

    if target is None:
        raise RuntimeError(
            f"Không tìm thấy Trip gid={TRIP_GID}"
        )

    grid = target.get(
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

    new_rows = max(
        current_rows,
        int(required_rows),
    )

    new_columns = max(
        current_columns,
        int(required_columns),
    )

    if (
        new_rows == current_rows
        and
        new_columns == current_columns
    ):
        return

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
                                    int(
                                        TRIP_GID
                                    ),

                                "gridProperties": {
                                    "rowCount":
                                        new_rows,

                                    "columnCount":
                                        new_columns,
                                },
                            },

                            "fields": (
                                "gridProperties."
                                "rowCount,"
                                "gridProperties."
                                "columnCount"
                            ),
                        }
                    }
                ]
            },
        )
        .execute()
    )

    print(
        "[TRIP SHEET] Grid expanded: "
        f"rows {current_rows}->{new_rows}, "
        f"columns {current_columns}->{new_columns}"
    )
    
def build_trip_row(
    trip_id,
    trip_detail,
):
    trip_id = str(
        trip_id or ""
    ).strip()

    if not trip_id:
        raise RuntimeError(
            "trip_id rỗng"
        )

    detail = normalize_spx_data(
        trip_detail
    )

    row = {
        "_key":
            trip_id,

        "trip_id":
            trip_id,
    }

    if isinstance(
        detail,
        dict,
    ):
        row.update(
            flatten_dict(
                detail
            )
        )

    row[
        "sync_time"
    ] = now_vn()

    return row


def build_trip_rows(
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

        trip_id = str(
            item.get(
                "trip_id"
            )
            or item.get(
                "id"
            )
            or ""
        ).strip()

        if not trip_id:
            continue

        if trip_id in seen:
            continue

        seen.add(
            trip_id
        )

        try:
            row = build_trip_row(
                trip_id=
                    trip_id,

                trip_detail=
                    item,
            )
        except Exception:
            continue

        rows.append(
            row
        )

    return rows


def upsert_trip_rows(
    service,
    sheet_name,
    rows,
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

    existing = read_existing_data(
        service,
        sheet_name,
    )

    headers = ensure_headers(
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

    unchanged_count = 0
    skipped_count = 0

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

        row_number = existing_map.get(
            key
        )

        if row_number is None:
            values = [
                row.get(
                    header,
                    "",
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

            new_value = row.get(
                header,
                "",
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
                final_value = (
                    new_value
                )

            else:
                final_value = (
                    old_value
                )

            if str(
                final_value
            ) != str(
                old_value
            ):
                data_changed = True

            merged_values.append(
                final_value
            )

        if not data_changed:
            unchanged_count += 1
            continue

        if sync_index is not None:
            incoming_sync = row.get(
                "sync_time",
                "",
            )

            if incoming_sync not in (
                None,
                "",
            ):
                merged_values[
                    sync_index
                ] = incoming_sync

        updates.append({
            "range": (
                f"'{sheet_name}'!"
                f"A{row_number}:"
                f"{end_col}{row_number}"
            ),

            "values": [
                merged_values
            ],
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
                },
            )
            .execute()
        )

    if inserts:
        start_row = max(
            2,
            last_row + 1,
        )

        end_row = (
            start_row
            + len(
                inserts
            )
            - 1
        )
        ensure_trip_grid(
            service=
                service,

            required_rows=
                end_row,

            required_columns=
                len(
                    headers
                ),
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
                },
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

        "unchanged":
            unchanged_count,

        "skipped":
            skipped_count,
    }


def push_trip_rows(
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
        service = get_sheets_service()

    sheet_name = get_sheet_name_by_gid(
        gid=
            TRIP_GID,

        service=
            service,
    )

    return upsert_trip_rows(
        service=
            service,

        sheet_name=
            sheet_name,

        rows=
            rows,
    )


def push_trip(
    trip_id,
    trip_detail,
    service=None,
):
    row = build_trip_row(
        trip_id=
            trip_id,

        trip_detail=
            trip_detail,
    )

    result = push_trip_rows(
        rows=[
            row
        ],

        service=
            service,
    )

    return {
        "trip_id":
            str(
                trip_id
            ).strip(),

        "row":
            row,

        "sheet":
            result,
    }