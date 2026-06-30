import { useQuery } from "@tanstack/react-query";
import {
  getAnalyticsSummary,
  getEnrollments,
  getWeaknesses,
} from "@/api/studentDashboard";
import DashboardAnalytics from "@/student/components/DashboardAnalytics";
import LoadingState from "@/student/components/LoadingState";
import SectionHeader from "@/student/components/SectionHeader";

export default function Analytics() {
  const analyticsQuery = useQuery({ queryKey: ["analytics-summary"], queryFn: getAnalyticsSummary });
  const enrollmentsQuery = useQuery({ queryKey: ["enrollments"], queryFn: getEnrollments });
  const weaknessesQuery = useQuery({ queryKey: ["weaknesses"], queryFn: getWeaknesses });

  const isLoading =
    analyticsQuery.isLoading || enrollmentsQuery.isLoading || weaknessesQuery.isLoading;

  return (
    <div className="space-y-6 overflow-x-hidden p-4 pb-24 md:pb-6 md:p-6">
      <header className="min-w-0">
        <h1 className="text-2xl font-bold text-ink dark:text-sand">Analytics</h1>
        <p className="mt-1 text-sm text-muted dark:text-muted">
          Quiz trends, completion, and weak-topic breakdown across your courses.
        </p>
      </header>

      {isLoading ? (
        <LoadingState label="Loading analytics…" rows={4} />
      ) : (
        <>
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <article className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/30 dark:bg-ocean-950/40">
              <p className="text-xs text-muted dark:text-reef/80">Avg quiz score</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {Math.round(Number(analyticsQuery.data?.avg_quiz_score) || 0)}%
              </p>
            </article>
            <article className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/30 dark:bg-ocean-950/40">
              <p className="text-xs text-muted dark:text-reef/80">Quiz attempts</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.quiz_attempts_total ?? 0}
              </p>
            </article>
            <article className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/30 dark:bg-ocean-950/40">
              <p className="text-xs text-muted dark:text-reef/80">Lessons passed</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.lessons_passed_quiz ?? 0}
              </p>
            </article>
            <article className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/30 dark:bg-ocean-950/40">
              <p className="text-xs text-muted dark:text-reef/80">Weak topics</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.weak_topics_tracked ?? weaknessesQuery.data?.topics?.length ?? 0}
              </p>
            </article>
          </section>

          <DashboardAnalytics
            analytics={analyticsQuery.data ?? {}}
            weaknesses={weaknessesQuery.data?.topics ?? []}
            enrollments={enrollmentsQuery.data ?? []}
          />

          <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 dark:border-line/30 dark:bg-ocean-950/40">
            <SectionHeader title="Recent quiz activity" subtitle="Latest submissions." />
            {(analyticsQuery.data?.recent_quiz_scores ?? []).length === 0 ? (
              <p className="text-sm text-muted dark:text-muted">No quiz attempts yet.</p>
            ) : (
              <ul className="divide-y divide-line dark:divide-line/30">
                {(analyticsQuery.data.recent_quiz_scores ?? []).map((row, index) => (
                  <li
                    key={`${row.taken_at}-${index}`}
                    className="flex items-center justify-between gap-2 py-3 first:pt-0"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink dark:text-sand">
                        {row.lesson_title || "Quiz"}
                      </p>
                      <p className="text-xs text-muted dark:text-reef/90">
                        {row.taken_at ? new Date(row.taken_at).toLocaleString() : ""}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm font-semibold tabular-nums text-ocean-800 dark:text-reef">
                      {Math.round(Number(row.score) || 0)}%
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
