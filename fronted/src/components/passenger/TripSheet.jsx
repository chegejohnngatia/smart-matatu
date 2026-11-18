import { useState, useRef } from "react";
import {
  BusFront,
  ChevronDown,
  ChevronUp,
  Clock3,
  History,
  MapPin,
  Moon,
  Sun,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Flag,
  ArrowRight,
  Navigation,
} from "lucide-react";
import StatusChip from "./StatusChip";
import JourneyProgress from "./JourneyProgress";

export default function TripSheet({
  trip,
  history,
  location,
  journeyProgress,
  locationStatus,
  updatedLabel,
  error,
  destination,
  setDestination,
  onRegister,
  submitting,
  connected,
  expanded,
  setExpanded,
  theme,
  setTheme,
  matatus = [],
  activeDestinationStageId,
  onMoveMatatu,
  onResetMatatu,
  onEndJourney,
  onSelectMatatu,
}) {
  const pointerStart = useRef(null);
  const [moving, setMoving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

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

  const handleMove = async () => {
    if (!onMoveMatatu || moving) return;
    setMoving(true);
    try {
      await onMoveMatatu();
    } finally {
      setMoving(false);
    }
  };

  const handleReset = async () => {
    if (!onResetMatatu || resetting) return;
    setResetting(true);
    try {
      await onResetMatatu();
    } finally {
      setResetting(false);
    }
  };

  // Find destination stage object
  const destinationStage = trip.stages?.find(
    (s) =>
      s.id === Number(activeDestinationStageId) ||
      s.id === Number(destination) ||
      s.name === journeyProgress?.destination
  );

  const currentSequence = location?.current_stage_sequence || 0;
  const currentStage = trip.stages?.find(
    (s) => s.sequence_number === currentSequence
  ) || trip.stages?.[0];

  const destinationSequence =
    destinationStage?.sequence_number ||
    journeyProgress?.destination_sequence ||
    0;

  const isArrived =
    journeyProgress?.status === "Arrived" ||
    (destinationSequence > 0 && currentSequence >= destinationSequence);

  const isApproaching =
    !isArrived &&
    (journeyProgress?.status?.includes("Approaching") ||
      (destinationSequence > 0 && destinationSequence - currentSequence <= 2));

  const stopsRemaining =
    destinationSequence > 0
      ? Math.max(0, destinationSequence - currentSequence)
      : null;

  const hasActiveJourney = Boolean(journeyProgress || activeDestinationStageId);

  return (
    <aside
      className={`trip-sheet ${expanded ? "trip-sheet-expanded" : ""}`}
      aria-label="Trip and location details"
    >
      <button
        className="sheet-handle-area"
        type="button"
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        aria-expanded={expanded}
        aria-label={expanded ? "Collapse trip details" : "Expand trip details"}
      >
        <span className="sheet-handle" />
        <span className="sr-only">
          Drag to {expanded ? "collapse" : "expand"} trip details
        </span>
      </button>

      <div className="trip-sheet-scroll">
        {/* Header */}
        <header className="trip-sheet-heading">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-primary/10 p-2 text-primary">
                <BusFront size={20} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">
                    Matatu Vehicle
                  </p>
                  {matatus.length > 1 && onSelectMatatu && (
                    <select
                      className="select select-ghost select-xs text-xs font-semibold"
                      value={trip.id || ""}
                      onChange={(e) => onSelectMatatu(e.target.value)}
                      title="Switch vehicle"
                    >
                      {matatus.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.registration_number} ({m.route_name})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <h1 className="truncate text-xl font-extrabold tracking-tight">
                  {trip.plate || "Select Matatu"}
                </h1>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              className="btn btn-ghost btn-circle btn-sm"
              type="button"
              onClick={() =>
                setTheme(
                  theme === "passenger-dark"
                    ? "passenger-light"
                    : "passenger-dark"
                )
              }
              aria-label={`Switch to ${
                theme === "passenger-dark" ? "light" : "dark"
              } theme`}
            >
              {theme === "passenger-dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Status and Route Badge */}
        <div className="trip-status-row flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusChip status={locationStatus} />
            <span className="flex items-center gap-1.5 text-xs text-base-content/60">
              <Clock3 size={14} />
              {updatedLabel}
            </span>
          </div>
          {trip.code && (
            <span className="badge badge-outline shrink-0 font-mono text-xs">
              {trip.code}
            </span>
          )}
        </div>

        {/* Route Info Card */}
        <div className="rounded-xl bg-base-200/60 p-3 ring-1 ring-base-300">
          <div className="flex items-center gap-2 mb-1">
            <Navigation size={15} className="text-primary" />
            <span className="text-xs font-bold text-primary uppercase tracking-wider">
              Assigned Route
            </span>
          </div>
          <h2 className="font-bold text-base text-base-content" id="journey-heading">
            {trip.route || "Loading route..."}
          </h2>
          {trip.route_description && (
            <p className="text-xs text-base-content/70 mt-0.5">
              {trip.route_description}
            </p>
          )}
          {trip.stages?.length > 0 && (
            <p className="text-[11px] text-base-content/60 mt-1 flex items-center gap-1">
              <span>{trip.stages[0]?.name}</span>
              <ArrowRight size={12} className="inline opacity-60" />
              <span>{trip.stages[trip.stages.length - 1]?.name}</span>
              <span className="ml-auto font-medium">({trip.stages.length} stages)</span>
            </p>
          )}
        </div>

        {error && (
          <p className="alert alert-error px-3 py-2 text-sm" role="alert">
            {error}
          </p>
        )}

        {/* ACTIVE JOURNEY NOTIFICATION & DETAILS */}
        {hasActiveJourney && (
          <section className="space-y-3">
            {/* Arrival / Approaching Alert Banner */}
            {isArrived ? (
              <div className="rounded-2xl bg-emerald-500/15 ring-2 ring-emerald-500/30 p-4 text-emerald-950 dark:text-emerald-200 flex items-start gap-3">
                <CheckCircle2 size={24} className="text-emerald-500 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-extrabold text-base">Arrived at Destination!</h3>
                  <p className="text-xs opacity-90 mt-0.5">
                    You have arrived at <strong>{destinationStage?.name || journeyProgress?.destination}</strong>. Thank you for riding with Matatu Smart!
                  </p>
                </div>
              </div>
            ) : isApproaching ? (
              <div className="rounded-2xl bg-amber-500/15 ring-2 ring-amber-500/40 p-4 text-amber-950 dark:text-amber-200 flex items-start gap-3 animate-pulse">
                <AlertTriangle size={24} className="text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-extrabold text-base">
                    Approaching Destination!
                  </h3>
                  <p className="text-xs opacity-90 mt-0.5">
                    <strong>{destinationStage?.name || journeyProgress?.destination}</strong> is{" "}
                    {stopsRemaining === 1 ? "the next stop" : `${stopsRemaining} stops away`}. Get ready to alight!
                  </p>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl bg-blue-500/10 ring-1 ring-blue-500/20 p-3.5 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-3 w-3 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                  </span>
                  <div>
                    <h3 className="font-bold text-sm">Journey In Progress</h3>
                    <p className="text-xs text-base-content/65">
                      Heading to {destinationStage?.name || journeyProgress?.destination}
                    </p>
                  </div>
                </div>
                <span className="badge badge-primary text-xs font-semibold">Active</span>
              </div>
            )}

            {/* Key Journey Metrics */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="rounded-xl bg-base-200/50 p-3 border border-base-300">
                <p className="text-[11px] font-medium text-base-content/60">Current Stop</p>
                <p className="font-bold text-sm text-base-content truncate mt-0.5">
                  {currentStage?.name || "Depot"}
                </p>
                <span className="text-[10px] text-base-content/50">
                  Stop #{currentSequence || 1} of {trip.stages?.length || 0}
                </span>
              </div>

              <div className="rounded-xl bg-base-200/50 p-3 border border-base-300">
                <p className="text-[11px] font-medium text-base-content/60">Your Destination</p>
                <p className="font-bold text-sm text-primary truncate mt-0.5">
                  {destinationStage?.name || journeyProgress?.destination || "Selected Stop"}
                </p>
                <span className="text-[10px] text-base-content/50">
                  {stopsRemaining != null
                    ? stopsRemaining === 0
                      ? "Arrived"
                      : `${stopsRemaining} stop${stopsRemaining > 1 ? "s" : ""} remaining`
                    : "On route"}
                </span>
              </div>

              <div className="rounded-xl bg-base-200/50 p-3 border border-base-300">
                <p className="text-[11px] font-medium text-base-content/60">Estimated Arrival</p>
                <p className="font-bold text-base text-base-content mt-0.5">
                  {journeyProgress?.eta == null
                    ? isArrived
                      ? "Arrived"
                      : "Calculating..."
                    : `${Number(journeyProgress.eta).toFixed(0)} min`}
                </p>
                <span className="text-[10px] text-base-content/50">
                  {journeyProgress?.distance != null
                    ? `${Number(journeyProgress.distance).toFixed(1)} km away`
                    : "En route"}
                </span>
              </div>

              <div className="rounded-xl bg-base-200/50 p-3 border border-base-300">
                <p className="text-[11px] font-medium text-base-content/60">Vehicle Speed</p>
                <p className="font-bold text-base text-base-content mt-0.5">
                  {location?.speed != null ? `${Number(location.speed).toFixed(0)} km/h` : "20 km/h"}
                </p>
                <span className="text-[10px] text-base-content/50">
                  {location?.speed > 0 ? "Moving on route" : "Stopped at stage"}
                </span>
              </div>
            </div>

            {/* Overall Route Progress Bar */}
            <JourneyProgress stages={trip.stages} location={location} />

            {/* Stages Stepper List */}
            <div className="rounded-2xl bg-base-200/40 p-3.5 border border-base-300">
              <h4 className="text-xs font-bold text-base-content/70 uppercase tracking-wider mb-2.5">
                Route Stages Progress
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {trip.stages?.map((stage) => {
                  const passed = currentSequence >= stage.sequence_number;
                  const isCurrent = currentSequence === stage.sequence_number;
                  const isDest =
                    destinationStage?.id === stage.id ||
                    stage.name === journeyProgress?.destination;

                  return (
                    <div
                      key={stage.id}
                      className={`flex items-center gap-2.5 text-xs p-1.5 rounded-lg transition-all ${
                        isCurrent
                          ? "bg-primary/10 font-bold text-primary ring-1 ring-primary/30"
                          : isDest
                          ? "bg-emerald-500/10 font-bold text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-500/30"
                          : passed
                          ? "text-base-content/50 opacity-80"
                          : "text-base-content/80"
                      }`}
                    >
                      <span className="w-5 text-center font-mono text-[10px] opacity-60">
                        #{stage.sequence_number}
                      </span>
                      {isCurrent ? (
                        <BusFront size={16} className="text-primary animate-bounce shrink-0" />
                      ) : isDest ? (
                        <Flag size={16} className="text-emerald-500 shrink-0" />
                      ) : passed ? (
                        <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                      ) : (
                        <span className="w-3.5 h-3.5 rounded-full border border-base-content/30 shrink-0" />
                      )}
                      <span className="truncate flex-1">{stage.name}</span>
                      {isCurrent && (
                        <span className="badge badge-primary badge-xs">Current</span>
                      )}
                      {isDest && (
                        <span className="badge badge-success badge-xs">Destination</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Journey Simulation & Management Controls */}
            <div className="pt-1 flex flex-wrap gap-2">
              {onMoveMatatu && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm flex-1 gap-1.5"
                  onClick={handleMove}
                  disabled={moving}
                >
                  <Play size={14} className={moving ? "animate-spin" : ""} />
                  {moving ? "Moving..." : "Advance to Next Stop"}
                </button>
              )}
              {onResetMatatu && (
                <button
                  type="button"
                  className="btn btn-outline btn-sm gap-1.5"
                  onClick={handleReset}
                  disabled={resetting}
                  title="Reset vehicle back to Stage 1"
                >
                  <RotateCcw size={14} />
                  Reset
                </button>
              )}
              {onEndJourney && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm text-error"
                  onClick={onEndJourney}
                >
                  End Journey
                </button>
              )}
            </div>
          </section>
        )}

        {/* DESTINATION SELECTION & REGISTRATION FORM */}
        <section className="sheet-section space-y-3" aria-labelledby="destination-selector-heading">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold text-base" id="destination-selector-heading">
                {hasActiveJourney ? "Change Destination" : "Select Your Destination"}
              </h2>
              <p className="text-xs text-base-content/65">
                Stages from the admin-configured route for this matatu.
              </p>
            </div>
            <span className="badge badge-ghost text-xs">
              {trip.stages?.length || 0} Stops
            </span>
          </div>

          <form className="space-y-3" onSubmit={onRegister}>
            <div className="form-control">
              <label className="label py-1">
                <span className="label-text text-xs font-semibold">
                  Choose Destination Stage
                </span>
              </label>
              <select
                className="select select-bordered select-md w-full font-medium"
                value={destination}
                onChange={(event) => setDestination(event.target.value)}
                disabled={!connected || submitting}
                required
                aria-label="Select your destination stage"
              >
                <option value="" disabled>
                  {connected
                    ? "— Choose a destination stage —"
                    : "Loading route stages..."}
                </option>
                {trip.stages?.map((stage, idx) => (
                  <option key={stage.id} value={stage.id}>
                    Stop #{stage.sequence_number}: {stage.name}
                    {idx === 0
                      ? " (Origin)"
                      : idx === trip.stages.length - 1
                      ? " (Final Terminal)"
                      : ""}
                  </option>
                ))}
              </select>
            </div>

            <button
              className="btn btn-primary w-full gap-2 font-bold shadow-md shadow-primary/20"
              type="submit"
              disabled={!connected || submitting || !destination}
            >
              <MapPin size={18} />
              {submitting
                ? "Registering..."
                : hasActiveJourney
                ? "Update Destination"
                : "Register Destination & Start Journey"}
            </button>
          </form>
        </section>

        {/* JOURNEY HISTORY */}
        <section className="sheet-section pt-2" aria-labelledby="history-heading">
          <button
            type="button"
            className="w-full flex items-center justify-between py-1 text-left font-semibold text-sm"
            onClick={() => setShowHistory(!showHistory)}
          >
            <div className="flex items-center gap-2">
              <History size={16} className="text-base-content/60" />
              <span id="history-heading">Journey History</span>
              <span className="badge badge-ghost badge-sm">{history.length}</span>
            </div>
            {showHistory ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showHistory && (
            <div className="mt-2.5">
              {history.length === 0 ? (
                <p className="py-2 text-xs text-base-content/60">
                  No registered journeys yet.
                </p>
              ) : (
                <ul className="divide-y divide-base-300 text-xs">
                  {history.slice(0, 5).map((item) => (
                    <li
                      className="flex items-center justify-between gap-3 py-2"
                      key={item.id}
                    >
                      <div className="min-w-0">
                        <span className="font-semibold truncate block">
                          {item.destination}
                        </span>
                        <span className="text-[10px] text-base-content/50">
                          Token: {item.passenger_token || `#${item.id}`}
                        </span>
                      </div>
                      <span className="badge badge-ghost badge-sm shrink-0">
                        {item.status || "Registered"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>

        <div className="pb-6 text-center text-xs text-base-content/40">
          Matatu Smart · Live Route Information
        </div>
      </div>

      <button
        className="sheet-expand-button btn btn-circle btn-sm shadow-md"
        onClick={() => setExpanded(!expanded)}
        type="button"
        aria-label={expanded ? "Collapse trip details" : "Expand trip details"}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
      </button>
    </aside>
  );
}
