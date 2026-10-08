import math


def calculate_distance(
    latitude1,
    longitude1,
    latitude2,
    longitude2
):

    earth_radius = 6371000

    latitude1 = math.radians(latitude1)
    latitude2 = math.radians(latitude2)

    difference_latitude = math.radians(
        latitude2 - latitude1
    )

    difference_longitude = math.radians(
        longitude2 - longitude1
    )

    a = (
        math.sin(difference_latitude / 2) ** 2
        +
        math.cos(latitude1)
        *
        math.cos(latitude2)
        *
        math.sin(difference_longitude / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    distance = earth_radius * c

    return distance


#nobles modifications 

import math

EARTH_RADIUS_M = 6_371_000  # mean Earth radius in meters


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Straight-line ("as the crow flies") distance between two GPS points,
    in meters, using the Haversine formula.

    Accepts plain floats so callers don't need to know about Decimal fields
    on the Stage model -- convert at the call site.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Convenience wrapper returning kilometers instead of meters."""
    return haversine_distance_m(lat1, lon1, lat2, lon2) / 1000



print(haversine_distance_km(-0.756750, 34.598330, -0.680482, 34.777061))
