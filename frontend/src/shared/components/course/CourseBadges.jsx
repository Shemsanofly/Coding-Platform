const levelStyles = {
  beginner:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
  intermediate:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100",
  advanced:
    "border-coral/30 bg-coral/10 text-ocean-950 dark:border-coral/40 dark:bg-coral/15 dark:text-sand",
};

const statusStyles = {
  draft:
    "border-slate-200 bg-slate-50 text-slate-700 dark:border-white/10 dark:bg-white/10 dark:text-reef",
  ready:
    "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-400/30 dark:bg-blue-500/15 dark:text-blue-100",
  published:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
};

export function formatCourseLevel(level) {
  if (!level) return "Beginner";
  const text = String(level).replace(/_/g, " ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

export function CourseLevelBadge({ level, className = "" }) {
  return (
    <span
      className={`inline-flex min-h-6 items-center rounded-full border px-2.5 text-xs font-semibold ${levelStyles[level] ?? levelStyles.beginner} ${className}`.trim()}
    >
      {formatCourseLevel(level)}
    </span>
  );
}

export function CourseStatusPill({ status, className = "" }) {
  const label = status ? formatCourseLevel(status) : "Draft";
  return (
    <span
      className={`inline-flex min-h-6 items-center rounded-full border px-2.5 text-xs font-semibold ${statusStyles[status] ?? statusStyles.draft} ${className}`.trim()}
    >
      {label}
    </span>
  );
}

export function CourseMetric({ label, value }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium text-muted dark:text-reef/70">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-ink dark:text-sand">{value}</p>
    </div>
  );
}
