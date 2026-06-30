import StatusBadge from "@/admin/components/StatusBadge";

const LABELS = {
  draft: "Draft",
  ready: "Ready",
  published: "Published",
};

export default function CourseStatusBadge({ status }) {
  return <StatusBadge status={status} label={LABELS[String(status || "").toLowerCase()] || status} />;
}
