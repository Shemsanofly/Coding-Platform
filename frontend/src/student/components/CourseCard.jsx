import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";

const levelColors = {
  beginner: "bg-reef/80 text-ocean-800 dark:bg-ocean-600/20 dark:text-reef",
  intermediate: "bg-sand text-ocean-900 dark:bg-spice/20 dark:text-sand",
  advanced: "bg-coral/15 text-ocean-900 dark:bg-coral/20 dark:text-sand",
};

export default function CourseCard({ course, onOpen, onEnroll, enrolling }) {
  const levelClass = levelColors[course.level] ?? levelColors.beginner;

  return (
    <Card
      as="li"
      className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-ink dark:text-sand">{course.title}</h2>
          {course.is_enrolled ? (
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200">
              Enrolled
            </span>
          ) : null}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted dark:text-muted">
          <span className={`rounded-full px-2.5 py-0.5 font-semibold capitalize ${levelClass}`}>
            {course.level}
          </span>
          <span>{course.lesson_count ?? 0} lessons</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        {course.is_enrolled ? (
          <Button variant="gradient" onClick={() => onOpen(course.id)}>
            Open course
          </Button>
        ) : (
          <Button variant="gradient" loading={enrolling} onClick={() => onEnroll(course.id)}>
            Enroll
          </Button>
        )}
      </div>
    </Card>
  );
}
