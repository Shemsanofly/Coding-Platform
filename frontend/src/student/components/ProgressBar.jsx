export default function ProgressBar({ value = 0, label, showPercent = true, size = "md", className = "" }) {
  const safe = Math.min(100, Math.max(0, Number(value) || 0));
  const height = size === "sm" ? "h-1.5" : size === "lg" ? "h-3" : "h-2";

  return (
    <div className={className}>
      {(label || showPercent) && (
        <div className="mb-1.5 flex items-center justify-between gap-2 text-xs text-muted dark:text-muted">
          {label ? <span className="font-medium text-ink dark:text-sand">{label}</span> : <span />}
          {showPercent ? <span className="font-semibold tabular-nums text-ocean-700 dark:text-reef">{Math.round(safe)}%</span> : null}
        </div>
      )}
      <div className={`w-full overflow-hidden rounded-full bg-reef/50 dark:bg-ocean-950/60 ${height}`}>
        <div
          className={`${height} rounded-full bg-gradient-to-r from-coral to-ocean-600 transition-[width] duration-300`}
          style={{ width: `${safe}%` }}
          role="progressbar"
          aria-valuenow={Math.round(safe)}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
