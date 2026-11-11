import { useMemo, useRef, useState } from "react";
import { MapPin } from "lucide-react";
import MapControls from "./MapControls";

const WIDTH = 1000;
const HEIGHT = 760;

function makeProjection(stages) {
  const located = stages.filter((stage) => stage.latitude != null && stage.longitude != null && Number.isFinite(Number(stage.latitude)) && Number.isFinite(Number(stage.longitude)));
  if (!located.length) return { located, unitsPerMeter: 0, project: () => ({ x: WIDTH / 2, y: HEIGHT / 2 }) };
  const lats = located.map((stage) => Number(stage.latitude));
  const lons = located.map((stage) => Number(stage.longitude));
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latRange = maxLat - minLat || 0.01;
  const lonRange = maxLon - minLon || 0.01;
  const ratio = Math.min((WIDTH - 220) / lonRange, (HEIGHT - 220) / latRange);
  const centerLat = (minLat + maxLat) / 2;
  const centerLon = (minLon + maxLon) / 2;
  return {
    located,
    unitsPerMeter: ratio / 111_320,
    project(latitude, longitude) {
      return {
        x: WIDTH / 2 + (Number(longitude) - centerLon) * ratio,
        y: HEIGHT / 2 - (Number(latitude) - centerLat) * ratio,
      };
    },
  };
}

export default function PassengerMap({ stages, location, registration, status }) {
  const [following, setFollowing] = useState(true);
  const [zoom, setZoom] = useState(100);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef(null);
  const svgRef = useRef(null);
  const projection = useMemo(() => makeProjection(stages || []), [stages]);
  const routePoints = projection.located.map((stage) => projection.project(stage.latitude, stage.longitude));
  const vehiclePoint = location ? projection.project(location.latitude, location.longitude) : null;
  const route = routePoints.map(({ x, y }) => `${x},${y}`).join(" ");
  const scale = zoom / 100;
  const followedOffset = following && vehiclePoint
    ? { x: (WIDTH / 2 - vehiclePoint.x) * scale, y: (HEIGHT / 2 - vehiclePoint.y) * scale }
    : offset;

  const zoomBy = (direction) => setZoom((value) => Math.min(150, Math.max(80, value + direction * 10)));

  const startDrag = (event) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { x: event.clientX, y: event.clientY, offset: followedOffset };
  };

  const moveDrag = (event) => {
    if (!drag.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scale = WIDTH / rect.width;
    const dx = (event.clientX - drag.current.x) * scale;
    const dy = (event.clientY - drag.current.y) * scale;
    if (Math.abs(dx) + Math.abs(dy) > 3) {
      setFollowing(false);
    }
    setOffset({ x: drag.current.offset.x + dx, y: drag.current.offset.y + dy });
  };

  const stopDrag = () => {
    drag.current = null;
  };

  const follow = () => {
    setFollowing(true);
  };

  return (
    <section className="passenger-map" aria-label="Live vehicle route map">
      <svg
        ref={svgRef}
        className="passenger-map-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={location ? `Schematic route map showing ${registration} live position` : "Schematic vehicle route map loading"}
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={stopDrag}
        onPointerCancel={stopDrag}
      >
        <defs>
          <pattern id="map-grid" width="62" height="62" patternUnits="userSpaceOnUse" patternTransform="rotate(-13)">
            <path d="M 62 0 L 0 0 0 62" fill="none" stroke="currentColor" strokeOpacity=".08" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width={WIDTH} height={HEIGHT} fill="var(--color-base-200)" />
        <rect width={WIDTH} height={HEIGHT} fill="url(#map-grid)" />
        <g className="map-streets" fill="none" stroke="currentColor">
          <path d="M-50 180 C220 260 390 120 640 215 S960 320 1100 225" />
          <path d="M-70 530 C200 430 390 600 610 485 S890 425 1070 560" />
          <path d="M210 -30 C260 160 210 330 340 790" />
          <path d="M760 -20 C660 170 810 360 700 790" />
          <path d="M-30 355 C190 320 330 390 520 350 S820 290 1040 380" />
        </g>
        <g transform={`translate(${followedOffset.x} ${followedOffset.y}) translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${scale}) translate(${-WIDTH / 2} ${-HEIGHT / 2})`} style={{ transition: "transform 180ms ease-out" }}>
          {routePoints.length > 1 && <polyline points={route} className="route-underlay" />}
          {routePoints.length > 1 && <polyline points={route} className="route-line" />}
          {projection.located.map((stage, index) => {
            const point = projection.project(stage.latitude, stage.longitude);
            return (
              <g key={stage.id} className="map-stage">
                <circle cx={point.x} cy={point.y} r="9" />
                <text x={point.x + 15} y={point.y - 12}>{stage.name}</text>
                {index === 0 && <text className="map-stage-meta" x={point.x + 15} y={point.y + 8}>START</text>}
                {index === projection.located.length - 1 && <text className="map-stage-meta" x={point.x + 15} y={point.y + 8}>END</text>}
              </g>
            );
          })}
          {vehiclePoint && (
            <g className="vehicle-marker" transform={`translate(${vehiclePoint.x} ${vehiclePoint.y})`} style={{ transition: "transform 850ms cubic-bezier(.2,.7,.2,1)" }}>
              <circle className="vehicle-accuracy" r={Math.max(8, Math.min(Number(location.accuracy || 0) * projection.unitsPerMeter, 74))} />
              <circle className="vehicle-pulse" r="22" />
              <circle className="vehicle-dot" r="10" />
              <text className="vehicle-label" x="18" y="5">{registration || "Matatu"}</text>
            </g>
          )}
        </g>
        {!projection.located.length && (
          <g className="map-empty-state">
            <MapPin x={WIDTH / 2 - 13} y={HEIGHT / 2 - 20} size={26} />
            <text x={WIDTH / 2} y={HEIGHT / 2 + 36} textAnchor="middle">Route stage coordinates are not available</text>
          </g>
        )}
      </svg>
      <MapControls following={following} onFollow={follow} zoom={zoom} onZoom={zoomBy} />
      <div className="map-caption">
        <span className="map-legend-dot" />
        <span>Schematic route</span>
        <span className="map-caption-separator">·</span>
        <span>{status === "live" ? "Vehicle position" : "Last reported position"}</span>
        <span className="map-caption-separator">·</span>
        <span className="map-coordinate">Drag map to explore</span>
      </div>
    </section>
  );
}
