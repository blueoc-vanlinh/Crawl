import threading

import requests

from config import get_headers


_refresh_lock = threading.Lock()


def spx_get(
    url,
    params=None,
    timeout=30,
):
    response = requests.get(
        url,
        headers=get_headers(),
        params=params or {},
        timeout=timeout,
    )

    if response.status_code != 401:
        response.raise_for_status()
        return response

    with _refresh_lock:
        response = requests.get(
            url,
            headers=get_headers(
                force_refresh=True
            ),
            params=params or {},
            timeout=timeout,
        )

    response.raise_for_status()

    return response