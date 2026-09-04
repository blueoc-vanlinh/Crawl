from flask import (
    Blueprint,
    jsonify,
    request,
)

from api.services.order_service import sync_orders_sheet


orders_bp = Blueprint(
    "orders",
    __name__,
)


@orders_bp.route(
    "/orders/sync-sheet",
    methods=[
        "GET",
        "POST",
    ],
)
def orders_sync_sheet():

    try:

        result = sync_orders_sheet(
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
            "error": str(e),
        }), 500
