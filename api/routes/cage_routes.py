from flask import (
    Blueprint,
    jsonify,
    request,
)

from api.services.cage_service import (
    get_cage_packed_history,
    sync_cage_history,
    get_cage_history,
)


cage_bp = Blueprint(
    "cage",
    __name__,
)


@cage_bp.route(
    "/cage/packed-history/all",
    methods=["GET", "POST"],
)
def cage_packed_history_all():

    try:
        result = get_cage_packed_history(
            request_data=request.get_json(
                silent=True
            ),
            query_params=request.args,
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@cage_bp.route(
    "/cage/history/sync",
    methods=["POST"],
)
def cage_history_sync():

    try:
        result = sync_cage_history(
            request_data=request.get_json(
                silent=True
            ),
            query_params=request.args,
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@cage_bp.route(
    "/cage/history",
    methods=["GET"],
)
def cage_history():

    try:
        result = get_cage_history(
            query_params=request.args,
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500
