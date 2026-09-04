from api.to.scanto import (
    scan_to_orders,
)

from api.sheet.to_order_sheet import (
    build_to_order_rows,
    get_shipment_ids_from_to_order_rows,
    push_to_order_rows,
)

from api.sheet.order_full_sheet import (
    build_full_order_row,
    push_full_order_rows,
)

from api.services.order_service import (
    check_order,
)


# ============================================================
# TO ORDERS
# ============================================================

def get_to_orders(
    to_number,
    query_params=None,
):
    """
    Crawl danh sách order thuộc TO.

    Tương đương logic cũ trong app.py:
        scan_to_orders(
            to_number=to_number,
            count=count,
        )
    """

    to_number = str(
        to_number or ""
    ).strip().upper()

    if not to_number:
        raise ValueError(
            "Thiếu to_number"
        )

    query_params = (
        query_params
        or {}
    )

    count = (
        query_params.get(
            "count",
            10000,
        )
    )

    try:
        count = int(
            count
        )
    except (
        TypeError,
        ValueError,
    ):
        count = 10000

    if count < 1:
        count = 10000

    data = scan_to_orders(
        to_number=to_number,
        count=count,
    )

    return {
        "success": True,
        "to_number": to_number,
        "data": data,
    }


# ============================================================
# TO SYNC
# ============================================================

def sync_to_orders(
    to_number,
    request_data=None,
    query_params=None,
):
    """
    Sync toàn bộ order của một TO.

    Flow:

        TO
         ↓
        scan_to_orders
         ↓
        build_to_order_rows
         ↓
        push_to_order_rows
         ↓
        lấy shipment_id
         ↓
        crawl order
         ↓
        build_full_order_row
         ↓
        push_full_order_rows
    """

    to_number = str(
        to_number or ""
    ).strip().upper()

    if not to_number:
        raise ValueError(
            "Thiếu to_number"
        )

    request_data = (
        request_data
        or {}
    )

    query_params = (
        query_params
        or {}
    )

    # --------------------------------------------------------
    # TRIP ID
    # --------------------------------------------------------

    trip_id = (
        query_params.get(
            "trip_id"
        )
        or request_data.get(
            "trip_id"
        )
    )

    if not trip_id:
        raise ValueError(
            "Thiếu trip_id"
        )

    trip_id = str(
        trip_id
    ).strip()

    # --------------------------------------------------------
    # COUNT
    # --------------------------------------------------------

    count = (
        query_params.get(
            "count"
        )
        or request_data.get(
            "count"
        )
        or 10000
    )

    try:
        count = int(
            count
        )
    except (
        TypeError,
        ValueError,
    ):
        count = 10000

    if count < 1:
        count = 10000

    # --------------------------------------------------------
    # BATCH SIZE
    # --------------------------------------------------------

    batch_size = (
        query_params.get(
            "batch_size"
        )
        or request_data.get(
            "batch_size"
        )
        or 20
    )

    try:
        batch_size = int(
            batch_size
        )
    except (
        TypeError,
        ValueError,
    ):
        batch_size = 20

    if batch_size < 1:
        batch_size = 20

    if batch_size > 100:
        batch_size = 100

    print(
        "=" * 70
    )

    print(
        f"TO SYNC: {to_number}"
    )

    print(
        f"TRIP ID: {trip_id}"
    )

    # --------------------------------------------------------
    # 1. SCAN TO
    # --------------------------------------------------------

    scan_result = scan_to_orders(
        to_number=to_number,
        count=count,
    )

    scan_data = (
        scan_result.get(
            "data",
            {},
        )
        if isinstance(
            scan_result,
            dict,
        )
        else {}
    )

    items = (
        scan_data.get(
            "list",
            [],
        )
        if isinstance(
            scan_data,
            dict,
        )
        else []
    )

    # --------------------------------------------------------
    # 2. BUILD TO ORDER ROWS
    # --------------------------------------------------------

    to_order_rows = build_to_order_rows(
        trip_id=trip_id,
        to_number=to_number,
        items=items,
    )

    # --------------------------------------------------------
    # 3. PUSH MAPPING SHEET
    # --------------------------------------------------------

    mapping_result = push_to_order_rows(
        to_order_rows
    )

    # --------------------------------------------------------
    # 4. GET SHIPMENT IDS
    # --------------------------------------------------------

    shipment_ids = (
        get_shipment_ids_from_to_order_rows(
            to_order_rows
        )
    )

    total_orders = len(
        shipment_ids
    )

    print(
        f"TO ORDERS: {total_orders}"
    )

    # --------------------------------------------------------
    # 5. CRAWL FULL ORDER
    # --------------------------------------------------------

    full_rows_buffer = []

    full_pushed = 0
    order_success = 0
    order_failed = 0

    failed_orders = []

    full_sheet_batches = []

    for (
        index,
        shipment_id,
    ) in enumerate(
        shipment_ids,
        start=1,
    ):

        shipment_id = str(
            shipment_id or ""
        ).strip().upper()

        if not shipment_id:
            continue

        print(
            f"[{index}/{total_orders}] "
            f"ORDER {shipment_id}"
        )

        try:

            order_data = check_order(
                shipment_id=shipment_id,
                station_id=None,
                station_type=2,
            )

            full_row = build_full_order_row(
                shipment_id=shipment_id,
                order_data=order_data,
            )

            full_rows_buffer.append(
                full_row
            )

            order_success += 1

        except Exception as e:

            order_failed += 1

            failed_orders.append({
                "shipment_id":
                    shipment_id,

                "error":
                    str(e),
            })

            print(
                f"[{index}/{total_orders}] "
                f"ERROR: {e}"
            )

        # ----------------------------------------------------
        # PUSH BATCH
        # ----------------------------------------------------

        if (
            len(
                full_rows_buffer
            )
            >= batch_size
        ):

            batch_result = (
                push_full_order_rows(
                    full_rows_buffer
                )
            )

            full_sheet_batches.append(
                batch_result
            )

            full_pushed += len(
                full_rows_buffer
            )

            full_rows_buffer = []

    # --------------------------------------------------------
    # 6. PUSH REMAINING
    # --------------------------------------------------------

    if full_rows_buffer:

        batch_result = (
            push_full_order_rows(
                full_rows_buffer
            )
        )

        full_sheet_batches.append(
            batch_result
        )

        full_pushed += len(
            full_rows_buffer
        )

        full_rows_buffer = []

    # --------------------------------------------------------
    # 7. MERGE SHEET RESULT
    # --------------------------------------------------------

    full_sheet_result = {
        "inserted": sum(
            int(
                item.get(
                    "inserted",
                    0,
                )
                or 0
            )
            for item
            in full_sheet_batches
        ),

        "updated": sum(
            int(
                item.get(
                    "updated",
                    0,
                )
                or 0
            )
            for item
            in full_sheet_batches
        ),

        "unchanged": sum(
            int(
                item.get(
                    "unchanged",
                    0,
                )
                or 0
            )
            for item
            in full_sheet_batches
        ),

        "skipped": sum(
            int(
                item.get(
                    "skipped",
                    0,
                )
                or 0
            )
            for item
            in full_sheet_batches
        ),
    }

    # --------------------------------------------------------
    # 8. RESULT
    # --------------------------------------------------------

    print(
        f"TO MAPPING: {mapping_result}"
    )

    print(
        f"FULL ORDER: {full_sheet_result}"
    )

    print(
        "=" * 70
    )

    return {
        "success": True,

        "trip_id":
            trip_id,

        "to_number":
            to_number,

        "scan_total":
            (
                scan_data.get(
                    "total",
                    len(items),
                )
                if isinstance(
                    scan_data,
                    dict,
                )
                else len(items)
            ),

        "scan_crawled":
            len(items),

        "mapping_rows":
            len(
                to_order_rows
            ),

        "shipment_ids":
            total_orders,

        "order_success":
            order_success,

        "order_failed":
            order_failed,

        "full_pushed":
            full_pushed,

        "mapping_sheet":
            mapping_result,

        "full_order_sheet":
            full_sheet_result,

        "failed_orders":
            failed_orders,
    }