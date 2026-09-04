import threading

import requests

from config import get_headers


_session = requests.Session()
_session_lock = threading.Lock()
_refresh_lock = threading.Lock()


def _apply_headers(
    force_refresh=False,
):
    headers = get_headers(
        force_refresh=
            force_refresh
    )

    if not headers:
        raise RuntimeError(
            "Không lấy được SPX headers"
        )

    if not headers.get(
        "Cookie"
    ):
        raise RuntimeError(
            "SPX headers thiếu Cookie"
        )

    if not headers.get(
        "X-Csrftoken"
    ):
        raise RuntimeError(
            "SPX headers thiếu X-Csrftoken"
        )

    return headers


def _send_get(
    url,
    params=None,
    timeout=30,
    force_refresh=False,
):
    headers = (
        _apply_headers(
            force_refresh=
                force_refresh
        )
    )

    with _session_lock:
        response = (
            _session.get(
                url,
                headers=
                    headers,
                params=
                    params or {},
                timeout=
                    timeout,
            )
        )

    return response


def spx_get(
    url,
    params=None,
    timeout=30,
):
    response = (
        _send_get(
            url=
                url,
            params=
                params,
            timeout=
                timeout,
            force_refresh=
                False,
        )
    )

    if (
        response.status_code
        not in (
            401,
            403,
        )
    ):
        response.raise_for_status()

        return response

    print(
        "[SPX REQUEST] "
        f"HTTP={response.status_code} "
        "=> refresh auth"
    )

    with _refresh_lock:
        response = (
            _send_get(
                url=
                    url,
                params=
                    params,
                timeout=
                    timeout,
                force_refresh=
                    True,
            )
        )

    if (
        response.status_code
        in (
            401,
            403,
        )
    ):
        body = ""

        try:
            body = (
                response.text
                or ""
            )[:1000]

        except Exception:
            body = ""

        print(
            "[SPX REQUEST] "
            f"RETRY HTTP="
            f"{response.status_code}"
        )

        if body:
            print(
                "[SPX REQUEST] "
                f"BODY={body}"
            )

    response.raise_for_status()

    return response


def reset_spx_session():
    global _session

    with _session_lock:
        try:
            _session.close()

        except Exception:
            pass

        _session = (
            requests.Session()
        )