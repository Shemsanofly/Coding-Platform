import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { bootstrapCourseCatalog, getAdminDashboardSummary } from "@/api/adminCourses";
import AdminMetricCard from "@/admin/components/AdminMetricCard";
import EmptyState from "@/admin/components/EmptyState";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import PageHeader from "@/shared/components/ui/PageHeader";
import Card from "@/shared/components/ui/Card";

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

  const activity = data?.recent_activity || [];
  const hasCourses = (data?.total_courses ?? 0) > 0;
  const pendingApprovals = data?.pending_quiz_approvals ?? 0;

  return (
    <div className="space-y-6 p-4 md:p-6">
      {pendingApprovals > 0 ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50/90 p-4 shadow-panel">
          <h2 className="text-base font-semibold text-amber-950">
            {pendingApprovals} quiz{pendingApprovals === 1 ? "" : "zes"} awaiting approval
          </h2>
          <p className="mt-1 text-sm text-amber-900/90">
            Review and publish AI-generated questions before students can take these quizzes.
          </p>
          <Link to="/admin/courses" className="lc-btn-primary mt-3 inline-flex">
            Review courses
          </Link>
        </section>
      ) : null}

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

      <PageHeader
        title="Admin dashboard"
        subtitle="Course management, AI quiz pipeline, student progress, and system health at a glance."
        actions={
          <>
            <Link to="/admin/courses" className="lc-btn-primary">
              Manage courses
            </Link>
            <Link to="/admin/users" className="lc-btn-ghost">
              View students
            </Link>
            <Link to="/admin/analytics" className="lc-btn-ghost">
              Analytics
            </Link>
          </>
        }
      />

      <Card variant="subtle">
        <h2 className="text-lg font-semibold text-ink">Reports Center</h2>
        <p className="mt-1 text-sm text-muted">
          Download official platform, course, student, weakness, and AI generation reports.
        </p>
        <Link to="/admin/reports" className="lc-btn-ghost mt-4 inline-flex">
          Open Reports
        </Link>
      </Card>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <AdminMetricCard key={metric.title} {...metric} />
        ))}
      </section>

      <section>
        <Card variant="subtle">
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
        </Card>
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
