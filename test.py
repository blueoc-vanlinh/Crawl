import json

from api.trip import get_trip_detail


trip = get_trip_detail(
    trip_id=290842327,
    station_id=3909
)

print(json.dumps(
    trip,
    indent=4,
    ensure_ascii=False
))