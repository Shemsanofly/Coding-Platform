import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deactivateAdminStudent,
  getAdminUsers,
  purgeAdminStudent,
  updateAdminStudent,
} from "@/api/adminUsers";
import StudentEditModal from "@/admin/components/StudentEditModal";
import AdminTable from "@/admin/components/AdminTable";
import EmptyState from "@/admin/components/EmptyState";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import StatusBadge from "@/admin/components/StatusBadge";

const WEAKNESS_LEVEL_OPTIONS = [
  { value: "", label: "All levels" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const SORT_OPTIONS = [
  { value: "", label: "Default" },
  { value: "avg_score", label: "Avg score (low to high)" },
  { value: "-avg_score", label: "Avg score (high to low)" },
];

const parseDate = (value) => {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
};

const getDaysSince = (value) => {
  const parsed = parseDate(value);
  if (!parsed) {
    return null;
  }
  return Math.floor((Date.now() - parsed.getTime()) / (1000 * 60 * 60 * 24));
};

const formatDateTime = (value) => {
  const parsed = parseDate(value);
  if (!parsed) {
    return "N/A";
  }
  return parsed.toLocaleString();
};

function extractApiError(error) {
  const data = error?.response?.data;
  if (!data) {
    return "";
  }
  if (typeof data === "string") {
    return data;
  }
  if (data.detail) {
    return String(data.detail);
  }
  const parts = Object.entries(data).map(([key, value]) => {
    if (Array.isArray(value)) {
      return `${key}: ${value.join(" ")}`;
    }
    return `${key}: ${value}`;
  });
  return parts.join(" ");
}

export default function UserList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [weaknessLevel, setWeaknessLevel] = useState("");
  const [ordering, setOrdering] = useState("");
  const [editingStudent, setEditingStudent] = useState(null);
  const [editError, setEditError] = useState("");

  const filters = useMemo(
    () => ({
      search: search.trim(),
      weaknessLevel,
      ordering,
    }),
    [search, weaknessLevel, ordering]
  );

  const { data = [], isLoading, isPending, isError, refetch } = useQuery({
    queryKey: ["admin-users", filters],
    queryFn: () => getAdminUsers(filters),
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, payload }) => updateAdminStudent(userId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setEditingStudent(null);
      setEditError("");
    },
    onError: (error) => {
      setEditError(extractApiError(error) || "Could not update student.");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId) => deactivateAdminStudent(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const purgeMutation = useMutation({
    mutationFn: (userId) => purgeAdminStudent(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const users = useMemo(() => (Array.isArray(data) ? data : data?.results || []), [data]);
  const showLoading = isLoading || isPending;

  const handleDeactivate = (student) => {
    const label = student.name || student.email;
    const confirmed = window.confirm(
      `Deactivate ${label} (${student.email})?\n\nThey will no longer be able to sign in. You can delete the account permanently afterward to free space.`
    );
    if (confirmed) {
      deactivateMutation.mutate(student.id);
    }
  };

  const handlePermanentDelete = (student) => {
    const label = student.name || student.email;
    const confirmed = window.confirm(
      `Permanently delete ${label} (${student.email})?\n\nThis cannot be undone. All enrollments, progress, and quiz history for this student will be removed.`
    );
    if (confirmed) {
      purgeMutation.mutate(student.id);
    }
  };

  const columns = [
    {
      key: "name",
      label: "Student",
      render: (row) => (
        <div>
          <p className="font-medium text-ink">{row.name || row.full_name || "N/A"}</p>
          <p className="text-xs text-muted">{row.email}</p>
        </div>
      ),
    },
    {
      key: "enrolled_courses",
      label: "Courses",
      render: (row) => row.enrolled_courses ?? 0,
    },
    {
      key: "completed_lessons",
      label: "Lessons done",
      render: (row) => row.completed_lessons ?? 0,
    },
    {
      key: "avg_score",
      label: "Avg score",
      render: (row) =>
        row.avg_score != null ? `${Math.round(Number(row.avg_score))}%` : "N/A",
    },
    {
      key: "weak_topics_count",
      label: "Weak topics",
      render: (row) => row.weak_topics_count ?? 0,
    },
    {
      key: "learning_level",
      label: "Level",
      render: (row) => (
        <span className="capitalize text-ocean-800">{row.learning_level || "—"}</span>
      ),
    },
    {
      key: "last_active",
      label: "Last active",
      render: (row) => {
        const inactiveDays = getDaysSince(row.last_active);
        const isInactive = typeof inactiveDays === "number" && inactiveDays > 7;
        return (
          <span className={isInactive ? "font-medium text-red-600" : "text-muted"}>
            {formatDateTime(row.last_active)}
          </span>
        );
      },
    },
    {
      key: "top_weakness",
      label: "Top weakness",
      render: (row) => (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm">{row.top_weakness_topic || "—"}</span>
          {row.top_weakness_level ? <StatusBadge status={row.top_weakness_level} /> : null}
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (row) => (
        <span
          className={
            row.is_active === false
              ? "text-xs font-semibold uppercase text-red-600"
              : "text-xs font-semibold uppercase text-emerald-700"
          }
        >
          {row.is_active === false ? "Inactive" : "Active"}
        </span>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => navigate(`/admin/users/${row.id}`)}
            className="inline-flex min-h-9 items-center rounded-xl border border-emerald-200 px-3 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
          >
            View
          </button>
          <button
            type="button"
            onClick={() => {
              setEditError("");
              setEditingStudent(row);
            }}
            className="inline-flex min-h-9 items-center rounded-xl border border-line px-3 text-xs font-semibold text-ocean-800 hover:bg-cream"
          >
            Edit
          </button>
          {row.is_active !== false ? (
            <button
              type="button"
              onClick={() => handleDeactivate(row)}
              disabled={deactivateMutation.isPending}
              className="inline-flex min-h-9 items-center rounded-xl border border-red-200 px-3 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60"
            >
              Deactivate
            </button>
          ) : (
            <button
              type="button"
              onClick={() => handlePermanentDelete(row)}
              disabled={purgeMutation.isPending}
              className="inline-flex min-h-9 items-center rounded-xl border border-red-300 bg-red-50 px-3 text-xs font-semibold text-red-700 hover:bg-red-100 disabled:opacity-60"
            >
              Delete
            </button>
          )}
        </div>
      ),
    },
  ];

  const tableRows = users.map((user) => ({
    ...user,
    cardTitle: user.name || user.email,
  }));

  return (
    <div className="space-y-5 p-4 md:p-6">
      <header className="space-y-3 rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur">
        <h1 className="text-xl font-semibold text-ink">Students</h1>
        <p className="text-sm text-muted">Progress, weaknesses, and quiz performance across your platform.</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            type="text"
            placeholder="Search by name or email"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
          />
          <select
            value={weaknessLevel}
            onChange={(event) => setWeaknessLevel(event.target.value)}
            className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
            aria-label="Filter by weakness level"
          >
            {WEAKNESS_LEVEL_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={ordering}
            onChange={(event) => setOrdering(event.target.value)}
            className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value || "default"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {showLoading ? (
        <LoadingState label="Loading students…" />
      ) : isError ? (
        <ErrorState message="Failed to load users." onRetry={() => refetch()} />
      ) : users.length === 0 ? (
        <EmptyState title="No students found" message="Try adjusting search or weakness filters." />
      ) : (
        <section className="overflow-hidden rounded-2xl border border-emerald-100 bg-white/90 shadow-lg backdrop-blur">
          <AdminTable
            columns={columns}
            rows={tableRows}
            emptyMessage="No users found for current filters."
          />
        </section>
      )}

      <StudentEditModal
        student={editingStudent}
        open={Boolean(editingStudent)}
        onClose={() => {
          setEditingStudent(null);
          setEditError("");
        }}
        onSave={(payload) => {
          if (!editingStudent) {
            return;
          }
          updateMutation.mutate({ userId: editingStudent.id, payload });
        }}
        isSaving={updateMutation.isPending}
        errorMessage={editError}
      />
    </div>
  );
}
