import ProgressBar from "@/student/components/ProgressBar";

export default function CourseCard({ course, progress = 0 }) {
  const title = course?.title ?? "Course";
  const safeProgress = Math.min(100, Math.max(0, Number(progress) || 0));

  return (
    <article className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg transition hover:border-line hover:bg-cream dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl dark:hover:border-line/50 dark:hover:bg-ocean-900/50">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink dark:text-sand">{title}</p>
          <p className="mt-1 text-xs text-muted dark:text-muted">
            {course?.level ? `${course.level} · ` : ""}
            {course?.lesson_count != null ? `${course.lesson_count} lessons` : "Lessons TBD"}
          </p>
        </div>
        <span className="text-xs font-semibold text-ocean-700 dark:text-reef">{Math.round(safeProgress)}%</span>
      </div>
      <div className="mt-3">
        <ProgressBar value={safeProgress} showPercent={false} size="sm" />
      </div>
    </article>
  );
}
