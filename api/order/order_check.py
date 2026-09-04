import json
import os
import threading
import time

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

import requests

from config import BASE_URL
from core.spx_request import spx_get


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


CHECKPOINT_FILE = os.getenv(
    "SPX_ORDER_CHECKPOINT_FILE",
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "order_check_checkpoint.json",
    ),
)

_refresh_lock = threading.Lock()
_checkpoint_lock = threading.Lock()
_auth_generation = 0


def _normalize_shipment_id(
    shipment_id,
):
    return str(
        shipment_id
        or ""
    ).strip().upper()


def _response_error_body(
    response,
):
    if response is None:
        return ""

    try:
        return response.text[:2000]
    except Exception:
        return ""


def _is_login_invalid_response(
    response,
):
    if response is None:
        return False

    if response.status_code not in (
        401,
        403,
    ):
        return False

    try:
        data = response.json()

        if isinstance(
            data,
            dict,
        ):
            if data.get(
                "is_login"
            ) is False:
                return True

            if data.get(
                "error"
            ) == 90309999:
                return True

    except Exception:
        pass

    body = _response_error_body(
        response
    ).replace(
        " ",
        "",
    ).lower()

    return (
        '"is_login":false'
        in body
        or '"error":90309999'
        in body
    )


def _request_json(
    url,
    params=None,
    name="SPX API",
    retries=1,
):
    global _auth_generation

    last_error = None

    for attempt in range(
        retries + 1
    ):
        request_auth_generation = (
            _auth_generation
        )

        try:
            response = spx_get(
                url,
                params=params or {},
                timeout=30,
            )

            data = response.json()

            if not isinstance(
                data,
                dict,
            ):
                raise RuntimeError(
                    f"{name}: "
                    f"response không phải dict"
                )

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

        except requests.HTTPError as exc:
            last_error = exc

            response = getattr(
                exc,
                "response",
                None,
            )

            status_code = (
                response.status_code
                if response is not None
                else None
            )

            body = _response_error_body(
                response
            )

            print(
                f"[{name}] "
                f"HTTP={status_code} "
                f"attempt={attempt + 1}/"
                f"{retries + 1}"
            )

            if body:
                print(
                    f"[{name}] "
                    f"BODY={body}"
                )

            login_invalid = (
                _is_login_invalid_response(
                    response
                )
            )

            if (
                status_code
                in (
                    401,
                    403,
                )
                and attempt < retries
            ):
                if login_invalid:
                    with _refresh_lock:
                        if (
                            request_auth_generation
                            == _auth_generation
                        ):
                            print(
                                f"[{name}] "
                                f"SPX session bị coi là logout, "
                                f"refresh auth"
                            )

                            try:
                                from config import get_headers

                                get_headers(
                                    force_refresh=True
                                )

                                _auth_generation += 1

                                print(
                                    f"[{name}] "
                                    f"refresh auth OK "
                                    f"generation="
                                    f"{_auth_generation}"
                                )

                            except Exception as refresh_error:
                                print(
                                    f"[{name}] "
                                    f"AUTH REFRESH ERROR: "
                                    f"{refresh_error}"
                                )
                                raise

                        else:
                            print(
                                f"[{name}] "
                                f"auth đã được thread khác "
                                f"refresh, retry luôn"
                            )

                time.sleep(
                    1.0
                )

                continue

            raise RuntimeError(
                f"{name}: "
                f"HTTP {status_code} "
                f"{body}"
            ) from exc

        except Exception as exc:
            last_error = exc

            print(
                f"[{name}] "
                f"ERROR={exc}"
            )

            raise

    raise RuntimeError(
        f"{name}: {last_error}"
    )


def get_pickup_switches(
    station_id,
):
    if station_id in (
        None,
        "",
    ):
        return {}

    return _request_json(
        PICKUP_SWITCH_API,
        params={
            "station_id":
                station_id,
        },
        name=
            "pickup switches",
        retries=
            1,
    )


def get_recipient_info(
    shipment_id,
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

    return _request_json(
        RECIPIENT_INFO_API,
        params={
            "shipment_id":
                shipment_id,
            "station_type":
                station_type,
        },
        name=
            f"recipient info "
            f"{shipment_id}",
        retries=
            1,
    )


def get_tracking_info(
    shipment_id,
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

    return _request_json(
        TRACKING_INFO_API,
        params={
            "shipment_id":
                shipment_id,
        },
        name=
            f"tracking info "
            f"{shipment_id}",
        retries=
            1,
    )


def get_trade_info(
    shipment_id,
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

    return _request_json(
        TRADE_INFO_API,
        params={
            "shipment_id":
                shipment_id,
        },
        name=
            f"trade info "
            f"{shipment_id}",
        retries=
            1,
    )


def _safe_api_call(
    function,
    source_name,
    shipment_id,
    *args,
):
    try:
        data = function(
            shipment_id,
            *args,
        )

        return {
            "success":
                True,
            "source":
                source_name,
            "data":
                data,
            "error":
                "",
        }

    except Exception as exc:
        print(
            f"[ORDER API ERROR] "
            f"{shipment_id} "
            f"{source_name} "
            f"=> {exc}"
        )

        return {
            "success":
                False,
            "source":
                source_name,
            "data":
                {},
            "error":
                str(exc),
        }


def _empty_order_result(
    shipment_id,
):
    return {
        "shipment_id":
            shipment_id,
        "tracking_info":
            {},
        "recipient_info":
            {},
        "trade_info":
            {},
        "_api_errors":
            [],
    }


def _error_map(
    result,
):
    errors = {}

    for item in (
        result.get(
            "_api_errors"
        )
        or []
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        source = str(
            item.get(
                "source",
                "",
            )
        ).strip()

        if not source:
            continue

        errors[source] = str(
            item.get(
                "error",
                "",
            )
        )

    return errors


def _set_api_result(
    result,
    api_result,
):
    source = api_result.get(
        "source"
    )

    key_map = {
        "tracking_info":
            "tracking_info",
        "recipient_info":
            "recipient_info",
        "trade_info":
            "trade_info",
    }

    data_key = key_map.get(
        source
    )

    errors = _error_map(
        result
    )

    if api_result.get(
        "success"
    ):
        if data_key:
            result[
                data_key
            ] = (
                api_result.get(
                    "data"
                )
                or {}
            )

        errors.pop(
            source,
            None,
        )

    else:
        errors[
            source
        ] = str(
            api_result.get(
                "error",
                "",
            )
        )

    result[
        "_api_errors"
    ] = [
        {
            "source": source_name,
            "error": error_text,
        }
        for source_name, error_text
        in errors.items()
    ]


def _needs_api(
    result,
    source,
):
    key_map = {
        "tracking_info":
            "tracking_info",
        "recipient_info":
            "recipient_info",
        "trade_info":
            "trade_info",
    }

    data_key = key_map[
        source
    ]

    if not result.get(
        data_key
    ):
        return True

    errors = _error_map(
        result
    )

    return source in errors


def _is_complete_result(
    result,
    station_id=None,
):
    if not isinstance(
        result,
        dict,
    ):
        return False

    required = (
        "tracking_info",
        "recipient_info",
        "trade_info",
    )

    for key in required:
        if not result.get(
            key
        ):
            return False

    errors = _error_map(
        result
    )

    for source in required:
        if source in errors:
            return False

    if station_id is not None:
        if "pickup_switches" not in result:
            return False

        if "pickup_switches" in errors:
            return False

    return True


def _has_any_order_data(
    result,
):
    return bool(
        result.get(
            "tracking_info"
        )
        or result.get(
            "recipient_info"
        )
        or result.get(
            "trade_info"
        )
    )


def check_order(
    shipment_id,
    station_id=None,
    station_type=2,
    existing_result=None,
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

    if isinstance(
        existing_result,
        dict,
    ):
        result = dict(
            existing_result
        )

        result[
            "shipment_id"
        ] = shipment_id

        result.setdefault(
            "tracking_info",
            {},
        )

        result.setdefault(
            "recipient_info",
            {},
        )

        result.setdefault(
            "trade_info",
            {},
        )

        result.setdefault(
            "_api_errors",
            [],
        )

    else:
        result = (
            _empty_order_result(
                shipment_id
            )
        )

    if _needs_api(
        result,
        "tracking_info",
    ):
        tracking_result = (
            _safe_api_call(
                get_tracking_info,
                "tracking_info",
                shipment_id,
            )
        )

        _set_api_result(
            result,
            tracking_result,
        )

    if _needs_api(
        result,
        "recipient_info",
    ):
        recipient_result = (
            _safe_api_call(
                get_recipient_info,
                "recipient_info",
                shipment_id,
                station_type,
            )
        )

        _set_api_result(
            result,
            recipient_result,
        )

    if _needs_api(
        result,
        "trade_info",
    ):
        trade_result = (
            _safe_api_call(
                get_trade_info,
                "trade_info",
                shipment_id,
            )
        )

        _set_api_result(
            result,
            trade_result,
        )

    if station_id is not None:
        pickup_errors = _error_map(
            result
        )

        need_pickup = (
            "pickup_switches"
            not in result
            or "pickup_switches"
            in pickup_errors
        )

        if need_pickup:
            try:
                result[
                    "pickup_switches"
                ] = (
                    get_pickup_switches(
                        station_id
                    )
                )

                pickup_errors.pop(
                    "pickup_switches",
                    None,
                )

            except Exception as exc:
                result[
                    "pickup_switches"
                ] = {}

                pickup_errors[
                    "pickup_switches"
                ] = str(
                    exc
                )

            result[
                "_api_errors"
            ] = [
                {
                    "source":
                        source_name,
                    "error":
                        error_text,
                }
                for source_name, error_text
                in pickup_errors.items()
            ]

    if not _has_any_order_data(
        result
    ):
        errors = (
            result.get(
                "_api_errors"
            )
            or []
        )

        error_text = " | ".join(
            str(
                item.get(
                    "error",
                    "",
                )
            )
            for item in errors
            if isinstance(
                item,
                dict,
            )
        )

        raise RuntimeError(
            f"Không lấy được dữ liệu "
            f"order {shipment_id}: "
            f"{error_text}"
        )

    return result


def _load_checkpoint():
    with _checkpoint_lock:
        if not os.path.exists(
            CHECKPOINT_FILE
        ):
            return {
                "orders": {},
                "failed": {},
            }

        try:
            with open(
                CHECKPOINT_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(
                    file
                )

            if not isinstance(
                data,
                dict,
            ):
                return {
                    "orders": {},
                    "failed": {},
                }

            orders = data.get(
                "orders"
            )

            failed = data.get(
                "failed"
            )

            if not isinstance(
                orders,
                dict,
            ):
                orders = {}

            if not isinstance(
                failed,
                dict,
            ):
                failed = {}

            return {
                "orders":
                    orders,
                "failed":
                    failed,
            }

        except Exception as exc:
            print(
                f"[ORDER CHECKPOINT] "
                f"read error => {exc}"
            )

            return {
                "orders": {},
                "failed": {},
            }


def _save_checkpoint(
    checkpoint,
):
    with _checkpoint_lock:
        directory = os.path.dirname(
            CHECKPOINT_FILE
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True,
            )

        temp_file = (
            CHECKPOINT_FILE
            + ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                checkpoint,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temp_file,
            CHECKPOINT_FILE,
        )


def _checkpoint_order(
    checkpoint,
    shipment_id,
    result,
    station_id=None,
):
    checkpoint[
        "orders"
    ][
        shipment_id
    ] = {
        "updated_at":
            time.time(),
        "complete":
            _is_complete_result(
                result,
                station_id=
                    station_id,
            ),
        "data":
            result,
    }

    checkpoint[
        "failed"
    ].pop(
        shipment_id,
        None,
    )

    _save_checkpoint(
        checkpoint
    )


def _checkpoint_failure(
    checkpoint,
    shipment_id,
    error,
):
    checkpoint[
        "failed"
    ][
        shipment_id
    ] = {
        "updated_at":
            time.time(),
        "error":
            str(
                error
            ),
    }

    _save_checkpoint(
        checkpoint
    )


def clear_order_checkpoint(
    shipment_ids=None,
):
    if shipment_ids is None:
        with _checkpoint_lock:
            if os.path.exists(
                CHECKPOINT_FILE
            ):
                os.remove(
                    CHECKPOINT_FILE
                )

        return

    if not isinstance(
        shipment_ids,
        (
            list,
            tuple,
            set,
        ),
    ):
        shipment_ids = [
            shipment_ids
        ]

    checkpoint = (
        _load_checkpoint()
    )

    for shipment_id in shipment_ids:
        shipment_id = (
            _normalize_shipment_id(
                shipment_id
            )
        )

        if not shipment_id:
            continue

        checkpoint[
            "orders"
        ].pop(
            shipment_id,
            None,
        )

        checkpoint[
            "failed"
        ].pop(
            shipment_id,
            None,
        )

    _save_checkpoint(
        checkpoint
    )


def _get_cached_result(
    checkpoint,
    shipment_id,
):
    entry = (
        checkpoint.get(
            "orders",
            {},
        ).get(
            shipment_id
        )
    )

    if not isinstance(
        entry,
        dict,
    ):
        return None

    data = entry.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    return data


def _run_order_batch(
    shipment_ids,
    checkpoint,
    station_id,
    station_type,
    worker_count,
    force=False,
    label="ORDER",
):
    results = {}
    failures = {}

    def run_one(
        shipment_id,
    ):
        existing_result = None

        if not force:
            existing_result = (
                _get_cached_result(
                    checkpoint,
                    shipment_id,
                )
            )

            if (
                existing_result
                and _is_complete_result(
                    existing_result,
                    station_id=
                        station_id,
                )
            ):
                return (
                    shipment_id,
                    existing_result,
                    True,
                )

        result = check_order(
            shipment_id,
            station_id,
            station_type,
            existing_result=
                existing_result,
        )

        return (
            shipment_id,
            result,
            False,
        )

    with ThreadPoolExecutor(
        max_workers=
            worker_count
    ) as executor:

        future_map = {
            executor.submit(
                run_one,
                shipment_id,
            ):
                shipment_id

            for shipment_id
            in shipment_ids
        }

        completed = 0

        for future in as_completed(
            future_map
        ):
            shipment_id = (
                future_map[
                    future
                ]
            )

            completed += 1

            try:
                (
                    _,
                    result,
                    from_cache,
                ) = future.result()

                results[
                    shipment_id
                ] = result

                _checkpoint_order(
                    checkpoint,
                    shipment_id,
                    result,
                    station_id=
                        station_id,
                )

                complete = (
                    _is_complete_result(
                        result,
                        station_id=
                            station_id,
                    )
                )

                if from_cache:
                    state = "CACHED"

                elif complete:
                    state = "OK"

                else:
                    state = "PARTIAL"

                print(
                    f"[{label} "
                    f"{completed}/"
                    f"{len(shipment_ids)}] "
                    f"{state} "
                    f"{shipment_id}"
                )

            except Exception as exc:
                failures[
                    shipment_id
                ] = str(
                    exc
                )

                _checkpoint_failure(
                    checkpoint,
                    shipment_id,
                    exc,
                )

                print(
                    f"[{label} "
                    f"{completed}/"
                    f"{len(shipment_ids)}] "
                    f"ERROR "
                    f"{shipment_id} "
                    f"=> {exc}"
                )

    return (
        results,
        failures,
    )


def check_orders(
    shipment_ids,
    station_id=None,
    station_type=2,
    max_workers=3,
    retry_rounds=1,
    retry_cooldown_seconds=15,
    force=False,
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
            "total": 0,
            "success": 0,
            "complete_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "cached_count": 0,
            "checkpoint_file":
                CHECKPOINT_FILE,
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
            "total": 0,
            "success": 0,
            "complete_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "cached_count": 0,
            "checkpoint_file":
                CHECKPOINT_FILE,
        }

    try:
        worker_count = int(
            max_workers
        )

    except (
        TypeError,
        ValueError,
    ):
        worker_count = 3

    worker_count = max(
        1,
        min(
            worker_count,
            3,
        ),
    )

    try:
        retry_rounds = int(
            retry_rounds
        )

    except (
        TypeError,
        ValueError,
    ):
        retry_rounds = 1

    retry_rounds = max(
        0,
        min(
            retry_rounds,
            3,
        ),
    )

    try:
        retry_cooldown_seconds = float(
            retry_cooldown_seconds
        )

    except (
        TypeError,
        ValueError,
    ):
        retry_cooldown_seconds = 15.0

    retry_cooldown_seconds = max(
        0.0,
        retry_cooldown_seconds,
    )

    checkpoint = (
        _load_checkpoint()
    )

    cached_count = 0

    if not force:
        for shipment_id in normalized_ids:
            cached_result = (
                _get_cached_result(
                    checkpoint,
                    shipment_id,
                )
            )

            if (
                cached_result
                and _is_complete_result(
                    cached_result,
                    station_id=
                        station_id,
                )
            ):
                cached_count += 1

    print(
        f"[ORDER CHECK] "
        f"total={len(normalized_ids)} "
        f"workers={worker_count} "
        f"cached={cached_count} "
        f"retry_rounds={retry_rounds}"
    )

    results, failures = (
        _run_order_batch(
            normalized_ids,
            checkpoint,
            station_id,
            station_type,
            worker_count,
            force=
                force,
            label=
                "ORDER",
        )
    )

    for retry_round in range(
        1,
        retry_rounds + 1,
    ):
        retry_ids = []

        for shipment_id in normalized_ids:
            result = results.get(
                shipment_id
            )

            if result is None:
                cached_result = (
                    _get_cached_result(
                        checkpoint,
                        shipment_id,
                    )
                )

                if cached_result:
                    result = (
                        cached_result
                    )

                    results[
                        shipment_id
                    ] = (
                        cached_result
                    )

            if (
                result is None
                or not _is_complete_result(
                    result,
                    station_id=
                        station_id,
                )
            ):
                retry_ids.append(
                    shipment_id
                )

        if not retry_ids:
            break

        print(
            f"[ORDER RETRY] "
            f"round={retry_round}/"
            f"{retry_rounds} "
            f"pending={len(retry_ids)} "
            f"cooldown="
            f"{retry_cooldown_seconds:.0f}s"
        )

        if (
            retry_cooldown_seconds
            > 0
        ):
            time.sleep(
                retry_cooldown_seconds
            )

        (
            retry_results,
            retry_failures,
        ) = (
            _run_order_batch(
                retry_ids,
                checkpoint,
                station_id,
                station_type,
                1,
                force=False,
                label=
                    f"RETRY "
                    f"{retry_round}",
            )
        )

        results.update(
            retry_results
        )

        for shipment_id in retry_ids:
            if (
                shipment_id
                in retry_results
            ):
                failures.pop(
                    shipment_id,
                    None,
                )

        failures.update(
            retry_failures
        )

    orders = []
    failed = []

    complete_count = 0
    partial_count = 0

    for shipment_id in normalized_ids:
        result = results.get(
            shipment_id
        )

        if result is None:
            result = (
                _get_cached_result(
                    checkpoint,
                    shipment_id,
                )
            )

        if result is not None:
            orders.append(
                result
            )

            if _is_complete_result(
                result,
                station_id=
                    station_id,
            ):
                complete_count += 1

            else:
                partial_count += 1

            continue

        error_text = failures.get(
            shipment_id
        )

        if not error_text:
            failed_entry = (
                checkpoint.get(
                    "failed",
                    {},
                ).get(
                    shipment_id,
                    {},
                )
            )

            if isinstance(
                failed_entry,
                dict,
            ):
                error_text = str(
                    failed_entry.get(
                        "error",
                        "Unknown error",
                    )
                )

        failed.append({
            "shipment_id":
                shipment_id,
            "error":
                error_text
                or "Unknown error",
        })

    orders.sort(
        key=lambda item:
            str(
                item.get(
                    "shipment_id",
                    "",
                )
            )
    )

    failed.sort(
        key=lambda item:
            str(
                item.get(
                    "shipment_id",
                    "",
                )
            )
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
        "complete_count":
            complete_count,
        "partial_count":
            partial_count,
        "failed_count":
            len(
                failed
            ),
        "cached_count":
            cached_count,
        "checkpoint_file":
            CHECKPOINT_FILE,
    }