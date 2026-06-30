const STYLE_MAP = {
  pending: "bg-sand text-ocean-800 border-line",
  processing: "bg-blue-100 text-blue-800 border-blue-200",
  running: "bg-blue-100 text-blue-800 border-blue-200",
  done: "bg-emerald-100 text-emerald-800 border-emerald-200",
  completed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  ready: "bg-emerald-100 text-emerald-800 border-emerald-200",
  failed: "bg-red-100 text-red-800 border-red-200",
  published: "bg-emerald-100 text-emerald-800 border-emerald-200",
  pending_approval: "bg-amber-100 text-amber-800 border-amber-200",
  generating: "bg-blue-100 text-blue-800 border-blue-200",
  none: "bg-sand text-muted border-line",
};

export default function StatusBadge({ status, label }) {
  const normalized = String(status || "pending").toLowerCase().replace(/\s+/g, "_");
  const display = label || normalized.replace(/_/g, " ");

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${STYLE_MAP[normalized] || STYLE_MAP.pending}`}
    >
      {display}
    </span>
  );
}
