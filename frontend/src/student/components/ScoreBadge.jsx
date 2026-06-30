export default function ScoreBadge({ score, passed, threshold = 60 }) {
  const numeric = Number(score);
  const safe = Number.isFinite(numeric) ? Math.round(numeric) : 0;
  const didPass = typeof passed === "boolean" ? passed : safe >= threshold;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
        didPass
          ? "bg-reef text-ocean-800 dark:bg-emerald-500/25 dark:text-emerald-100"
          : "bg-rose-100 text-rose-900 dark:bg-rose-500/25 dark:text-rose-100"
      }`}
    >
      <span className="tabular-nums">{safe}%</span>
      <span className="opacity-80">·</span>
      <span>{didPass ? "Pass" : "Fail"}</span>
    </span>
  );
}
