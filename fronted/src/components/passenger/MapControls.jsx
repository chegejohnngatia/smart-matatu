import { LocateFixed, Minus, Plus } from "lucide-react";

export default function MapControls({ following, onFollow, zoom, onZoom }) {
  return (
    <div className="map-controls" aria-label="Map controls">
      <button className="btn btn-circle btn-sm bg-base-100 shadow-sm" type="button" onClick={() => onZoom(1)} aria-label="Zoom in">
        <Plus size={18} />
      </button>
      <button className="btn btn-circle btn-sm bg-base-100 shadow-sm" type="button" onClick={() => onZoom(-1)} aria-label="Zoom out">
        <Minus size={18} />
      </button>
      <button className={`btn btn-sm shadow-sm ${following ? "btn-primary" : "bg-base-100"}`} type="button" onClick={onFollow} aria-label={following ? "Following vehicle location" : "Follow vehicle location"} aria-pressed={following}>
        <LocateFixed size={17} />
        <span className="hidden sm:inline">{following ? "Following" : "Follow vehicle"}</span>
      </button>
      <span className="sr-only" aria-live="polite">Map zoom {zoom} percent</span>
    </div>
  );
}
