from gps import calculate_distance


latitude = -1.286389
longitude = 36.817223


distance = calculate_distance(
    latitude,
    longitude,
    latitude,
    longitude
)


print(f"Distance: {distance:.2f} metres")