const toneMap = {
  HIGH: "border-red-300 bg-red-100 text-red-800 dark:border-red-400/40 dark:bg-red-500/20 dark:text-red-100",
  MEDIUM:
    "border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-400/40 dark:bg-amber-500/20 dark:text-amber-100",
  LOW: "border-blue-300 bg-blue-100 text-blue-900 dark:border-blue-400/40 dark:bg-blue-500/20 dark:text-blue-100",
};

export default function SeverityBadge({ level, value }) {
  const raw = level ?? value;
  if (raw === undefined || raw === null || raw === "") {
    return (
      <span className="inline-flex rounded-full border border-line bg-cream px-2 py-0.5 text-xs font-medium text-muted dark:border-line/40 dark:bg-ocean-950/50 dark:text-reef">
        —
      </span>
    );
  }

  const text = typeof raw === "string" ? raw.toUpperCase() : String(raw);
  const tone =
    toneMap[text] ||
    "border-line bg-sand text-ocean-800 dark:border-line/40 dark:bg-ocean-950/50 dark:text-sand";

  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${tone}`}
    >
      {text}
    </span>
  );
}
