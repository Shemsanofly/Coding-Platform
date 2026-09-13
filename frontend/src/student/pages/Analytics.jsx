import { useQuery } from "@tanstack/react-query";
import { getAnalyticsSummary, getEnrollments, getWeaknesses } from "@/api/studentDashboard";
import DashboardAnalytics from "@/student/components/DashboardAnalytics";
import LoadingState from "@/student/components/LoadingState";
import SectionHeader from "@/student/components/SectionHeader";
import PageHeader from "@/shared/components/ui/PageHeader";
import Card from "@/shared/components/ui/Card";
import ErrorState from "@/shared/components/ErrorState";

export default function Analytics() {
  const analyticsQuery = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: getAnalyticsSummary,
  });
  const enrollmentsQuery = useQuery({ queryKey: ["enrollments"], queryFn: getEnrollments });
  const weaknessesQuery = useQuery({ queryKey: ["weaknesses"], queryFn: getWeaknesses });

  const isLoading =
    analyticsQuery.isLoading || enrollmentsQuery.isLoading || weaknessesQuery.isLoading;
  const isError = analyticsQuery.isError || enrollmentsQuery.isError || weaknessesQuery.isError;

  const refetchAll = () => {
    void analyticsQuery.refetch();
    void enrollmentsQuery.refetch();
    void weaknessesQuery.refetch();
  };

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <PageHeader
        title="Analytics"
        subtitle="Quiz trends, completion, and weak-topic breakdown across your courses."
      />

      {isError ? (
        <ErrorState message="Could not load analytics." onRetry={refetchAll} />
      ) : isLoading ? (
        <LoadingState label="Loading analytics…" rows={4} />
      ) : (
        <>
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card padding="sm">
              <p className="text-xs text-muted dark:text-reef/80">Avg quiz score</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {Math.round(Number(analyticsQuery.data?.avg_quiz_score) || 0)}%
              </p>
            </Card>
            <Card padding="sm">
              <p className="text-xs text-muted dark:text-reef/80">Quiz attempts</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.quiz_attempts_total ?? 0}
              </p>
            </Card>
            <Card padding="sm">
              <p className="text-xs text-muted dark:text-reef/80">Lessons passed</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.lessons_passed_quiz ?? 0}
              </p>
            </Card>
            <Card padding="sm">
              <p className="text-xs text-muted dark:text-reef/80">Weak topics</p>
              <p className="mt-1 text-xl font-bold text-ink dark:text-sand">
                {analyticsQuery.data?.weak_topics_tracked ??
                  weaknessesQuery.data?.topics?.length ??
                  0}
              </p>
            </Card>
          </section>

          <DashboardAnalytics
            analytics={analyticsQuery.data ?? {}}
            weaknesses={weaknessesQuery.data?.topics ?? []}
            enrollments={enrollmentsQuery.data ?? []}
          />

          <Card>
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
          </Card>
        </>
      )}
    </div>
  );
}
