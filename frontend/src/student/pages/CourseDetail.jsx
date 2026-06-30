import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { joinCourse, getStudentCourse } from "@/api/studentLearning";
import ProgressBar from "@/student/components/ProgressBar";
import SectionHeader from "@/student/components/SectionHeader";

const sourceLabel = () => "YouTube";

export default function CourseDetail() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const id = Number(courseId);

  const {
    data: course,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["student-course", id],
    queryFn: () => getStudentCourse(id),
    enabled: Number.isFinite(id),
    retry: false,
  });

  const enrollMutation = useMutation({
    mutationFn: () => joinCourse(id),
    onSuccess: () => {
      toast.success("Enrolled. Loading your path.", { id: "cd-enroll" });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      void refetch();
    },
    onError: (e) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Enrollment failed.", { id: "cd-enroll-err" });
    },
  });

  const status = error?.response?.status;
  const needsEnroll = status === 403;

  if (!Number.isFinite(id)) {
    return (
      <div className="p-6 text-sm text-red-600 dark:text-red-200">
        Invalid course id.{" "}
        <Link className="font-medium text-ocean-800 underline dark:text-reef" to="/catalog">
          Back to catalog
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return <p className="p-6 text-sm text-muted dark:text-muted">Loading adaptive course map…</p>;
  }

  if (needsEnroll) {
    return (
      <div className="space-y-4 p-4 md:p-6">
        <div className="rounded-2xl border border-amber-300/80 bg-amber-50 p-6 text-amber-950 dark:border-amber-400/40 dark:bg-amber-500/10 dark:text-amber-50">
          <h1 className="text-xl font-semibold text-amber-950 dark:text-sand">Enrollment required</h1>
          <p className="mt-2 text-sm text-amber-900 dark:text-amber-100/90">
            The platform blocks lessons, quizzes, analytics, and recommendations until you join this course.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => enrollMutation.mutate()}
              disabled={enrollMutation.isPending}
              className="rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {enrollMutation.isPending ? "Enrolling…" : "Enroll now"}
            </button>
            <Link
              to="/catalog"
              className="rounded-xl border border-amber-800/25 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100 dark:border-line/40 dark:text-sand dark:hover:bg-ocean-900/50"
            >
              Browse catalog
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !course) {
    return (
      <div className="p-6 text-sm text-red-600 dark:text-red-200">
        Could not load this course.{" "}
        <Link className="font-medium text-ocean-800 underline dark:text-reef" to="/catalog">
          Return to catalog
        </Link>
      </div>
    );
  }

  const lessons = Array.isArray(course.lessons) ? course.lessons : [];

  const completedCount = lessons.filter((l) => l.quiz_passed).length;
  const courseProgress = lessons.length ? Math.round((completedCount / lessons.length) * 100) : 0;

  return (
    <div className="space-y-6 overflow-x-hidden p-4 pb-24 md:pb-6 md:p-6">
      <header className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-ocean-800 dark:text-reef">
          Adaptive path
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink dark:text-sand">{course.title}</h1>
        <p className="mt-2 text-sm text-muted dark:text-muted">
          Level <span className="font-medium capitalize text-ink dark:text-sand">{course.level}</span>
          {" · "}
          Lessons unlock in order; each stage is a YouTube video with transcript-powered quizzes.
        </p>
        <div className="mt-4">
          <ProgressBar
            value={courseProgress}
            label={`${completedCount} of ${lessons.length} lessons quiz-cleared`}
          />
        </div>
      </header>

      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
        <SectionHeader title="Lessons" subtitle="Study videos and pass quizzes to unlock the next step." />
        <ul className="mt-4 divide-y divide-line dark:divide-line/30">
          {lessons.map((lesson) => (
            <li key={lesson.id} className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-ink dark:text-sand">
                  {(lesson.order ?? 0) + 1}. {lesson.title}
                  {!lesson.unlocked ? (
                    <span className="ml-2 rounded-full bg-reef/50 px-2 py-0.5 text-xs text-ocean-800 dark:bg-cream0/40 dark:text-sand">
                      Locked
                    </span>
                  ) : null}
                  {lesson.unlocked && lesson.quiz_passed ? (
                    <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-500/30 dark:text-emerald-100">
                      Quiz cleared
                    </span>
                  ) : null}
                </p>
                <p className="mt-1 text-xs text-muted dark:text-muted">
                  {sourceLabel()}
                  {lesson.estimated_minutes ? ` · ~${lesson.estimated_minutes} min` : ""}
                  {lesson.learning_objective ? ` · ${lesson.learning_objective}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {lesson.unlocked ? (
                  <>
                    <button
                      type="button"
                      onClick={() => navigate(`/lessons/${lesson.id}`)}
                      className="min-h-[40px] rounded-xl border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-sand dark:border-line/40 dark:text-sand dark:hover:bg-ocean-900/50"
                    >
                      Study
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/lessons/${lesson.id}/quiz`)}
                      className="min-h-[40px] rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-3 py-2 text-xs font-semibold text-white hover:brightness-110"
                    >
                      Quiz
                    </button>
                  </>
                ) : (
                  <span className="text-xs text-muted dark:text-muted/80">Pass the prior quiz to unlock</span>
                )}
              </div>
            </li>
          ))}
        </ul>
        {lessons.length === 0 ? (
          <p className="mt-2 text-sm text-muted dark:text-muted">No lessons yet.</p>
        ) : null}
      </section>
    </div>
  );
}
