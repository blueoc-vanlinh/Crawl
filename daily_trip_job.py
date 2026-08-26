from api.daily_trip_sync import (
    sync_two_day_trips,
)


def main():
    result = (
        sync_two_day_trips(
            target_date=None,
            trip_wait_seconds=0,
            max_workers=5,
        )
    )

    print()
    print(
        "=" * 80
    )

    print(
        "TOTAL:",
        result.get(
            "total_trips",
            0,
        ),
    )

    print(
        "SUCCESS:",
        result.get(
            "success_count",
            0,
        ),
    )

    print(
        "FAILED:",
        result.get(
            "failed_count",
            0,
        ),
    )

    print(
        "LOADING:",
        result.get(
            "loading_count",
            0,
        ),
    )

    print(
        "TO BY TRIP:",
        result.get(
            "to_count",
            0,
        ),
    )

    print(
        "TO UNIQUE GLOBAL:",
        result.get(
            "scan_to_cache_size",
            0,
        ),
    )

    print(
        "TO API CALLS:",
        result.get(
            "scan_to_api_calls",
            0,
        ),
    )

    print(
        "TO CACHE HITS:",
        result.get(
            "scan_to_cache_hits",
            0,
        ),
    )

    print(
        "BULKY:",
        result.get(
            "bulky_count",
            0,
        ),
    )

    print(
        "SCAN TO ROWS:",
        result.get(
            "scan_to_rows",
            0,
        ),
    )

    print(
        "ORDER CANDIDATES:",
        result.get(
            "order_candidates",
            0,
        ),
    )

    print(
        "ORDER CRAWL:",
        result.get(
            "order_crawl",
            False,
        ),
    )

    print(
        "WORKERS:",
        result.get(
            "max_workers",
            0,
        ),
    )

    print(
        "ELAPSED:",
        result.get(
            "elapsed_seconds",
            0,
        ),
        "seconds",
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()