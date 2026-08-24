import Button from "@/shared/components/ui/Button";
import { CourseLevelBadge, CourseMetric, CourseStatusPill } from "@/shared/components/course/CourseBadges";

export default function CourseCard({ course, onOpen, onEnroll, enrolling }) {
  const isEnrolled = Boolean(course.is_enrolled);
  const lessonCount = course.lesson_count ?? 0;
  const status = course.status || "published";

  return (
    <article className="group flex h-full min-h-[220px] flex-col justify-between rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-ocean-600/20 hover:shadow-lg dark:border-white/10 dark:bg-[#172433]/85 dark:hover:bg-[#1b2b3b]">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="line-clamp-2 text-lg font-bold leading-snug text-ink dark:text-sand">
              {course.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted dark:text-reef/75">
              {isEnrolled
                ? "Continue your lessons and quizzes from the course workspace."
                : "Enroll to unlock the lesson sequence, quizzes, and progress tracking."}
            </p>
          </div>
          {isEnrolled ? (
            <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100">
              Enrolled
            </span>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <CourseLevelBadge level={course.level} />
          <CourseStatusPill status={status} />
        </div>
      </div>

      <div className="mt-6 flex items-end justify-between gap-4 border-t border-line/70 pt-4 dark:border-white/10">
        <CourseMetric label="Lessons" value={lessonCount} />
        <Button
          variant={isEnrolled ? "primary" : "gradient"}
          loading={enrolling}
          onClick={() => (isEnrolled ? onOpen(course.id) : onEnroll(course.id))}
          className="shrink-0"
        >
          {isEnrolled ? "Open course" : "Enroll"}
        </Button>
      </div>
    </article>
  );
}
