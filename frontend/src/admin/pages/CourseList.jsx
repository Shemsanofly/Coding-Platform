import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { deleteAdminCourse, getAdminCourses, updateAdminCourse } from "@/api/adminCourses";
import AdminTable from "@/admin/components/AdminTable";
import EmptyState from "@/admin/components/EmptyState";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import Button from "@/shared/components/ui/Button";
import { CourseLevelBadge, CourseMetric, CourseStatusPill } from "@/shared/components/course/CourseBadges";

const STATUS_FILTERS = [
  { value: "published", label: "Published" },
  { value: "ready", label: "Ready" },
  { value: "draft", label: "Draft" },
];

const actionLinkClass =
  "inline-flex min-h-9 items-center justify-center rounded-xl border border-ocean-600/20 bg-white px-3 text-xs font-semibold text-ocean-800 transition hover:bg-reef/50 dark:border-white/10 dark:bg-ocean-950/35 dark:text-reef dark:hover:bg-ocean-900/60";

function quizProgressLabel(course) {
  const done = course.quiz_lessons_done ?? 0;
  const total = course.lesson_count ?? 0;
  if (!total) return "No lessons";
  return `${done}/${total} ready`;
}

function matchesCourse(course, query, status) {
  const matchesStatus = course.status === status;
  if (!matchesStatus) return false;
  if (!query) return true;
  const text = `${course.title || ""} ${course.level || ""} ${course.status || ""}`.toLowerCase();
  return text.includes(query.toLowerCase());
}

export default function CourseList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("published");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-courses"],
    queryFn: getAdminCourses,
  });

  const publishMutation = useMutation({
    mutationFn: ({ courseId, status }) => updateAdminCourse(courseId, { status }),
    onSuccess: () => {
      toast.success("Course published.", { id: "course-publish-ok" });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
    },
    onError: () => {
      toast.error("Could not publish course.", { id: "course-publish-err" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAdminCourse,
    onSuccess: () => {
      toast.success("Course deleted.", { id: "course-delete-ok" });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["course-catalog"] });
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not delete course.", {
        id: "course-delete-err",
      });
    },
  });

  const handleDeleteCourse = (course) => {
    const studentCount = course.enrolled_students ?? 0;
    const studentNote =
      studentCount > 0
        ? `\n\n${studentCount} enrolled student${studentCount === 1 ? "" : "s"} will lose access to this course and its progress.`
        : "";
    const confirmed = window.confirm(
      `Permanently delete "${course.title}"?\n\nThis removes all lessons, quizzes, and enrollments.${studentNote}\n\nThis cannot be undone.`,
    );
    if (confirmed) {
      deleteMutation.mutate(course.id);
    }
  };

  const courses = useMemo(() => {
    const rows = Array.isArray(data) ? data : data?.results || [];
    return rows.filter((course) => matchesCourse(course, search.trim(), statusFilter));
  }, [data, search, statusFilter]);

  const allCourses = Array.isArray(data) ? data : data?.results || [];
  const publishedCount = allCourses.filter((course) => course.status === "published").length;
  const draftCount = allCourses.filter((course) => course.status === "draft").length;

  if (isLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading courses..." />
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
        <div className="min-w-[220px]">
          <p className="font-semibold text-ink dark:text-sand">{row.title}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <CourseLevelBadge level={row.level} />
            <CourseStatusPill status={row.status} />
          </div>
        </div>
      ),
    },
    {
      key: "lesson_count",
      label: "Lessons",
      render: (row) => row.lesson_count ?? 0,
    },
    {
      key: "quiz_progress",
      label: "Quizzes",
      render: (row) => quizProgressLabel(row),
    },
    {
      key: "pending_approval_count",
      label: "Pending",
      render: (row) => row.pending_approval_count ?? 0,
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
        return stamp ? new Date(stamp).toLocaleDateString() : "None";
      },
    },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => navigate(`/admin/courses/${row.id}/setup`)} className={actionLinkClass}>
            Setup
          </button>
          {row.status !== "published" ? (
            <Button
              variant="primary"
              size="sm"
              disabled={publishMutation.isPending}
              onClick={() => publishMutation.mutate({ courseId: row.id, status: "published" })}
            >
              Publish
            </Button>
          ) : null}
          <Link to="/admin/analytics" className={actionLinkClass}>
            Analytics
          </Link>
          <Button
            variant="danger"
            size="sm"
            disabled={deleteMutation.isPending}
            onClick={() => handleDeleteCourse(row)}
          >
            Delete
          </Button>
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
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#172433]/85">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink dark:text-sand">Courses</h1>
            <p className="mt-1 text-sm text-muted dark:text-reef/75">
              Manage course status, lessons, quiz readiness, and enrollment impact from one place.
            </p>
          </div>
          <Link to="/admin/courses/new" className="lc-btn-primary w-fit">
            Create course
          </Link>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <CourseMetric label="Total courses" value={allCourses.length} />
          <CourseMetric label="Published" value={publishedCount} />
          <CourseMetric label="Drafts" value={draftCount} />
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search courses by title, level, or status"
            className="lc-input"
          />
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((option) => (
              <Button
                key={option.value}
                variant={statusFilter === option.value ? "primary" : "ghost"}
                size="sm"
                onClick={() => setStatusFilter(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>
      </section>

      {courses.length === 0 ? (
        <EmptyState
          title="No matching courses"
          message={
            search
              ? "Clear the search or choose another status filter."
              : "Choose another status filter or create a new course."
          }
          action={
            <Link to="/admin/courses/new" className="lc-btn-primary">
              Create course
            </Link>
          }
        />
      ) : (
        <section className="overflow-hidden rounded-2xl border border-ocean-600/10 bg-white shadow-sm dark:border-white/10 dark:bg-[#172433]/85">
          <AdminTable columns={columns} rows={tableRows} emptyMessage="No courses found." />
        </section>
      )}
    </div>
  );
}
