import { useMemo } from "react";
import { calculateRouteProgress } from "./journeyProgress";

export default function JourneyProgress({ stages, location }) {
  const progress = useMemo(() => calculateRouteProgress(stages, location), [stages, location]);
  if (!progress) {
    return (
      <div className="journey-progress-unavailable" role="status">
        Route progress appears when GPS and route coordinates are available.
      </div>
    );
  }

  return (
    <section className="journey-progress" aria-label="Journey progress">
      <div className="journey-progress-heading">
        <span>Journey progress</span>
        <span className="tabular-nums">{progress.percent}%</span>
      </div>
      <div className="journey-progress-track">
        <progress className="progress progress-primary journey-progress-bar" value={progress.percent} max="100" aria-label={`${progress.percent} percent of route complete`} />
        <span className="journey-progress-current" style={{ left: `${progress.percent}%` }} aria-hidden="true" />
        <ol className="journey-progress-stops" aria-label="Route stages">
          {progress.stages.map((stage, index) => (
            <li
              className={index <= progress.stages.indexOf(progress.from) ? "journey-stop journey-stop-passed" : "journey-stop"}
              key={stage.id}
              style={{ left: `${index / (progress.stages.length - 1) * 100}%` }}
              aria-label={stage.name}
              title={stage.name}
            />
          ))}
        </ol>
      </div>
      <p className="journey-progress-caption">
        <span className="truncate">{progress.from.name} → {progress.to.name}</span>
        <span className="shrink-0">{progress.from.sequence_number} of {progress.stages.length} stops</span>
      </p>
    </section>
  );
}
