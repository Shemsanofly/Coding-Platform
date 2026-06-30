import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getEnrollments, getLearningPath } from "@/api/studentDashboard";
import CourseFilterSelect from "@/student/components/CourseFilterSelect";
import MetricCard from "@/student/components/MetricCard";
import SectionHeader from "@/student/components/SectionHeader";
import LearningPathStep from "@/student/components/LearningPathStep";
import SeverityBadge from "@/student/components/SeverityBadge";
import ProgressBar from "@/student/components/ProgressBar";
import LoadingState from "@/student/components/LoadingState";
import EmptyState from "@/student/components/EmptyState";

export default function LearningPath() {
  const navigate = useNavigate();
  const [courseFilter, setCourseFilter] = useState("");

  const enrollmentsQuery = useQuery({ queryKey: ["enrollments"], queryFn: getEnrollments });

  const { data, isLoading, isPending, isError, refetch, isFetching } = useQuery({
    queryKey: ["learning-path", courseFilter || "all"],
    queryFn: () => getLearningPath({ courseId: courseFilter || undefined }),
  });

  const showLoading = isLoading || isPending;
  const weakTopics = Array.isArray(data?.weak_topics) ? data.weak_topics : [];
  const path = Array.isArray(data?.learning_path) ? data.learning_path : [];
  const recommended = Array.isArray(data?.recommended_lessons) ? data.recommended_lessons : [];
  const progress = data?.progress ?? {};
  const nextLessonId = progress.next_lesson_id;
  const nextStep = path.find((row) => row.status === "next") ?? path[0];
  const currentStepNumber = progress.current_step ?? nextStep?.step ?? 0;
  const hasPath = path.length > 0;
  const courses = enrollmentsQuery.data ?? [];
  const pageTitle = data?.course_title
    ? `Learning path for ${data.course_title}`
    : "Personalized learning path";

  return (
    <div className="space-y-6 overflow-x-hidden p-4 pb-24 md:pb-6 md:p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-ink dark:text-sand">{pageTitle}</h1>
          <p className="mt-1 text-sm text-muted dark:text-muted">
            A guided study plan from your weak topics, quiz history, and recommendations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="min-h-[44px] rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink transition hover:bg-sand disabled:opacity-50 dark:border-line/40 dark:text-sand dark:hover:bg-ocean-900/50"
        >
          {isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      <CourseFilterSelect
        courses={courses}
        value={courseFilter}
        onChange={setCourseFilter}
        className="max-w-md"
      />

      {showLoading ? <LoadingState label="Building your learning path…" rows={4} /> : null}

      {!showLoading && isError ? (
        <EmptyState
          title="Could not load your learning path"
          message="Check your connection and try refreshing the page."
        />
      ) : null}

      {!showLoading && !isError ? (
        <>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MetricCard
              title="Course progress"
              value={`${progress.percent_complete ?? 0}%`}
              helper={`${progress.lessons_completed ?? 0} of ${progress.total_enrolled_lessons ?? 0} lessons`}
              color="blue"
            />
            <MetricCard
              title="Current step"
              value={hasPath ? currentStepNumber : "—"}
              helper={hasPath ? `${progress.path_steps ?? path.length} steps in your path` : "No steps yet"}
              color="green"
            />
            <article className="rounded-2xl border border-emerald-200/50 bg-emerald-50/80 p-4 shadow-lg dark:border-emerald-400/30 dark:bg-emerald-500/10">
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-800 dark:text-emerald-100/90">
                Next lesson
              </p>
              {nextStep ? (
                <>
                  <p className="mt-2 text-lg font-bold text-ink dark:text-sand">{nextStep.lesson_title}</p>
                  <button
                    type="button"
                    onClick={() => navigate(`/lessons/${nextLessonId ?? nextStep.lesson_id}`)}
                    className="mt-3 min-h-[44px] w-full rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 sm:w-auto"
                  >
                    Start next lesson
                  </button>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted dark:text-muted">
                  Take more quizzes to build your personalized learning path.
                </p>
              )}
            </article>
          </section>

          <ProgressBar value={progress.percent_complete} label="Overall completion" size="lg" />

          <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
            <SectionHeader
              title="Weak topics driving your path"
              subtitle="These topics influence lesson ordering."
            />
            {weakTopics.length === 0 ? (
              <EmptyState
                title="No weak topics yet"
                message="Complete quizzes to populate this list and unlock a personalized path."
              />
            ) : (
              <ul className="divide-y divide-line dark:divide-line/30">
                {weakTopics.map((topic) => (
                  <li
                    key={topic.id ?? topic.topic_tag}
                    className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-ink dark:text-sand">
                        {(topic.topic_tag || topic.topic || "").replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-muted dark:text-muted">
                        Accuracy {topic.accuracy_percent ?? topic.score ?? 0}% · {topic.attempt_count ?? 0} attempts
                      </p>
                    </div>
                    <SeverityBadge level={topic.weakness_level} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
            <SectionHeader title="Your study sequence" subtitle="Up next, then upcoming steps." />
            {!hasPath ? (
              <EmptyState
                title="No path steps yet"
                message="Take more quizzes to build your personalized learning path."
              />
            ) : (
              <ol className="space-y-3">
                {path.map((step) => (
                  <LearningPathStep
                    key={`${step.step}-${step.lesson_id}`}
                    step={step}
                    onSelect={() => navigate(`/lessons/${step.lesson_id}`)}
                  />
                ))}
              </ol>
            )}
          </section>

          {recommended.length > 0 ? (
            <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
              <SectionHeader title="Also recommended" />
              <ul className="divide-y divide-line dark:divide-line/30">
                {recommended.slice(0, 6).map((item) => (
                  <li key={item.lesson_id} className="py-3 first:pt-0">
                    <button
                      type="button"
                      onClick={() => navigate(`/lessons/${item.lesson_id}`)}
                      className="min-h-[44px] text-left text-sm font-medium text-ocean-700 hover:underline dark:text-reef"
                    >
                      {item.lesson_title}
                    </button>
                    <p className="text-xs text-muted dark:text-muted">{item.reason}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
