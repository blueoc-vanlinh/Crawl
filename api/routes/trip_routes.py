from __future__ import annotations

import threading
import traceback

from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    request,
)

from config import get_headers

from api.services.trip_service import (
    resolve_trip_identifier,
    get_trip_detail_data,
    get_trip_loading_data,
    get_trip_editing_data,
    get_trip_seal_data,
    extract_list,
    build_trip_row,
    build_to_rows,
    push_to_sheet,
    sync_trips,
)


trip_bp = Blueprint(
    "trip",
    __name__,
)


_trip_daily_lock = threading.Lock()


def check_auth():
    headers = get_headers()

    if not headers.get(
        "Cookie"
    ):
        raise RuntimeError(
            "Không tìm thấy Cookie"
        )

    if not headers.get(
        "X-Csrftoken"
    ):
        raise RuntimeError(
            "Không tìm thấy CSRF"
        )

    return headers


@trip_bp.route(
    "/trip",
    methods=["GET"],
)
def trip_home():
    return jsonify({
        "success":
            True,

        "service":
            "trip",

        "routes": {
            "sync_by_code":
                (
                    "/trip/<trip_id>/sync"
                    "?direction=outbound"
                    "&sequence=1"
                ),

            "sync_by_date":
                (
                    "/api/trip/daily-crawl"
                    "?date=YYYY-MM-DD"
                ),

            "detail":
                "/trip/<trip_id>/detail",

            "loading":
                (
                    "/trip/<trip_id>/loading"
                    "?direction=outbound"
                    "&sequence=1"
                ),

            "editing":
                "/trip/<trip_id>/editing",

            "seal":
                "/trip/<trip_id>/seal",
        },
    })


@trip_bp.route(
    "/trip/<trip_id>/detail",
    methods=["GET"],
)
def trip_detail(
    trip_id,
):
    try:
        check_auth()

        trip_input = str(
            trip_id
        ).strip()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        data = (
            get_trip_detail_data(
                resolved_trip_id
            )
        )

        return jsonify({
            "success":
                True,

            "trip_id":
                trip_input,

            "resolved_trip_id":
                resolved_trip_id,

            "data":
                data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "trip_id":
                str(
                    trip_id
                ),

            "error":
                str(
                    e
                ),
        }), 500


@trip_bp.route(
    "/trip/<trip_id>/loading",
    methods=["GET"],
)
def trip_loading(
    trip_id,
):
    try:
        check_auth()

        trip_input = str(
            trip_id
        ).strip()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        direction = (
            request.args.get(
                "direction",
                default="outbound",
                type=str,
            )
            or "outbound"
        ).strip().lower()

        if direction not in (
            "outbound",
            "inbound",
        ):
            return jsonify({
                "success":
                    False,

                "error":
                    (
                        "direction phải là "
                        "outbound hoặc inbound"
                    ),
            }), 400

        sequence = (
            request.args.get(
                "sequence",
                default=1,
                type=int,
            )
            or 1
        )

        data = (
            get_trip_loading_data(
                trip_id=
                    resolved_trip_id,

                direction=
                    direction,

                sequence=
                    sequence,
            )
        )

        return jsonify({
            "success":
                True,

            "trip_id":
                trip_input,

            "resolved_trip_id":
                resolved_trip_id,

            "direction":
                direction,

            "sequence":
                sequence,

            "data":
                data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "trip_id":
                str(
                    trip_id
                ),

            "error":
                str(
                    e
                ),
        }), 500


@trip_bp.route(
    "/trip/<trip_id>/editing",
    methods=["GET"],
)
def trip_editing(
    trip_id,
):
    try:
        check_auth()

        trip_input = str(
            trip_id
        ).strip()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        data = (
            get_trip_editing_data(
                resolved_trip_id
            )
        )

        return jsonify({
            "success":
                True,

            "trip_id":
                trip_input,

            "resolved_trip_id":
                resolved_trip_id,

            "data":
                data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "trip_id":
                str(
                    trip_id
                ),

            "error":
                str(
                    e
                ),
        }), 500


@trip_bp.route(
    "/trip/<trip_id>/seal",
    methods=["GET"],
)
def trip_seal(
    trip_id,
):
    try:
        check_auth()

        trip_input = str(
            trip_id
        ).strip()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        data = (
            get_trip_seal_data(
                resolved_trip_id
            )
        )

        return jsonify({
            "success":
                True,

            "trip_id":
                trip_input,

            "resolved_trip_id":
                resolved_trip_id,

            "data":
                data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "trip_id":
                str(
                    trip_id
                ),

            "error":
                str(
                    e
                ),
        }), 500


@trip_bp.route(
    "/trip/<trip_id>/sync",
    methods=[
        "GET",
        "POST",
    ],
)
def trip_sync(
    trip_id,
):
    try:
        check_auth()

        trip_input = str(
            trip_id
            or ""
        ).strip().upper()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        direction = (
            request.args.get(
                "direction",
                default="outbound",
                type=str,
            )
            or "outbound"
        ).strip().lower()

        if direction not in (
            "outbound",
            "inbound",
        ):
            return jsonify({
                "success":
                    False,

                "error":
                    (
                        "direction phải là "
                        "outbound hoặc inbound"
                    ),
            }), 400

        sequence = (
            request.args.get(
                "sequence",
                default=1,
                type=int,
            )
            or 1
        )

        print()
        print(
            "=" * 70
        )
        print(
            "TRIP SYNC BY CODE"
        )
        print(
            "INPUT:",
            trip_input,
        )
        print(
            "RESOLVED:",
            resolved_trip_id,
        )
        print(
            "=" * 70
        )

        trip_detail_data = (
            get_trip_detail_data(
                resolved_trip_id
            )
        )

        loading_data = (
            get_trip_loading_data(
                trip_id=
                    resolved_trip_id,

                direction=
                    direction,

                sequence=
                    sequence,
            )
        )

        loading_items = (
            extract_list(
                loading_data
            )
        )

        trip_row = (
            build_trip_row(
                trip_id=
                    resolved_trip_id,

                trip_detail=
                    trip_detail_data,
            )
        )

        to_rows = (
            build_to_rows(
                trip_id=
                    resolved_trip_id,

                items=
                    loading_items,

                direction=
                    direction,

                sequence=
                    sequence,
            )
        )

        sheet_result = (
            push_to_sheet(
                trip_rows=[
                    trip_row
                ],

                to_rows=
                    to_rows,
            )
        )

        return jsonify({
            "success":
                True,

            "mode":
                "trip_code",

            "trip_input":
                trip_input,

            "trip_id":
                resolved_trip_id,

            "direction":
                direction,

            "sequence":
                sequence,

            "trip_rows":
                1,

            "to_rows":
                len(
                    to_rows
                ),

            "sheet":
                sheet_result,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "mode":
                "trip_code",

            "trip_id":
                str(
                    trip_id
                ),

            "error":
                str(
                    e
                ),
        }), 500


def _run_daily_sync(
    target_date,
):
    if not _trip_daily_lock.acquire(
        blocking=False
    ):
        print(
            "[TRIP DAILY] "
            "Job đang chạy"
        )
        return

    try:
        print()
        print(
            "=" * 90
        )
        print(
            "TRIP SYNC BY DATE"
        )
        print(
            "DATE:",
            target_date,
        )
        print(
            "=" * 90
        )

        result = (
            sync_trips(
                target_date=
                    target_date,

                trip_wait_seconds=
                    0,

                max_workers=
                    5,
            )
        )

        print()
        print(
            "=" * 90
        )
        print(
            "TRIP SYNC BY DATE COMPLETE"
        )
        print(
            "DATE:",
            target_date,
        )
        print(
            "TOTAL:",
            result.get(
                "total_trips",
                0,
            ),
        )
        print(
            "SUCCESS:",
            result.get(
                "success_count",
                0,
            ),
        )
        print(
            "FAILED:",
            result.get(
                "failed_count",
                0,
            ),
        )
        print(
            "=" * 90
        )

    except Exception:
        print(
            traceback.format_exc()
        )

    finally:
        _trip_daily_lock.release()


@trip_bp.route(
    "/api/trip/daily-crawl",
    methods=["POST"],
)
def trip_daily_crawl():
    try:
        check_auth()

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        target_date = (
            request.args.get(
                "date",
                default=None,
                type=str,
            )
            or body.get(
                "date"
            )
        )

        if not target_date:
            return jsonify({
                "success":
                    False,

                "error":
                    "Thiếu date",
            }), 400

        target_date = str(
            target_date
        ).strip()

        datetime.strptime(
            target_date,
            "%Y-%m-%d",
        )

        if (
            _trip_daily_lock.locked()
        ):
            return jsonify({
                "success":
                    False,

                "running":
                    True,

                "date":
                    target_date,

                "message":
                    "Trip crawl đang chạy",
            }), 409

        thread = (
            threading.Thread(
                target=
                    _run_daily_sync,

                args=(
                    target_date,
                ),

                name=
                    (
                        "trip-daily-"
                        f"{target_date}"
                    ),

                daemon=
                    True,
            )
        )

        thread.start()

        return jsonify({
            "success":
                True,

            "mode":
                "date",

            "running":
                True,

            "date":
                target_date,

            "message":
                (
                    "Đã bắt đầu cào Trip "
                    f"ngày {target_date}"
                ),
        })

    except ValueError:
        return jsonify({
            "success":
                False,

            "error":
                (
                    "date phải có định dạng "
                    "YYYY-MM-DD"
                ),
        }), 400

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,

            "error":
                str(
                    e
                ),
        }), 500