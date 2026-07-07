import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getRecommendations, getWeaknesses } from "@/api/studentDashboard";
import CourseFilterSelect from "@/student/components/CourseFilterSelect";
import SectionHeader from "@/student/components/SectionHeader";
import SeverityBadge from "@/student/components/SeverityBadge";
import LoadingState from "@/student/components/LoadingState";
import EmptyState from "@/student/components/EmptyState";
import ErrorState from "@/shared/components/ErrorState";

const formatTopicLabel = (tag) => String(tag || "").replace(/_/g, " ");

function RecommendationFocusCard({ item, onStartLesson }) {
  const focusArea = item.focus_area || formatTopicLabel(item.weak_topic_tag);
  const sourceLesson = item.related_lessons_taken?.[0]?.title;
  const lessonTitle = item.lesson?.title || item.lesson_title || "Suggested lesson";
  const courseTitle = item.lesson?.course_title || item.course_title || "";

  return (
    <article className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
        Focus area
      </p>
      <h3 className="mt-1 text-lg font-semibold text-ink dark:text-sand">{focusArea}</h3>

      <dl className="mt-4 space-y-2 text-sm">
        {courseTitle ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
              Course
            </dt>
            <dd className="text-ink dark:text-sand">{courseTitle}</dd>
          </div>
        ) : null}
        {sourceLesson ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
              Found from
            </dt>
            <dd className="text-ink dark:text-sand">{sourceLesson} quiz</dd>
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge level={item.weakness_level} />
          {item.accuracy_percent != null ? (
            <span className="text-xs text-muted dark:text-muted">
              Accuracy {item.accuracy_percent}%
            </span>
          ) : null}
        </div>
      </dl>

      <div className="mt-4 rounded-xl border border-ocean-200/70 bg-reef/60 p-3 dark:border-ocean-600/30 dark:bg-ocean-600/10">
        <p className="text-xs font-semibold uppercase tracking-wide text-ocean-900 dark:text-reef/90">
          Recommended lesson
        </p>
        <p className="mt-1 font-medium text-ink dark:text-sand">{lessonTitle}</p>
        <p className="mt-2 text-sm leading-relaxed text-ocean-800 dark:text-muted">
          <span className="font-medium text-ink dark:text-sand">Why: </span>
          {item.reason}
        </p>
        <button
          type="button"
          onClick={() => onStartLesson(item)}
          className="mt-3 min-h-[44px] rounded-xl bg-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-700"
        >
          Start lesson
        </button>
      </div>
    </article>
  );
}

export default function SuggestionsPanel({ courseFilter, onCourseFilterChange }) {
  const navigate = useNavigate();

  const recsQuery = useQuery({
    queryKey: ["recommendations", courseFilter || "all"],
    queryFn: () => getRecommendations({ courseId: courseFilter || undefined }),
  });
  const weaknessesQuery = useQuery({
    queryKey: ["weaknesses", courseFilter || "all"],
    queryFn: () => getWeaknesses({ courseId: courseFilter || undefined }),
  });

  const showLoading =
    recsQuery.isLoading ||
    recsQuery.isPending ||
    weaknessesQuery.isLoading ||
    weaknessesQuery.isPending;

  const items = Array.isArray(recsQuery.data) ? recsQuery.data : [];
  const weaknessPayload = weaknessesQuery.data ?? {};
  const courses = weaknessPayload.courses ?? [];
  const weaknesses = weaknessPayload.topics ?? [];

  const focusCards = useMemo(() => {
    const withWeakTag = items.filter((item) => item.weak_topic_tag);
    if (withWeakTag.length) return withWeakTag;
    return items;
  }, [items]);

  const handleStudy = (item) => {
    const lessonId = item.lesson?.id ?? item.lesson_id;
    if (lessonId) navigate(`/lessons/${lessonId}`);
    else if (item.course_id) navigate(`/courses/${item.course_id}`);
    else navigate("/catalog");
  };

  const refreshAll = () => {
    void recsQuery.refetch();
    void weaknessesQuery.refetch();
  };

  const hasError = recsQuery.isError || weaknessesQuery.isError;

  return (
    <div className="space-y-6">
      <CourseFilterSelect
        courses={courses}
        value={courseFilter}
        onChange={onCourseFilterChange}
        className="max-w-md"
      />

      {showLoading ? <LoadingState label="Analyzing your learning needs…" rows={4} /> : null}

      {!showLoading && hasError ? (
        <ErrorState message="Could not load suggestions." onRetry={refreshAll} />
      ) : null}

      {!showLoading && !hasError ? (
        <>
          {!weaknesses.length && !items.length ? (
            <EmptyState
              title="No suggestions yet"
              message="Complete at least one quiz so the platform can recommend what to study next."
            />
          ) : null}

          {focusCards.length ? (
            <section className="space-y-4">
              <SectionHeader
                title="Suggested lessons"
                subtitle="Each card ties a weak topic to a lesson you should study next."
              />
              {focusCards.map((item, index) => (
                <RecommendationFocusCard
                  key={item.id ?? `${item.lesson_id}-${index}`}
                  item={item}
                  onStartLesson={handleStudy}
                />
              ))}
            </section>
          ) : weaknesses.length ? (
            <EmptyState
              title="Weak topics detected"
              message="No matching lessons are available yet. More course content may be added soon."
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
