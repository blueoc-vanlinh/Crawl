from flask import (
    Blueprint,
    jsonify,
    request,
)

from api.services.station_service import (
    get_station_detail,
    get_station_data,
    get_trip_stations,
)


station_bp = Blueprint(
    "station",
    __name__,
)


@station_bp.route(
    "/trip/<trip_id>/stations",
    methods=["GET"],
)
def trip_stations(
    trip_id,
):
    try:
        result = get_trip_stations(
            trip_id=trip_id,
        )

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "count": len(result),
            "data": result,
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "error": str(exc),
        }), 500


@station_bp.route(
    "/trip/<trip_id>/station/<station_id>",
    methods=["GET"],
)
def station_detail(
    trip_id,
    station_id,
):
    try:
        sequence_number = request.args.get(
            "sequence_number"
        )

        result = get_station_detail(
            trip_id=trip_id,
            station_id=station_id,
            sequence_number=sequence_number,
        )

        if not result:
            return jsonify({
                "success": False,
                "trip_id": trip_id,
                "station_id": station_id,
                "sequence_number": sequence_number,
                "error": "Không tìm thấy station trong trip",
            }), 404

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "station_id": station_id,
            "sequence_number": sequence_number,
            "data": result,
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "station_id": station_id,
            "error": str(exc),
        }), 500


@station_bp.route(
    "/trip/<trip_id>/station/<station_id>/data",
    methods=["GET"],
)
def station_data(
    trip_id,
    station_id,
):
    try:
        sequence_number = request.args.get(
            "sequence_number"
        )

        result = get_station_data(
            trip_id=trip_id,
            station_id=station_id,
            sequence_number=sequence_number,
        )

        if not result:
            return jsonify({
                "success": False,
                "trip_id": trip_id,
                "station_id": station_id,
                "sequence_number": sequence_number,
                "error": "Không tìm thấy station trong trip",
            }), 404

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "station_id": station_id,
            "sequence_number": sequence_number,
            "data": result,
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "station_id": station_id,
            "error": str(exc),
        }), 500