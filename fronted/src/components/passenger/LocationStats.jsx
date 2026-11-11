import { Compass, Gauge, LocateFixed } from "lucide-react";

const items = [
  { key: "speed", label: "Speed", unit: "km/h", Icon: Gauge },
  { key: "heading", label: "Heading", unit: "", Icon: Compass },
  { key: "accuracy", label: "GPS accuracy", unit: "m", Icon: LocateFixed },
];

export default function LocationStats({ speed, heading, accuracy }) {
  const values = { speed, heading, accuracy };

  return (
    <div className="grid grid-cols-3 divide-x divide-base-300 rounded-box border border-base-300 bg-base-100">
      {items.map(({ key, label, unit, Icon }) => (
        <div className="min-w-0 px-2 py-3 sm:px-3" key={key}>
          <div className="flex items-center justify-center gap-1 text-base-content/60">
            <Icon size={14} aria-hidden="true" />
            <span className="truncate text-[11px] font-medium">{label}</span>
          </div>
          <p className="mt-1 text-center text-sm font-semibold tabular-nums">
            {values[key] == null ? "—" : `${values[key]}${unit ? ` ${unit}` : ""}`}
          </p>
        </div>
      ))}
    </div>
  );
}
