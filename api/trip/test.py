from __future__ import annotations

from config import BASE_URL
from core.spx_request import spx_get


MTIME_START = 1788195600
MTIME_END = 1788281999

COUNT = 100


def get_page(
    page_no: int,
) -> dict:
    url = (
        BASE_URL
        + "/api/admin/transportation/"
        "trip/history/list"
    )

    response = spx_get(
        url,
        params={
            "mtime":
                f"{MTIME_START},"
                f"{MTIME_END}",
            "pageno":
                page_no,
            "count":
                COUNT,
        },
        timeout=60,
    )

    return response.json()


def main():
    first = get_page(1)

    data = first.get(
        "data",
        {},
    )

    total = int(
        data.get(
            "total",
            0,
        )
        or 0
    )

    total_pages = (
        total
        + COUNT
        - 1
    ) // COUNT

    trips = []

    for page_no in range(
        1,
        total_pages + 1,
    ):
        payload = (
            first
            if page_no == 1
            else get_page(
                page_no
            )
        )

        rows = (
            payload.get(
                "data",
                {},
            ).get(
                "list",
                [],
            )
            or []
        )

        trips.extend(
            rows
        )

        print(
            f"PAGE {page_no}/{total_pages} "
            f"| rows={len(rows)} "
            f"| collected={len(trips)}"
        )

    status_count = {}

    for trip in trips:
        status = trip.get(
            "trip_status"
        )

        status_count[
            status
        ] = (
            status_count.get(
                status,
                0,
            )
            + 1
        )

    print()
    print("=" * 70)
    print(
        "SERVER TOTAL:",
        total,
    )
    print(
        "COLLECTED:",
        len(trips),
    )
    print()
    print(
        "TRIP STATUS COUNT:"
    )

    for status, count in sorted(
        status_count.items(),
        key=lambda x: str(
            x[0]
        ),
    ):
        print(
            f"status={status}: "
            f"{count}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()