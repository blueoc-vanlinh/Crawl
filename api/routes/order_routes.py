from flask import (
    Blueprint,
    jsonify,
)

from api.services.order_service import (
    get_order_tracking,
    check_order,
    sync_order,
)


order_bp = Blueprint(
    "order",
    __name__,
)


# ============================================================
# ORDER TRACKING
# ============================================================

@order_bp.route(
    "/order/<shipment_id>/tracking",
    methods=["GET"],
)
def order_tracking(
    shipment_id,
):

    try:

        result = get_order_tracking(
            shipment_id=shipment_id,
        )

        return jsonify({
            "success": True,
            "shipment_id": shipment_id,
            "data": result,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "shipment_id": shipment_id,
            "error": str(e),
        }), 500


# ============================================================
# ORDER CHECK
# ============================================================

@order_bp.route(
    "/order/<shipment_id>/check",
    methods=["GET"],
)
def order_check(
    shipment_id,
):

    try:

        result = check_order(
            shipment_id=shipment_id,
        )

        return jsonify(
            result
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "shipment_id": shipment_id,
            "error": str(e),
        }), 500


# ============================================================
# ORDER SYNC
# ============================================================

@order_bp.route(
    "/order/<shipment_id>/sync",
    methods=[
        "GET",
        "POST",
    ],
)
def order_sync(
    shipment_id,
):

    try:

        result = sync_order(
            shipment_id=shipment_id,
        )

        return jsonify(
            result
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "shipment_id": shipment_id,
            "error": str(e),
        }), 500
