from flask import (
    Blueprint,
    jsonify,
    request,
)

from api.services.to_service import (
    get_to_orders,
    sync_to_orders,
)


to_bp = Blueprint(
    "to",
    __name__,
)


# ============================================================
# TO ORDERS
# ============================================================

@to_bp.route(
    "/to/<to_number>/orders",
    methods=["GET"],
)
def to_orders(
    to_number,
):

    try:

        result = get_to_orders(
            to_number=to_number,
            query_params=request.args,
        )

        return jsonify(
            result
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "to_number": to_number,
            "error": str(e),
        }), 500


# ============================================================
# TO SYNC
# ============================================================

@to_bp.route(
    "/to/<to_number>/sync",
    methods=[
        "GET",
        "POST",
    ],
)
def sync_to(
    to_number,
):

    try:

        result = sync_to_orders(
            to_number=to_number,
            request_data=request.get_json(
                silent=True
            ),
            query_params=request.args,
        )

        return jsonify(
            result
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "to_number": to_number,
            "error": str(e),
        }), 500
