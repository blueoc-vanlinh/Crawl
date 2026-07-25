import requests

from config import BASE_URL, HEADERS

TRACKING_API = BASE_URL + "/api/fleet_order/order/detail/tracking_info"


def get_tracking(shipment_id):
    """
    Lấy tracking của 1 shipment
    """

    params = {
        "shipment_id": shipment_id
    }

    r = requests.get(
        TRACKING_API,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    if data["retcode"] != 0:
        raise Exception(data["message"])

    return data