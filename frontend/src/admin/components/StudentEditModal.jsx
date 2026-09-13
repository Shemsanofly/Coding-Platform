import { useEffect, useState } from "react";

const LEVEL_OPTIONS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

export default function StudentEditModal({
  student,
  open,
  onClose,
  onSave,
  isSaving,
  errorMessage,
}) {
  const [email, setEmail] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!student) {
      return;
    }
    setEmail(student.email || "");
    setExperienceLevel(student.learning_level || "beginner");
    setIsActive(student.is_active !== false);
  }, [student, open]);

  if (!open || !student) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSave({
      email: email.trim(),
      experience_level: experienceLevel,
      is_active: isActive,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ocean-900/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md rounded-2xl border border-emerald-100 bg-white p-5 shadow-xl"
      >
        <h2 className="text-lg font-semibold text-ink">Edit student</h2>
        <p className="mt-1 text-sm text-muted">{student.name || student.email}</p>
        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor="student-email"
              className="mb-1 block text-sm font-medium text-ocean-800"
            >
              Email
            </label>
            <input
              id="student-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="w-full rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
            />
          </div>
          <div>
            <label
              htmlFor="student-level"
              className="mb-1 block text-sm font-medium text-ocean-800"
            >
              Experience level
            </label>
            <select
              id="student-level"
              value={experienceLevel}
              onChange={(event) => setExperienceLevel(event.target.value)}
              className="w-full rounded-xl border border-line px-3 py-2 text-sm"
            >
              {LEVEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-ocean-800">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="rounded border-line text-emerald-600 focus:ring-emerald-500"
            />
            Account active
          </label>
          {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex min-h-10 items-center rounded-xl border border-line px-4 text-sm font-semibold text-ocean-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex min-h-10 items-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white disabled:opacity-60"
            >
              {isSaving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
