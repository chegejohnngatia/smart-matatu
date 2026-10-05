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