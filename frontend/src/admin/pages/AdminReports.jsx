import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getAdminCourses } from "@/api/adminCourses";
import { getAdminUsers } from "@/api/adminUsers";
import {
  downloadAdminAIGenerationReport,
  downloadAdminCoursesReport,
  downloadAdminStudentsReport,
  downloadAdminSummaryReport,
  downloadAdminWeaknessesReport,
} from "@/api/reports";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

function ReportCard({ title, description, onDownload, isLoading, errorMessage }) {
  return (
    <article className="flex h-full flex-col rounded-2xl border border-emerald-100 bg-white/90 p-5 shadow-lg backdrop-blur">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-2 flex-1 text-sm text-muted">{description}</p>
      {errorMessage ? (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{errorMessage}</p>
      ) : null}
      <button
        type="button"
        disabled={isLoading}
        onClick={onDownload}
        className="mt-4 inline-flex min-h-10 items-center justify-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Preparing PDF…" : "Download PDF"}
      </button>
    </article>
  );
}

export default function AdminReports() {
  const [activeKey, setActiveKey] = useState(null);
  const [lastError, setLastError] = useState("");
  const [courseFilter, setCourseFilter] = useState("");
  const [studentFilter, setStudentFilter] = useState("");

  const coursesQuery = useQuery({ queryKey: ["admin-courses"], queryFn: getAdminCourses });
  const studentsQuery = useQuery({ queryKey: ["admin-users"], queryFn: () => getAdminUsers() });

  const downloadMutation = useMutation({
    mutationFn: async ({ key, fn, filename, params }) => {
      setActiveKey(key);
      setLastError("");
      const response = await fn(params);
      triggerBlobDownload(response, filename);
    },
    onSuccess: () => {
      toast.success("Report downloaded.", { id: "reports-center-ok" });
      setActiveKey(null);
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail;
      const message =
        typeof detail === "string" ? detail : "Could not download report. Check that data exists for this report.";
      setLastError(message);
      toast.error(message, { id: "reports-center-err" });
      setActiveKey(null);
    },
  });

  const download = (key, fn, filename, params = {}) => {
    downloadMutation.mutate({ key, fn, filename, params });
  };

  if (coursesQuery.isLoading || studentsQuery.isLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading reports center…" rows={4} />
      </div>
    );
  }

  if (coursesQuery.isError || studentsQuery.isError) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState
          message="Could not load report filters."
          onRetry={() => {
            void coursesQuery.refetch();
            void studentsQuery.refetch();
          }}
        />
      </div>
    );
  }

  const courses = coursesQuery.data ?? [];
  const students = studentsQuery.data ?? [];

  return (
    <div className="space-y-8 p-4 md:p-6">
      <header className="rounded-2xl border border-emerald-100 bg-white/90 p-5 shadow-lg backdrop-blur">
        <h1 className="text-xl font-semibold text-ink">Reports Center</h1>
        <p className="mt-1 text-sm text-muted">
          Generate official PDF reports for platform performance, courses, students, weaknesses, and AI generation.
        </p>
      </header>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">Platform Reports</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportCard
            title="Summary Report"
            description="Platform-wide totals for students, courses, enrollments, quiz activity, weak topics, and AI generation."
            isLoading={activeKey === "summary" && downloadMutation.isPending}
            errorMessage={activeKey === "summary" ? lastError : ""}
            onDownload={() => download("summary", downloadAdminSummaryReport, "admin-platform-summary.pdf")}
          />
          <ReportCard
            title="AI Generation Report"
            description="Status of AI quiz generation across your lessons, including success, failure, and pending runs."
            isLoading={activeKey === "ai" && downloadMutation.isPending}
            errorMessage={activeKey === "ai" ? lastError : ""}
            onDownload={() => download("ai", downloadAdminAIGenerationReport, "ai-quiz-generation-status.pdf")}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">Course Reports</h2>
        <div className="rounded-xl border border-line bg-white p-4">
          <label className="block text-sm font-medium text-ocean-800" htmlFor="course-filter">
            Optional course filter
          </label>
          <select
            id="course-filter"
            value={courseFilter}
            onChange={(event) => setCourseFilter(event.target.value)}
            className="mt-2 w-full max-w-md rounded-xl border border-line px-3 py-2 text-sm"
          >
            <option value="">All courses</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.title}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportCard
            title="Course Performance Report"
            description="Enrollment, quiz scores, completion rates, and common weak topics per course."
            isLoading={activeKey === "courses" && downloadMutation.isPending}
            errorMessage={activeKey === "courses" ? lastError : ""}
            onDownload={() =>
              download(
                "courses",
                downloadAdminCoursesReport,
                courseFilter ? `course-report-${courseFilter}.pdf` : "course-performance-report.pdf",
                courseFilter ? { course_id: courseFilter } : {}
              )
            }
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">Student Reports</h2>
        <div className="rounded-xl border border-line bg-white p-4">
          <label className="block text-sm font-medium text-ocean-800" htmlFor="student-filter">
            Optional student filter
          </label>
          <select
            id="student-filter"
            value={studentFilter}
            onChange={(event) => setStudentFilter(event.target.value)}
            className="mt-2 w-full max-w-md rounded-xl border border-line px-3 py-2 text-sm"
          >
            <option value="">All students</option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.email}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportCard
            title="Student Performance Report"
            description="Quiz attempts, scores, completion, and weak topic counts across students."
            isLoading={activeKey === "students" && downloadMutation.isPending}
            errorMessage={activeKey === "students" ? lastError : ""}
            onDownload={() =>
              download(
                "students",
                downloadAdminStudentsReport,
                studentFilter ? `student-report-${studentFilter}.pdf` : "student-performance-report.pdf",
                studentFilter ? { student_id: studentFilter } : {}
              )
            }
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">Learning Analytics Reports</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportCard
            title="Weakness Report"
            description="Aggregated weak topic levels and student impact across your platform."
            isLoading={activeKey === "weaknesses" && downloadMutation.isPending}
            errorMessage={activeKey === "weaknesses" ? lastError : ""}
            onDownload={() => download("weaknesses", downloadAdminWeaknessesReport, "weak-topic-summary.pdf")}
          />
        </div>
      </section>
    </div>
  );
}
