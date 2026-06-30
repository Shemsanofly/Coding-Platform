export default function LoadingState({ label = "Loading…", rows = 3 }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-live="polite">
      <p className="text-sm text-muted dark:text-muted">{label}</p>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="h-16 animate-pulse rounded-xl bg-reef/50 dark:bg-ocean-950/60"
        />
      ))}
    </div>
  );
}
