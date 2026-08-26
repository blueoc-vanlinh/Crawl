import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

import requests

from config import (
    BASE_URL,
    get_headers,
)


PICKUP_SWITCH_API = (
    BASE_URL
    + "/api/admin/pickup/pickup_config/switches/list"
)

RECIPIENT_INFO_API = (
    BASE_URL
    + "/api/fleet_order/order/detail/recipient_info"
)

TRACKING_INFO_API = (
    BASE_URL
    + "/api/fleet_order/order/detail/tracking_info"
)

TRADE_INFO_API = (
    BASE_URL
    + "/api/fleet_order/order/detail/trade_info"
)


_thread_local = threading.local()
_auth_lock = threading.Lock()


def _normalize_shipment_id(
    shipment_id,
):
    return str(
        shipment_id or ""
    ).strip().upper()


def _get_session():
    session = getattr(
        _thread_local,
        "session",
        None,
    )

    if session is None:
        session = requests.Session()

        adapter = (
            requests.adapters.HTTPAdapter(
                pool_connections=50,
                pool_maxsize=50,
                max_retries=0,
            )
        )

        session.mount(
            "https://",
            adapter,
        )

        session.mount(
            "http://",
            adapter,
        )

        _thread_local.session = session

    return session


def _request_json(
    url,
    params=None,
    name="SPX API",
    headers=None,
):
    session = _get_session()

    request_headers = (
        headers
        if isinstance(
            headers,
            dict,
        )
        else get_headers()
    )

    response = session.get(
        url,
        headers=request_headers,
        params=params or {},
        timeout=30,
    )

    if response.status_code == 401:
        with _auth_lock:
            refreshed_headers = (
                get_headers(
                    force_refresh=True
                )
            )

        response = session.get(
            url,
            headers=refreshed_headers,
            params=params or {},
            timeout=30,
        )

    response.raise_for_status()

    try:
        data = response.json()

    except Exception as e:
        raise RuntimeError(
            f"{name}: "
            f"response không phải JSON: {e}"
        )

    if isinstance(
        data,
        dict,
    ):
        retcode = data.get(
            "retcode"
        )

        if retcode not in (
            None,
            0,
            "0",
        ):
            raise RuntimeError(
                f"{name}: "
                f"{data.get('message', 'Unknown SPX error')}"
            )

    return data


def get_pickup_switches(
    station_id,
    headers=None,
):
    return _request_json(
        PICKUP_SWITCH_API,
        params={
            "station_id":
                station_id,
        },
        name=
            "pickup switches",
        headers=
            headers,
    )


def get_recipient_info(
    shipment_id,
    station_type=2,
    headers=None,
):
    shipment_id = (
        _normalize_shipment_id(
            shipment_id
        )
    )

    return _request_json(
        RECIPIENT_INFO_API,
        params={
            "shipment_id":
                shipment_id,

            "station_type":
                station_type,
        },
        name=
            "recipient info",
        headers=
            headers,
    )


def get_tracking_info(
    shipment_id,
    headers=None,
):
    shipment_id = (
        _normalize_shipment_id(
            shipment_id
        )
    )

    return _request_json(
        TRACKING_INFO_API,
        params={
            "shipment_id":
                shipment_id,
        },
        name=
            "tracking info",
        headers=
            headers,
    )


def get_trade_info(
    shipment_id,
    headers=None,
):
    shipment_id = (
        _normalize_shipment_id(
            shipment_id
        )
    )

    return _request_json(
        TRADE_INFO_API,
        params={
            "shipment_id":
                shipment_id,
        },
        name=
            "trade info",
        headers=
            headers,
    )


def check_order(
    shipment_id,
    station_id=None,
    station_type=2,
):
    shipment_id = (
        _normalize_shipment_id(
            shipment_id
        )
    )

    if not shipment_id:
        raise RuntimeError(
            "shipment_id rỗng"
        )

    headers = get_headers()

    with ThreadPoolExecutor(
        max_workers=(
            4
            if station_id is not None
            else 3
        )
    ) as executor:

        future_tracking = (
            executor.submit(
                get_tracking_info,
                shipment_id,
                headers,
            )
        )

        future_recipient = (
            executor.submit(
                get_recipient_info,
                shipment_id,
                station_type,
                headers,
            )
        )

        future_trade = (
            executor.submit(
                get_trade_info,
                shipment_id,
                headers,
            )
        )

        future_pickup = None

        if station_id is not None:
            future_pickup = (
                executor.submit(
                    get_pickup_switches,
                    station_id,
                    headers,
                )
            )

        result = {
            "shipment_id":
                shipment_id,

            "tracking_info":
                future_tracking.result(),

            "recipient_info":
                future_recipient.result(),

            "trade_info":
                future_trade.result(),
        }

        if future_pickup is not None:
            result[
                "pickup_switches"
            ] = (
                future_pickup.result()
            )

    return result


def check_orders(
    shipment_ids,
    station_id=None,
    station_type=2,
    max_workers=20,
):
    if not isinstance(
        shipment_ids,
        (
            list,
            tuple,
            set,
        ),
    ):
        return {
            "orders": [],
            "failed": [],
        }

    normalized_ids = []
    seen = set()

    for shipment_id in shipment_ids:
        shipment_id = (
            _normalize_shipment_id(
                shipment_id
            )
        )

        if not shipment_id:
            continue

        if shipment_id in seen:
            continue

        seen.add(
            shipment_id
        )

        normalized_ids.append(
            shipment_id
        )

    if not normalized_ids:
        return {
            "orders": [],
            "failed": [],
        }

    headers = get_headers()

    order_results = {
        shipment_id: {
            "shipment_id":
                shipment_id,

            "tracking_info":
                None,

            "recipient_info":
                None,

            "trade_info":
                None,
        }
        for shipment_id
        in normalized_ids
    }

    if station_id is not None:
        for shipment_id in normalized_ids:
            order_results[
                shipment_id
            ][
                "pickup_switches"
            ] = None

    failed_map = {}

    futures = {}

    worker_count = min(
        max(
            1,
            int(
                max_workers
            ),
        ),
        32,
    )

    with ThreadPoolExecutor(
        max_workers=
            worker_count
    ) as executor:

        for shipment_id in normalized_ids:
            future = executor.submit(
                get_tracking_info,
                shipment_id,
                headers,
            )

            futures[
                future
            ] = (
                shipment_id,
                "tracking_info",
            )

            future = executor.submit(
                get_recipient_info,
                shipment_id,
                station_type,
                headers,
            )

            futures[
                future
            ] = (
                shipment_id,
                "recipient_info",
            )

            future = executor.submit(
                get_trade_info,
                shipment_id,
                headers,
            )

            futures[
                future
            ] = (
                shipment_id,
                "trade_info",
            )

            if station_id is not None:
                future = executor.submit(
                    get_pickup_switches,
                    station_id,
                    headers,
                )

                futures[
                    future
                ] = (
                    shipment_id,
                    "pickup_switches",
                )

        for future in as_completed(
            futures
        ):
            (
                shipment_id,
                field_name,
            ) = futures[
                future
            ]

            try:
                data = future.result()

                order_results[
                    shipment_id
                ][
                    field_name
                ] = data

            except Exception as e:
                if shipment_id not in failed_map:
                    failed_map[
                        shipment_id
                    ] = {
                        "shipment_id":
                            shipment_id,

                        "errors":
                            [],
                    }

                failed_map[
                    shipment_id
                ][
                    "errors"
                ].append({
                    "source":
                        field_name,

                    "error":
                        str(e),
                })

    orders = []
    failed = []

    required_fields = (
        "tracking_info",
        "recipient_info",
        "trade_info",
    )

    for shipment_id in normalized_ids:
        result = order_results[
            shipment_id
        ]

        missing = [
            field
            for field
            in required_fields
            if result.get(
                field
            ) is None
        ]

        if missing:
            failed_item = (
                failed_map.get(
                    shipment_id,
                    {
                        "shipment_id":
                            shipment_id,

                        "errors":
                            [],
                    },
                )
            )

            if not failed_item[
                "errors"
            ]:
                failed_item[
                    "errors"
                ] = [
                    {
                        "source":
                            field,

                        "error":
                            "Không lấy được dữ liệu",
                    }
                    for field
                    in missing
                ]

            failed.append(
                failed_item
            )

            continue

        orders.append(
            result
        )

    return {
        "orders":
            orders,

        "failed":
            failed,

        "total":
            len(
                normalized_ids
            ),

        "success":
            len(
                orders
            ),

        "failed_count":
            len(
                failed
            ),
    }