from api.trip.station_detail import (
    get_station_detail as api_get_station_detail,
    get_station_data as api_get_station_data,
    get_trip_stations as api_get_trip_stations,
)


def get_station_detail(
    trip_id,
    station_id=None,
    sequence_number=None,
):
    return api_get_station_detail(
        trip_id=trip_id,
        station_id=station_id,
        sequence_number=sequence_number,
    )


def get_station_data(
    trip_id,
    station_id=None,
    sequence_number=None,
):
    return api_get_station_data(
        trip_id=trip_id,
        station_id=station_id,
        sequence_number=sequence_number,
    )


def get_trip_stations(
    trip_id,
):
    return api_get_trip_stations(
        trip_id=trip_id,
    )