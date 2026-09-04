from api.order.order_check import (
    check_order as _check_order,
    check_orders as _check_orders,
    get_tracking_info,
)


# ============================================================
# ORDER CHECK
# ============================================================

def check_order(
    shipment_id,
    station_id=None,
    station_type=2,
):
    """
    Crawl/check một order.

    Giữ interface cho route:
        /order/<shipment_id>/check
        /order/<shipment_id>/sync
    """

    shipment_id = str(
        shipment_id or ""
    ).strip().upper()

    if not shipment_id:
        raise ValueError(
            "Thiếu shipment_id"
        )

    return _check_order(
        shipment_id=shipment_id,
        station_id=station_id,
        station_type=station_type,
    )


# ============================================================
# ORDER CHECK MANY
# ============================================================

def check_orders(
    shipment_ids,
    station_id=None,
    station_type=2,
    max_workers=5,
):
    """
    Crawl/check nhiều order.
    """

    return _check_orders(
        shipment_ids=shipment_ids,
        station_id=station_id,
        station_type=station_type,
        max_workers=max_workers,
    )


# ============================================================
# ORDER TRACKING
# ============================================================

def get_order_tracking(
    shipment_id,
):
    """
    Lấy tracking information của order.
    """

    shipment_id = str(
        shipment_id or ""
    ).strip().upper()

    if not shipment_id:
        raise ValueError(
            "Thiếu shipment_id"
        )

    return get_tracking_info(
        shipment_id
    )


# ============================================================
# ORDER CRAWL ALIAS
# ============================================================

def crawl_order(
    shipment_id,
):
    return check_order(
        shipment_id=shipment_id,
        station_id=None,
        station_type=2,
    )


def crawl_orders(
    shipment_ids,
    station_id=None,
    station_type=2,
    max_workers=5,
):
    return check_orders(
        shipment_ids=shipment_ids,
        station_id=station_id,
        station_type=station_type,
        max_workers=max_workers,
    )


# ============================================================
# ORDER SYNC
# ============================================================

def sync_order(
    shipment_id,
):
    """
    Hiện tại service chỉ chịu trách nhiệm crawl/check.

    Phần ghi Sheet được route/service khác xử lý.
    """

    shipment_id = str(
        shipment_id or ""
    ).strip().upper()

    if not shipment_id:
        raise ValueError(
            "Thiếu shipment_id"
        )

    return check_order(
        shipment_id=shipment_id,
        station_id=None,
        station_type=2,
    )