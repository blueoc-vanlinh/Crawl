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


TRIP_STATION_GID = 1157738563


def build_trip_station_rows(
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

    rows = []

    sync_time = now_vn()

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

    def walk(
        data,
    ):
        if isinstance(
            data,
            dict,
        ):
            for (
                key,
                value
            ) in data.items():
                key_lower = str(
                    key
                ).strip().lower()

                if (
                    key_lower
                    in candidate_keys
                    and isinstance(
                        value,
                        list,
                    )
                ):
                    for item in value:
                        if isinstance(
                            item,
                            dict,
                        ):
                            found_items.append(
                                item
                            )

                walk(
                    value
                )

        elif isinstance(
            data,
            list,
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

        def collect(
            data,
        ):
            if isinstance(
                data,
                dict,
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
                list,
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
                for key
                in (
                    "station_id",
                    "station_name",
                    "station",
                    "station_code",
                )
            )

            has_sequence = any(
                key in item
                for key
                in (
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

    for (
        index,
        item
    ) in enumerate(
        found_items,
        start=1,
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

        station_code = (
            item.get(
                "station_code"
            )
            or item.get(
                "code"
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

            "station_code":
                station_code,
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


def upsert_trip_station_rows(
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
                final_value = new_value

            else:
                final_value = old_value

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


def push_trip_station_rows(
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
            TRIP_STATION_GID,

        service=
            service,
    )

    return upsert_trip_station_rows(
        service=
            service,

        sheet_name=
            sheet_name,

        rows=
            rows,
    )


def push_trip_stations(
    trip_id,
    trip_detail,
    service=None,
):
    rows = build_trip_station_rows(
        trip_id=
            trip_id,

        trip_detail=
            trip_detail,
    )

    result = push_trip_station_rows(
        rows=
            rows,

        service=
            service,
    )

    return {
        "trip_id":
            str(
                trip_id
            ).strip(),

        "rows":
            len(
                rows
            ),

        "sheet":
            result,
    }