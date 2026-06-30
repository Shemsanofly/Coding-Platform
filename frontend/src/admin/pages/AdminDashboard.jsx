import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { bootstrapCourseCatalog, getAdminDashboardSummary } from "@/api/adminCourses";
import AdminMetricCard from "@/admin/components/AdminMetricCard";
import EmptyState from "@/admin/components/EmptyState";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";

const formatDateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
};

export default function AdminDashboard() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-dashboard-summary"],
    queryFn: getAdminDashboardSummary,
  });

  const bootstrapMutation = useMutation({
    mutationFn: bootstrapCourseCatalog,
    onSuccess: (result) => {
      toast.success(`Starter catalog loaded (${result?.created_count ?? 0} new course(s)).`);
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["course-catalog"] });
    },
    onError: () => {
      toast.error("Could not load starter catalog.");
    },
  });

  if (isLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading dashboard…" rows={5} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState message="Could not load dashboard metrics." onRetry={() => refetch()} />
      </div>
    );
  }

  const metrics = [
    { title: "Total courses", value: data?.total_courses ?? 0, color: "slate" },
    { title: "Published", value: data?.published_courses ?? 0, color: "green" },
    { title: "Ready", value: data?.ready_courses ?? 0, color: "blue" },
    { title: "Draft", value: data?.draft_courses ?? 0, color: "amber" },
    { title: "Students", value: data?.total_students ?? 0, color: "purple" },
    { title: "Active enrollments", value: data?.active_enrollments ?? 0, color: "blue" },
    { title: "AI quizzes generated", value: data?.ai_quizzes_generated ?? 0, color: "green" },
    { title: "Pending approvals", value: data?.pending_quiz_approvals ?? 0, color: "amber" },
    { title: "Failed AI runs", value: data?.failed_ai_generations ?? 0, color: "rose" },
  ];

  const weakTopics = data?.top_weak_topics || [];
  const activity = data?.recent_activity || [];
  const hasCourses = (data?.total_courses ?? 0) > 0;

  return (
    <div className="space-y-6 p-4 md:p-6">
      {!hasCourses ? (
        <section className="rounded-2xl border border-ocean-200 bg-reef/40 p-5 shadow-panel">
          <h2 className="text-lg font-semibold text-ocean-950">No courses yet</h2>
          <p className="mt-1 text-sm text-muted">
            Students will see an empty catalog until you create or load starter courses.
          </p>
          <button
            type="button"
            disabled={bootstrapMutation.isPending}
            onClick={() => bootstrapMutation.mutate()}
            className="lc-btn-primary mt-4"
          >
            {bootstrapMutation.isPending ? "Loading starter catalog…" : "Load starter catalog"}
          </button>
        </section>
      ) : null}

      <header className="rounded-2xl border border-ocean-600/10 bg-white/90 p-5 shadow-panel backdrop-blur">
        <h1 className="text-xl font-semibold text-ink">Admin dashboard</h1>
        <p className="mt-1 text-sm text-muted">
          Course management, AI quiz pipeline, student progress, and system health at a glance.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to="/admin/courses"
            className="inline-flex min-h-10 items-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500"
          >
            Manage courses
          </Link>
          <Link
            to="/admin/users"
            className="inline-flex min-h-10 items-center rounded-xl border border-line px-4 text-sm font-semibold text-ocean-800 hover:bg-cream"
          >
            View students
          </Link>
          <Link
            to="/admin/analytics"
            className="inline-flex min-h-10 items-center rounded-xl border border-line px-4 text-sm font-semibold text-ocean-800 hover:bg-cream"
          >
            Analytics
          </Link>
        </div>
      </header>

      <section className="rounded-2xl border border-emerald-100 bg-white/90 p-5 shadow-lg backdrop-blur">
        <h2 className="text-lg font-semibold text-ink">Reports Center</h2>
        <p className="mt-1 text-sm text-muted">
          Download official platform, course, student, weakness, and AI generation reports.
        </p>
        <Link
          to="/admin/reports"
          className="mt-4 inline-flex min-h-10 items-center rounded-xl border border-emerald-200 px-4 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"
        >
          Open Reports
        </Link>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <AdminMetricCard key={metric.title} {...metric} />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <article className="rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur">
          <h2 className="text-lg font-semibold text-ink">Top weak topics</h2>
          <p className="mt-1 text-sm text-muted">Across all students on the platform.</p>
          {weakTopics.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No weak topics yet" message="Weakness data appears after students take quizzes." />
            </div>
          ) : (
            <ul className="mt-4 space-y-2">
              {weakTopics.map((topic) => (
                <li
                  key={topic.topic_tag}
                  className="flex items-center justify-between rounded-lg border border-line/70 bg-cream px-3 py-2 text-sm"
                >
                  <span className="font-medium text-ink">{topic.topic_tag}</span>
                  <span className="text-muted">{topic.student_count} students</span>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur">
          <h2 className="text-lg font-semibold text-ink">Recent activity</h2>
          <p className="mt-1 text-sm text-muted">Latest quiz attempts in your courses.</p>
          {activity.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No recent activity" message="Quiz attempts from enrolled students will show here." />
            </div>
          ) : (
            <ul className="mt-4 max-h-72 space-y-2 overflow-y-auto">
              {activity.map((item, index) => (
                <li
                  key={`${item.taken_at}-${index}`}
                  className="rounded-lg border border-line/70 bg-cream px-3 py-2 text-sm"
                >
                  <p className="font-medium text-ink">{item.lesson_title}</p>
                  <p className="text-muted">
                    {item.student_email} · {item.score}% · {formatDateTime(item.taken_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      {(data?.pending_quiz_approvals ?? 0) > 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <span className="font-semibold">{data.pending_quiz_approvals} lesson(s)</span> need quiz approval before
          students can take them. Open{" "}
          <Link to="/admin/courses" className="font-semibold underline">
            course setup
          </Link>{" "}
          to review.
        </div>
      ) : null}

      {(data?.failed_ai_generations ?? 0) > 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="font-semibold">{data.failed_ai_generations} failed</span> AI generation(s). Check lesson
          errors in course setup.
        </div>
      ) : null}
    </div>
  );
}
