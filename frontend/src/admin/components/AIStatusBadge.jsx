import StatusBadge from "@/admin/components/StatusBadge";

export default function AIStatusBadge({ kind, status }) {
  const prefix = kind === "quiz" ? "Quiz" : kind === "transcript" ? "Transcript" : "AI";
  const normalized = String(status || "pending").toLowerCase();
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className="text-muted">{prefix}</span>
      <StatusBadge status={normalized} />
    </span>
  );
}
