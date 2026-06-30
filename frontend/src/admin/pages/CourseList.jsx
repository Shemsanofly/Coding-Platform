import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAdminCourses, updateAdminCourse } from "@/api/adminCourses";
import AdminTable from "@/admin/components/AdminTable";
import CourseStatusBadge from "@/admin/components/CourseStatusBadge";
import EmptyState from "@/admin/components/EmptyState";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";

const quizProgressLabel = (course) => {
  const done = course.quiz_lessons_done ?? 0;
  const total = course.lesson_count ?? 0;
  if (!total) return "—";
  return `${done}/${total} quizzes ready`;
};

export default function CourseList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-courses"],
    queryFn: getAdminCourses,
  });

  const publishMutation = useMutation({
    mutationFn: ({ courseId, status }) => updateAdminCourse(courseId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
    },
  });

  const courses = Array.isArray(data) ? data : data?.results || [];

  if (isLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading courses…" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState message="Could not load courses." onRetry={() => refetch()} />
      </div>
    );
  }

  const columns = [
    {
      key: "title",
      label: "Course",
      render: (row) => (
        <div>
          <p className="font-medium text-ink">{row.title}</p>
          <p className="text-xs text-muted capitalize">{row.level}</p>
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (row) => <CourseStatusBadge status={row.status} />,
    },
    {
      key: "lesson_count",
      label: "Lessons",
      render: (row) => row.lesson_count ?? 0,
    },
    {
      key: "quiz_progress",
      label: "Quiz progress",
      render: (row) => quizProgressLabel(row),
    },
    {
      key: "pending_approval_count",
      label: "Pending",
      render: (row) => row.pending_approval_count ?? 0,
    },
    {
      key: "failed_generation_count",
      label: "Failed",
      render: (row) =>
        (row.failed_generation_count ?? 0) > 0 ? (
          <span className="font-semibold text-red-600">{row.failed_generation_count}</span>
        ) : (
          "0"
        ),
    },
    {
      key: "enrolled_students",
      label: "Students",
      render: (row) => row.enrolled_students ?? 0,
    },
    {
      key: "last_updated",
      label: "Updated",
      render: (row) => {
        const stamp = row.last_updated || row.created_at;
        return stamp ? new Date(stamp).toLocaleDateString() : "—";
      },
    },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => navigate(`/admin/courses/${row.id}/setup`)}
            className="inline-flex min-h-9 items-center rounded-lg border border-emerald-200 px-2.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
          >
            Setup
          </button>
          {row.status !== "published" ? (
            <button
              type="button"
              disabled={publishMutation.isPending}
              onClick={() => publishMutation.mutate({ courseId: row.id, status: "published" })}
              className="inline-flex min-h-9 items-center rounded-lg bg-emerald-600 px-2.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              Publish
            </button>
          ) : null}
          <Link
            to="/admin/analytics"
            className="inline-flex min-h-9 items-center rounded-lg border border-line px-2.5 text-xs font-semibold text-muted hover:bg-cream"
          >
            Analytics
          </Link>
        </div>
      ),
    },
  ];

  const tableRows = courses.map((course) => ({
    ...course,
    cardTitle: course.title,
  }));

  return (
    <div className="space-y-5 p-4 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur">
        <div>
          <h1 className="text-xl font-semibold text-ink">Courses</h1>
          <p className="mt-1 text-sm text-muted">Status, quiz pipeline, enrollments, and quick actions.</p>
        </div>
        <Link
          to="/admin/courses/new"
          className="inline-flex min-h-10 items-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500"
        >
          Create course
        </Link>
      </header>

      {courses.length === 0 ? (
        <EmptyState
          title="No courses yet"
          message="Create your first course to add YouTube lessons and AI-generated quizzes."
          action={
            <Link
              to="/admin/courses/new"
              className="inline-flex min-h-10 items-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white"
            >
              Create course
            </Link>
          }
        />
      ) : (
        <section className="overflow-hidden rounded-2xl border border-emerald-100 bg-white/90 shadow-lg backdrop-blur">
          <AdminTable columns={columns} rows={tableRows} emptyMessage="No courses found." />
        </section>
      )}
    </div>
  );
}
