import SeverityBadge from "@/student/components/SeverityBadge";

const statusStyles = {
  next: "border-emerald-400/60 bg-emerald-50 dark:border-emerald-400/50 dark:bg-emerald-500/15",
  upcoming: "border-ocean-600/10 bg-cream dark:border-line/40 dark:bg-ocean-950/40",
  completed: "border-line/60 bg-sand/80 opacity-80 dark:border-line/30 dark:bg-ocean-950/40",
};

export default function LearningPathStep({ step, onSelect }) {
  const status = step?.status || "upcoming";
  const shell = statusStyles[status] ?? statusStyles.upcoming;

  const inner = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-reef/50 text-xs font-bold text-ink dark:bg-white/20 dark:text-sand">
          {step.step}
        </span>
        <p className="font-semibold text-ink dark:text-sand">{step.lesson_title}</p>
        {status === "next" ? (
          <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
            Up next
          </span>
        ) : null}
        {status === "completed" ? (
          <span className="rounded-full bg-cream0/20 px-2 py-0.5 text-[10px] font-bold uppercase text-ocean-800 dark:text-reef">
            Done
          </span>
        ) : null}
        {step.weakness_level ? <SeverityBadge level={step.weakness_level} /> : null}
      </div>
      <p className="mt-1 text-xs text-muted dark:text-reef/90">{step.course_title}</p>
      {step.reason ? <p className="mt-2 text-xs text-muted dark:text-muted">{step.reason}</p> : null}
    </>
  );

  if (onSelect) {
    return (
      <li>
        <button
          type="button"
          onClick={onSelect}
          className={`w-full rounded-xl border p-4 text-left transition hover:opacity-95 ${shell}`}
        >
          {inner}
        </button>
      </li>
    );
  }

  return (
    <li className={`rounded-xl border p-4 ${shell}`}>
      {inner}
    </li>
  );
}
