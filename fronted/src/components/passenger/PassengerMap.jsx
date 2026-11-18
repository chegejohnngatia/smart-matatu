import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import { MapPin } from "lucide-react";
import MapControls from "./MapControls";
import VehicleMarker from "./VehicleMarker";

const FALLBACK_CENTER = [-1.2864, 36.8172];
const FOLLOW_DURATION_SECONDS = 0.85;

function isLocated(stage) {
  return (
    stage.latitude != null &&
    stage.longitude != null &&
    Number.isFinite(Number(stage.latitude)) &&
    Number.isFinite(Number(stage.longitude))
  );
}

function stagePosition(stage) {
  return [Number(stage.latitude), Number(stage.longitude)];
}

function vehiclePosition(location) {
  return [Number(location.latitude), Number(location.longitude)];
}

function MapController({ located, location, following, onUserDrag, onZoomChange, onMapReady }) {
  const map = useMap();

  useEffect(() => {
    onMapReady(map);
    const stopFollowing = () => onUserDrag();
    const announceZoom = () => onZoomChange(map.getZoom());
    map.on("dragstart", stopFollowing);
    map.on("zoomend", announceZoom);
    announceZoom();
    return () => {
      map.off("dragstart", stopFollowing);
      map.off("zoomend", announceZoom);
    };
  }, [map, onUserDrag, onZoomChange, onMapReady]);

  // Fit the viewport once when the route data first arrives.
  useEffect(() => {
    const points = located.map(stagePosition);
    if (location) points.push(vehiclePosition(location));
    if (!points.length) map.setView(FALLBACK_CENTER, 12, { animate: false });
    else if (points.length === 1) map.setView(points[0], 15, { animate: false });
    else map.fitBounds(points, { padding: [36, 36], animate: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [located.length]);

  useEffect(() => {
    if (!following || !location) return;
    map.panTo(vehiclePosition(location), { animate: true, duration: FOLLOW_DURATION_SECONDS });
  }, [following, location, map]);

  return null;
}

export default function PassengerMap({ stages, location, registration, status }) {
  const [following, setFollowing] = useState(true);
  const [zoom, setZoom] = useState(null);
  const mapRef = useRef(null);
  const located = useMemo(() => (stages || []).filter(isLocated), [stages]);
  const routePositions = located.map(stagePosition);

  const handleMapReady = useCallback((map) => {
    mapRef.current = map;
  }, []);
  const handleUserDrag = useCallback(() => setFollowing(false), []);
  const handleZoomChange = useCallback((value) => setZoom(value), []);
  const handleZoom = useCallback((direction) => {
    const map = mapRef.current;
    if (!map) return;
    if (direction > 0) map.zoomIn(1);
    else map.zoomOut(1);
  }, []);
  const handleFollow = useCallback(() => setFollowing(true), []);

  return (
    <section className="passenger-map" aria-label="Live vehicle route map">
      <MapContainer
        center={FALLBACK_CENTER}
        zoom={12}
        zoomControl={false}
        className="passenger-map-canvas"
        aria-label={location ? `Street map showing ${registration || "the matatu"} position` : "Street map loading"}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        {routePositions.length > 1 && (
          <>
            <Polyline positions={routePositions} className="route-underlay" interactive={false} />
            <Polyline positions={routePositions} className="route-line" interactive={false} />
          </>
        )}
        {located.map((stage, index) => (
          <CircleMarker key={stage.id} center={stagePosition(stage)} radius={9} className="map-stage-dot">
            <Tooltip direction="right" offset={[14, 0]} permanent className="map-stage-tooltip">
              <span className="map-stage-name">{stage.name}</span>
              {(index === 0 || index === located.length - 1) && (
                <span className="map-stage-meta">{index === 0 ? "START" : "END"}</span>
              )}
            </Tooltip>
          </CircleMarker>
        ))}
        {location && <VehicleMarker location={location} registration={registration} />}
        <MapController
          located={located}
          location={location}
          following={following}
          onUserDrag={handleUserDrag}
          onZoomChange={handleZoomChange}
          onMapReady={handleMapReady}
        />
      </MapContainer>
      {!located.length && (
        <div className="map-empty-state">
          <MapPin size={26} />
          <p>Route stage coordinates are not available</p>
        </div>
      )}
      <MapControls following={following} onFollow={handleFollow} zoom={zoom} onZoom={handleZoom} />
      <div className="map-caption">
        <span className="map-legend-dot" />
        <span>Route</span>
        <span className="map-caption-separator">·</span>
        <span>{status === "live" ? "Vehicle position" : "Last reported position"}</span>
        <span className="map-caption-separator">·</span>
        <span className="map-coordinate">Drag map to explore</span>
      </div>
    </section>
  );
}
