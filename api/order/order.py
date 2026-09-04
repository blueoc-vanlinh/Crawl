from core.client import FMSClient

client = FMSClient()


def pending(
    current_station,
    next_station,
    status,
):
    payload = {
        "order_status": status,
        "count": 24,
        "current_station_ids": current_station,
        "next_station_ids": next_station,
        "page_no": 1,
    }

    try:
        return client.post(
            "/api/fleet_order/order/tracking_list/search",
            payload,
        )

    except Exception as exc:
        print(
            "[PENDING ERROR]",
            repr(exc),
        )

        response = getattr(
            exc,
            "response",
            None,
        )

        if response is not None:
            print(
                "STATUS:",
                response.status_code,
            )

            print(
                "URL:",
                response.url,
            )

            print(
                "RESPONSE:",
                response.text[:3000],
            )

        raise