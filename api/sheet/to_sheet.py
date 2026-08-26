from api.sheet.common import (
    first_not_empty,
    flatten_dict,
    format_timestamp,
    get_sheet_name_by_gid,
    get_sheets_service,
    now_vn,
    read_existing_data,
    row_to_dict,
    column_letter,
    last_used_row,
    ensure_headers,
    SPREADSHEET_ID,
)


TO_GID = 91531087


def get_to_identity_parts(
    item,
):
    to_id = first_not_empty(
        item,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        ),
    )

    station_id = first_not_empty(
        item,
        (
            "station_id",
            "loaded_station_id",
            "actual_loaded_station_id",
            "unloaded_station_id",
            "actual_unloaded_station_id",
            "current_station_id",
        ),
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
    sequence=1,
):
    trip_id = str(
        trip_id or ""
    ).strip()

    direction = str(
        direction or "outbound"
    ).strip().lower()

    sequence = str(
        sequence or 1
    ).strip()

    (
        to_id,
        station_id,
    ) = get_to_identity_parts(
        item
    )

    return (
        f"{trip_id}|"
        f"{direction}|"
        f"{sequence}|"
        f"{station_id}|"
        f"{to_id}"
    )


def is_to_complete(
    row,
):
    if not isinstance(
        row,
        dict,
    ):
        return False

    to_id = first_not_empty(
        row,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        ),
    )

    loaded_time = first_not_empty(
        row,
        (
            "loaded_time",
            "to_scan_time",
            "actual_loaded_time",
        ),
    )

    loaded_station = first_not_empty(
        row,
        (
            "loaded_station_id",
            "loaded_station_name",
            "loaded_station",
            "actual_loaded_station_id",
            "actual_loaded_station_name",
            "to_scan_station",
        ),
    )

    unloaded_time = first_not_empty(
        row,
        (
            "unloaded_time",
            "actual_unloaded_time",
            "to_unload_time",
        ),
    )

    unloaded_station = first_not_empty(
        row,
        (
            "actual_unloaded_station_id",
            "actual_unloaded_station_name",
            "unloaded_station_id",
            "unloaded_station_name",
            "actual_unloaded_station",
            "unloaded_station",
            "to_unload_station",
        ),
    )

    return bool(
        to_id
        and loaded_time
        and loaded_station
        and unloaded_time
        and unloaded_station
    )


def build_to_row(
    trip_id,
    item,
    direction="outbound",
    sequence=1,
    sync_time=None,
):
    if not isinstance(
        item,
        dict,
    ):
        raise RuntimeError(
            "TO item không hợp lệ"
        )

    trip_id = str(
        trip_id or ""
    ).strip()

    if not trip_id:
        raise RuntimeError(
            "trip_id rỗng"
        )

    direction = str(
        direction or "outbound"
    ).strip().lower()

    sequence = (
        sequence
        if sequence not in (
            None,
            "",
        )
        else 1
    )

    (
        to_id,
        station_id,
    ) = get_to_identity_parts(
        item
    )

    key = make_to_key(
        trip_id=
            trip_id,
        item=
            item,
        direction=
            direction,
        sequence=
            sequence,
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
    ] = (
        sync_time
        or now_vn()
    )

    return row


def build_to_rows(
    trip_id,
    items,
    direction="outbound",
    sequence=1,
):
    if not isinstance(
        items,
        list,
    ):
        return []

    rows = []

    sync_time = now_vn()

    seen = set()

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        try:
            row = build_to_row(
                trip_id=
                    trip_id,
                item=
                    item,
                direction=
                    direction,
                sequence=
                    sequence,
                sync_time=
                    sync_time,
            )
        except Exception:
            continue

        key = str(
            row.get(
                "_key",
                "",
            )
            or ""
        ).strip()

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        rows.append(
            row
        )

    return rows


def canonical_to_identity(
    row,
):
    if not isinstance(
        row,
        dict,
    ):
        return ""

    trip_id = str(
        row.get(
            "trip_id",
            "",
        )
        or ""
    ).strip()

    direction = str(
        row.get(
            "direction",
            "outbound",
        )
        or "outbound"
    ).strip().lower()

    sequence = str(
        row.get(
            "sequence_number",
            row.get(
                "sequence",
                1,
            ),
        )
        or 1
    ).strip()

    to_id = first_not_empty(
        row,
        (
            "to_id",
            "transport_order_id",
            "id",
            "to_number",
            "scan_number",
        ),
    )

    station_id = first_not_empty(
        row,
        (
            "station_id",
            "loaded_station_id",
            "actual_loaded_station_id",
            "unloaded_station_id",
            "actual_unloaded_station_id",
            "current_station_id",
        ),
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


def get_existing_to_status(
    service=None,
):
    if service is None:
        service = (
            get_sheets_service()
        )

    to_sheet = (
        get_sheet_name_by_gid(
            gid=
                TO_GID,
            service=
                service,
        )
    )

    existing = (
        read_existing_data(
            service,
            to_sheet,
        )
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

    for (
        row_number,
        values
    ) in enumerate(
        existing[1:],
        start=2,
    ):
        row = row_to_dict(
            headers,
            values,
        )

        identity = (
            canonical_to_identity(
                row
            )
        )

        if not identity:
            continue

        complete_value = str(
            row.get(
                "is_complete",
                "",
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
            complete = (
                is_to_complete(
                    row
                )
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
    rows,
    service=None,
):
    existing_status = (
        get_existing_to_status(
            service=
                service
        )
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
            canonical_to_identity(
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

    direct_key_map = {}
    identity_map = {}

    for (
        row_number,
        values
    ) in enumerate(
        existing[1:],
        start=2,
    ):
        old_row = (
            row_to_dict(
                headers,
                values,
            )
        )

        old_key = str(
            old_row.get(
                "_key",
                "",
            )
            or ""
        ).strip()

        if old_key:
            direct_key_map[
                old_key
            ] = row_number

        identity = (
            canonical_to_identity(
                old_row
            )
        )

        if (
            identity
            and identity
            not in identity_map
        ):
            identity_map[
                identity
            ] = row_number

    end_col = (
        column_letter(
            len(
                headers
            )
        )
    )

    updates = []
    inserts = []

    skipped_count = 0
    unchanged_count = 0

    last_row = (
        last_used_row(
            existing
        )
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

        identity = (
            canonical_to_identity(
                row
            )
        )

        if not key:
            skipped_count += 1
            continue

        row_number = (
            direct_key_map.get(
                key
            )
        )

        if (
            row_number is None
            and identity
        ):
            row_number = (
                identity_map.get(
                    identity
                )
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

        old_row = (
            row_to_dict(
                headers,
                old_values,
            )
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
            old_value = (
                old_row.get(
                    header,
                    "",
                )
            )

            new_value = (
                row.get(
                    header,
                    "",
                )
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
            incoming_sync = (
                row.get(
                    "sync_time",
                    "",
                )
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


def push_to_rows(
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
                TO_GID,
            service=
                service,
        )
    )

    return upsert_to_rows(
        service=
            service,

        sheet_name=
            sheet_name,

        rows=
            rows,
    )


def push_to_items(
    trip_id,
    items,
    direction="outbound",
    sequence=1,
    service=None,
):
    rows = (
        build_to_rows(
            trip_id=
                trip_id,

            items=
                items,

            direction=
                direction,

            sequence=
                sequence,
        )
    )

    result = (
        push_to_rows(
            rows=
                rows,

            service=
                service,
        )
    )

    return {
        "trip_id":
            str(
                trip_id
            ).strip(),

        "direction":
            str(
                direction
            ).strip().lower(),

        "sequence":
            sequence,

        "rows":
            len(
                rows
            ),

        "sheet":
            result,
    }