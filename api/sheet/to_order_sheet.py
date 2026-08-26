from api.sheet.common import (
    flatten_dict,
    format_timestamp,
    get_sheet_name_by_gid,
    get_sheets_service,
    now_vn,
    upsert_rows,
)


TO_ORDER_GID = 1056134297


def build_to_order_row(
    trip_id,
    to_number,
    item,
):
    trip_id = str(
        trip_id or ""
    ).strip()

    to_number = str(
        to_number or ""
    ).strip().upper()

    if not trip_id:
        raise RuntimeError(
            "trip_id rỗng"
        )

    if not to_number:
        raise RuntimeError(
            "to_number rỗng"
        )

    if not isinstance(
        item,
        dict,
    ):
        raise RuntimeError(
            "TO Order item không hợp lệ"
        )

    shipment_id = str(
        item.get(
            "shipment_id"
        )
        or item.get(
            "fleet_order_id"
        )
        or ""
    ).strip().upper()

    if not shipment_id:
        raise RuntimeError(
            "Không tìm thấy shipment_id"
        )

    key = (
        f"{trip_id}|"
        f"{to_number}|"
        f"{shipment_id}"
    )

    row = {
        "_key":
            key,

        "trip_id":
            trip_id,

        "to_number":
            to_number,

        "shipment_id":
            shipment_id,
    }

    fleet_order_id = str(
        item.get(
            "fleet_order_id"
        )
        or ""
    ).strip().upper()

    if fleet_order_id:
        row[
            "fleet_order_id"
        ] = fleet_order_id

    sls_tracking_number = str(
        item.get(
            "sls_tracking_number"
        )
        or ""
    ).strip()

    if sls_tracking_number:
        row[
            "sls_tracking_number"
        ] = sls_tracking_number

    row[
        "station_name"
    ] = (
        item.get(
            "station_name"
        )
        or ""
    )

    row[
        "station_code"
    ] = (
        item.get(
            "station_code"
        )
        or ""
    )

    row[
        "third_party_sorting_code"
    ] = (
        item.get(
            "third_party_sorting_code"
        )
        or ""
    )

    row[
        "third_party_tracking_num"
    ] = (
        item.get(
            "third_party_tracking_num"
        )
        or ""
    )

    row[
        "receiver_name"
    ] = (
        item.get(
            "receiver_name"
        )
        or ""
    )

    row[
        "zone_id"
    ] = (
        item.get(
            "zone_id"
        )
        or ""
    )

    row[
        "zone_name"
    ] = (
        item.get(
            "zone_name"
        )
        or ""
    )

    row[
        "chargeable_weight"
    ] = (
        item.get(
            "chargeable_weight"
        )
        or ""
    )

    row[
        "remark"
    ] = (
        item.get(
            "remark"
        )
        or ""
    )

    row[
        "status"
    ] = (
        item.get(
            "status"
        )
        or ""
    )

    row[
        "type"
    ] = (
        item.get(
            "type"
        )
        or ""
    )

    row[
        "high_value"
    ] = (
        item.get(
            "high_value"
        )
        or ""
    )

    row[
        "receive_tag"
    ] = (
        item.get(
            "receive_tag"
        )
        or ""
    )

    row[
        "transfer_direction"
    ] = (
        item.get(
            "transfer_direction"
        )
        or ""
    )

    row[
        "pick_direction"
    ] = (
        item.get(
            "pick_direction"
        )
        or ""
    )

    row[
        "receive_station_id"
    ] = (
        item.get(
            "receive_station_id"
        )
        or ""
    )

    row[
        "receive_station_type"
    ] = (
        item.get(
            "receive_station_type"
        )
        or ""
    )

    row[
        "receive_operator"
    ] = (
        item.get(
            "receive_operator"
        )
        or ""
    )

    row[
        "receive_time"
    ] = format_timestamp(
        item.get(
            "receive_time"
        )
    )

    row[
        "ctime"
    ] = format_timestamp(
        item.get(
            "ctime"
        )
    )

    row[
        "mtime"
    ] = format_timestamp(
        item.get(
            "mtime"
        )
    )

    flattened = flatten_dict(
        item
    )

    protected_fields = {
        "_key",
        "trip_id",
        "to_number",
        "shipment_id",
        "fleet_order_id",
        "sls_tracking_number",
        "station_name",
        "station_code",
        "third_party_sorting_code",
        "third_party_tracking_num",
        "receiver_name",
        "zone_id",
        "zone_name",
        "chargeable_weight",
        "remark",
        "status",
        "type",
        "high_value",
        "receive_tag",
        "transfer_direction",
        "pick_direction",
        "receive_station_id",
        "receive_station_type",
        "receive_operator",
        "receive_time",
        "ctime",
        "mtime",
    }

    for (
        field,
        value
    ) in flattened.items():
        if field in protected_fields:
            continue

        row[
            field
        ] = value

    row[
        "sync_time"
    ] = now_vn()

    return row


def build_to_order_rows(
    trip_id,
    to_number,
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

        shipment_id = str(
            item.get(
                "shipment_id"
            )
            or item.get(
                "fleet_order_id"
            )
            or ""
        ).strip().upper()

        if not shipment_id:
            continue

        key = (
            str(
                trip_id
            ).strip(),

            str(
                to_number
            ).strip().upper(),

            shipment_id,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        try:
            row = build_to_order_row(
                trip_id=
                    trip_id,

                to_number=
                    to_number,

                item=
                    item,
            )

            rows.append(
                row
            )

        except Exception:
            continue

    return rows


def build_to_order_rows_from_scan(
    trip_id,
    scan_result,
):
    if not isinstance(
        scan_result,
        dict,
    ):
        return []

    data = scan_result.get(
        "data",
        {}
    )

    if not isinstance(
        data,
        dict,
    ):
        return []

    to_number = str(
        data.get(
            "to_number"
        )
        or ""
    ).strip().upper()

    items = data.get(
        "list",
        []
    )

    if not isinstance(
        items,
        list,
    ):
        items = []

    if not to_number:
        for item in items:
            if not isinstance(
                item,
                dict,
            ):
                continue

            to_number = str(
                item.get(
                    "to_number"
                )
                or ""
            ).strip().upper()

            if to_number:
                break

    if not to_number:
        return []

    return build_to_order_rows(
        trip_id=
            trip_id,

        to_number=
            to_number,

        items=
            items,
    )


def get_shipment_ids_from_to_order_rows(
    rows,
):
    shipment_ids = []

    seen = set()

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        shipment_id = str(
            row.get(
                "shipment_id"
            )
            or row.get(
                "fleet_order_id"
            )
            or ""
        ).strip().upper()

        if not shipment_id:
            continue

        if shipment_id in seen:
            continue

        seen.add(
            shipment_id
        )

        shipment_ids.append(
            shipment_id
        )

    return shipment_ids


def push_to_order_rows(
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
                TO_ORDER_GID,

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
            True,
    )


def push_to_order_scan(
    trip_id,
    scan_result,
    service=None,
):
    rows = (
        build_to_order_rows_from_scan(
            trip_id=
                trip_id,

            scan_result=
                scan_result,
        )
    )

    result = (
        push_to_order_rows(
            rows=
                rows,

            service=
                service,
        )
    )

    return {
        "rows":
            len(
                rows
            ),

        "shipment_ids":
            get_shipment_ids_from_to_order_rows(
                rows
            ),

        "sheet":
            result,
    }


def push_to_order_items(
    trip_id,
    to_number,
    items,
    service=None,
):
    rows = (
        build_to_order_rows(
            trip_id=
                trip_id,

            to_number=
                to_number,

            items=
                items,
        )
    )

    result = (
        push_to_order_rows(
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

        "to_number":
            str(
                to_number
            ).strip().upper(),

        "rows":
            len(
                rows
            ),

        "shipment_ids":
            get_shipment_ids_from_to_order_rows(
                rows
            ),

        "sheet":
            result,
    }