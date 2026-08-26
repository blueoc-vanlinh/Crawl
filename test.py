import json
import requests

from config import BASE_URL, get_headers


API_PATH = "/api/in-station/cage/packed_history/list"

TEST_SHIPMENT_ID = "SPXVN066003093938"


def main():
    url = f"{BASE_URL}{API_PATH}"

    headers = get_headers()

    payload = {
        "pageno": 1,
        "count": 20,
        "mapping_item_number": TEST_SHIPMENT_ID,
        "scan_time_begin": 1786464000,
        "scan_time_end": 1786550399,
    }

    print("=" * 80)
    print("URL:")
    print(url)
    print("=" * 80)

    print("METHOD:")
    print("POST")
    print("=" * 80)

    print("PAYLOAD:")
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )
    print("=" * 80)

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print("HTTP STATUS:")
    print(response.status_code)
    print("=" * 80)

    print("CONTENT-TYPE:")
    print(response.headers.get("Content-Type"))
    print("=" * 80)

    print("RAW RESPONSE:")
    print(response.text)
    print("=" * 80)

    response.raise_for_status()

    try:
        data = response.json()
    except Exception:
        print("Response không phải JSON")
        return

    print("JSON RESPONSE:")
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
    )

    items = (
        data
        .get("data", {})
        .get("list", [])
    )

    print("=" * 80)
    print(f"FOUND: {len(items)}")

    for index, item in enumerate(
        items,
        start=1,
    ):
        print("=" * 80)
        print(f"ITEM {index}")

        print(
            "mapping_item_number:",
            item.get("mapping_item_number"),
        )

        print(
            "cage_id:",
            item.get("cage_id"),
        )

        print(
            "cage_name:",
            item.get("cage_name"),
        )

        print(
            "mapping_item_scan_time:",
            item.get("mapping_item_scan_time"),
        )

        print(
            "cage_packing_start_time:",
            item.get("cage_packing_start_time"),
        )

        print(
            "cage_packed_time:",
            item.get("cage_packed_time"),
        )

        print(
            "detach_time:",
            item.get("detach_time"),
        )

        print(
            "operator:",
            item.get("operator"),
        )

        print(
            "station_id:",
            item.get("station_id"),
        )


if __name__ == "__main__":
    main()