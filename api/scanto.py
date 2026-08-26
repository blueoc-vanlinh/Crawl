from config import BASE_URL
from core.spx_request import spx_get


TO_ORDER_API = (
    BASE_URL
    + "/api/in-station/general_to/outbound/order/search"
)


def scan_to_orders(
    to_number,
    count=10000,
):
    to_number = str(
        to_number or ""
    ).strip().upper()

    if not to_number:
        raise RuntimeError(
            "TO number rỗng"
        )

    if count is None:
        count = 10000

    try:
        count = int(
            count
        )
    except (
        TypeError,
        ValueError,
    ):
        count = 10000

    if count < 1:
        count = 10000

    all_items = []

    page = 1
    total = 0

    while True:
        response = spx_get(
            TO_ORDER_API,
            params={
                "to_number":
                    to_number,

                "pageno":
                    page,

                "count":
                    count,
            },
            timeout=60,
        )

        payload = response.json()

        if not isinstance(
            payload,
            dict
        ):
            raise RuntimeError(
                "Scan TO response không hợp lệ"
            )

        retcode = payload.get(
            "retcode"
        )

        if (
            retcode is not None
            and retcode != 0
        ):
            raise RuntimeError(
                payload.get(
                    "message",
                    "Scan TO error",
                )
            )

        data = payload.get(
            "data",
            {}
        )

        if not isinstance(
            data,
            dict
        ):
            data = {}

        items = data.get(
            "list",
            []
        )

        if not isinstance(
            items,
            list
        ):
            items = []

        try:
            total = int(
                data.get(
                    "total",
                    0
                )
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            total = 0

        if not items:
            break

        all_items.extend(
            items
        )

        if (
            total
            and len(
                all_items
            ) >= total
        ):
            break

        if len(
            items
        ) < count:
            break

        page += 1

    unique_items = []

    seen = set()

    for item in all_items:
        if not isinstance(
            item,
            dict
        ):
            continue

        shipment_id = str(
            item.get(
                "shipment_id"
            )
            or item.get(
                "fleet_order_id"
            )
            or ""
        ).strip().upper()

        if not shipment_id:
            continue

        key = (
            to_number,
            shipment_id,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique_items.append(
            item
        )

    return {
        "retcode":
            0,

        "message":
            "Success",

        "data": {
            "to_number":
                to_number,

            "total":
                total
                if total
                else len(
                    unique_items
                ),

            "crawled":
                len(
                    unique_items
                ),

            "list":
                unique_items,
        },
    }


def get_to_order_items(
    to_number,
    count=10000,
):
    result = scan_to_orders(
        to_number=
            to_number,

        count=
            count,
    )

    return (
        result
        .get(
            "data",
            {}
        )
        .get(
            "list",
            []
        )
    )


def get_to_shipment_ids(
    to_number,
    count=10000,
):
    items = get_to_order_items(
        to_number=
            to_number,

        count=
            count,
    )

    shipment_ids = []

    seen = set()

    for item in items:
        if not isinstance(
            item,
            dict
        ):
            continue

        shipment_id = str(
            item.get(
                "shipment_id"
            )
            or item.get(
                "fleet_order_id"
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

    return shipment_ids