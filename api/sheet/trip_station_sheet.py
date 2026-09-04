from api.sheet.common import (
    SPREADSHEET_ID,
    column_letter,
    ensure_headers,
    flatten_dict,
    get_sheet_name_by_gid,
    get_sheets_service,
    last_used_row,
    normalize_sheet_value,
    normalize_spx_data,
    now_vn,
    read_existing_data,
    row_to_dict,
)


TRIP_STATION_GID = 1157738563

HUNG_YEN_SOC_ID = 3909
HUNG_YEN_SOC_NAME = "Hung Yen SOC"


def _text(
    value,
):
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _int_value(
    value,
    default=0,
):
    try:
        return int(
            float(
                value
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return default


def _ensure_sheet_grid(
    service,
    sheet_name,
    required_rows,
    required_columns,
):
    metadata = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,

            fields=(
                "sheets("
                "properties("
                "sheetId,"
                "title,"
                "gridProperties("
                "rowCount,"
                "columnCount"
                ")"
                ")"
                ")"
            ),
        )
        .execute()
    )

    target_sheet = None

    for sheet in metadata.get(
        "sheets",
        [],
    ):
        properties = sheet.get(
            "properties",
            {},
        )

        if (
            properties.get(
                "title"
            )
            == sheet_name
        ):
            target_sheet = properties
            break

    if target_sheet is None:
        raise RuntimeError(
            f"Không tìm thấy sheet: {sheet_name}"
        )

    sheet_id = target_sheet.get(
        "sheetId"
    )

    grid = target_sheet.get(
        "gridProperties",
        {},
    )

    current_rows = _int_value(
        grid.get(
            "rowCount"
        ),
        0,
    )

    current_columns = _int_value(
        grid.get(
            "columnCount"
        ),
        0,
    )

    requests = []

    if required_rows > current_rows:
        requests.append({
            "appendDimension": {
                "sheetId":
                    sheet_id,

                "dimension":
                    "ROWS",

                "length":
                    required_rows
                    - current_rows,
            }
        })

    if required_columns > current_columns:
        requests.append({
            "appendDimension": {
                "sheetId":
                    sheet_id,

                "dimension":
                    "COLUMNS",

                "length":
                    required_columns
                    - current_columns,
            }
        })

    if not requests:
        return {
            "rows":
                current_rows,

            "columns":
                current_columns,
        }

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=
                SPREADSHEET_ID,

            body={
                "requests":
                    requests,
            },
        )
        .execute()
    )

    final_rows = max(
        current_rows,
        required_rows,
    )

    final_columns = max(
        current_columns,
        required_columns,
    )

    print(
        "[TRIP STATION SHEET] "
        f"Grid expanded: "
        f"rows {current_rows}->{final_rows}, "
        f"columns {current_columns}->{final_columns}"
    )

    return {
        "rows":
            final_rows,

        "columns":
            final_columns,
    }


def _get_trip_station_list(
    detail,
):
    if not isinstance(
        detail,
        dict,
    ):
        return []

    stations = detail.get(
        "trip_station"
    )

    if isinstance(
        stations,
        list,
    ):
        return [
            item
            for item in stations
            if isinstance(
                item,
                dict,
            )
        ]

    for key in (
        "trip_stations",
        "trip_station_list",
        "station_list",
        "stations",
        "route_stations",
        "route_station_list",
    ):
        value = detail.get(
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


def _station_id(
    item,
):
    if not isinstance(
        item,
        dict,
    ):
        return ""

    value = (
        item.get(
            "station"
        )
        or item.get(
            "station_id"
        )
        or ""
    )

    if not value:
        station_info = item.get(
            "station_info"
        )

        if isinstance(
            station_info,
            dict,
        ):
            value = station_info.get(
                "id"
            )

    return _text(
        value
    )


def _station_name(
    item,
):
    if not isinstance(
        item,
        dict,
    ):
        return ""

    value = (
        item.get(
            "station_name"
        )
        or ""
    )

    if not value:
        station_info = item.get(
            "station_info"
        )

        if isinstance(
            station_info,
            dict,
        ):
            value = station_info.get(
                "station_name"
            )

    return _text(
        value
    )


def _station_code(
    item,
):
    if not isinstance(
        item,
        dict,
    ):
        return ""

    value = (
        item.get(
            "station_code"
        )
        or ""
    )

    if not value:
        station_info = item.get(
            "station_info"
        )

        if isinstance(
            station_info,
            dict,
        ):
            value = station_info.get(
                "station_code"
            )

    return _text(
        value
    )


def _sequence_number(
    item,
    fallback,
):
    if not isinstance(
        item,
        dict,
    ):
        return fallback

    return _int_value(
        item.get(
            "sequence_number"
        )
        or item.get(
            "sequence"
        )
        or item.get(
            "station_sequence"
        )
        or fallback,
        fallback,
    )


def _get_first_docked_info(
    logs,
):
    result = {
        "time":
            "",

        "number":
            "",

        "operator":
            "",
    }

    if not isinstance(
        logs,
        list,
    ):
        return result

    for item in logs:
        if not isinstance(
            item,
            dict,
        ):
            continue

        docked_time = (
            item.get(
                "docked_time"
            )
            or item.get(
                "dock_time"
            )
            or ""
        )

        docked_number = (
            item.get(
                "docked_number"
            )
            or item.get(
                "dock_number"
            )
            or ""
        )

        docked_operator = (
            item.get(
                "docked_operator"
            )
            or item.get(
                "operator"
            )
            or ""
        )

        if (
            docked_time
            or docked_number
            or docked_operator
        ):
            result = {
                "time":
                    docked_time,

                "number":
                    docked_number,

                "operator":
                    docked_operator,
            }

            break

    return result


def _get_docked_info(
    item,
):
    inbound = _get_first_docked_info(
        item.get(
            "unloading_docked_logs"
        )
    )

    outbound = _get_first_docked_info(
        item.get(
            "loading_docked_logs"
        )
    )

    return {
        "inbound_docked_time":
            inbound.get(
                "time",
                "",
            ),

        "inbound_docked_number":
            inbound.get(
                "number",
                "",
            ),

        "inbound_docked_operator":
            inbound.get(
                "operator",
                "",
            ),

        "outbound_docked_time":
            outbound.get(
                "time",
                "",
            ),

        "outbound_docked_number":
            outbound.get(
                "number",
                "",
            ),

        "outbound_docked_operator":
            outbound.get(
                "operator",
                "",
            ),
    }


def _normalize_row_times(
    row,
):
    if not isinstance(
        row,
        dict,
    ):
        return row

    result = {}

    for (
        field_name,
        value
    ) in row.items():
        result[
            field_name
        ] = normalize_sheet_value(
            field_name,
            value,
        )

    return result


def build_trip_station_rows(
    trip_id,
    trip_detail,
):
    trip_id = _text(
        trip_id
    )

    if not trip_id:
        raise RuntimeError(
            "trip_id rỗng"
        )

    detail = normalize_spx_data(
        trip_detail
    )

    if not isinstance(
        detail,
        dict,
    ):
        return []

    stations = _get_trip_station_list(
        detail
    )

    if not stations:
        return []

    trip_number = _text(
        detail.get(
            "trip_number"
        )
    )

    trip_name = _text(
        detail.get(
            "trip_name"
        )
    )

    trip_date = detail.get(
        "trip_date",
        "",
    )

    trip_status = detail.get(
        "trip_status",
        "",
    )

    trip_source = detail.get(
        "trip_source",
        "",
    )

    trip_type = detail.get(
        "trip_type",
        "",
    )

    trip_type_name = detail.get(
        "trip_type_name",
        "",
    )

    vehicle_number = _text(
        detail.get(
            "vehicle_number"
        )
    )

    schedule_vehicle_number = _text(
        detail.get(
            "schedule_vehicle_number"
        )
    )

    vehicle_type = detail.get(
        "vehicle_type",
        "",
    )

    vehicle_type_name = _text(
        detail.get(
            "vehicle_type_name"
        )
    )

    driver = detail.get(
        "driver",
        "",
    )

    driver_name = _text(
        detail.get(
            "driver_name"
        )
    )

    agency_id = detail.get(
        "agency_id",
        "",
    )

    agency_name = _text(
        detail.get(
            "agency_name"
        )
    )

    completed_time = detail.get(
        "completed_time",
        "",
    )

    sync_time = now_vn()

    sequence_values = []

    for (
        index,
        item
    ) in enumerate(
        stations,
        start=1,
    ):
        sequence_values.append(
            _sequence_number(
                item,
                index,
            )
        )

    valid_sequences = [
        value
        for value in sequence_values
        if value > 0
    ]

    min_sequence = (
        min(
            valid_sequences
        )
        if valid_sequences
        else 1
    )

    max_sequence = (
        max(
            valid_sequences
        )
        if valid_sequences
        else len(
            stations
        )
    )

    rows = []

    seen = set()

    for (
        index,
        item
    ) in enumerate(
        stations,
        start=1,
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        station_id = _station_id(
            item
        )

        station_name = _station_name(
            item
        )

        station_code = _station_code(
            item
        )

        sequence = _sequence_number(
            item,
            index,
        )

        key = (
            f"{trip_id}|"
            f"{sequence}|"
            f"{station_id}"
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        is_origin = (
            sequence
            == min_sequence
        )

        is_destination = (
            sequence
            == max_sequence
        )

        is_middle = (
            not is_origin
            and not is_destination
        )

        is_hung_yen = (
            _int_value(
                station_id
            )
            == HUNG_YEN_SOC_ID
            or station_name.lower()
            == HUNG_YEN_SOC_NAME.lower()
        )

        if is_origin:
            station_role = "origin"

        elif is_destination:
            station_role = "destination"

        else:
            station_role = "middle"

        row = {}

        flat_item = flatten_dict(
            item
        )

        if isinstance(
            flat_item,
            dict,
        ):
            row.update(
                flat_item
            )

        row.update({
            "_key":
                key,

            "trip_id":
                trip_id,

            "trip_number":
                trip_number,

            "trip_name":
                trip_name,

            "trip_date":
                trip_date,

            "trip_status":
                trip_status,

            "trip_source":
                trip_source,

            "trip_type":
                trip_type,

            "trip_type_name":
                trip_type_name,

            "vehicle_number":
                vehicle_number,

            "schedule_vehicle_number":
                schedule_vehicle_number,

            "vehicle_type":
                vehicle_type,

            "vehicle_type_name":
                vehicle_type_name,

            "driver":
                driver,

            "driver_name":
                driver_name,

            "agency_id":
                agency_id,

            "agency_name":
                agency_name,

            "completed_time":
                completed_time,

            "sequence_number":
                sequence,

            "station_id":
                station_id,

            "station_name":
                station_name,

            "station_code":
                station_code,

            "station_role":
                station_role,

            "is_origin":
                is_origin,

            "is_middle":
                is_middle,

            "is_destination":
                is_destination,

            "is_hung_yen":
                is_hung_yen,

            "std":
                item.get(
                    "std",
                    "",
                ),

            "sta":
                item.get(
                    "sta",
                    "",
                ),

            "atd":
                item.get(
                    "atd",
                    "",
                ),

            "ata":
                item.get(
                    "ata",
                    "",
                ),

            "trip_station_status":
                item.get(
                    "trip_station_status",
                    "",
                ),

            "trip_driver_status":
                item.get(
                    "trip_driver_status",
                    "",
                ),

            "queuing_time":
                item.get(
                    "queuing_time",
                    "",
                ),

            "assign_time":
                item.get(
                    "assign_time",
                    "",
                ),

            "loading_time":
                item.get(
                    "loading_time",
                    "",
                ),

            "loaded_time":
                item.get(
                    "loaded_time",
                    "",
                ),

            "seal_time":
                item.get(
                    "seal_time",
                    "",
                ),

            "unseal_time":
                item.get(
                    "unseal_time",
                    "",
                ),

            "unloading_time":
                item.get(
                    "unloading_time",
                    "",
                ),

            "unloaded_time":
                item.get(
                    "unloaded_time",
                    "",
                ),

            "create_time":
                item.get(
                    "create_time",
                    "",
                ),

            "arrive_in_geofence":
                item.get(
                    "arrive_in_geofence",
                    "",
                ),

            "depart_in_geofence":
                item.get(
                    "depart_in_geofence",
                    "",
                ),

            "arrive_latitude":
                item.get(
                    "arrive_latitude",
                    "",
                ),

            "arrive_longitude":
                item.get(
                    "arrive_longitude",
                    "",
                ),

            "depart_latitude":
                item.get(
                    "depart_latitude",
                    "",
                ),

            "depart_longitude":
                item.get(
                    "depart_longitude",
                    "",
                ),

            "load_quantity":
                item.get(
                    "load_quantity",
                    "",
                ),

            "unload_quantity":
                item.get(
                    "unload_quantity",
                    "",
                ),

            "expect_unload_quantity":
                item.get(
                    "expect_unload_quantity",
                    "",
                ),

            "transport_quantity":
                item.get(
                    "transport_quantity",
                    "",
                ),

            "sync_time":
                sync_time,
        })

        row.update(
            _get_docked_info(
                item
            )
        )

        row = _normalize_row_times(
            row
        )

        rows.append(
            row
        )

    return rows
def _get_last_non_empty_position(
    service,
    sheet_name,
):
    try:
        result = (
            service
            .spreadsheets()
            .values()
            .get(
                spreadsheetId=
                    SPREADSHEET_ID,
                range=
                    f"'{sheet_name}'",
                majorDimension=
                    "ROWS",
            )
            .execute()
        )

        values = (
            result.get(
                "values",
                [],
            )
            or []
        )

        if not values:
            return 1, 1

        last_row = 1
        last_col = 1

        for (
            row_index,
            row,
        ) in enumerate(
            values,
            start=1,
        ):
            if not isinstance(
                row,
                list,
            ):
                continue

            row_has_value = False

            for (
                col_index,
                value,
            ) in enumerate(
                row,
                start=1,
            ):
                if str(
                    value
                    if value is not None
                    else ""
                ).strip():
                    row_has_value = True

                    if (
                        col_index
                        > last_col
                    ):
                        last_col = (
                            col_index
                        )

            if row_has_value:
                last_row = (
                    row_index
                )

        return (
            last_row,
            last_col,
        )

    except Exception as e:
        print(
            "[GRID CLEANUP] "
            f"Không đọc được "
            f"{sheet_name}: {e}"
        )

        return None, None


def _compact_workbook_grid(
    service,
    exclude_sheet_id=None,
    row_buffer=100,
    column_buffer=5,
):
    metadata = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            fields=(
                "sheets("
                "properties("
                "sheetId,"
                "title,"
                "gridProperties("
                "rowCount,"
                "columnCount"
                ")"
                ")"
                ")"
            ),
        )
        .execute()
    )

    requests = []

    before_cells = 0
    after_cells = 0

    for sheet in (
        metadata.get(
            "sheets",
            [],
        )
        or []
    ):
        properties = (
            sheet.get(
                "properties",
                {},
            )
        )

        sheet_id = int(
            properties.get(
                "sheetId",
                -1,
            )
        )

        sheet_name = str(
            properties.get(
                "title",
                "",
            )
            or ""
        )

        grid = (
            properties.get(
                "gridProperties",
                {},
            )
        )

        current_rows = int(
            grid.get(
                "rowCount",
                1,
            )
            or 1
        )

        current_columns = int(
            grid.get(
                "columnCount",
                1,
            )
            or 1
        )

        before_cells += (
            current_rows
            * current_columns
        )

        if (
            exclude_sheet_id
            is not None
            and sheet_id
            == int(
                exclude_sheet_id
            )
        ):
            after_cells += (
                current_rows
                * current_columns
            )

            continue

        (
            used_rows,
            used_columns,
        ) = (
            _get_last_non_empty_position(
                service,
                sheet_name,
            )
        )

        if (
            used_rows is None
            or used_columns is None
        ):
            after_cells += (
                current_rows
                * current_columns
            )

            continue

        target_rows = max(
            used_rows
            + row_buffer,
            100,
        )

        target_columns = max(
            used_columns
            + column_buffer,
            10,
        )

        target_rows = min(
            target_rows,
            current_rows,
        )

        target_columns = min(
            target_columns,
            current_columns,
        )

        after_cells += (
            target_rows
            * target_columns
        )

        if (
            current_rows
            > target_rows
        ):
            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId":
                            sheet_id,

                        "dimension":
                            "ROWS",

                        "startIndex":
                            target_rows,

                        "endIndex":
                            current_rows,
                    }
                }
            })

            print(
                "[GRID CLEANUP] "
                f"{sheet_name}: "
                f"rows "
                f"{current_rows}"
                f"->{target_rows}"
            )

        if (
            current_columns
            > target_columns
        ):
            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId":
                            sheet_id,

                        "dimension":
                            "COLUMNS",

                        "startIndex":
                            target_columns,

                        "endIndex":
                            current_columns,
                    }
                }
            })

            print(
                "[GRID CLEANUP] "
                f"{sheet_name}: "
                f"columns "
                f"{current_columns}"
                f"->{target_columns}"
            )

    if requests:
        for index in range(
            0,
            len(
                requests
            ),
            50,
        ):
            batch = (
                requests[
                    index:
                    index + 50
                ]
            )

            (
                service
                .spreadsheets()
                .batchUpdate(
                    spreadsheetId=
                        SPREADSHEET_ID,

                    body={
                        "requests":
                            batch,
                    },
                )
                .execute()
            )

    print(
        "[GRID CLEANUP] "
        f"Workbook cells "
        f"{before_cells:,}"
        f" -> "
        f"{after_cells:,}"
    )


def ensure_trip_station_grid(
    service,
    required_rows,
    required_columns,
):
    def get_trip_station_grid():
        spreadsheet = (
            service
            .spreadsheets()
            .get(
                spreadsheetId=
                    SPREADSHEET_ID,
                fields=(
                    "sheets("
                    "properties("
                    "sheetId,"
                    "title,"
                    "gridProperties("
                    "rowCount,"
                    "columnCount"
                    ")"
                    ")"
                    ")"
                ),
            )
            .execute()
        )

        for sheet in (
            spreadsheet.get(
                "sheets",
                [],
            )
            or []
        ):
            properties = (
                sheet.get(
                    "properties",
                    {},
                )
            )

            if (
                int(
                    properties.get(
                        "sheetId",
                        -1,
                    )
                )
                == int(
                    TRIP_STATION_GID
                )
            ):
                return (
                    properties
                )

        return None

    sheet_properties = (
        get_trip_station_grid()
    )

    if not sheet_properties:
        raise RuntimeError(
            "Không tìm thấy "
            f"TRIP_STATION_GID="
            f"{TRIP_STATION_GID}"
        )

    grid = (
        sheet_properties.get(
            "gridProperties",
            {},
        )
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

    required_rows = max(
        1,
        int(
            required_rows
            or 1
        ),
    )

    required_columns = max(
        1,
        int(
            required_columns
            or 1
        ),
    )

    target_rows = max(
        current_rows,
        required_rows,
    )

    target_columns = max(
        current_columns,
        required_columns,
    )

    if (
        target_rows
        == current_rows
        and
        target_columns
        == current_columns
    ):
        return

    def expand():
        requests = []

        if (
            target_rows
            > current_rows
        ):
            requests.append({
                "appendDimension": {
                    "sheetId":
                        TRIP_STATION_GID,

                    "dimension":
                        "ROWS",

                    "length":
                        target_rows
                        - current_rows,
                }
            })

        if (
            target_columns
            > current_columns
        ):
            requests.append({
                "appendDimension": {
                    "sheetId":
                        TRIP_STATION_GID,

                    "dimension":
                        "COLUMNS",

                    "length":
                        target_columns
                        - current_columns,
                }
            })

        if not requests:
            return

        (
            service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=
                    SPREADSHEET_ID,

                body={
                    "requests":
                        requests,
                },
            )
            .execute()
        )

    try:
        expand()

    except Exception as e:
        message = str(
            e
        )

        if (
            "10000000 cells"
            not in message
            and
            "above the limit"
            not in message
        ):
            raise

        print(
            "[TRIP STATION SHEET] "
            "Workbook đạt giới hạn "
            "10,000,000 cells."
        )

        print(
            "[TRIP STATION SHEET] "
            "Đang thu gọn grid trống..."
        )

        _compact_workbook_grid(
            service=
                service,

            exclude_sheet_id=
                TRIP_STATION_GID,

            row_buffer=
                100,

            column_buffer=
                5,
        )

        sheet_properties = (
            get_trip_station_grid()
        )

        if not sheet_properties:
            raise RuntimeError(
                "Không tìm thấy Trip Station "
                "sau khi cleanup."
            )

        grid = (
            sheet_properties.get(
                "gridProperties",
                {},
            )
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

        target_rows = max(
            current_rows,
            required_rows,
        )

        target_columns = max(
            current_columns,
            required_columns,
        )

        expand()

    print(
        "[TRIP STATION SHEET] "
        "Grid expanded: "
        f"rows "
        f"{current_rows}"
        f"->{target_rows}, "
        f"columns "
        f"{current_columns}"
        f"->{target_columns}"
    )

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

        key = _text(
            values[
                key_index
            ]
        )

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

        key = _text(
            row.get(
                "_key"
            )
        )

        if not key:
            skipped_count += 1
            continue

        row_number = existing_map.get(
            key
        )

        if row_number is None:
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

            new_value = normalize_sheet_value(
                header,
                new_value,
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

            if _text(
                final_value
            ) != _text(
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
            incoming_sync = normalize_sheet_value(
                "sync_time",
                row.get(
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

        ensure_trip_station_grid(
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
            _text(
                trip_id
            ),

        "rows":
            len(
                rows
            ),

        "sheet":
            result,
    }