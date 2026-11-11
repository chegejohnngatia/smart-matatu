import { Activity, CircleAlert, WifiOff } from "lucide-react";

const labels = {
  live: "Live",
  reconnecting: "Reconnecting",
  offline: "Offline",
};

export default function StatusChip({ status }) {
  const Icon = status === "live" ? Activity : status === "offline" ? WifiOff : CircleAlert;
  const color = status === "live" ? "badge-success" : status === "offline" ? "badge-error" : "badge-warning";

  return (
    <span className={`badge badge-soft ${color} gap-1.5 px-3 py-3`} role="status" aria-live="polite">
      <Icon size={14} aria-hidden="true" />
      {labels[status] || labels.reconnecting}
    </span>
  );
}
