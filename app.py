import os
import time
import threading
import traceback
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from core.spx_request import spx_get
from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
)

from config import (
    BASE_URL,
    get_headers,
)
from api.routes.vehicle_status import vehicle_status_bp
from api.trip.realtime_trip import (
    sync_realtime_vehicle_trips,
)
from api.order.daily_trip_sync import sync_two_day_trips
from api.order.order_check import (
    check_order,
    check_orders,
    get_tracking_info,
)
from api.order.data_order_deli import (
    build_order_row,
    analyze_order,
)
from api.order.cage_packed_history import (
    read_sheet_rows,
    sync_cage_history,
    crawl_all_packed_history,
)
from api.to.scanto import (
    scan_to_orders,
)

from api.sheet.trip_sheet import (
    build_trip_row,
    push_trip_rows,
)

from api.sheet.trip_station_sheet import (
    build_trip_station_rows,
    push_trip_station_rows,
)

from api.sheet.to_sheet import (
    TO_GID,
    build_to_rows,
    push_to_rows,
)

from api.sheet.to_order_sheet import (
    TO_ORDER_GID,
    build_to_order_rows,
    build_to_order_rows_from_scan,
    get_shipment_ids_from_to_order_rows,
    push_to_order_rows,
)

from api.sheet.order_full_sheet import (
    build_full_order_row,
    push_full_order_rows,
)

from api.sheet.order_legacy_sheet import (
    get_push_order_ids,
    push_order_rows,
)

from api.sheet.common import (
    get_sheet_name_by_gid,
    get_sheets_service,
    read_existing_data,
)

app = Flask(__name__)

app.register_blueprint(vehicle_status_bp)

VN_TZ = timezone(
    timedelta(hours=7)
)

TRIP_STATION_GID = 1157738563
VOLUME_GID = 81652235
VOLUME_SPREADSHEET_ID = "1YfRPJd99ipWnUqPqXCFDlQzHj8ADxdP_UE1363KqLS8"
VOLUME_SYNC_WORKERS = 5
_volume_sync_lock = threading.Lock()
_volume_sync_state_lock = threading.Lock()
_volume_sync_state = {
    "running": False,
    "date": None,
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}
TRIP_CRAWL_MINUTES = {
    0,
    30,
}
TRIP_CRAWL_WORKERS = 5

_trip_scheduler_started = False

_trip_scheduler_lock = threading.Lock()

_trip_running_lock = threading.Lock()


def run_daily_trip_crawl(
    target_date=None,
):
    if not _trip_running_lock.acquire(
        blocking=False
    ):
        print(
            "[TRIP SCHEDULER] "
            "Một lần crawl đang chạy, bỏ qua lần này."
        )
        return

    try:
        crawl_date = (
            target_date
            if target_date
            else datetime.now(
                VN_TZ
            ).strftime(
                "%Y-%m-%d"
            )
        )

        print()
        print("=" * 90)
        print(
            "DAILY TRIP + REALTIME + VOLUME CRAWL"
        )
        print(
            "TIME:",
            datetime.now(
                VN_TZ
            ).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
        )
        print(
            "DATE:",
            crawl_date,
        )
        print(
            "WORKERS:",
            TRIP_CRAWL_WORKERS,
        )
        print("=" * 90)

        try:
            # =========================================================
            # 1. DAILY TRIP
            # =========================================================

            print()
            print("=" * 90)
            print(
                "STEP 1/3 - DAILY TRIP SYNC"
            )
            print("=" * 90)

            trip_result = (
                sync_two_day_trips(
                    target_date=
                        crawl_date,

                    trip_wait_seconds=
                        0,

                    max_workers=
                        TRIP_CRAWL_WORKERS,
                )
            )

            print()
            print("=" * 90)
            print(
                "DAILY TRIP SYNC COMPLETE"
            )
            print(
                "TOTAL:",
                trip_result.get(
                    "total_trips",
                    0,
                ),
            )
            print(
                "SUCCESS:",
                trip_result.get(
                    "success_count",
                    0,
                ),
            )
            print(
                "FAILED:",
                trip_result.get(
                    "failed_count",
                    0,
                ),
            )
            print("=" * 90)

            # =========================================================
            # 2. REALTIME
            # ARRIVED 50
            # UNSEAL 60
            # UNLOADED 80
            # =========================================================

            print()
            print("=" * 90)
            print(
                "STEP 2/3 - REALTIME VEHICLE SYNC"
            )
            print(
                "STATUSES: 50 / 60 / 80"
            )
            print(
                "DATE:",
                crawl_date,
            )
            print("=" * 90)

            realtime_result = (
                sync_realtime_vehicle_trips(
                    target_date=
                        crawl_date,

                    max_workers=
                        TRIP_CRAWL_WORKERS,
                )
            )

            print()
            print("=" * 90)
            print(
                "REALTIME VEHICLE SYNC COMPLETE"
            )
            print(
                "TRIPS:",
                realtime_result.get(
                    "trip_count",
                    0,
                ),
            )
            print(
                "TRIP ROWS:",
                realtime_result.get(
                    "trip_rows",
                    0,
                ),
            )
            print(
                "TRIP STATION ROWS:",
                realtime_result.get(
                    "trip_station_rows",
                    0,
                ),
            )
            print(
                "FAILED:",
                len(
                    realtime_result.get(
                        "failed",
                        [],
                    )
                    or []
                ),
            )
            print("=" * 90)

            # =========================================================
            # 3. VOLUME
            # loading -> TO -> scanTO -> Bulky -> Volume
            # =========================================================

            print()
            print("=" * 90)
            print(
                "STEP 3/3 - VOLUME SYNC"
            )
            print(
                "DATE:",
                crawl_date,
            )
            print("=" * 90)

            volume_result = (
                run_volume_sync(
                    target_date=
                        crawl_date,

                    max_workers=
                        VOLUME_SYNC_WORKERS,
                )
            )

            print()
            print("=" * 90)
            print(
                "VOLUME SYNC COMPLETE"
            )

            print(
                "INBOUND TRIPS:",
                volume_result.get(
                    "inbound_trips",
                    0,
                ),
            )

            print(
                "LOADING ITEMS:",
                volume_result.get(
                    "loading_items",
                    0,
                ),
            )

            print(
                "TO UNIQUE:",
                volume_result.get(
                    "to_unique",
                    0,
                ),
            )

            print(
                "BULKY:",
                volume_result.get(
                    "bulky_unique",
                    0,
                ),
            )

            print(
                "TO SCAN SUCCESS:",
                volume_result.get(
                    "to_scan_success",
                    0,
                ),
            )

            print(
                "TO SCAN FAILED:",
                volume_result.get(
                    "to_scan_failed",
                    0,
                ),
            )

            print(
                "SHIPMENT UNIQUE:",
                volume_result.get(
                    "shipment_unique",
                    0,
                ),
            )

            print(
                "VOLUME ROWS:",
                volume_result.get(
                    "volume_rows",
                    0,
                ),
            )

            print("=" * 90)

            print()
            print("=" * 90)
            print(
                "FULL AUTO CRAWL COMPLETE"
            )
            print(
                "DATE:",
                crawl_date,
            )
            print(
                "DAILY TRIPS:",
                trip_result.get(
                    "total_trips",
                    0,
                ),
            )
            print(
                "REALTIME TRIPS:",
                realtime_result.get(
                    "trip_count",
                    0,
                ),
            )
            print(
                "VOLUME TRIPS:",
                volume_result.get(
                    "inbound_trips",
                    0,
                ),
            )
            print("=" * 90)

            return {
                "success":
                    True,

                "date":
                    crawl_date,

                "trip":
                    trip_result,

                "realtime":
                    realtime_result,

                "volume":
                    volume_result,
            }

        except Exception as exc:
            print()
            print("=" * 90)
            print(
                "DAILY TRIP CRAWL ERROR"
            )
            print(
                type(exc).__name__,
                ":",
                exc,
            )
            print(
                traceback.format_exc()
            )
            print("=" * 90)

            return {
                "success":
                    False,

                "date":
                    crawl_date,

                "error":
                    str(
                        exc
                    ),
            }

    finally:
        _trip_running_lock.release()

def daily_trip_scheduler():
    last_run_key = None

    while True:
        try:
            now = datetime.now()

            run_key = (
                now.strftime("%Y-%m-%d"),
                now.hour,
                now.minute,
            )

            if (
                now.minute in TRIP_CRAWL_MINUTES
                and run_key != last_run_key
            ):
                last_run_key = run_key

                print(
                    "\n"
                    + "=" * 90
                )
                print(
                    "AUTO DAILY TRIP CRAWL"
                )
                print(
                    "TIME:",
                    now.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ),
                )
                print(
                    "=" * 90
                )

                run_daily_trip_crawl(
                    target_date=now.strftime(
                        "%Y-%m-%d"
                    )
                )

            time.sleep(10)

        except Exception as exc:
            print(
                "[DAILY TRIP SCHEDULER ERROR]",
                exc,
            )

            time.sleep(30)


def start_daily_trip_scheduler():
    thread = threading.Thread(
        target=daily_trip_scheduler,
        name="daily-trip-scheduler",
        daemon=True,
    )

    thread.start()

    print(
        "=" * 90
    )
    print(
        "DAILY TRIP SCHEDULER STARTED"
    )
    print(
        "SCHEDULE: EVERY 30 MINUTES"
    )
    print(
        "RUN AT: HH:00 + HH:30"
    )
    print(
        "=" * 90
    )

    return thread

def check_auth():
    return get_headers()


def startup_auth_check():
    print("=" * 60)
    print("Checking SPX authentication...")

    try:
        headers = check_auth()

        if not headers.get("Cookie"):
            raise RuntimeError("Không tìm thấy Cookie")

        if not headers.get("X-Csrftoken"):
            raise RuntimeError("Không tìm thấy CSRF")

        print("SPX AUTH: OK")
        print("Cookie: OK")
        print("CSRF:   OK")
        print("=" * 60)

        return True

    except Exception as e:
        print("SPX AUTH: FAILED")
        print(f"ERROR: {e}")
        print("=" * 60)

        return False


def extract_list(data):
    if not isinstance(data, dict):
        return []

    payload = data.get("data")

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in (
            "list",
            "items",
            "rows",
            "records",
        ):
            value = payload.get(key)

            if isinstance(value, list):
                return value

    return []


def get_trip_detail_data(
    trip_id,
):
    endpoints = [
        (
            BASE_URL
            + "/api/admin/transportation/trip/history/detail",
            {
                "trip_id": trip_id,
                "new_process_switch": "false",
            },
        ),
    ]

    last_error = None

    for url, params in endpoints:
        try:
            response = spx_get(
                url,
                params=params,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Không lấy được Trip Detail: "
        f"{last_error}"
    )


def get_trip_loading_data(
    trip_id,
    direction="outbound",
    sequence=1,
):
    all_items = []

    page = 1
    count = 2000

    while True:
        params = {
            "trip_id":
                trip_id,

            "pageno":
                page,

            "count":
                count,

            "type":
                direction,
        }

        if (
            direction
            == "outbound"
        ):
            params[
                "loaded_sequence_number"
            ] = (
                sequence
            )

        else:
            params[
                "actual_unloaded_sequence_number"
            ] = (
                sequence
            )

        url = (
            BASE_URL
            + "/api/admin/transportation/trip/history/loading/list"
        )

        response = spx_get(
            url,
            params=params,
            timeout=60,
        )

        data = response.json()

        if data.get(
            "retcode"
        ) != 0:
            raise RuntimeError(
                data.get(
                    "message",
                    "Trip loading error",
                )
            )

        payload = (
            data.get(
                "data",
                {},
            )
        )

        rows = (
            payload.get(
                "list",
                [],
            )
            if isinstance(
                payload,
                dict,
            )
            else []
        )

        total = int(
            payload.get(
                "total",
                0,
            )
            or 0
        )

        if not rows:
            break

        all_items.extend(
            rows
        )

        if (
            total
            and
            len(all_items) >= total
        ):
            break

        page += 1

    return {
        "retcode":
            0,

        "data": {
            "list":
                all_items,

            "total":
                len(
                    all_items
                ),
        },
    }

def get_trip_editing_data(
    trip_id,
):
    endpoints = [
        (
            "/api/admin/transportation/trip/editing/detail",
            {
                "trip_id": trip_id,
            },
        ),
        (
            "/api/admin/transportation/trip/edit/detail",
            {
                "trip_id": trip_id,
            },
        ),
    ]

    last_error = None

    for endpoint, params in endpoints:
        try:
            response = spx_get(
                BASE_URL + endpoint,
                params=params,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Không lấy được Trip Editing: "
        f"{last_error}"
    )


def get_trip_seal_data(
    trip_id,
):
    endpoints = [
        (
            "/api/admin/transportation/trip/seal/detail",
            {
                "trip_id": trip_id,
            },
        ),
        (
            "/api/admin/transportation/trip/seal/report/detail",
            {
                "trip_id": trip_id,
            },
        ),
    ]

    last_error = None

    for endpoint, params in endpoints:
        try:
            response = spx_get(
                BASE_URL + endpoint,
                params=params,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Không lấy được Trip Seal: "
        f"{last_error}"
    )


def get_station_detail_data(
    station_id,
):
    endpoints = [
        (
            "/api/admin/station/detail",
            {
                "station_id": station_id,
            },
        ),
        (
            "/api/admin/station/get",
            {
                "station_id": station_id,
            },
        ),
    ]

    last_error = None

    for endpoint, params in endpoints:
        try:
            response = spx_get(
                BASE_URL + endpoint,
                params=params,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Không lấy được Station Detail: "
        f"{last_error}"
    )
@app.route(
    "/auth/status"
)
def auth_status():
    try:
        headers = check_auth()

        return jsonify({
            "logged_in": True,
            "cookie_found": bool(
                headers.get(
                    "Cookie"
                )
            ),
            "csrf_found": bool(
                headers.get(
                    "X-Csrftoken"
                )
            ),
        })

    except Exception as e:
        return jsonify({
            "logged_in": False,
            "error": str(e),
        }), 401


@app.route(
    "/trip/<trip_id>/detail"
)
def trip_detail(
    trip_id
):
    try:
        #check_auth()

        trip_id = (
            str(trip_id)
            .strip()
        )

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_id
            )
        )

        trip_detail = (
            get_trip_detail_data(
                resolved_trip_id
            )
        )

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "data": trip_detail,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "error": str(e),
        }), 500


@app.route(
    "/trip/<trip_id>/loading"
)
def trip_loading(
    trip_id
):
    try:
        check_auth()

        trip_id = (
            str(trip_id)
            .strip()
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
                "success": False,
                "error":
                    "direction phải là "
                    "outbound hoặc inbound",
            }), 400

        sequence = request.args.get(
            "sequence",
            default=1,
            type=int,
        )

        if sequence is None:
            sequence = 1

        data = get_trip_loading_data(
            trip_id=trip_id,
            direction=direction,
            sequence=sequence,
        )

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "direction": direction,
            "sequence": sequence,
            "data": data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "error": str(e),
        }), 500


@app.route(
    "/trip/<trip_id>/editing"
)
def trip_editing(
    trip_id
):
    try:
        #check_auth()

        trip_id = (
            str(trip_id)
            .strip()
        )

        data = get_trip_editing_data(
            trip_id
        )

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "data": data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "error": str(e),
        }), 500


@app.route(
    "/trip/<trip_id>/seal"
)
def trip_seal(
    trip_id
):
    try:
        #check_auth()

        trip_id = (
            str(trip_id)
            .strip()
        )

        data = get_trip_seal_data(
            trip_id
        )

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "data": data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "trip_id": trip_id,
            "error": str(e),
        }), 500


@app.route(
    "/station/<station_id>"
)
def station_detail(
    station_id
):
    try:
        #check_auth()

        station_id = (
            str(station_id)
            .strip()
        )

        data = get_station_detail_data(
            station_id
        )

        return jsonify({
            "success": True,
            "station_id": station_id,
            "data": data,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "station_id": station_id,
            "error": str(e),
        }), 500



@app.route(
    "/trip/<trip_id>/sync",
    methods=[
        "GET",
        "POST",
    ],
)
def trip_sync_all(
    trip_id,
):
    try:
        #check_auth()

        trip_input = str(
            trip_id or ""
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
                    "direction phải là outbound hoặc inbound",
            }), 400

        sequence = request.args.get(
            "sequence",
            default=1,
            type=int,
        )

        if sequence is None:
            sequence = 1

        print("=" * 70)
        print(
            f"TRIP + TO SYNC: "
            f"{trip_input}"
        )
        print(
            f"RESOLVED TRIP ID: "
            f"{resolved_trip_id}"
        )
        print(
            f"DIRECTION: "
            f"{direction}"
        )
        print(
            f"SEQUENCE: "
            f"{sequence}"
        )
        print("=" * 70)

        print(
            "[1/6] GET TRIP DETAIL"
        )

        trip_detail_data = (
            get_trip_detail_data(
                resolved_trip_id
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

        print(
            "[2/6] BUILD TRIP STATION"
        )

        trip_station_rows = (
            build_trip_station_rows(
                trip_id=
                    resolved_trip_id,
                trip_detail=
                    trip_detail_data,
            )
        )

        print(
            f"TRIP STATION FOUND: "
            f"{len(trip_station_rows)}"
        )

        print(
            "[3/6] GET TRIP LOADING"
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

        print(
            f"LOADING ITEMS: "
            f"{len(loading_items)}"
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

        print(
            "[4/6] PUSH TRIP + STATION + LOADING"
        )

        trip_sheet_result = (
            push_trip_rows(
                [
                    trip_row
                ]
            )
        )

        trip_station_sheet_result = (
            push_trip_station_rows(
                trip_station_rows
            )
        )

        to_sheet_result = (
            push_to_rows(
                to_rows
            )
        )

        print(
            f"TRIP SHEET: "
            f"{trip_sheet_result}"
        )
        print(
            f"TRIP STATION SHEET: "
            f"{trip_station_sheet_result}"
        )
        print(
            f"TO SHEET: "
            f"{to_sheet_result}"
        )

        print(
            "[5/6] CLASSIFY scan_number + SCAN TO"
        )

        all_to_order_rows = []
        shipment_seen = set()
        to_number_seen = set()

        to_count = 0
        bulky_count = 0
        unknown_count = 0
        to_scan_success = 0
        to_scan_failed = 0
        failed_tos = []

        total_loading = len(
            loading_items
        )

        for (
            index,
            loading_item
        ) in enumerate(
            loading_items,
            start=1,
        ):
            if not isinstance(
                loading_item,
                dict,
            ):
                unknown_count += 1
                continue

            scan_number = str(
                loading_item.get(
                    "scan_number"
                )
                or loading_item.get(
                    "to_number"
                )
                or loading_item.get(
                    "shipment_id"
                )
                or loading_item.get(
                    "fleet_order_id"
                )
                or ""
            ).strip().upper()

            if not scan_number:
                unknown_count += 1
                continue

            if scan_number.startswith(
                "SPXVN"
            ):
                bulky_count += 1
                shipment_seen.add(
                    scan_number
                )

                print(
                    f"[LOADING "
                    f"{index}/"
                    f"{total_loading}] "
                    f"BULKY: "
                    f"{scan_number}"
                )
                continue

            if not scan_number.startswith(
                "TO"
            ):
                unknown_count += 1

                print(
                    f"[LOADING "
                    f"{index}/"
                    f"{total_loading}] "
                    f"UNKNOWN: "
                    f"{scan_number}"
                )
                continue

            to_count += 1

            if scan_number in to_number_seen:
                continue

            to_number_seen.add(
                scan_number
            )

            print(
                f"[TO "
                f"{len(to_number_seen)}] "
                f"{scan_number}"
            )

            try:
                scan_result = (
                    scan_to_orders(
                        to_number=
                            scan_number,
                        count=
                            10000,
                    )
                )

                to_order_rows = (
                    build_to_order_rows_from_scan(
                        trip_id=
                            resolved_trip_id,
                        scan_result=
                            scan_result,
                    )
                )

                all_to_order_rows.extend(
                    to_order_rows
                )

                current_ids = (
                    get_shipment_ids_from_to_order_rows(
                        to_order_rows
                    )
                )

                for shipment_id_value in current_ids:
                    shipment_id_value = str(
                        shipment_id_value or ""
                    ).strip().upper()

                    if shipment_id_value:
                        shipment_seen.add(
                            shipment_id_value
                        )

                to_scan_success += 1

                print(
                    f"TO OK: "
                    f"{scan_number} "
                    f"=> "
                    f"{len(to_order_rows)} orders"
                )

            except Exception as e:
                to_scan_failed += 1

                failed_tos.append({
                    "to_number":
                        scan_number,
                    "error":
                        str(
                            e
                        ),
                })

                print(
                    f"TO ERROR: "
                    f"{scan_number} "
                    f"=> "
                    f"{e}"
                )

        print(
            "[6/6] PUSH SCAN TO"
        )

        to_order_sheet_result = (
            push_to_order_rows(
                all_to_order_rows
            )
        )

        print("=" * 70)
        print(
            "TRIP + TO SYNC COMPLETE"
        )
        print(
            f"LOADING: "
            f"{len(loading_items)}"
        )
        print(
            f"TO UNIQUE: "
            f"{len(to_number_seen)}"
        )
        print(
            f"BULKY: "
            f"{bulky_count}"
        )
        print(
            f"SCAN TO ROWS: "
            f"{len(all_to_order_rows)}"
        )
        print(
            f"ORDER CANDIDATES: "
            f"{len(shipment_seen)}"
        )
        print("=" * 70)

        return jsonify({
            "success":
                True,
            "trip_input":
                trip_input,
            "trip_id":
                resolved_trip_id,
            "direction":
                direction,
            "sequence":
                sequence,
            "loading": {
                "total":
                    len(
                        loading_items
                    ),
                "to_rows":
                    len(
                        to_rows
                    ),
                "to_count":
                    to_count,
                "to_unique":
                    len(
                        to_number_seen
                    ),
                "bulky":
                    bulky_count,
                "unknown":
                    unknown_count,
            },
            "trip": {
                "rows":
                    1,
                "sheet":
                    trip_sheet_result,
            },
            "trip_station": {
                "rows":
                    len(
                        trip_station_rows
                    ),
                "sheet":
                    trip_station_sheet_result,
            },
            "to": {
                "rows":
                    len(
                        to_rows
                    ),
                "sheet":
                    to_sheet_result,
            },
            "scan_to": {
                "rows":
                    len(
                        all_to_order_rows
                    ),
                "to_scan_success":
                    to_scan_success,
                "to_scan_failed":
                    to_scan_failed,
                "failed_tos":
                    failed_tos,
                "sheet":
                    to_order_sheet_result,
            },
            "orders_ready":
                len(
                    shipment_seen
                ),
            "next_api": (
                f"/trip/"
                f"{resolved_trip_id}"
                f"/sync-orders"
                f"?offset=0"
                f"&limit=300"
            ),
        })

    except Exception as e:
        print("=" * 70)
        print(
            "TRIP + TO SYNC ERROR"
        )
        print(
            traceback.format_exc()
        )
        print("=" * 70)

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


def _sheet_rows_as_dicts(
    service,
    gid,
):
    sheet_name = (
        get_sheet_name_by_gid(
            gid=
                gid,
            service=
                service,
        )
    )

    existing = (
        read_existing_data(
            service,
            sheet_name,
        )
    )

    if not existing:
        return []

    headers = [
        str(
            header
        ).strip()
        for header
        in existing[0]
    ]

    rows = []

    for values in existing[1:]:
        row = {}

        for (
            index,
            header
        ) in enumerate(
            headers
        ):
            if not header:
                continue

            row[
                header
            ] = (
                values[
                    index
                ]
                if index
                < len(
                    values
                )
                else ""
            )

        rows.append(
            row
        )

    return rows


def get_trip_order_ids_from_sheets(
    trip_id,
):
    trip_id = str(
        trip_id or ""
    ).strip()

    service = (
        get_sheets_service()
    )

    shipment_ids = []
    seen = set()

    scan_to_rows = (
        _sheet_rows_as_dicts(
            service=
                service,
            gid=
                TO_ORDER_GID,
        )
    )

    scan_to_count = 0

    for row in scan_to_rows:
        row_trip_id = str(
            row.get(
                "trip_id",
                "",
            )
            or ""
        ).strip()

        if row_trip_id != trip_id:
            continue

        shipment_id = str(
            row.get(
                "shipment_id",
                "",
            )
            or row.get(
                "fleet_order_id",
                "",
            )
            or ""
        ).strip().upper()

        if not shipment_id:
            continue

        scan_to_count += 1

        if shipment_id in seen:
            continue

        seen.add(
            shipment_id
        )

        shipment_ids.append(
            shipment_id
        )

    loading_rows = (
        _sheet_rows_as_dicts(
            service=
                service,
            gid=
                TO_GID,
        )
    )

    bulky_count = 0

    for row in loading_rows:
        row_trip_id = str(
            row.get(
                "trip_id",
                "",
            )
            or ""
        ).strip()

        if row_trip_id != trip_id:
            continue

        scan_number = str(
            row.get(
                "scan_number",
                "",
            )
            or row.get(
                "to_id",
                "",
            )
            or row.get(
                "shipment_id",
                "",
            )
            or row.get(
                "fleet_order_id",
                "",
            )
            or ""
        ).strip().upper()

        if not scan_number.startswith(
            "SPXVN"
        ):
            continue

        bulky_count += 1

        if scan_number in seen:
            continue

        seen.add(
            scan_number
        )

        shipment_ids.append(
            scan_number
        )

    return {
        "shipment_ids":
            shipment_ids,
        "scan_to_rows":
            scan_to_count,
        "bulky_rows":
            bulky_count,
        "total_unique":
            len(
                shipment_ids
            ),
    }


@app.route(
    "/trip/<trip_id>/sync-orders",
    methods=[
        "GET",
        "POST",
    ],
)
def trip_sync_orders(
    trip_id,
):
    try:
        #check_auth()

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        trip_input = str(
            trip_id or ""
        ).strip().upper()

        resolved_trip_id = (
            resolve_trip_identifier(
                trip_input
            )
        )

        offset = (
            request.args.get(
                "offset",
                default=None,
                type=int,
            )
        )

        if offset is None:
            offset = body.get(
                "offset",
                0,
            )

        try:
            offset = int(
                offset
            )
        except (
            TypeError,
            ValueError,
        ):
            offset = 0

        if offset < 0:
            offset = 0

        limit = (
            request.args.get(
                "limit",
                default=None,
                type=int,
            )
        )

        if limit is None:
            limit = body.get(
                "limit",
                100,
            )

        try:
            limit = int(
                limit
            )
        except (
            TypeError,
            ValueError,
        ):
            limit = 100

        if limit < 1:
            limit = 100

        if limit > 500:
            limit = 500

        max_workers = (
            request.args.get(
                "max_workers",
                default=None,
                type=int,
            )
        )

        max_workers = (
    request.args.get(
        "max_workers",
        default=None,
        type=int,
    )
)

        if max_workers is None:
            max_workers = body.get(
                "max_workers",
                8,
            )

        try:
            max_workers = int(
                max_workers
            )
        except (
            TypeError,
            ValueError,
        ):
            max_workers = 7

        if max_workers < 6:
            max_workers = 6

        if max_workers > 8:
            max_workers = 8

        print("=" * 70)
        print(
            f"ORDER PARALLEL SYNC: "
            f"{resolved_trip_id}"
        )
        print(
            f"OFFSET: "
            f"{offset}"
        )
        print(
            f"LIMIT: "
            f"{limit}"
        )
        print(
            f"MAX WORKERS: "
            f"{max_workers}"
        )
        print("=" * 70)

        source = (
            get_trip_order_ids_from_sheets(
                resolved_trip_id
            )
        )

        all_shipment_ids = (
            source.get(
                "shipment_ids",
                [],
            )
        )

        total_orders = len(
            all_shipment_ids
        )

        selected_ids = (
            all_shipment_ids[
                offset:
                offset + limit
            ]
        )

        print(
            f"TOTAL UNIQUE ORDERS: "
            f"{total_orders}"
        )

        print(
            f"THIS BATCH: "
            f"{len(selected_ids)}"
        )

        if not selected_ids:
            return jsonify({
                "success":
                    True,

                "trip_input":
                    trip_input,

                "trip_id":
                    resolved_trip_id,

                "source": {
                    "scan_to_rows":
                        source.get(
                            "scan_to_rows",
                            0,
                        ),

                    "bulky_rows":
                        source.get(
                            "bulky_rows",
                            0,
                        ),

                    "total_unique":
                        total_orders,
                },

                "batch": {
                    "offset":
                        offset,

                    "limit":
                        limit,

                    "count":
                        0,

                    "next_offset":
                        offset,

                    "has_more":
                        False,

                    "max_workers":
                        max_workers,
                },

                "orders": {
                    "success":
                        0,

                    "failed":
                        0,

                    "pushed":
                        0,

                    "failed_orders":
                        [],
                },

                "sheet": {
                    "inserted":
                        0,

                    "updated":
                        0,

                    "unchanged":
                        0,

                    "skipped":
                        0,
                },

                "next_api":
                    None,
            })

        print("=" * 70)
        print(
            f"START PARALLEL CRAWL "
            f"{len(selected_ids)} ORDERS"
        )
        print("=" * 70)

        started_at = time.time()

        crawl_result = (
            check_orders(
                shipment_ids=
                    selected_ids,

                station_id=
                    None,

                station_type=
                    2,

                max_workers=
                    max_workers,
            )
        )

        crawled_orders = (
            crawl_result.get(
                "orders",
                [],
            )
        )

        failed_orders = (
            crawl_result.get(
                "failed",
                [],
            )
        )

        print("=" * 70)
        print(
            f"PARALLEL CRAWL COMPLETE"
        )
        print(
            f"SUCCESS: "
            f"{len(crawled_orders)}"
        )
        print(
            f"FAILED: "
            f"{len(failed_orders)}"
        )
        print(
            f"SECONDS: "
            f"{round(time.time() - started_at, 2)}"
        )
        print("=" * 70)

        full_order_rows = []
        build_failed = []

        total_crawled = len(
            crawled_orders
        )

        for (
            index,
            order_data
        ) in enumerate(
            crawled_orders,
            start=1,
        ):
            shipment_id_value = str(
                order_data.get(
                    "shipment_id",
                    "",
                )
                or ""
            ).strip().upper()

            if not shipment_id_value:
                build_failed.append({
                    "shipment_id":
                        "",

                    "error":
                        "shipment_id rỗng sau khi crawl",
                })

                continue

            try:
                row = (
                    build_full_order_row(
                        shipment_id=
                            shipment_id_value,

                        order_data=
                            order_data,
                    )
                )

                full_order_rows.append(
                    row
                )

                print(
                    f"[BUILD "
                    f"{index}/"
                    f"{total_crawled}] "
                    f"{shipment_id_value} "
                    f"=> "
                    f"{row.get('latest_status', '')}"
                )

            except Exception as e:
                build_failed.append({
                    "shipment_id":
                        shipment_id_value,

                    "error":
                        str(e),
                })

                print(
                    f"BUILD ORDER ERROR: "
                    f"{shipment_id_value} "
                    f"=> "
                    f"{e}"
                )

        failed_orders.extend(
            build_failed
        )

        order_success = len(
            full_order_rows
        )

        order_failed = len(
            failed_orders
        )

        print("=" * 70)
        print(
            f"PUSH FULL ORDER SHEET: "
            f"{len(full_order_rows)} ROWS"
        )
        print("=" * 70)

        if full_order_rows:
            try:
                sheet_result = (
                    push_full_order_rows(
                        full_order_rows
                    )
                )

            except Exception as e:
                print(
                    f"FULL ORDER SHEET ERROR: "
                    f"{e}"
                )

                failed_orders.append({
                    "shipment_id":
                        "SHEET_BATCH",

                    "error":
                        str(e),
                })

                sheet_result = {
                    "inserted":
                        0,

                    "updated":
                        0,

                    "unchanged":
                        0,

                    "skipped":
                        0,
                }

        else:
            sheet_result = {
                "inserted":
                    0,

                "updated":
                    0,

                "unchanged":
                    0,

                "skipped":
                    0,
            }

        order_pushed = (
            int(
                sheet_result.get(
                    "inserted",
                    0,
                )
                or 0
            )
            +
            int(
                sheet_result.get(
                    "updated",
                    0,
                )
                or 0
            )
            +
            int(
                sheet_result.get(
                    "unchanged",
                    0,
                )
                or 0
            )
        )

        next_offset = (
            offset
            + len(
                selected_ids
            )
        )

        has_more = (
            next_offset
            < total_orders
        )

        elapsed_seconds = round(
            time.time()
            - started_at,
            2,
        )

        print("=" * 70)
        print(
            "ORDER PARALLEL SYNC COMPLETE"
        )
        print(
            f"CRAWLED: "
            f"{len(selected_ids)}"
        )
        print(
            f"SUCCESS: "
            f"{order_success}"
        )
        print(
            f"FAILED: "
            f"{order_failed}"
        )
        print(
            f"PUSHED: "
            f"{order_pushed}"
        )
        print(
            f"ELAPSED: "
            f"{elapsed_seconds}s"
        )
        print(
            f"HAS MORE: "
            f"{has_more}"
        )
        print("=" * 70)

        next_api = None

        if has_more:
            next_api = (
                f"/trip/"
                f"{resolved_trip_id}"
                f"/sync-orders"
                f"?offset="
                f"{next_offset}"
                f"&limit="
                f"{limit}"
                f"&max_workers="
                f"{max_workers}"
            )

        return jsonify({
            "success":
                True,

            "trip_input":
                trip_input,

            "trip_id":
                resolved_trip_id,

            "source": {
                "scan_to_rows":
                    source.get(
                        "scan_to_rows",
                        0,
                    ),

                "bulky_rows":
                    source.get(
                        "bulky_rows",
                        0,
                    ),

                "total_unique":
                    total_orders,
            },

            "batch": {
                "offset":
                    offset,

                "limit":
                    limit,

                "count":
                    len(
                        selected_ids
                    ),

                "next_offset":
                    next_offset,

                "has_more":
                    has_more,

                "max_workers":
                    max_workers,

                "elapsed_seconds":
                    elapsed_seconds,
            },

            "orders": {
                "success":
                    order_success,

                "failed":
                    order_failed,

                "pushed":
                    order_pushed,

                "failed_orders":
                    failed_orders,
            },

            "sheet":
                sheet_result,

            "next_api":
                next_api,
        })

    except Exception as e:
        print("=" * 70)
        print(
            "ORDER PARALLEL SYNC ERROR"
        )
        print(
            traceback.format_exc()
        )
        print("=" * 70)

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


@app.route(
    "/order/<shipment_id>/tracking"
)
def order_tracking(
    shipment_id
):
    try:
        #check_auth()

        shipment_id = (
            shipment_id
            .strip()
            .upper()
        )

        data = get_tracking_info(
            shipment_id
        )

        return jsonify({
            "success": True,
            "shipment_id":
                shipment_id,
            "data": data,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "shipment_id":
                shipment_id,
            "error": str(e),
        }), 500


@app.route(
    "/order/<shipment_id>/check"
)
def order_check(
    shipment_id
):
    try:
        #check_auth()

        shipment_id = (
            shipment_id
            .strip()
            .upper()
        )

        station_id = (
            request.args.get(
                "station_id",
                default=None,
                type=int,
            )
        )

        data = check_order(
            shipment_id=
                shipment_id,
            station_id=
                station_id,
            station_type=2,
        )

        row = build_order_row(
            shipment_id=
                shipment_id,
            order_data=
                data,
        )

        return jsonify({
            "success": True,
            "data": row,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "shipment_id":
                shipment_id,
            "error": str(e),
        }), 500


@app.route(
    "/order/<shipment_id>/sync",
    methods=[
        "GET",
        "POST",
    ]
)
def sync_order(
    shipment_id
):
    try:
        #check_auth()

        shipment_id = (
            shipment_id
            .strip()
            .upper()
        )

        station_id = (
            request.args.get(
                "station_id",
                default=None,
                type=int,
            )
        )

        data = check_order(
            shipment_id=
                shipment_id,
            station_id=
                station_id,
            station_type=2,
        )

        row = build_order_row(
            shipment_id=
                shipment_id,
            order_data=
                data,
        )

        legacy_sheet_result = (
            push_order_rows(
                [
                    row
                ]
            )
        )

        sheet_result = {
            "success": True,
            "order":
                legacy_sheet_result,
        }

        return jsonify({
            "success": True,
            "shipment_id":
                shipment_id,
            "new_status":
                row.get(
                    "new_status"
                ),
            "new_status_time":
                row.get(
                    "new_status_time"
                ),
            "new_status_reason":
                row.get(
                    "new_status_reason"
                ),
            "next_station":
                row.get(
                    "next_station"
                ),
            "sheet":
                sheet_result,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "shipment_id":
                shipment_id,
            "error": str(e),
        }), 500


@app.route(
    "/orders/sync-sheet",
    methods=[
        "GET",
        "POST",
    ]
)
def sync_orders_from_sheet():
    try:
        #check_auth()

        shipment_ids = (
            get_push_order_ids()
        )

        if not shipment_ids:
            return jsonify({
                "success": False,
                "error":
                    "Không có shipment_id "
                    "trong tab push order",
            }), 400

        shipment_ids = [
            str(
                shipment_id
            )
            .strip()
            .upper()
            for shipment_id
            in shipment_ids
            if str(
                shipment_id
            ).strip()
        ]

        total = len(
            shipment_ids
        )

        process_limit = 500
        wait_seconds = 60

        sheet_batch_size = (
            request.args.get(
                "batch_size",
                default=20,
                type=int,
            )
        )

        if (
            sheet_batch_size is None
            or sheet_batch_size < 1
        ):
            sheet_batch_size = 20

        if sheet_batch_size > 100:
            sheet_batch_size = 100

        success_count = 0
        failed_count = 0
        pushed_count = 0

        rows_buffer = []
        failed_orders = []

        print("=" * 70)
        print(
            f"TOTAL ORDERS: "
            f"{total}"
        )
        print(
            f"PROCESS LIMIT: "
            f"{process_limit}"
        )
        print(
            f"WAIT SECONDS: "
            f"{wait_seconds}"
        )
        print(
            f"SHEET BATCH SIZE: "
            f"{sheet_batch_size}"
        )
        print("=" * 70)

        for index, shipment_id in enumerate(
            shipment_ids,
            start=1,
        ):
            print(
                f"[{index}/{total}] "
                f"Checking "
                f"{shipment_id}"
            )

            try:
                data = check_order(
                    shipment_id=
                        shipment_id,
                    station_id=None,
                    station_type=2,
                )

                row = build_order_row(
                    shipment_id=
                        shipment_id,
                    order_data=
                        data,
                )

                rows_buffer.append(
                    row
                )

                success_count += 1

                print(
                    f"[{index}/{total}] "
                    f"{shipment_id} "
                    f"=> "
                    f"{row.get('new_status', '')} "
                    f"| "
                    f"{row.get('new_status_reason', '')}"
                )

            except Exception as e:
                failed_count += 1

                failed_orders.append({
                    "shipment_id":
                        shipment_id,
                    "error":
                        str(e),
                })

                print(
                    f"[{index}/{total}] "
                    f"{shipment_id} "
                    f"ERROR: {e}"
                )

            if (
                len(
                    rows_buffer
                )
                >=
                sheet_batch_size
            ):
                current_rows = (
                    rows_buffer
                )

                try:
                    push_order_rows(
                        current_rows
                    )

                    pushed_count += len(
                        current_rows
                    )

                    print(
                        f"PUSHED: "
                        f"{pushed_count}/"
                        f"{total}"
                    )

                    rows_buffer = []

                except Exception as e:
                    print(
                        f"SHEET PUSH ERROR: "
                        f"{e}"
                    )

                    failed_orders.append({
                        "shipment_id":
                            "SHEET_BATCH",
                        "error":
                            str(e),
                    })

                    rows_buffer = []

            if (
                index
                % process_limit
                == 0
                and index < total
            ):
                if rows_buffer:
                    current_rows = (
                        rows_buffer
                    )

                    try:
                        push_order_rows(
                            current_rows
                        )

                        pushed_count += len(
                            current_rows
                        )

                        rows_buffer = []

                    except Exception as e:
                        print(
                            f"SHEET PUSH ERROR: "
                            f"{e}"
                        )

                        failed_orders.append({
                            "shipment_id":
                                "SHEET_BATCH",
                            "error":
                                str(e),
                        })

                        rows_buffer = []

                remaining = (
                    total - index
                )

                print("=" * 70)
                print(
                    f"DONE "
                    f"{index} "
                    f"ORDERS"
                )
                print(
                    f"REMAINING: "
                    f"{remaining}"
                )
                print(
                    f"WAITING "
                    f"{wait_seconds} "
                    f"SECONDS..."
                )
                print("=" * 70)

                time.sleep(
                    wait_seconds
                )

                print("=" * 70)
                print(
                    f"CONTINUE FROM "
                    f"ORDER "
                    f"{index + 1}"
                )
                print("=" * 70)

        if rows_buffer:
            current_rows = (
                rows_buffer
            )

            try:
                push_order_rows(
                    current_rows
                )

                pushed_count += len(
                    current_rows
                )

                rows_buffer = []

            except Exception as e:
                print(
                    f"FINAL SHEET PUSH ERROR: "
                    f"{e}"
                )

                failed_orders.append({
                    "shipment_id":
                        "FINAL_SHEET_BATCH",
                    "error":
                        str(e),
                })

                rows_buffer = []

        print("=" * 70)
        print("SYNC COMPLETE")
        print(
            f"TOTAL: "
            f"{total}"
        )
        print(
            f"SUCCESS: "
            f"{success_count}"
        )
        print(
            f"FAILED: "
            f"{failed_count}"
        )
        print(
            f"PUSHED: "
            f"{pushed_count}"
        )
        print("=" * 70)

        return jsonify({
            "success": True,
            "total":
                total,
            "process_limit":
                process_limit,
            "wait_seconds":
                wait_seconds,
            "success_count":
                success_count,
            "failed_count":
                failed_count,
            "pushed_count":
                pushed_count,
            "failed_orders":
                failed_orders,
        })

    except Exception as e:
        print("=" * 60)
        print(
            "SYNC ORDER SHEET ERROR"
        )
        print(
            str(e)
        )
        traceback.print_exc()
        print("=" * 60)

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500

def resolve_trip_number_to_id(
    trip_number
):
    trip_number = str(
        trip_number or ""
    ).strip().upper()

    if not trip_number:
        raise RuntimeError(
            "Trip number rỗng"
        )

    if trip_number.isdigit():
        return int(
            trip_number
        )

    if not trip_number.startswith(
        "LT"
    ):
        raise RuntimeError(
            f"Trip không hợp lệ: "
            f"{trip_number}"
        )

    end_ts = int(
        time.time()
    )

    start_ts = (
        end_ts
        - (
            45
            * 24
            * 60
            * 60
        )
    )

    url = (
        f"{BASE_URL}"
        "/api/admin/transportation/"
        "trip/history/list"
    )

    params = {
        "trip_number":
            trip_number,

        "mtime":
            f"{start_ts},{end_ts}",

        "pageno":
            1,

        "count":
            100,
    }

    response = spx_get(
        url,
        params=params,
        timeout=60,
    )

    payload = response.json()

    data = payload.get(
        "data",
        {}
    )

    items = (
        data.get(
            "list",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    for item in items:
        if not isinstance(
            item,
            dict
        ):
            continue

        item_trip_number = str(
            item.get(
                "trip_number",
                ""
            )
        ).strip().upper()

        if (
            item_trip_number
            != trip_number
        ):
            continue

        trip_id = (
            item.get("id")
            or item.get(
                "trip_id"
            )
        )

        if trip_id:
            return int(
                trip_id
            )

    raise RuntimeError(
        f"Không tìm thấy trip_id "
        f"cho {trip_number}"
    )
def resolve_trip_identifier(
    value
):
    value = str(
        value or ""
    ).strip().upper()

    if value.isdigit():
        return int(
            value
        )

    return (
        resolve_trip_number_to_id(
            value
        )
    )
@app.route(
    "/cage/packed-history/all",
    methods=[
        "GET",
        "POST",
    ]
)
def cage_packed_history_all():
    try:
        #check_auth()

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        scan_time_begin = (
            request.args.get(
                "scan_time_begin",
                type=int,
            )
            or body.get(
                "scan_time_begin"
            )
        )

        scan_time_end = (
            request.args.get(
                "scan_time_end",
                type=int,
            )
            or body.get(
                "scan_time_end"
            )
        )

        count = (
            request.args.get(
                "count",
                default=100,
                type=int,
            )
            or body.get(
                "count",
                100
            )
        )

        if (
            not scan_time_begin
            or
            not scan_time_end
        ):
            return jsonify({
                "success":
                    False,
                "error":
                    "Thiếu scan_time_begin "
                    "hoặc scan_time_end",
            }), 400

        if count < 1:
            count = 100

        if count > 100:
            count = 100

        data = (
            crawl_all_packed_history(
                scan_time_begin=
                    scan_time_begin,
                scan_time_end=
                    scan_time_end,
                count=
                    count,
            )
        )

        return jsonify({
            "success":
                True,
            "scan_time_begin":
                scan_time_begin,
            "scan_time_end":
                scan_time_end,
            "total":
                data.get(
                    "total",
                    0
                ),
            "crawled":
                data.get(
                    "crawled",
                    0
                ),
            "data":
                data.get(
                    "list",
                    []
                ),
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,
            "error":
                str(e),
        }), 500


@app.route(
    "/cage/history/sync",
    methods=["POST"],
)
def cage_history_sync():
    try:
        #check_auth()

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        scan_time_begin = (
            body.get(
                "scan_time_begin"
            )
        )

        scan_time_end = (
            body.get(
                "scan_time_end"
            )
        )

        if (
            not scan_time_begin
            or not scan_time_end
        ):
            return jsonify({
                "success": False,
                "error":
                    "Thiếu scan_time_begin hoặc scan_time_end",
            }), 400

        print(
            "CAGE SYNC:",
            scan_time_begin,
            scan_time_end,
        )

        result = (
            sync_cage_history(
                int(
                    scan_time_begin
                ),
                int(
                    scan_time_end
                ),
            )
        )

        return jsonify({
            "success": True,
            **result,
        })

    except Exception as e:
        print("=" * 80)
        print("CAGE HISTORY SYNC ERROR")
        print(traceback.format_exc())
        print("=" * 80)

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route(
    "/cage/history",
    methods=["GET"],
)
def cage_history_data():
    try:
        page = request.args.get(
            "page",
            default=1,
            type=int,
        )

        page_size = request.args.get(
            "page_size",
            default=100,
            type=int,
        )

        search = request.args.get(
            "search",
            default="",
            type=str,
        )

        result = read_sheet_rows(
            page=page,
            page_size=page_size,
            search=search,
        )

        return jsonify({
            "success": True,
            **result,
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500
@app.route(
    "/to/<to_number>/orders",
    methods=["GET"],
)
def to_orders(
    to_number
):
    try:
        #check_auth()

        count = request.args.get(
            "count",
            default=10000,
            type=int,
        )

        data = scan_to_orders(
            to_number=
                to_number,

            count=
                count,
        )

        return jsonify({
            "success":
                True,

            "to_number":
                str(
                    to_number
                ).strip().upper(),

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

            "to_number":
                str(
                    to_number
                ).strip().upper(),

            "error":
                str(
                    e
                ),
        }), 500


@app.route(
    "/to/<to_number>/sync",
    methods=["GET", "POST"],
)
def sync_to_orders(
    to_number
):
    try:
        #check_auth()

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        trip_id = (
            request.args.get(
                "trip_id",
                default=None,
                type=str,
            )
            or body.get(
                "trip_id"
            )
        )

        if not trip_id:
            return jsonify({
                "success": False,
                "error":
                    "Thiếu trip_id",
            }), 400

        trip_id = str(
            trip_id
        ).strip()

        to_number = str(
            to_number or ""
        ).strip().upper()

        count = (
            request.args.get(
                "count",
                default=None,
                type=int,
            )
            or body.get(
                "count"
            )
            or 10000
        )

        batch_size = (
            request.args.get(
                "batch_size",
                default=None,
                type=int,
            )
            or body.get(
                "batch_size"
            )
            or 20
        )

        if batch_size < 1:
            batch_size = 20

        if batch_size > 100:
            batch_size = 100

        print("=" * 70)
        print(
            f"TO SYNC: "
            f"{to_number}"
        )
        print(
            f"TRIP ID: "
            f"{trip_id}"
        )

        scan_result = (
            scan_to_orders(
                to_number=
                    to_number,
                count=
                    count,
            )
        )

        scan_data = (
            scan_result.get(
                "data",
                {}
            )
            if isinstance(
                scan_result,
                dict
            )
            else {}
        )

        items = (
            scan_data.get(
                "list",
                []
            )
            if isinstance(
                scan_data,
                dict
            )
            else []
        )

        to_order_rows = (
            build_to_order_rows(
                trip_id=
                    trip_id,
                to_number=
                    to_number,
                items=
                    items,
            )
        )

        mapping_result = (
            push_to_order_rows(
                to_order_rows
            )
        )

        shipment_ids = (
            get_shipment_ids_from_to_order_rows(
                to_order_rows
            )
        )

        total_orders = len(
            shipment_ids
        )

        print(
            f"TO ORDERS: "
            f"{total_orders}"
        )

        full_rows_buffer = []
        full_pushed = 0
        order_success = 0
        order_failed = 0
        failed_orders = []
        full_sheet_batches = []

        for (
            index,
            shipment_id
        ) in enumerate(
            shipment_ids,
            start=1,
        ):
            print(
                f"[{index}/{total_orders}] "
                f"ORDER "
                f"{shipment_id}"
            )

            try:
                order_data = (
                    check_order(
                        shipment_id=
                            shipment_id,
                        station_id=
                            None,
                        station_type=
                            2,
                    )
                )

                full_row = (
                    build_full_order_row(
                        shipment_id=
                            shipment_id,
                        order_data=
                            order_data,
                    )
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

        full_sheet_result = {
            "inserted":
                sum(
                    int(
                        item.get(
                            "inserted",
                            0
                        )
                        or 0
                    )
                    for item
                    in full_sheet_batches
                ),
            "updated":
                sum(
                    int(
                        item.get(
                            "updated",
                            0
                        )
                        or 0
                    )
                    for item
                    in full_sheet_batches
                ),
            "unchanged":
                sum(
                    int(
                        item.get(
                            "unchanged",
                            0
                        )
                        or 0
                    )
                    for item
                    in full_sheet_batches
                ),
            "skipped":
                sum(
                    int(
                        item.get(
                            "skipped",
                            0
                        )
                        or 0
                    )
                    for item
                    in full_sheet_batches
                ),
        }

        print(
            f"TO MAPPING: "
            f"{mapping_result}"
        )
        print(
            f"FULL ORDER: "
            f"{full_sheet_result}"
        )
        print("=" * 70)

        return jsonify({
            "success":
                True,
            "trip_id":
                trip_id,
            "to_number":
                to_number,
            "scan_total":
                scan_data.get(
                    "total",
                    len(items)
                )
                if isinstance(
                    scan_data,
                    dict
                )
                else len(items),
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
        })

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,
            "to_number":
                str(
                    to_number
                ).strip().upper(),
            "error":
                str(e),
        }), 500


def _volume_safe_int(
    value,
    default=0,
):
    try:
        if value in (
            None,
            "",
        ):
            return default

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def _volume_parse_ts(
    value,
):
    if value in (
        None,
        "",
        0,
        "0",
    ):
        return None

    try:
        number = float(
            value
        )

        while (
            number
            > 10_000_000_000
        ):
            number /= 1000

        return datetime.fromtimestamp(
            number,
            VN_TZ,
        )

    except (
        TypeError,
        ValueError,
        OSError,
        OverflowError,
    ):
        pass

    text_value = str(
        value
    ).strip()

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(
                text_value,
                fmt,
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=VN_TZ
                )

            return parsed.astimezone(
                VN_TZ
            )

        except ValueError:
            continue

    return None


def _volume_get_station_id(
    row,
):
    return str(
        row.get(
            "station_id",
            "",
        )
        or row.get(
            "station",
            "",
        )
        or row.get(
            "trip_station_id",
            "",
        )
        or ""
    ).strip()


def _volume_get_sequence(
    row,
):
    return _volume_safe_int(
        row.get(
            "sequence",
        )
        or row.get(
            "sequence_number",
        )
        or row.get(
            "station_sequence",
        )
    )


def _volume_get_trip_id(
    row,
):
    return str(
        row.get(
            "trip_id",
            "",
        )
        or row.get(
            "id",
            "",
        )
        or ""
    ).strip()


def _volume_get_ata(
    row,
):
    return _volume_parse_ts(
        row.get(
            "ata",
        )
        or row.get(
            "actual_arrival_time",
        )
    )


def _volume_get_unseal(
    row,
):
    return _volume_parse_ts(
        row.get(
            "unseal_time",
        )
        or row.get(
            "unsealed_time",
        )
    )


def _volume_get_unloaded(
    row,
):
    return _volume_parse_ts(
        row.get(
            "unloaded_time",
        )
        or row.get(
            "actual_unloaded_time",
        )
    )


def _volume_format_sheet_time(
    value,
):
    parsed = _volume_parse_ts(
        value
    )

    if parsed is None:
        return ""

    return parsed.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def _volume_get_business_range(
    target_date=None,
):
    if target_date is None:
        current_date = (
            datetime.now(
                VN_TZ
            ).date()
        )

    else:
        current_date = (
            datetime.strptime(
                str(
                    target_date
                ).strip(),
                "%Y-%m-%d",
            ).date()
        )

    start_datetime = datetime(
        current_date.year,
        current_date.month,
        current_date.day,
        6,
        0,
        0,
        tzinfo=VN_TZ,
    )

    end_datetime = (
        start_datetime
        + timedelta(
            days=1
        )
    )

    return (
        current_date,
        start_datetime,
        end_datetime,
    )


def _get_volume_trip_contexts(
    target_date=None,
):
    (
        current_date,
        start_datetime,
        end_datetime,
    ) = _volume_get_business_range(
        target_date
    )

    service = (
        get_sheets_service()
    )

    rows = _sheet_rows_as_dicts(
        service=
            service,
        gid=
            TRIP_STATION_GID,
    )

    selected = {}
    skipped_station = 0
    skipped_sequence = 0
    skipped_ata = 0
    skipped_range = 0

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        station_id = (
            _volume_get_station_id(
                row
            )
        )

        if station_id != "3909":
            skipped_station += 1
            continue

        sequence = (
            _volume_get_sequence(
                row
            )
        )

        if sequence <= 1:
            skipped_sequence += 1
            continue

        ata = _volume_get_ata(
            row
        )

        if ata is None:
            skipped_ata += 1
            continue

        if not (
            start_datetime
            <= ata
            < end_datetime
        ):
            skipped_range += 1
            continue

        trip_id = (
            _volume_get_trip_id(
                row
            )
        )

        if not trip_id:
            continue

        current = (
            selected.get(
                trip_id
            )
        )

        unseal = _volume_get_unseal(
            row
        )

        unloaded = _volume_get_unloaded(
            row
        )

        candidate = {
            "trip_id":
                trip_id,
            "trip_number":
                str(
                    row.get("trip_number")
                    or row.get("trip_no")
                    or row.get("trip_name")
                    or row.get("LH Trip Number")
                    or ""
                ).strip().upper(),
            "vehicle_number":
                str(
                    row.get("vehicle_number")
                    or row.get("vehicle_plate_number")
                    or row.get("vehicle_no")
                    or row.get("Vehicle Plate Number")
                    or ""
                ).strip().upper(),
            "sequence":
                sequence,
            "ata":
                ata.isoformat(),
            "unseal_time":
                (
                    unseal.isoformat()
                    if unseal
                    else ""
                ),
            "unloaded_time":
                (
                    unloaded.isoformat()
                    if unloaded
                    else ""
                ),
        }

        if current is None:
            selected[
                trip_id
            ] = candidate
            continue

        current_ata = (
            _volume_parse_ts(
                current.get(
                    "ata"
                )
            )
        )

        if (
            current_ata is None
            or ata > current_ata
        ):
            selected[
                trip_id
            ] = candidate

    trips = list(
        selected.values()
    )

    trips.sort(
        key=lambda item:
            item.get(
                "ata",
                "",
            )
    )

    return {
        "date":
            current_date.isoformat(),
        "from":
            start_datetime.isoformat(),
        "to":
            end_datetime.isoformat(),
        "source_rows":
            len(rows),
        "trips":
            trips,
        "trip_count":
            len(trips),
        "skipped": {
            "other_station":
                skipped_station,
            "not_inbound":
                skipped_sequence,
            "no_ata":
                skipped_ata,
            "outside_range":
                skipped_range,
        },
    }


def _crawl_loading_for_volume_trip(
    trip_context,
):
    trip_id = (
        trip_context[
            "trip_id"
        ]
    )

    sequence = int(
        trip_context[
            "sequence"
        ]
    )

    loading_data = (
        get_trip_loading_data(
            trip_id=
                trip_id,
            direction=
                "inbound",
            sequence=
                sequence,
        )
    )

    items = extract_list(
        loading_data
    )

    to_rows = build_to_rows(
        trip_id=
            trip_id,
        items=
            items,
        direction=
            "inbound",
        sequence=
            sequence,
    )

    to_numbers = []
    bulky_ids = []
    seen_to = set()
    seen_bulky = set()

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        scan_number = str(
            item.get(
                "scan_number"
            )
            or item.get(
                "to_number"
            )
            or item.get(
                "shipment_id"
            )
            or item.get(
                "fleet_order_id"
            )
            or ""
        ).strip().upper()

        if not scan_number:
            continue

        if scan_number.startswith(
            "TO"
        ):
            if (
                scan_number
                not in seen_to
            ):
                seen_to.add(
                    scan_number
                )

                to_numbers.append(
                    scan_number
                )

            continue

        if scan_number.startswith(
            "SPXVN"
        ):
            if (
                scan_number
                not in seen_bulky
            ):
                seen_bulky.add(
                    scan_number
                )

                bulky_ids.append(
                    scan_number
                )

    return {
        "trip_id":
            trip_id,
        "trip_number":
            trip_context.get(
                "trip_number",
                "",
            ),
        "vehicle_number":
            trip_context.get(
                "vehicle_number",
                "",
            ),
        "ata":
            trip_context.get(
                "ata",
                "",
            ),
        "unseal_time":
            trip_context.get(
                "unseal_time",
                "",
            ),
        "unloaded_time":
            trip_context.get(
                "unloaded_time",
                "",
            ),
        "sequence":
            sequence,
        "loading_items":
            len(items),
        "to_rows":
            to_rows,
        "to_numbers":
            to_numbers,
        "bulky_ids":
            bulky_ids,
    }


def _scan_one_volume_to(
    to_number,
    trip_id,
):
    scan_result = scan_to_orders(
        to_number=
            to_number,
        count=
            10000,
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

    shipment_ids = []
    seen = set()

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        shipment_id = str(
            item.get(
                "shipment_id",
            )
            or item.get(
                "fleet_order_id",
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

    return {
        "to_number":
            to_number,
        "trip_id":
            trip_id,
        "shipment_ids":
            shipment_ids,
    }

def ensure_volume_grid(
    service,
    required_rows,
    required_columns,
):
    spreadsheet = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                VOLUME_SPREADSHEET_ID,

            fields=(
                "sheets.properties("
                "sheetId,"
                "gridProperties"
                ")"
            ),
        )
        .execute()
    )

    target = None

    for sheet in spreadsheet.get(
        "sheets",
        [],
    ):
        props = sheet.get(
            "properties",
            {},
        )

        if int(
            props.get(
                "sheetId",
                -1,
            )
        ) == int(
            VOLUME_GID
        ):
            target = props
            break

    if target is None:
        raise RuntimeError(
            f"Không tìm thấy Volume gid={VOLUME_GID}"
        )

    grid = target.get(
        "gridProperties",
        {},
    )

    current_rows = int(
        grid.get(
            "rowCount",
            0,
        )
        or 0
    )

    current_columns = int(
        grid.get(
            "columnCount",
            0,
        )
        or 0
    )

    new_rows = max(
        current_rows,
        int(required_rows),
    )

    new_columns = max(
        current_columns,
        int(required_columns),
    )

    if (
        new_rows == current_rows
        and
        new_columns == current_columns
    ):
        return

    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=
                VOLUME_SPREADSHEET_ID,

            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId":
                                    int(
                                        VOLUME_GID
                                    ),

                                "gridProperties": {
                                    "rowCount":
                                        new_rows,

                                    "columnCount":
                                        new_columns,
                                },
                            },

                            "fields":
                                "gridProperties.rowCount,"
                                "gridProperties.columnCount",
                        }
                    }
                ]
            },
        )
        .execute()
    )

    print(
        "[VOLUME SHEET] Grid expanded: "
        f"rows {current_rows}->{new_rows}, "
        f"columns {current_columns}->{new_columns}"
    )

def _push_volume_rows(
    rows,
):
    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
        }

    service = (
        get_sheets_service()
    )

    sheet_name = (
        get_sheet_name_by_gid(
            gid=
                VOLUME_GID,
            service=
                service,
        )
    )

    existing = (
        read_existing_data(
            service,
            sheet_name,
        )
    )

    required_headers = [
        "_key",
        "Operational Date",
        "trip_id",
        "LH Trip Number",
        "Vehicle Plate Number",
        "Station Name",
        "Actual Arrival Time",
        "Unsealed time",
        "Unloaded time",
        "Inbound(order)",
        "Bulky",
        "TO Count",
        "sync_time",
    ]

    if existing:
        headers = [
            str(
                item
            ).strip()
            for item in existing[0]
        ]
    else:
        headers = []

    changed = False

    for header in required_headers:
        if header not in headers:
            headers.append(
                header
            )
            changed = True

    if not headers:
        headers = list(
            required_headers
        )
        changed = True

    def column_letter(
        number,
    ):
        result = ""

        while number:
            number, remainder = divmod(
                number - 1,
                26,
            )

            result = (
                chr(
                    65 + remainder
                )
                + result
            )

        return result

    end_col = column_letter(
        len(headers)
    )

    if (
        changed
        or not existing
    ):
        (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=
                    VOLUME_SPREADSHEET_ID,
                range=(
                    f"'{sheet_name}'!"
                    f"A1:{end_col}1"
                ),
                valueInputOption=
                    "RAW",
                body={
                    "values": [
                        headers
                    ]
                },
            )
            .execute()
        )

    key_index = headers.index(
        "_key"
    )

    existing_map = {}

    for row_number, values in enumerate(
        existing[1:]
        if existing
        else [],
        start=2,
    ):
        key = (
            str(
                values[
                    key_index
                ]
            ).strip()
            if key_index < len(
                values
            )
            else ""
        )

        if key:
            existing_map[
                key
            ] = (
                row_number,
                values,
            )

    updates = []
    inserts = []
    unchanged = 0

    for row in rows:
        key = str(
            row.get(
                "_key",
                "",
            )
            or ""
        ).strip()

        if not key:
            continue

        new_values = [
            row.get(
                header,
                "",
            )
            for header in headers
        ]

        current = existing_map.get(
            key
        )

        if current is None:
            inserts.append(
                new_values
            )
            continue

        row_number, old_values = current

        normalized_old = list(
            old_values
        )

        if len(
            normalized_old
        ) < len(headers):
            normalized_old.extend(
                [""]
                * (
                    len(headers)
                    - len(
                        normalized_old
                    )
                )
            )

        comparable_new = [
            ""
            if value is None
            else str(
                value
            )
            for value in new_values
        ]

        comparable_old = [
            ""
            if value is None
            else str(
                value
            )
            for value in normalized_old[
                :len(headers)
            ]
        ]

        if (
            comparable_new
            == comparable_old
        ):
            unchanged += 1
            continue

        updates.append({
            "range": (
                f"'{sheet_name}'!"
                f"A{row_number}:"
                f"{end_col}{row_number}"
            ),
            "values": [
                new_values
            ],
        })

    if updates:
        (
            service.spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=
                    VOLUME_SPREADSHEET_ID,
                body={
                    "valueInputOption":
                        "RAW",
                    "data":
                        updates,
                },
            )
            .execute()
        )

    inserted = 0

    if inserts:
        start_row = max(
            2,
            len(
                existing
            ) + 1,
        )

        end_row = (
            start_row
            + len(
                inserts
            )
            - 1
        )

        ensure_volume_grid(
            service=
                service,
            required_rows=
                end_row,
            required_columns=
                len(
                    headers
                ),
        )

        (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=
                    VOLUME_SPREADSHEET_ID,
                range=(
                    f"'{sheet_name}'!"
                    f"A{start_row}:"
                    f"{end_col}{end_row}"
                ),
                valueInputOption=
                    "RAW",
                body={
                    "values":
                        inserts,
                },
            )
            .execute()
        )

        inserted = len(
            inserts
        )

    return {
        "sheet":
            sheet_name,
        "gid":
            VOLUME_GID,
        "inserted":
            inserted,
        "updated":
            len(
                updates
            ),
        "unchanged":
            unchanged,
        "rows":
            len(
                rows
            ),
    }


def run_volume_sync(
    target_date=None,
    max_workers=5,
):
    if not _volume_sync_lock.acquire(
        blocking=False
    ):
        raise RuntimeError(
            "Volume sync đang chạy"
        )

    started_at = time.time()

    try:
        try:
            max_workers = int(
                max_workers
            )
        except (
            TypeError,
            ValueError,
        ):
            max_workers = 5

        max_workers = max(
            1,
            min(
                max_workers,
                5,
            ),
        )

        context = (
            _get_volume_trip_contexts(
                target_date
            )
        )

        trips = context[
            "trips"
        ]

        print()
        print("=" * 90)
        print(
            "VOLUME SYNC"
        )
        print(
            "DATE:",
            context[
                "date"
            ],
        )
        print(
            "FROM:",
            context[
                "from"
            ],
        )
        print(
            "TO:",
            context[
                "to"
            ],
        )
        print(
            "INBOUND TRIPS:",
            len(trips),
        )
        print(
            "WORKERS:",
            max_workers,
        )
        print("=" * 90)

        loading_results = []
        loading_failed = []

        if trips:
            with ThreadPoolExecutor(
                max_workers=
                    max_workers
            ) as executor:
                future_map = {
                    executor.submit(
                        _crawl_loading_for_volume_trip,
                        trip,
                    ): trip

                    for trip in trips
                }

                total_trips = len(
                    future_map
                )

                done_count = 0

                for future in as_completed(
                    future_map
                ):
                    trip = future_map[
                        future
                    ]

                    done_count += 1

                    try:
                        result = (
                            future.result()
                        )

                        loading_results.append(
                            result
                        )

                        print(
                            f"[LOADING "
                            f"{done_count}/"
                            f"{total_trips}] "
                            f"TRIP="
                            f"{result['trip_id']} "
                            f"ITEMS="
                            f"{result['loading_items']} "
                            f"TO="
                            f"{len(result['to_numbers'])}"
                        )

                    except Exception as e:
                        loading_failed.append({
                            "trip_id":
                                trip.get(
                                    "trip_id"
                                ),
                            "trip_number":
                                trip.get(
                                    "trip_number"
                                ),
                            "error":
                                str(e),
                        })

                        print(
                            f"[LOADING "
                            f"{done_count}/"
                            f"{total_trips}] "
                            f"ERROR "
                            f"{trip.get('trip_id')} "
                            f"=> {e}"
                        )

        global_to_map = {}
        bulky_seen = set()
        loading_item_total = 0
        trip_volume_map = {}

        for result in loading_results:
            loading_item_total += int(
                result.get(
                    "loading_items",
                    0,
                )
                or 0
            )

            trip_id = str(
                result.get(
                    "trip_id",
                    "",
                )
                or ""
            ).strip()

            trip_state = trip_volume_map.setdefault(
                trip_id,
                {
                    "trip_id": trip_id,
                    "trip_number": result.get(
                        "trip_number",
                        "",
                    ),
                    "vehicle_number": result.get(
                        "vehicle_number",
                        "",
                    ),
                    "ata": result.get(
                        "ata",
                        "",
                    ),
                    "unseal_time": result.get(
                        "unseal_time",
                        "",
                    ),
                    "unloaded_time": result.get(
                        "unloaded_time",
                        "",
                    ),
                    "to_numbers": set(),
                    "bulky_ids": set(),
                    "shipment_ids": set(),
                },
            )

            for to_number in (
                result.get(
                    "to_numbers",
                    [],
                )
            ):
                trip_state[
                    "to_numbers"
                ].add(
                    to_number
                )

                if (
                    to_number
                    not in global_to_map
                ):
                    global_to_map[
                        to_number
                    ] = trip_id

            for bulky_id in (
                result.get(
                    "bulky_ids",
                    [],
                )
            ):
                trip_state[
                    "bulky_ids"
                ].add(
                    bulky_id
                )

                bulky_seen.add(
                    bulky_id
                )

        to_sheet_result = {
            "skipped": True,
            "reason":
                "BULK_VOLUME_SYNC_DOES_NOT_PUSH_TO",
        }

        to_numbers = sorted(
            global_to_map
        )

        print()
        print(
            "LOADING ITEMS:",
            loading_item_total,
        )
        print(
            "TO UNIQUE GLOBAL:",
            len(to_numbers),
        )
        print(
            "BULKY UNIQUE:",
            len(bulky_seen),
        )

        scan_results = []
        scan_failed = []

        if to_numbers:
            with ThreadPoolExecutor(
                max_workers=
                    max_workers
            ) as executor:
                future_map = {
                    executor.submit(
                        _scan_one_volume_to,
                        to_number,
                        global_to_map[
                            to_number
                        ],
                    ): to_number

                    for to_number
                    in to_numbers
                }

                total_to = len(
                    future_map
                )

                done_count = 0

                for future in as_completed(
                    future_map
                ):
                    to_number = (
                        future_map[
                            future
                        ]
                    )

                    done_count += 1

                    try:
                        result = (
                            future.result()
                        )

                        scan_results.append(
                            result
                        )

                        print(
                            f"[SCAN TO "
                            f"{done_count}/"
                            f"{total_to}] "
                            f"{to_number} "
                            f"=> "
                            f"{len(result['shipment_ids'])} "
                            f"orders"
                        )

                    except Exception as e:
                        scan_failed.append({
                            "to_number":
                                to_number,
                            "trip_id":
                                global_to_map.get(
                                    to_number,
                                    "",
                                ),
                            "error":
                                str(e),
                        })

                        print(
                            f"[SCAN TO "
                            f"{done_count}/"
                            f"{total_to}] "
                            f"{to_number} "
                            f"ERROR => {e}"
                        )

        shipment_seen = set()

        for scan_item in scan_results:
            trip_id = str(
                scan_item.get(
                    "trip_id",
                    "",
                )
                or ""
            ).strip()

            trip_state = trip_volume_map.get(
                trip_id
            )

            for shipment_id in (
                scan_item.get(
                    "shipment_ids",
                    [],
                )
            ):
                shipment_id = str(
                    shipment_id
                    or ""
                ).strip().upper()

                if not shipment_id:
                    continue

                shipment_seen.add(
                    shipment_id
                )

                if trip_state is not None:
                    trip_state[
                        "shipment_ids"
                    ].add(
                        shipment_id
                    )

        volume_rows = []
        sync_time = datetime.now(
            VN_TZ
        ).strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        for trip_id, trip_state in sorted(
            trip_volume_map.items(),
            key=lambda item: (
                item[1].get(
                    "ata",
                    "",
                ),
                item[0],
            ),
        ):
            shipment_ids = set(
                trip_state.get(
                    "shipment_ids",
                    set(),
                )
            )

            bulky_ids = set(
                trip_state.get(
                    "bulky_ids",
                    set(),
                )
            )

            all_orders = (
                shipment_ids
                | bulky_ids
            )

            volume_rows.append({
                "_key": (
                    f"{context['date']}|"
                    f"{trip_id}"
                ),
                "Operational Date":
                    context[
                        "date"
                    ],
                "trip_id":
                    trip_id,
                "LH Trip Number":
                    trip_state.get(
                        "trip_number",
                        "",
                    ),
                "Vehicle Plate Number":
                    trip_state.get(
                        "vehicle_number",
                        "",
                    ),
                "Station Name":
                    "Hung Yen SOC",
                "Actual Arrival Time":
                    _volume_format_sheet_time(
                        trip_state.get(
                            "ata"
                        )
                    ),
                "Unsealed time":
                    _volume_format_sheet_time(
                        trip_state.get(
                            "unseal_time"
                        )
                    ),
                "Unloaded time":
                    _volume_format_sheet_time(
                        trip_state.get(
                            "unloaded_time"
                        )
                    ),
                "Inbound(order)":
                    len(
                        all_orders
                    ),
                "Bulky":
                    len(
                        bulky_ids
                    ),
                "TO Count":
                    len(
                        trip_state.get(
                            "to_numbers",
                            set(),
                        )
                    ),
                "sync_time":
                    sync_time,
            })

        volume_sheet_result = (
            _push_volume_rows(
                volume_rows
            )
        )

        to_order_sheet_result = {
            "skipped": True,
            "reason":
                "BULK_VOLUME_SYNC_DOES_NOT_PUSH_TO_ORDER",
        }

        elapsed = round(
            time.time()
            - started_at,
            2,
        )

        result = {
            "success":
                (
                    len(
                        loading_failed
                    )
                    == 0
                    and len(
                        scan_failed
                    )
                    == 0
                ),
            "date":
                context[
                    "date"
                ],
            "from":
                context[
                    "from"
                ],
            "to":
                context[
                    "to"
                ],
            "source_rows":
                context[
                    "source_rows"
                ],
            "inbound_trips":
                len(trips),
            "loading_success":
                len(
                    loading_results
                ),
            "loading_failed":
                len(
                    loading_failed
                ),
            "loading_items":
                loading_item_total,
            "to_unique":
                len(
                    to_numbers
                ),
            "bulky_unique":
                len(
                    bulky_seen
                ),
            "to_scan_success":
                len(
                    scan_results
                ),
            "to_scan_failed":
                len(
                    scan_failed
                ),
            "to_order_rows":
                0,
            "volume_rows":
                len(
                    volume_rows
                ),
            "shipment_unique":
                len(
                    shipment_seen
                ),
            "sheet": {
                "to":
                    to_sheet_result,
                "to_order":
                    to_order_sheet_result,
                "volume":
                    volume_sheet_result,
            },
            "failed": {
                "loading":
                    loading_failed,
                "scan_to":
                    scan_failed,
            },
            "skipped":
                context[
                    "skipped"
                ],
            "elapsed_seconds":
                elapsed,
        }

        print()
        print("=" * 90)
        print(
            "VOLUME SYNC COMPLETE"
        )
        print(
            "INBOUND TRIPS:",
            result[
                "inbound_trips"
            ],
        )
        print(
            "LOADING ITEMS:",
            result[
                "loading_items"
            ],
        )
        print(
            "TO UNIQUE:",
            result[
                "to_unique"
            ],
        )
        print(
            "TO SCAN SUCCESS:",
            result[
                "to_scan_success"
            ],
        )
        print(
            "TO SCAN FAILED:",
            result[
                "to_scan_failed"
            ],
        )
        print(
            "VOLUME ROWS:",
            result[
                "volume_rows"
            ],
        )
        print(
            "VOLUME SHEET:",
            result[
                "sheet"
            ][
                "volume"
            ],
        )
        print(
            "SHIPMENT UNIQUE:",
            result[
                "shipment_unique"
            ],
        )
        print(
            "ELAPSED:",
            elapsed,
            "seconds",
        )
        print("=" * 90)

        return result

    finally:
        _volume_sync_lock.release()


def _run_volume_sync_background(
    target_date,
    max_workers,
):
    with _volume_sync_state_lock:
        _volume_sync_state[
            "running"
        ] = True
        _volume_sync_state[
            "date"
        ] = target_date
        _volume_sync_state[
            "started_at"
        ] = datetime.now(
            VN_TZ
        ).isoformat()
        _volume_sync_state[
            "finished_at"
        ] = None
        _volume_sync_state[
            "result"
        ] = None
        _volume_sync_state[
            "error"
        ] = None

    try:
        result = run_volume_sync(
            target_date=
                target_date,
            max_workers=
                max_workers,
        )

        with _volume_sync_state_lock:
            _volume_sync_state[
                "result"
            ] = result

    except Exception as e:
        with _volume_sync_state_lock:
            _volume_sync_state[
                "error"
            ] = str(e)

        print(
            traceback.format_exc()
        )

    finally:
        with _volume_sync_state_lock:
            _volume_sync_state[
                "running"
            ] = False
            _volume_sync_state[
                "finished_at"
            ] = datetime.now(
                VN_TZ
            ).isoformat()


@app.route(
    "/api/volume-sync",
    methods=["POST"],
)
def api_volume_sync():
    try:
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

        if target_date:
            datetime.strptime(
                str(
                    target_date
                ).strip(),
                "%Y-%m-%d",
            )

            target_date = str(
                target_date
            ).strip()

        max_workers = (
            request.args.get(
                "max_workers",
                default=None,
                type=int,
            )
            or body.get(
                "max_workers"
            )
            or VOLUME_SYNC_WORKERS
        )

        max_workers = max(
            1,
            min(
                int(
                    max_workers
                ),
                5,
            ),
        )

        with _volume_sync_state_lock:
            if _volume_sync_state.get(
                "running"
            ):
                return jsonify({
                    "success":
                        False,
                    "running":
                        True,
                    "message":
                        "Volume sync đang chạy",
                    "state":
                        dict(
                            _volume_sync_state
                        ),
                }), 409

        thread = threading.Thread(
            target=
                _run_volume_sync_background,
            args=(
                target_date,
                max_workers,
            ),
            name=
                "volume-sync",
            daemon=
                True,
        )

        thread.start()

        return jsonify({
            "success":
                True,
            "running":
                True,
            "date":
                target_date,
            "max_workers":
                max_workers,
            "message":
                "Volume sync đã được khởi chạy background",
            "status_api":
                "/api/volume-sync/status",
        })

    except ValueError:
        return jsonify({
            "success":
                False,
            "error":
                "date phải có định dạng YYYY-MM-DD",
        }), 400

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,
            "error":
                str(e),
        }), 500


@app.route(
    "/api/volume-sync/status",
    methods=["GET"],
)
def api_volume_sync_status():
    with _volume_sync_state_lock:
        state = dict(
            _volume_sync_state
        )

    return jsonify({
        "success":
            state.get(
                "error"
            )
            in (
                None,
                "",
            ),
        **state,
    })


@app.route(
    "/api/volume-sync/trips",
    methods=["GET"],
)
def api_volume_sync_trips():
    try:
        target_date = request.args.get(
            "date",
            default=None,
            type=str,
        )

        result = (
            _get_volume_trip_contexts(
                target_date
            )
        )

        return jsonify({
            "success":
                True,
            **result,
        })

    except ValueError:
        return jsonify({
            "success":
                False,
            "error":
                "date phải có định dạng YYYY-MM-DD",
        }), 400

    except Exception as e:
        print(
            traceback.format_exc()
        )

        return jsonify({
            "success":
                False,
            "error":
                str(e),
        }), 500

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FRONTEND_DIST = os.path.join(
    BASE_DIR,
    "frontend",
    "dist"
)

@app.route("/")
def home():
    return send_from_directory(
        FRONTEND_DIST,
        "index.html"
    )


@app.route("/<path:path>")
def frontend_routes(path):
    api_paths = (
        "api/",
        "trip/",
        "order/",
        "station/",
        "auth/",
        "cage/",
    )

    if path.startswith(
        api_paths
    ):
        return jsonify({
            "success": False,
            "error": "Not Found",
        }), 404

    if path.startswith(
        "orders/"
    ):
        real_orders_api = (
            "orders/sync-sheet",
        )

        if path.startswith(
            real_orders_api
        ):
            return jsonify({
                "success": False,
                "error": "Not Found",
            }), 404

    file_path = os.path.join(
        FRONTEND_DIST,
        path
    )

    if os.path.isfile(
        file_path
    ):
        return send_from_directory(
            FRONTEND_DIST,
            path
        )

    return send_from_directory(
        FRONTEND_DIST,
        "index.html"
    )
@app.route(
    "/api/trip/daily-crawl",
    methods=["POST"]
)
def manual_daily_trip_crawl():
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

    thread = threading.Thread(
        target=
            run_daily_trip_crawl,

        args=(
            target_date,
        ),

        name=
            "manual-daily-trip-crawl",

        daemon=
            True,
    )

    thread.start()

    return jsonify({
        "success":
            True,

        "date":
            target_date,

        "message":
            "Daily Trip + Volume crawl "
            "đã được khởi chạy background.",
    })    
if __name__ == "__main__":

    startup_auth_check()

    start_daily_trip_scheduler()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
    )