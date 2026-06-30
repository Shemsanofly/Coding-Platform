import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAdminCoursePipelineStatus } from "@/api/adminCourses";

const STEPS = [
  { key: "fetching_sources", label: "Fetching sources" },
  { key: "processing_text", label: "Processing text" },
  { key: "generating_quizzes", label: "Generating quizzes" },
  { key: "ready", label: "Ready" },
];

const normalizeStatus = (status) => {
  if (status === "done" || status === "running" || status === "failed") {
    return status;
  }
  return "pending";
};

const Badge = ({ status }) => {
  const styles = {
    pending: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    done: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex min-w-20 justify-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${styles[status]}`}
    >
      {status}
    </span>
  );
};

export default function PipelineStatus({ courseId }) {
  const { data } = useQuery({
    queryKey: ["admin-course-pipeline-status", courseId],
    queryFn: () => getAdminCoursePipelineStatus(courseId),
    enabled: Boolean(courseId),
    refetchInterval: (query) => {
      const steps = query.state.data?.steps;
      if (!steps) {
        return 3000;
      }

      const values = STEPS.map((step) => normalizeStatus(steps[step.key]));
      const hasFailed = values.some((value) => value === "failed");
      const allDone = values.every((value) => value === "done");
      return hasFailed || allDone ? false : 3000;
    },
  });

  const stepStatuses = useMemo(() => {
    const steps = data?.steps || {};
    return STEPS.map((step) => ({
      ...step,
      status: normalizeStatus(steps[step.key]),
    }));
  }, [data]);

  const allDone = stepStatuses.every((step) => step.status === "done");

  return (
    <section className="rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur">
      <h3 className="mb-4 text-base font-semibold text-gray-900">Pipeline status</h3>

      <div className="space-y-3">
        {stepStatuses.map((step) => (
          <div
            key={step.key}
            className="flex items-center justify-between rounded-xl border border-emerald-100/80 bg-white px-3 py-2"
          >
            <span className="text-sm font-medium text-gray-800">{step.label}</span>
            <Badge status={step.status} />
          </div>
        ))}
      </div>

      {allDone ? (
        <p className="mt-4 text-xs text-emerald-700">
          Pipeline complete. Use Publish course in the header when lessons are approved.
        </p>
      ) : null}
    </section>
  );
}
