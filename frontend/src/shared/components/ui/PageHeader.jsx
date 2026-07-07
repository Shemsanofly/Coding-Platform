export default function PageHeader({ title, subtitle, actions, className = "" }) {
  return (
    <header className={`flex flex-wrap items-end justify-between gap-3 ${className}`.trim()}>
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-ink dark:text-sand">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted dark:text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
