import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthProvider";
import { getAnalyticsSummary } from "@/api/studentDashboard";
import {
  downloadMyProgressReport,
  downloadMyQuizPerformanceReport,
  downloadMyWeaknessesReport,
} from "@/api/reports";
import LoadingState from "@/student/components/LoadingState";
import UserAvatar from "@/shared/components/UserAvatar";
import { getDisplayName } from "@/shared/utils/userDisplay";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

function formatLevel(level) {
  if (!level) return "Not set";
  const text = String(level).replace(/_/g, " ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

export default function Profile() {
  const { user } = useAuth();
  const analyticsQuery = useQuery({ queryKey: ["analytics-summary"], queryFn: getAnalyticsSummary });

  const downloadReport = useMutation({
    mutationFn: async ({ fn, filename }) => {
      const response = await fn();
      triggerBlobDownload(response, filename);
    },
    onSuccess: () => toast.success("Report downloaded.", { id: "student-report-ok" }),
    onError: () => toast.error("Could not download report.", { id: "student-report-err" }),
  });

  const reportActions = [
    { label: "Download My Progress Report", fn: downloadMyProgressReport, filename: "my-learning-progress.pdf" },
    { label: "Download My Quiz Report", fn: downloadMyQuizPerformanceReport, filename: "my-quiz-performance.pdf" },
    { label: "Download My Weakness Report", fn: downloadMyWeaknessesReport, filename: "my-weak-topics.pdf" },
  ];

  const displayName = getDisplayName(user);
  const learningLevel = formatLevel(analyticsQuery.data?.learning_level);

  return (
    <div className="space-y-6 overflow-x-hidden p-4 pb-24 md:pb-6 md:p-6">
      <header className="min-w-0 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink dark:text-sand">Profile</h1>
          <p className="mt-1 text-sm text-muted dark:text-muted">Your account and learning level.</p>
        </div>
        <Link
          to="/settings"
          className="inline-flex min-h-10 items-center rounded-xl border border-ocean-200 px-4 text-sm font-semibold text-ocean-800 hover:bg-reef/40 dark:border-ocean-600/40 dark:text-reef dark:hover:bg-ocean-600/10"
        >
          Edit settings
        </Link>
      </header>

      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <div className="flex flex-wrap items-center gap-4">
          <UserAvatar user={user} size="md" />
          <div className="min-w-0">
            <p className="text-lg font-semibold text-ink dark:text-sand">{displayName}</p>
            <p className="text-sm text-muted dark:text-muted">{user?.email}</p>
          </div>
        </div>
      </section>

      {analyticsQuery.isLoading ? (
        <LoadingState rows={2} />
      ) : (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <article className="rounded-xl border border-ocean-600/10 bg-white p-4 dark:border-line/30 dark:bg-ocean-950/40">
            <p className="text-xs font-medium uppercase tracking-wide text-muted dark:text-reef/80">
              Learning level
            </p>
            <p className="mt-2 text-lg font-semibold text-ink dark:text-sand">{learningLevel}</p>
          </article>
          <article className="rounded-xl border border-ocean-600/10 bg-white p-4 dark:border-line/30 dark:bg-ocean-950/40">
            <p className="text-xs font-medium uppercase tracking-wide text-muted dark:text-reef/80">
              Enrolled courses
            </p>
            <p className="mt-2 text-lg font-semibold text-ink dark:text-sand">
              {analyticsQuery.data?.enrolled_course_count ?? "—"}
            </p>
          </article>
        </section>
      )}

      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <h2 className="text-lg font-semibold text-ink dark:text-sand">Reports</h2>
        <p className="mt-1 text-sm text-muted dark:text-muted">
          Download PDF summaries of your learning progress and quiz performance.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {reportActions.map((action) => (
            <button
              key={action.label}
              type="button"
              disabled={downloadReport.isPending}
              onClick={() => downloadReport.mutate({ fn: action.fn, filename: action.filename })}
              className="inline-flex min-h-10 items-center rounded-xl border border-ocean-200 px-4 text-sm font-semibold text-ocean-800 hover:bg-reef/40 disabled:cursor-not-allowed disabled:opacity-60 dark:border-ocean-600/40 dark:text-reef dark:hover:bg-ocean-600/10"
            >
              {action.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
