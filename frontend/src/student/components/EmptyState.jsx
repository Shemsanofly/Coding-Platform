export default function EmptyState({ title, message, action }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-cream/80 px-4 py-8 text-center dark:border-line/40 dark:bg-ocean-950/40">
      <p className="text-sm font-semibold text-ink dark:text-sand">{title}</p>
      {message ? <p className="mt-2 text-sm text-muted dark:text-muted">{message}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
