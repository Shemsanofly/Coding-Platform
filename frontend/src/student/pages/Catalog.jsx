import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { getCourseCatalog, joinCourse } from "@/api/studentLearning";

export default function Catalog() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [joiningId, setJoiningId] = useState(null);

  const { data = [], isLoading, isPending, isError } = useQuery({
    queryKey: ["course-catalog"],
    queryFn: getCourseCatalog,
  });

  const enrollMutation = useMutation({
    mutationFn: joinCourse,
    onSuccess: (_, courseId) => {
      toast.success("You are enrolled. Opening the course.", { id: "enroll-ok" });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
      queryClient.invalidateQueries({ queryKey: ["course-catalog"] });
      navigate(`/courses/${courseId}`);
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not enroll.", { id: "enroll-err" });
    },
    onSettled: () => setJoiningId(null),
  });

  const items = useMemo(() => (Array.isArray(data) ? data : data?.results ?? []), [data]);
  const showSkeleton = isLoading || isPending;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
        <h1 className="text-2xl font-bold text-ink dark:text-sand">Course catalog</h1>
        <p className="mt-1 text-sm text-muted dark:text-muted">
          Courses match your registered learning level (beginner / intermediate / advanced). Enrollment is required
          before lessons, quizzes, and adaptive personalization activate.
        </p>
      </header>

      {showSkeleton ? (
        <p className="text-sm text-muted dark:text-muted">Loading courses…</p>
      ) : null}
      {!showSkeleton && isError ? (
        <p className="text-sm text-red-600 dark:text-red-300">Unable to load the catalog. Try again later.</p>
      ) : null}

      <ul className="space-y-3">
        {!showSkeleton &&
          !isError &&
          items.map((course) => (
            <li
              key={course.id}
              className="flex flex-col gap-3 rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-md dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-lg dark:backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-lg font-semibold text-ink dark:text-sand">{course.title}</p>
                <p className="mt-1 text-xs text-muted dark:text-muted">
                  Level{" "}
                  <span className="font-medium capitalize text-ink dark:text-sand">{course.level}</span>
                  {" · "}
                  {course.lesson_count ?? 0} lessons
                  {course.is_enrolled ? (
                    <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200">
                      Enrolled
                    </span>
                  ) : null}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {course.is_enrolled ? (
                  <button
                    type="button"
                    onClick={() => navigate(`/courses/${course.id}`)}
                    className="rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
                  >
                    Open course
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={enrollMutation.isPending && joiningId === course.id}
                    onClick={() => {
                      setJoiningId(course.id);
                      enrollMutation.mutate(course.id);
                    }}
                    className="rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {enrollMutation.isPending && joiningId === course.id ? "Enrolling…" : "Enroll"}
                  </button>
                )}
              </div>
            </li>
          ))}
      </ul>

      {!showSkeleton && !isError && items.length === 0 ? (
        <p className="text-sm text-muted dark:text-muted">
          No published courses yet. Ask an admin to create content.
        </p>
      ) : null}
    </div>
  );
}
