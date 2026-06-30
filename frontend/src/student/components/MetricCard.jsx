const colorMap = {
  blue: "border-ocean-200/50 bg-reef/80 dark:border-ocean-600/30 dark:bg-ocean-600/10",
  green: "border-ocean-200/50 bg-reef/60 dark:border-ocean-600/30 dark:bg-ocean-600/10",
  purple: "border-coral/20 bg-sand dark:border-coral/30 dark:bg-coral/10",
  amber: "border-spice/30 bg-sand dark:border-spice/30 dark:bg-spice/10",
  rose: "border-coral/30 bg-sand dark:border-coral/30 dark:bg-coral/10",
  slate: "border-ocean-600/10 bg-white dark:border-line/40 dark:bg-ocean-950/50",
};

export default function MetricCard({ title, value, helper, icon, color = "slate" }) {
  const palette = colorMap[color] || colorMap.slate;

  return (
    <article
      className={`rounded-2xl border p-4 shadow-md transition dark:shadow-xl dark:backdrop-blur-xl ${palette}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted dark:text-muted">
            {title}
          </p>
          <p className="mt-2 truncate text-2xl font-bold text-ink dark:text-sand">{value}</p>
          {helper ? (
            <p className="mt-1 text-xs leading-relaxed text-muted dark:text-muted/90">{helper}</p>
          ) : null}
        </div>
        {icon ? (
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/80 text-ocean-800 dark:bg-ocean-950/50 dark:text-reef"
            aria-hidden="true"
          >
            {icon}
          </span>
        ) : null}
      </div>
    </article>
  );
}
