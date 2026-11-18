import { useMemo } from "react";
import L from "leaflet";
import { Circle, Marker } from "react-leaflet";

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

export default function VehicleMarker({ location, registration }) {
  const position = [Number(location.latitude), Number(location.longitude)];

  const icon = useMemo(
    () =>
      L.divIcon({
        className: "vehicle-marker-icon",
        html: [
          '<span class="vehicle-marker">',
          '<span class="vehicle-pulse"></span>',
          '<span class="vehicle-dot"></span>',
          '<span class="vehicle-label">', escapeHtml(registration || "Matatu"), "</span>",
          "</span>",
        ].join(""),
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      }),
    [registration],
  );

  const accuracy = Number(location.accuracy);

  return (
    <>
      {Number.isFinite(accuracy) && accuracy > 0 && (
        <Circle center={position} radius={accuracy} className="vehicle-accuracy" interactive={false} />
      )}
      <Marker position={position} icon={icon} interactive={false} zIndexOffset={1000} />
    </>
  );
}
