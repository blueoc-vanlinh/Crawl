import re
from datetime import datetime, timezone, timedelta


VN_TZ = timezone(timedelta(hours=7))

HUNG_YEN_SOC_ID = 3909
HUNG_YEN_SOC_NAME = "Hung Yen SOC"


STATUS_RECEIVED_FORWARD = {
    1,
    8,
    42,
}

STATUS_PACKING_FORWARD = {
    9,
    43,
}

STATUS_PACKED_FORWARD = {
    33,
    44,
}

STATUS_LH_PACKING_FORWARD = {
    34,
    45,
}

STATUS_LH_PACKED_FORWARD = {
    35,
    46,
}

STATUS_LH_TRANSPORTING_FORWARD = {
    15,
    47,
}

STATUS_LH_TRANSPORTED_FORWARD = {
    36,
    48,
}

STATUS_LH_ARRIVED_FORWARD = {
    880,
    882,
}

STATUS_LH_UNLOADING_FORWARD = {
    918,
    920,
}

STATUS_LH_UNLOADED_FORWARD = {
    928,
    930,
}


STATUS_ASSIGNING = {
    49,
}

STATUS_ASSIGNED = {
    50,
}

STATUS_DELIVERING = {
    2,
}

STATUS_DELIVERED = {
    4,
}


STATUS_RETURN_RECEIVED = {
    58,
    67,
}

STATUS_RETURN_PACKING = {
    52,
    59,
    68,
}

STATUS_RETURN_PACKED = {
    53,
    60,
    69,
}

STATUS_RETURN_LH_PACKING = {
    54,
    61,
    70,
}

STATUS_RETURN_LH_PACKED = {
    55,
    62,
    71,
}

STATUS_RETURN_LH_TRANSPORTING = {
    56,
    64,
    235,
}

STATUS_RETURN_LH_TRANSPORTED = {
    57,
    65,
    236,
}

STATUS_RETURN_LH_ARRIVED = {
    884,
    887,
}

STATUS_RETURN_LH_UNLOADING = {
    917,
    919,
}

STATUS_RETURN_LH_UNLOADED = {
    927,
    929,
}

STATUS_RETURN_ASSIGNING = {
    115,
}

STATUS_RETURN_ASSIGNED = {
    116,
}

STATUS_RETURN_TO_SELLER = {
    72,
}

STATUS_RETURNED = {
    73,
}


STATUS_RECEIVED = (
    STATUS_RECEIVED_FORWARD
    | STATUS_RETURN_RECEIVED
)

STATUS_PACKING = (
    STATUS_PACKING_FORWARD
    | STATUS_RETURN_PACKING
)

STATUS_PACKED = (
    STATUS_PACKED_FORWARD
    | STATUS_RETURN_PACKED
)

STATUS_LH_PACKING = (
    STATUS_LH_PACKING_FORWARD
    | STATUS_RETURN_LH_PACKING
)

STATUS_LH_PACKED = (
    STATUS_LH_PACKED_FORWARD
    | STATUS_RETURN_LH_PACKED
)

STATUS_LH_TRANSPORTING = (
    STATUS_LH_TRANSPORTING_FORWARD
    | STATUS_RETURN_LH_TRANSPORTING
)

STATUS_LH_TRANSPORTED = (
    STATUS_LH_TRANSPORTED_FORWARD
    | STATUS_RETURN_LH_TRANSPORTED
)

STATUS_LH_ARRIVED = (
    STATUS_LH_ARRIVED_FORWARD
    | STATUS_RETURN_LH_ARRIVED
)

STATUS_LH_UNLOADING = (
    STATUS_LH_UNLOADING_FORWARD
    | STATUS_RETURN_LH_UNLOADING
)

STATUS_LH_UNLOADED = (
    STATUS_LH_UNLOADED_FORWARD
    | STATUS_RETURN_LH_UNLOADED
)

STATUS_ALL_ASSIGNING = (
    STATUS_ASSIGNING
    | STATUS_RETURN_ASSIGNING
)

STATUS_ALL_ASSIGNED = (
    STATUS_ASSIGNED
    | STATUS_RETURN_ASSIGNED
)


def normalize(value):
    return str(value or "").strip().lower()


def format_timestamp(value):
    if value in (
        None,
        "",
        0,
        "0",
    ):
        return ""

    try:
        ts = float(value)

        if ts > 10_000_000_000:
            ts /= 1000

        if ts < 946684800:
            return ""

        dt = datetime.fromtimestamp(
            ts,
            tz=timezone.utc
        ).astimezone(VN_TZ)

        return dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        OSError,
    ):
        return ""


def get_tracking_data(tracking_response):
    if not isinstance(
        tracking_response,
        dict
    ):
        return {}

    data = tracking_response.get(
        "data",
        tracking_response
    )

    if not isinstance(
        data,
        dict
    ):
        return {}

    return data


def get_tracking_list(tracking_response):
    data = get_tracking_data(
        tracking_response
    )

    tracking_list = data.get(
        "tracking_list",
        []
    )

    if not isinstance(
        tracking_list,
        list
    ):
        return []

    return tracking_list


def flatten_tracking_events(items):
    result = []

    if not isinstance(
        items,
        list
    ):
        return result

    for item in items:
        if not isinstance(
            item,
            dict
        ):
            continue

        result.append(item)

        children = item.get(
            "children",
            []
        )

        if isinstance(
            children,
            list
        ):
            result.extend(
                flatten_tracking_events(
                    children
                )
            )

        event_children = item.get(
            "event_children",
            []
        )

        if isinstance(
            event_children,
            list
        ):
            result.extend(
                flatten_tracking_events(
                    event_children
                )
            )

    return result


def dedupe_events(events):
    result = []
    seen = set()

    for event in events:
        if not isinstance(
            event,
            dict
        ):
            continue

        event_id = event.get(
            "id"
        )

        if event_id not in (
            None,
            "",
            0,
            "0",
        ):
            key = (
                "id",
                str(event_id),
            )

        else:
            key = (
                "fallback",
                str(
                    event.get(
                        "timestamp",
                        ""
                    )
                ),
                str(
                    event.get(
                        "status",
                        ""
                    )
                ),
                str(
                    event.get(
                        "station_id",
                        ""
                    )
                ),
                str(
                    event.get(
                        "message",
                        ""
                    )
                ),
            )

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


def event_timestamp(event):
    try:
        ts = float(
            event.get(
                "timestamp",
                0
            )
        )

        if ts > 10_000_000_000:
            ts /= 1000

        return ts

    except (
        TypeError,
        ValueError,
    ):
        return 0


def event_time_text(event):
    return format_timestamp(
        event.get(
            "timestamp"
        )
    )


def event_status(event):
    try:
        return int(
            event.get(
                "status",
                -1
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return -1


def event_message(event):
    return str(
        event.get(
            "message",
            ""
        )
    ).strip()


def event_station_name(event):
    return str(
        event.get(
            "station_name",
            ""
        )
    ).strip()


def event_station_id(event):
    try:
        return int(
            event.get(
                "station_id",
                0
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def event_tags(event):
    tags = event.get(
        "tags"
    )

    if not isinstance(
        tags,
        list
    ):
        return []

    return [
        normalize(tag)
        for tag in tags
        if tag
    ]


def received_type(event):
    if (
        event_status(event)
        not in STATUS_RECEIVED
    ):
        return ""

    tags = event_tags(event)

    if "single" in tags:
        return "Single"

    if "mass" in tags:
        return "Mass"

    return ""


def is_hung_yen(event):
    if (
        event_station_id(event)
        == HUNG_YEN_SOC_ID
    ):
        return True

    return (
        normalize(
            event_station_name(event)
        )
        ==
        normalize(
            HUNG_YEN_SOC_NAME
        )
    )


def latest_event_by_status(
    events,
    statuses
):
    matches = [
        event
        for event in events
        if event_status(event)
        in statuses
    ]

    if not matches:
        return None

    return max(
        matches,
        key=event_timestamp
    )


def extract_destination(message):
    if not message:
        return ""

    match = re.search(
        r"(?:transporting|transported)"
        r"\s+to\s+\[([^\]]+)\]",
        message,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    return match.group(1).strip()
def extract_to_number(message):
    if not message:
        return ""

    match = re.search(
        r"\[(TO[A-Z0-9]+)\]",
        str(message),
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    return (
        match.group(1)
        .strip()
        .upper()
    )


def extract_trip_number(message):
    if not message:
        return ""

    match = re.search(
        r"\[(LT[A-Z0-9]+)\]",
        str(message),
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    return (
        match.group(1)
        .strip()
        .upper()
    )


def find_latest_hy_to_trip(
    events
):
    hy_events = [
        event
        for event in events
        if is_hung_yen(event)
    ]

    if not hy_events:
        return {
            "to_number": "",
            "trip_number": "",
            "hy_trip_time": "",
        }

    hy_events.sort(
        key=event_timestamp,
        reverse=True
    )

    for event in hy_events:
        message = event_message(
            event
        )

        trip_number = (
            extract_trip_number(
                message
            )
        )

        to_number = (
            extract_to_number(
                message
            )
        )

        if (
            trip_number
            and to_number
        ):
            return {
                "to_number":
                    to_number,

                "trip_number":
                    trip_number,

                "hy_trip_time":
                    event_time_text(
                        event
                    ),
            }

    latest_hy_outbound = None

    for event in hy_events:
        if (
            event_status(event)
            not in STATUS_LH_TRANSPORTING
            | STATUS_LH_TRANSPORTED
            | STATUS_LH_PACKING
            | STATUS_LH_PACKED
        ):
            continue

        message = event_message(
            event
        )

        if (
            extract_to_number(
                message
            )
            or extract_trip_number(
                message
            )
        ):
            latest_hy_outbound = (
                event
            )
            break

    if not latest_hy_outbound:
        return {
            "to_number": "",
            "trip_number": "",
            "hy_trip_time": "",
        }

    anchor_ts = event_timestamp(
        latest_hy_outbound
    )

    to_number = ""
    trip_number = ""

    related_events = sorted(
        hy_events,
        key=lambda event:
            abs(
                event_timestamp(
                    event
                )
                - anchor_ts
            )
    )

    for event in related_events:
        if (
            abs(
                event_timestamp(
                    event
                )
                - anchor_ts
            )
            > 3600
        ):
            continue

        message = event_message(
            event
        )

        if not to_number:
            to_number = (
                extract_to_number(
                    message
                )
            )

        if not trip_number:
            trip_number = (
                extract_trip_number(
                    message
                )
            )

        if (
            to_number
            and trip_number
        ):
            break

    return {
        "to_number":
            to_number,

        "trip_number":
            trip_number,

        "hy_trip_time":
            event_time_text(
                latest_hy_outbound
            ),
    }

def find_hy_outbounds(
    events,
    min_ts=0
):
    result = []

    valid_statuses = (
        STATUS_LH_TRANSPORTING
        | STATUS_LH_TRANSPORTED
    )

    for event in events:
        ts = event_timestamp(event)

        if ts <= min_ts:
            continue

        if not is_hung_yen(event):
            continue

        if (
            event_status(event)
            not in valid_statuses
        ):
            continue

        destination = extract_destination(
            event_message(event)
        )

        if not destination:
            continue

        result.append(
            (
                ts,
                destination,
                event,
            )
        )

    result.sort(
        key=lambda item: item[0]
    )

    return result


def find_first_hub_arrival_for_outbounds(
    events,
    outbounds
):
    for (
        departure_ts,
        destination,
        departure_event,
    ) in reversed(outbounds):

        destination_norm = normalize(
            destination
        )

        matches = []

        for event in events:
            if (
                event_timestamp(event)
                <= departure_ts
            ):
                continue

            if (
                event_status(event)
                not in STATUS_LH_ARRIVED
            ):
                continue

            if (
                normalize(
                    event_station_name(
                        event
                    )
                )
                != destination_norm
            ):
                continue

            matches.append(event)

        if matches:
            arrival = min(
                matches,
                key=event_timestamp
            )

            return {
                "departure_ts":
                    departure_ts,

                "destination":
                    destination,

                "departure_event":
                    departure_event,

                "arrival_event":
                    arrival,

                "arrival_ts":
                    event_timestamp(
                        arrival
                    ),
            }

    return None


def get_destination_state(
    events,
    destination,
    departure_ts
):
    destination_norm = normalize(
        destination
    )

    station_events = []

    for event in events:
        if (
            event_timestamp(event)
            <= departure_ts
        ):
            continue

        if (
            normalize(
                event_station_name(
                    event
                )
            )
            != destination_norm
        ):
            continue

        station_events.append(event)

    lh_arrived = (
        latest_event_by_status(
            station_events,
            STATUS_LH_ARRIVED
        )
    )

    lh_unloading = (
        latest_event_by_status(
            station_events,
            STATUS_LH_UNLOADING
        )
    )

    lh_unloaded = (
        latest_event_by_status(
            station_events,
            STATUS_LH_UNLOADED
        )
    )

    received_events = [
        event
        for event in station_events
        if event_status(event)
        in STATUS_RECEIVED
    ]

    received_event = (
        max(
            received_events,
            key=event_timestamp
        )
        if received_events
        else None
    )

    packing = (
        latest_event_by_status(
            station_events,
            STATUS_PACKING
        )
    )

    packed = (
        latest_event_by_status(
            station_events,
            STATUS_PACKED
        )
    )

    lh_transporting = (
        latest_event_by_status(
            station_events,
            STATUS_LH_TRANSPORTING
        )
    )

    lh_transported = (
        latest_event_by_status(
            station_events,
            STATUS_LH_TRANSPORTED
        )
    )

    return {
        "station_events":
            station_events,

        "lh_arrived":
            lh_arrived,

        "lh_unloading":
            lh_unloading,

        "lh_unloaded":
            lh_unloaded,

        "received_event":
            received_event,

        "packing":
            packing,

        "packed":
            packed,

        "lh_transporting":
            lh_transporting,

        "lh_transported":
            lh_transported,
    }


def fill_destination_fields(
    result,
    state
):
    if state["lh_arrived"]:
        result[
            "lh_arrived_time"
        ] = event_time_text(
            state["lh_arrived"]
        )

    if state["lh_unloading"]:
        result[
            "lh_unloading_time"
        ] = event_time_text(
            state["lh_unloading"]
        )

    if state["lh_unloaded"]:
        result[
            "lh_unloaded_time"
        ] = event_time_text(
            state["lh_unloaded"]
        )

    if state["received_event"]:
        result[
            "received_type"
        ] = received_type(
            state["received_event"]
        )

        result[
            "received_time"
        ] = event_time_text(
            state["received_event"]
        )

    if state["packing"]:
        result[
            "packing_time"
        ] = event_time_text(
            state["packing"]
        )

    if state["packed"]:
        result[
            "packed_time"
        ] = event_time_text(
            state["packed"]
        )

    if state["lh_transporting"]:
        result[
            "lh_transporting_time"
        ] = event_time_text(
            state["lh_transporting"]
        )

    if state["lh_transported"]:
        result[
            "lh_transported_time"
        ] = event_time_text(
            state["lh_transported"]
        )


def positive_reason(event):
    code = event_status(event)

    if code in STATUS_RETURNED:
        return "Returned"

    if code in STATUS_RETURN_TO_SELLER:
        return "Returning to Seller"

    if code in STATUS_DELIVERED:
        return "Delivered"

    if code in STATUS_DELIVERING:
        return "Delivering"

    if code in STATUS_RETURN_ASSIGNED:
        return "Return Assigned"

    if code in STATUS_RETURN_ASSIGNING:
        return "Return Assigning"

    if code in STATUS_ASSIGNED:
        return "Assigned"

    if code in STATUS_ASSIGNING:
        return "Assigning"

    if code in STATUS_RECEIVED:
        rtype = received_type(event)

        if rtype == "Single":
            if (
                code
                in STATUS_RETURN_RECEIVED
            ):
                return (
                    "Return Received Single"
                )

            return "Received Single"

        return ""

    if code in STATUS_RETURN_PACKING:
        return "Return Packing"

    if code in STATUS_RETURN_PACKED:
        return "Return Packed"

    if (
        code
        in STATUS_RETURN_LH_PACKING
    ):
        return "Return LHPacking"

    if (
        code
        in STATUS_RETURN_LH_PACKED
    ):
        return "Return LHPacked"

    if (
        code
        in STATUS_RETURN_LH_TRANSPORTING
    ):
        return "Return LHTransporting"

    if (
        code
        in STATUS_RETURN_LH_TRANSPORTED
    ):
        return "Return LHTransported"

    if code in STATUS_PACKING_FORWARD:
        return "Packing"

    if code in STATUS_PACKED_FORWARD:
        return "Packed"

    if (
        code
        in STATUS_LH_PACKING_FORWARD
    ):
        return "LHPacking"

    if (
        code
        in STATUS_LH_PACKED_FORWARD
    ):
        return "LHPacked"

    if (
        code
        in STATUS_LH_TRANSPORTING_FORWARD
    ):
        return "LHTransporting"

    if (
        code
        in STATUS_LH_TRANSPORTED_FORWARD
    ):
        return "LHTransported"

    return ""


def is_positive_event(event):
    return bool(
        positive_reason(event)
    )


def is_global_positive(event):
    code = event_status(event)

    return (
        code in STATUS_ASSIGNING
        or code in STATUS_ASSIGNED
        or code in STATUS_RETURN_ASSIGNING
        or code in STATUS_RETURN_ASSIGNED
        or code in STATUS_DELIVERING
        or code in STATUS_DELIVERED
        or code in STATUS_RETURN_TO_SELLER
        or code in STATUS_RETURNED
    )


def find_latest_positive_normal(
    events,
    hub_arrival_ts
):
    matches = []

    for event in events:
        if (
            event_timestamp(event)
            <= hub_arrival_ts
        ):
            continue

        if not is_positive_event(event):
            continue

        code = event_status(event)

        if is_hung_yen(event):
            if (
                code in STATUS_RECEIVED
                and received_type(event)
                == "Single"
            ):
                matches.append(event)
                continue

            if code in STATUS_PACKING:
                matches.append(event)
                continue

            if code in STATUS_PACKED:
                matches.append(event)
                continue

            if code in STATUS_LH_PACKING:
                matches.append(event)
                continue

            if code in STATUS_LH_PACKED:
                matches.append(event)
                continue

            if is_global_positive(event):
                matches.append(event)
                continue

            continue

        matches.append(event)

    if not matches:
        return None

    return max(
        matches,
        key=event_timestamp
    )


def find_latest_positive_return(
    events,
    hub_arrival_ts
):
    matches = []

    for event in events:
        if (
            event_timestamp(event)
            <= hub_arrival_ts
        ):
            continue

        if not is_positive_event(event):
            continue

        if (
            is_hung_yen(event)
            and not is_global_positive(
                event
            )
        ):
            continue

        matches.append(event)

    if not matches:
        return None

    return max(
        matches,
        key=event_timestamp
    )


def has_real_return_after_delivered(
    events,
    delivered_ts
):
    return_hy_statuses = (
        STATUS_RETURN_RECEIVED
        | STATUS_RETURN_PACKING
        | STATUS_RETURN_PACKED
        | STATUS_RETURN_LH_PACKING
        | STATUS_RETURN_LH_PACKED
        | STATUS_RETURN_LH_TRANSPORTING
        | STATUS_RETURN_LH_TRANSPORTED
        | STATUS_RETURN_LH_ARRIVED
        | STATUS_RETURN_LH_UNLOADING
        | STATUS_RETURN_LH_UNLOADED
    )

    for event in events:
        if (
            event_timestamp(event)
            <= delivered_ts
        ):
            continue

        if not is_hung_yen(event):
            continue

        if (
            event_status(event)
            in return_hy_statuses
        ):
            return True

    return False


def set_no_reason(
    result,
    state
):
    received_event = state[
        "received_event"
    ]

    if (
        received_event
        and received_type(
            received_event
        )
        == "Mass"
    ):
        result[
            "new_status_reason"
        ] = (
            "Received Mass - "
            "waiting Packing/Packed"
        )

        return

    if state["lh_unloaded"]:
        event = state[
            "lh_unloaded"
        ]

        if (
            event_status(event)
            in STATUS_RETURN_LH_UNLOADED
        ):
            reason = (
                "Return LHUnloaded - "
                "waiting Single/Packing"
            )
        else:
            reason = (
                "LHUnloaded - "
                "waiting Single/Packing"
            )

        result[
            "new_status_reason"
        ] = reason

        return

    if state["lh_unloading"]:
        event = state[
            "lh_unloading"
        ]

        if (
            event_status(event)
            in STATUS_RETURN_LH_UNLOADING
        ):
            reason = (
                "Return LHUnloading - "
                "waiting Single/Packing"
            )
        else:
            reason = (
                "LHUnloading - "
                "waiting Single/Packing"
            )

        result[
            "new_status_reason"
        ] = reason

        return

    if state["lh_arrived"]:
        event = state[
            "lh_arrived"
        ]

        if (
            event_status(event)
            in STATUS_RETURN_LH_ARRIVED
        ):
            reason = (
                "Return LHArrived - "
                "waiting Single/Packing"
            )
        else:
            reason = (
                "LHArrived - "
                "waiting Single/Packing"
            )

        result[
            "new_status_reason"
        ] = reason

        return

    result[
        "new_status_reason"
    ] = (
        "Transporting to destination"
    )


def blank_result(data):
    return {
        "next_station": "",

        "display_status":
            data.get(
                "display_status",
                ""
            ),

        "latest_status": "",
        "latest_status_code": "",
        "latest_status_time": "",
        "latest_station": "",

        "lh_arrived_time": "",
        "lh_unloading_time": "",
        "lh_unloaded_time": "",

        "received_type": "",
        "received_time": "",

        "packing_time": "",
        "packed_time": "",

        "lh_transporting_time": "",
        "lh_transported_time": "",

        "assigning_time": "",
        "assigned_time": "",
        "delivering_time": "",
        "delivered_time": "",

        "cycle_type":
            "NORMAL",

        "new_status":
            "Chưa TTM",

        "new_status_time":
            "",

        "new_status_reason":
            "",
    }


def analyze_order(
    tracking_response
):
    data = get_tracking_data(
        tracking_response
    )

    events = flatten_tracking_events(
        get_tracking_list(
            tracking_response
        )
    )

    events = dedupe_events(
        events
    )

    events = [
        event
        for event in events
        if isinstance(
            event,
            dict
        )
    ]

    events.sort(
        key=event_timestamp
    )

    result = blank_result(
        data
    )
    hy_trip = (
        find_latest_hy_to_trip(
            events
        )
    )

    result[
        "to_number"
    ] = hy_trip[
        "to_number"
    ]

    result[
        "trip_number"
    ] = hy_trip[
        "trip_number"
    ]

    result[
        "hy_trip_time"
    ] = hy_trip[
        "hy_trip_time"
    ]
    if not events:
        try:
            display_status = int(
                data.get(
                    "display_status",
                    -1
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            display_status = -1

        if display_status == 4:
            result[
                "latest_status"
            ] = "Delivered"

            result[
                "latest_status_code"
            ] = 4

            result[
                "new_status"
            ] = "TTM"

            result[
                "new_status_reason"
            ] = "Delivered"

            return result

        if display_status == 2:
            result[
                "latest_status"
            ] = "Delivering"

            result[
                "latest_status_code"
            ] = 2

            result[
                "new_status"
            ] = "TTM"

            result[
                "new_status_reason"
            ] = "Delivering"

            return result

        result[
            "new_status_reason"
        ] = "No tracking data"

        return result


    current = max(
        events,
        key=event_timestamp
    )

    result[
        "latest_status"
    ] = event_message(
        current
    )

    result[
        "latest_status_code"
    ] = event_status(
        current
    )

    result[
        "latest_status_time"
    ] = event_time_text(
        current
    )

    result[
        "latest_station"
    ] = event_station_name(
        current
    )


    assigning = (
        latest_event_by_status(
            events,
            STATUS_ALL_ASSIGNING
        )
    )

    assigned = (
        latest_event_by_status(
            events,
            STATUS_ALL_ASSIGNED
        )
    )

    delivering = (
        latest_event_by_status(
            events,
            STATUS_DELIVERING
        )
    )

    delivered = (
        latest_event_by_status(
            events,
            STATUS_DELIVERED
        )
    )


    if assigning:
        result[
            "assigning_time"
        ] = event_time_text(
            assigning
        )

    if assigned:
        result[
            "assigned_time"
        ] = event_time_text(
            assigned
        )

    if delivering:
        result[
            "delivering_time"
        ] = event_time_text(
            delivering
        )

    if delivered:
        result[
            "delivered_time"
        ] = event_time_text(
            delivered
        )


    if delivered:
        delivered_ts = event_timestamp(
            delivered
        )

        has_return = (
            has_real_return_after_delivered(
                events,
                delivered_ts
            )
        )

        if not has_return:
            outbounds = (
                find_hy_outbounds(
                    events
                )
            )

            if outbounds:
                result[
                    "next_station"
                ] = outbounds[-1][1]

            result[
                "new_status"
            ] = "TTM"

            result[
                "new_status_time"
            ] = event_time_text(
                delivered
            )

            result[
                "new_status_reason"
            ] = "Delivered"

            return result


        result[
            "cycle_type"
        ] = (
            "RETURN_AFTER_DELIVERED"
        )

        return_outbounds = (
            find_hy_outbounds(
                events,
                min_ts=delivered_ts
            )
        )

        if not return_outbounds:
            result[
                "new_status"
            ] = "Chưa TTM"

            result[
                "new_status_time"
            ] = ""

            result[
                "new_status_reason"
            ] = (
                "Return at Hung Yen SOC - "
                "waiting outbound"
            )

            return result


        latest_departure_ts = (
            return_outbounds[-1][0]
        )

        destination = (
            return_outbounds[-1][1]
        )

        result[
            "next_station"
        ] = destination


        latest_state = (
            get_destination_state(
                events,
                destination,
                latest_departure_ts
            )
        )

        fill_destination_fields(
            result,
            latest_state
        )


        first_return_arrival = (
            find_first_hub_arrival_for_outbounds(
                events,
                return_outbounds
            )
        )

        if not first_return_arrival:
            result[
                "new_status"
            ] = "Chưa TTM"

            result[
                "new_status_time"
            ] = ""

            result[
                "new_status_reason"
            ] = (
                "Transporting to destination"
            )

            return result


        hub_arrival_ts = (
            first_return_arrival[
                "arrival_ts"
            ]
        )

        positive_event = (
            find_latest_positive_return(
                events,
                hub_arrival_ts
            )
        )

        if positive_event:
            result[
                "new_status"
            ] = "TTM"

            result[
                "new_status_time"
            ] = event_time_text(
                positive_event
            )

            result[
                "new_status_reason"
            ] = positive_reason(
                positive_event
            )

            return result


        set_no_reason(
            result,
            latest_state
        )

        return result


    if delivering:
        result[
            "new_status"
        ] = "TTM"

        result[
            "new_status_time"
        ] = event_time_text(
            delivering
        )

        result[
            "new_status_reason"
        ] = "Delivering"

        outbounds = (
            find_hy_outbounds(
                events
            )
        )

        if outbounds:
            result[
                "next_station"
            ] = outbounds[-1][1]

        return result


    try:
        display_status = int(
            data.get(
                "display_status",
                -1
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        display_status = -1


    if display_status == 4:
        result[
            "new_status"
        ] = "TTM"

        result[
            "new_status_reason"
        ] = "Delivered"

        if (
            result[
                "latest_status_code"
            ] == 4
        ):
            result[
                "new_status_time"
            ] = result[
                "latest_status_time"
            ]

        return result


    if display_status == 2:
        result[
            "new_status"
        ] = "TTM"

        result[
            "new_status_reason"
        ] = "Delivering"

        if (
            result[
                "latest_status_code"
            ] == 2
        ):
            result[
                "new_status_time"
            ] = result[
                "latest_status_time"
            ]

        return result


    outbounds = find_hy_outbounds(
        events
    )


    if not outbounds:
        result[
            "new_status"
        ] = "Chưa TTM"

        result[
            "new_status_time"
        ] = ""

        result[
            "new_status_reason"
        ] = (
            "No Hung Yen outbound"
        )

        return result


    latest_departure_ts = (
        outbounds[-1][0]
    )

    latest_destination = (
        outbounds[-1][1]
    )

    result[
        "next_station"
    ] = latest_destination


    latest_state = (
        get_destination_state(
            events,
            latest_destination,
            latest_departure_ts
        )
    )

    fill_destination_fields(
        result,
        latest_state
    )


    first_arrival = (
        find_first_hub_arrival_for_outbounds(
            events,
            outbounds
        )
    )


    if not first_arrival:
        result[
            "new_status"
        ] = "Chưa TTM"

        result[
            "new_status_time"
        ] = ""

        result[
            "new_status_reason"
        ] = (
            "Transporting to destination"
        )

        return result


    hub_arrival_ts = (
        first_arrival[
            "arrival_ts"
        ]
    )


    positive_event = (
        find_latest_positive_normal(
            events,
            hub_arrival_ts
        )
    )


    if positive_event:
        result[
            "new_status"
        ] = "TTM"

        result[
            "new_status_time"
        ] = event_time_text(
            positive_event
        )

        result[
            "new_status_reason"
        ] = positive_reason(
            positive_event
        )

        return result


    set_no_reason(
        result,
        latest_state
    )

    return result


def build_order_row(
    shipment_id,
    order_data
):
    tracking = order_data.get(
        "tracking_info",
        {}
    )

    status = analyze_order(
        tracking
    )

    return {
        "_key":
            shipment_id,

        "shipment_id":
            shipment_id,

        "next_station":
            status[
                "next_station"
            ],
        "to_number":
            status[
                "to_number"
            ],

        "trip_number":
            status[
                "trip_number"
            ],

        "hy_trip_time":
            status[
                "hy_trip_time"
            ],
        "display_status":
            status[
                "display_status"
            ],

        "latest_status":
            status[
                "latest_status"
            ],

        "latest_status_code":
            status[
                "latest_status_code"
            ],

        "latest_status_time":
            status[
                "latest_status_time"
            ],

        "latest_station":
            status[
                "latest_station"
            ],

        "lh_arrived_time":
            status[
                "lh_arrived_time"
            ],

        "lh_unloading_time":
            status[
                "lh_unloading_time"
            ],

        "lh_unloaded_time":
            status[
                "lh_unloaded_time"
            ],

        "received_type":
            status[
                "received_type"
            ],

        "received_time":
            status[
                "received_time"
            ],

        "packing_time":
            status[
                "packing_time"
            ],

        "packed_time":
            status[
                "packed_time"
            ],

        "lh_transporting_time":
            status[
                "lh_transporting_time"
            ],

        "lh_transported_time":
            status[
                "lh_transported_time"
            ],

        "assigning_time":
            status[
                "assigning_time"
            ],

        "assigned_time":
            status[
                "assigned_time"
            ],

        "delivering_time":
            status[
                "delivering_time"
            ],

        "delivered_time":
            status[
                "delivered_time"
            ],

        "cycle_type":
            status[
                "cycle_type"
            ],

        "new_status":
            status[
                "new_status"
            ],

        "new_status_time":
            status[
                "new_status_time"
            ],

        "new_status_reason":
            status[
                "new_status_reason"
            ],

        "sync_time":
            datetime.now(
                VN_TZ
            ).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
    }