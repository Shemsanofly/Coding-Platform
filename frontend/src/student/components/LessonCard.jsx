import SeverityBadge from "@/student/components/SeverityBadge";
import ScoreBadge from "@/student/components/ScoreBadge";

export default function LessonCard({
  title,
  courseTitle,
  reason,
  weakTopic,
  weaknessLevel,
  score,
  passed,
  onStart,
  compact = false,
}) {
  return (
    <article
      className={`rounded-xl border border-ocean-600/10 bg-cream transition dark:border-line/40 dark:bg-ocean-950/40 ${
        onStart ? "hover:border-line hover:bg-sand dark:hover:border-line/50 dark:hover:bg-ocean-900/50" : ""
      } ${compact ? "p-3" : "p-4"}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink dark:text-sand">{title}</p>
          {courseTitle ? (
            <p className="mt-0.5 text-xs text-muted dark:text-reef/90">{courseTitle}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {weaknessLevel ? <SeverityBadge level={weaknessLevel} /> : null}
          {score != null ? <ScoreBadge score={score} passed={passed} /> : null}
        </div>
      </div>
      {weakTopic ? (
        <p className="mt-2 text-xs text-muted dark:text-reef/90">
          Weak topic: <span className="font-medium text-ocean-800 dark:text-reef">{weakTopic}</span>
        </p>
      ) : null}
      {reason ? <p className="mt-2 text-xs leading-relaxed text-muted dark:text-muted">{reason}</p> : null}
      {onStart ? (
        <button
          type="button"
          onClick={onStart}
          className="mt-3 min-h-[40px] rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
        >
          Start lesson
        </button>
      ) : null}
    </article>
  );
}
