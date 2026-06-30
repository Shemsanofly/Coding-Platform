export default function RecommendationLessonCard({ lessonTitle, courseTitle, reason, onStudy }) {
  return (
    <article className="rounded-xl border border-ocean-200/70 bg-reef/50 p-4 dark:border-ocean-600/30 dark:bg-ocean-600/10">
      <p className="text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef/90">
        Recommended lesson
      </p>
      <p className="mt-1 text-sm font-semibold text-ink dark:text-sand">{lessonTitle}</p>
      {courseTitle ? (
        <p className="mt-0.5 text-xs text-muted dark:text-reef/90">{courseTitle}</p>
      ) : null}
      {reason ? (
        <p className="mt-2 text-xs leading-relaxed text-muted dark:text-muted">{reason}</p>
      ) : null}
      {onStudy ? (
        <button
          type="button"
          onClick={onStudy}
          className="mt-3 min-h-[44px] w-full rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 sm:w-auto"
        >
          Study this lesson
        </button>
      ) : null}
    </article>
  );
}
