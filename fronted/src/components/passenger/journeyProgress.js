export function calculateRouteProgress(stages = [], location) {
  const ordered = stages
    .filter((stage) => stage.latitude != null && stage.longitude != null && Number.isFinite(Number(stage.latitude)) && Number.isFinite(Number(stage.longitude)))
    .sort((a, b) => Number(a.sequence_number) - Number(b.sequence_number));
  if (!location || !Number.isFinite(Number(location.latitude)) || !Number.isFinite(Number(location.longitude)) || ordered.length < 2) return null;

  const centerLatitude = ordered.reduce((sum, stage) => sum + Number(stage.latitude), 0) / ordered.length;
  const longitudeScale = Math.cos(centerLatitude * Math.PI / 180);
  const toPoint = (latitude, longitude) => ({
    x: Number(longitude) * 111_320 * longitudeScale,
    y: Number(latitude) * 111_320,
  });
  const points = ordered.map((stage) => toPoint(stage.latitude, stage.longitude));
  const vehicle = toPoint(location.latitude, location.longitude);
  const lengths = points.slice(1).map((point, index) => Math.hypot(point.x - points[index].x, point.y - points[index].y));
  const totalLength = lengths.reduce((sum, length) => sum + length, 0);
  if (!totalLength) return null;

  let best = { distance: Infinity, along: 0, segment: 0 };
  let distanceBefore = 0;
  lengths.forEach((length, index) => {
    if (length === 0) return;
    const start = points[index];
    const end = points[index + 1];
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const fraction = Math.max(0, Math.min(1, ((vehicle.x - start.x) * dx + (vehicle.y - start.y) * dy) / (length * length)));
    const distance = Math.hypot(vehicle.x - (start.x + fraction * dx), vehicle.y - (start.y + fraction * dy));
    if (distance < best.distance) best = { distance, along: distanceBefore + fraction * length, segment: index };
    distanceBefore += length;
  });

  return {
    percent: Math.round(Math.max(0, Math.min(100, best.along / totalLength * 100))),
    from: ordered[best.segment],
    to: ordered[Math.min(best.segment + 1, ordered.length - 1)],
    stages: ordered,
  };
}
