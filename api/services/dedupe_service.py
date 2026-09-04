def get_trip_key(
    trip,
):
    trip_id = (
        trip.get("id")
        or trip.get("trip_id")
    )

    if trip_id:
        return f"ID:{trip_id}"

    trip_number = str(
        trip.get(
            "trip_number",
            "",
        )
        or ""
    ).strip().upper()

    if trip_number:
        return f"NUMBER:{trip_number}"

    return None


def dedupe_trips(
    trips,
):
    result = []
    index = {}

    for trip in trips:
        if not isinstance(
            trip,
            dict,
        ):
            continue

        key = get_trip_key(
            trip
        )

        if not key:
            continue

        if key not in index:
            index[key] = len(result)
            result.append(
                dict(trip)
            )
            continue

        current = result[
            index[key]
        ]

        current_source = str(
            current.get(
                "_trip_source",
                "",
            )
            or ""
        )

        incoming_source = str(
            trip.get(
                "_trip_source",
                "",
            )
            or ""
        )

        sources = []

        for source in (
            current_source.split("+")
            + incoming_source.split("+")
        ):
            source = source.strip()

            if (
                source
                and source not in sources
            ):
                sources.append(
                    source
                )

        if sources:
            current[
                "_trip_source"
            ] = "+".join(
                sources
            )

        for field, value in trip.items():
            if field == "_trip_source":
                continue

            if (
                value is None
                or value == ""
            ):
                continue

            current[field] = value

    return result