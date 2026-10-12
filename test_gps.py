from gps import calculate_distance, haversine_distance_m, haversine_distance_km


latitude = -0.756750
longitude = 34.598330
latitude1 = -0.680482
longitude1 = 34.777061


distance = calculate_distance(
    latitude,
    longitude,
    latitude1,
    longitude1
)


print(f"Distance: {distance:.2f} metres")