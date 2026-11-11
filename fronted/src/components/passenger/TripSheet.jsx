import { useRef } from "react";
import { BusFront, ChevronDown, ChevronUp, Clock3, History, MapPin, Moon, Sun } from "lucide-react";
import LocationStats from "./LocationStats";
import StatusChip from "./StatusChip";
import JourneyProgress from "./JourneyProgress";

export default function TripSheet({ trip, history, location, journeyProgress, locationStatus, heading, updatedLabel, error, destination, setDestination, onRegister, submitting, connected, expanded, setExpanded, theme, setTheme, isOnline }) {
  const pointerStart = useRef(null);

  const onPointerDown = (event) => {
    pointerStart.current = event.clientY;
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerUp = (event) => {
    if (pointerStart.current == null) return;
    const movement = event.clientY - pointerStart.current;
    if (movement < -32) setExpanded(true);
    else if (movement > 32) setExpanded(false);
    else setExpanded(!expanded);
    pointerStart.current = null;
  };

  return (
    <aside className={`trip-sheet ${expanded ? "trip-sheet-expanded" : ""}`} aria-label="Trip and location details">
      <button className="sheet-handle-area" type="button" onPointerDown={onPointerDown} onPointerUp={onPointerUp} aria-expanded={expanded} aria-label={expanded ? "Collapse trip details" : "Expand trip details"}>
        <span className="sheet-handle" />
        <span className="sr-only">Drag to {expanded ? "collapse" : "expand"} trip details</span>
      </button>
      <div className="trip-sheet-scroll">
        <header className="trip-sheet-heading">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-primary/10 p-2 text-primary"><BusFront size={18} /></span>
              <div className="min-w-0">
                <p className="text-xs font-medium text-base-content/60">Vehicle</p>
                <h1 className="truncate text-lg font-bold tracking-tight">{trip.plate || "Passenger journey"}</h1>
              </div>
            </div>
          </div>
          <button className="btn btn-ghost btn-circle btn-sm" type="button" onClick={() => setTheme(theme === "passenger-dark" ? "passenger-light" : "passenger-dark")} aria-label={`Switch to ${theme === "passenger-dark" ? "light" : "dark"} theme`}>
            {theme === "passenger-dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>

        <div className="trip-status-row">
          <StatusChip status={locationStatus} />
          <span className="flex items-center gap-1.5 text-xs text-base-content/60"><Clock3 size={14} />{updatedLabel}</span>
        </div>
        {location?.source && <p className="-mt-2 mb-3 text-[11px] text-base-content/55">Position source: {location.source === "gps" ? "Vehicle GPS" : "simulator"}</p>}

        {locationStatus === "offline" && (
          <p className="location-message" role="status">{isOnline ? "GPS signal lost. Showing the last reported position." : "No network connection. The last reported position is shown."}</p>
        )}
        {locationStatus === "reconnecting" && <p className="location-message" role="status">Connection interrupted. Trying to refresh the vehicle location.</p>}
        {error && <p className="alert alert-error px-3 py-2 text-sm" role="alert">{error}</p>}

        <section className="sheet-section" aria-labelledby="journey-heading">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium text-base-content/60">Route</p>
              <h2 className="truncate font-semibold" id="journey-heading">{trip.route || "Route details loading"}</h2>
            </div>
            <span className="badge badge-outline shrink-0 font-mono text-xs">{trip.code || "—"}</span>
          </div>
          <JourneyProgress stages={trip.stages} location={location} />
          <LocationStats speed={location?.speed == null ? null : Number(location.speed).toFixed(0)} heading={heading} accuracy={location?.accuracy == null ? null : Number(location.accuracy).toFixed(0)} />
          <div className="mt-4 grid grid-cols-[20px_1fr] gap-x-2 gap-y-3 text-sm">
            <MapPin size={17} className="mt-0.5 text-primary" />
            <div><p className="text-xs text-base-content/60">Your destination</p><p className="font-medium">{journeyProgress?.destination || "Choose a stop below"}</p></div>
            <Clock3 size={17} className="mt-0.5 text-base-content/50" />
            <div><p className="text-xs text-base-content/60">Estimated arrival</p><p className="font-medium">{journeyProgress?.eta == null ? "Unavailable while stopped" : `${Number(journeyProgress.eta).toFixed(0)} min`}</p></div>
          </div>
        </section>

        <form className="sheet-section space-y-3" onSubmit={onRegister}>
          <div>
            <h2 className="font-semibold">Your destination</h2>
            <p className="mt-0.5 text-xs text-base-content/60">Choose a stop to register your journey.</p>
          </div>
          <select className="select select-bordered w-full" value={destination} onChange={(event) => setDestination(event.target.value)} disabled={!connected} required aria-label="Select your destination">
            <option value="" disabled>{connected ? "Choose a route stop" : "Trip details are unavailable"}</option>
            {trip.stages?.map((stage) => <option key={stage.id} value={stage.id}>{stage.name}</option>)}
          </select>
          <button className="btn btn-primary w-full" type="submit" disabled={!connected || submitting || !destination}>
            {submitting ? "Registering…" : "Register journey"}
          </button>
        </form>

        <section className="sheet-section" aria-labelledby="history-heading">
          <div className="mb-2 flex items-center gap-2"><History size={17} className="text-base-content/60" /><h2 className="font-semibold" id="history-heading">Journey history</h2><span className="badge badge-ghost ml-auto">{history.length}</span></div>
          {history.length === 0 ? <p className="py-2 text-sm text-base-content/60">No registered journeys yet.</p> : (
            <ul className="divide-y divide-base-300">
              {history.slice(0, 5).map((item) => <li className="flex items-center justify-between gap-3 py-2.5 text-sm" key={item.id}><span className="truncate">{item.destination}</span><span className="badge badge-ghost shrink-0">{item.status}</span></li>)}
            </ul>
          )}
        </section>
        <div className="pb-6 text-center text-xs text-base-content/50">Matatu Smart · Live route information</div>
      </div>
      <button className="sheet-expand-button btn btn-circle btn-sm" onClick={() => setExpanded(!expanded)} type="button" aria-label={expanded ? "Collapse trip details" : "Expand trip details"}>
        {expanded ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
      </button>
    </aside>
  );
}
