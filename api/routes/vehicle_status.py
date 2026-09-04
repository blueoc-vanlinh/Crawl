from __future__ import annotations

from flask import (
    Blueprint,
    jsonify,
    request,
)

from api.trip.vehicle_status import (
    get_vehicle_status,
)


vehicle_status_bp = Blueprint(
    "vehicle_status",
    __name__,
)


@vehicle_status_bp.route(
    "/api/vehicle-status",
    methods=["GET"],
)
def vehicle_status():
    try:
        target_date = request.args.get(
            "date",
            default=None,
            type=str,
        )

        result = get_vehicle_status(
            target_date=target_date,
        )

        return jsonify(
            result
        )

    except ValueError:
        return jsonify({
            "success": False,
            "error": "date phải có định dạng YYYY-MM-DD",
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500