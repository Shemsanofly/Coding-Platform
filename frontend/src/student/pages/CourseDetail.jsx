import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { joinCourse, getStudentCourse } from "@/api/studentLearning";
import { downloadCertificate, generateCertificate } from "@/api/certificates";
import ProgressBar from "@/student/components/ProgressBar";
import SectionHeader from "@/student/components/SectionHeader";
import LoadingState from "@/student/components/LoadingState";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import PageHeader from "@/shared/components/ui/PageHeader";
import BrandMark from "@/shared/components/BrandMark";
import { formatSourceTypeLabel } from "@/shared/constants/lessonSources";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

function LessonTimelineItem({ lesson, index, lessons, onStudy, onQuiz }) {
  const isLast = index === lessons.length - 1;
  const quizAvailable = Boolean(lesson.quiz_available ?? lesson.quiz_ready);
  const quizFailed = lesson.quiz_generation_status === "failed";
  const status = lesson.quiz_passed ? "completed" : lesson.unlocked ? "active" : "locked";

  const statusStyles = {
    completed: "border-emerald-500 bg-emerald-500 text-white",
    active: "border-ocean-600 bg-ocean-600 text-white",
    locked: "border-line bg-cream text-muted dark:border-line/50 dark:bg-ocean-950/60 dark:text-muted",
  };

  return (
    <li className="relative flex gap-4 pb-6 last:pb-0">
      {!isLast ? (
        <span
          className="absolute left-[15px] top-8 h-[calc(100%-8px)] w-0.5 bg-line dark:bg-line/40"
          aria-hidden="true"
        />
      ) : null}
      <span
        className={`relative z-[1] flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold ${statusStyles[status]}`}
        aria-hidden="true"
      >
        {lesson.quiz_passed ? "✓" : (lesson.order ?? index) + 1}
      </span>
      <div className="min-w-0 flex-1 rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="font-semibold text-ink dark:text-sand">{lesson.title}</p>
            <p className="mt-1 text-xs text-muted dark:text-muted">
              {formatSourceTypeLabel(lesson.source_type)}
              {lesson.estimated_minutes ? ` · ~${lesson.estimated_minutes} min` : ""}
              {lesson.learning_objective ? ` · ${lesson.learning_objective}` : ""}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {!lesson.unlocked ? (
                <span className="rounded-full bg-reef/60 px-2 py-0.5 text-xs font-medium text-ocean-800 dark:bg-ocean-900/60 dark:text-reef">
                  Locked
                </span>
              ) : null}
              {lesson.unlocked && lesson.quiz_passed ? (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-500/30 dark:text-emerald-100">
                  Quiz cleared
                </span>
              ) : null}
              {lesson.unlocked && !lesson.quiz_passed && !quizAvailable ? (
                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-500/25 dark:text-red-100">
                  {quizFailed ? "Quiz failed to generate" : "Quiz not ready"}
                </span>
              ) : null}
            </div>
            {!lesson.unlocked ? (
              <p className="mt-2 text-xs text-muted dark:text-muted/80">
                {index > 0 && lessons[index - 1]
                  ? `Pass the quiz for "${lessons[index - 1].title}" to unlock`
                  : "Pass the prior quiz to unlock"}
              </p>
            ) : null}
          </div>
          {lesson.unlocked ? (
            <div className="flex shrink-0 flex-wrap gap-2">
              <Button variant="ghost" size="sm" onClick={() => onStudy(lesson.id)}>
                Study
              </Button>
              <Button
                variant="gradient"
                size="sm"
                disabled={!quizAvailable}
                onClick={() => onQuiz(lesson.id)}
              >
                Quiz
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </li>
  );
}

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
      queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      void refetch();
    },
    onError: (e) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Enrollment failed.", { id: "cd-enroll-err" });
    },
  });

  const generateMutation = useMutation({
    mutationFn: () => generateCertificate(id),
    onSuccess: () => {
      toast.success("Certificate ready.", { id: "certificate-ready" });
      queryClient.invalidateQueries({ queryKey: ["my-certificates"] });
      void refetch();
    },
    onError: (e) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Certificate generation failed.", {
        id: "certificate-error",
      });
    },
  });

  const downloadMutation = useMutation({
    mutationFn: (certificateId) => downloadCertificate(certificateId),
    onSuccess: (response) => triggerBlobDownload(response, "certificate.pdf"),
    onError: () => toast.error("Could not download certificate.", { id: "certificate-download-error" }),
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
    return (
      <div className="p-6">
        <LoadingState label="Loading course…" rows={4} />
      </div>
    );
  }

  if (needsEnroll) {
    return (
      <div className="space-y-4 p-4 md:p-6">
        <Card variant="alert">
          <h1 className="text-xl font-semibold">Enrollment required</h1>
          <p className="mt-2 text-sm opacity-90">
            Join this course to access lessons, quizzes, and your study plan.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              variant="gradient"
              loading={enrollMutation.isPending}
              onClick={() => enrollMutation.mutate()}
            >
              Enroll now
            </Button>
            <Link
              to="/catalog"
              className="inline-flex min-h-10 items-center rounded-xl border border-amber-800/25 px-4 text-sm font-medium hover:bg-amber-100 dark:border-line/40 dark:hover:bg-ocean-900/50"
            >
              Browse catalog
            </Link>
          </div>
        </Card>
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
  const completedCount =
    Number(course.completed_lessons) || lessons.filter((l) => l.lesson_officially_completed || l.quiz_passed).length;
  const courseProgress =
    typeof course.progress_percent === "number"
      ? Math.round(course.progress_percent)
      : lessons.length
        ? Math.round((completedCount / lessons.length) * 100)
        : 0;
  const certificate = generateMutation.data ?? course.certificate ?? null;
  const certificateEligible = Boolean(course.certificate_eligible || certificate);
  const certificateReasons = Array.isArray(course.certificate_reasons) ? course.certificate_reasons : [];
  const issueDate = certificate?.issue_date ? new Date(certificate.issue_date).toLocaleDateString() : "";

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <Card variant="elevated">
        <p className="text-xs font-semibold uppercase tracking-widest text-ocean-800 dark:text-reef">
          Course path
        </p>
        <PageHeader
          className="mt-1"
          title={course.title}
          subtitle={`Level ${course.level} · Lessons unlock in order after passing each quiz`}
        />
        <div className="mt-4">
          <ProgressBar
            value={courseProgress}
            label={`${completedCount} of ${lessons.length} lessons completed`}
          />
        </div>
      </Card>

      <Card variant="elevated" padding="md" className="overflow-hidden">
        <div className="-mx-5 -mt-5 mb-5 h-1.5 bg-gradient-to-r from-coral via-spice to-ocean-600" />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-ocean-600/10 bg-reef/70 dark:border-white/10 dark:bg-[#213548]">
              <BrandMark />
            </div>
            <SectionHeader
              title="LearnCode Certificate"
              subtitle={`Official completion record - ${courseProgress}% course progress`}
            />
          </div>
          <span
            className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-bold uppercase ${
              certificate
                ? "border-emerald-300/60 bg-emerald-50 text-emerald-800 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-100"
                : certificateEligible
                  ? "border-spice/50 bg-spice/10 text-ocean-950 dark:border-spice/40 dark:bg-spice/10 dark:text-sand"
                  : "border-line bg-cream text-muted dark:border-white/10 dark:bg-[#1b2b3b] dark:text-reef/80"
            }`}
          >
            {certificate ? "Issued" : certificateEligible ? "Ready" : "In progress"}
          </span>
        </div>
        {certificate ? (
          <div className="mt-5 flex flex-col gap-5 rounded-xl border border-ocean-600/10 bg-cream/80 p-4 dark:border-white/10 dark:bg-[#1b2b3b]/70 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ocean-800 dark:text-reef">
                Certificate of Completion
              </p>
              <h3 className="mt-1 truncate text-lg font-bold text-ink dark:text-sand">{course.title}</h3>
              <dl className="mt-3 grid gap-2 text-xs text-muted dark:text-reef/80 sm:grid-cols-2">
                <div>
                  <dt className="font-semibold uppercase tracking-wide">Certificate no.</dt>
                  <dd className="mt-0.5 font-medium text-ink dark:text-sand">{certificate.certificate_number}</dd>
                </div>
                <div>
                  <dt className="font-semibold uppercase tracking-wide">Issued</dt>
                  <dd className="mt-0.5 font-medium text-ink dark:text-sand">{issueDate || "Available"}</dd>
                </div>
              </dl>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="gradient"
                loading={downloadMutation.isPending}
                onClick={() => downloadMutation.mutate(certificate.id)}
              >
                Download Certificate
              </Button>
              <Link
                to={`/verify-certificate/${certificate.verification_code}`}
                className="inline-flex min-h-10 items-center rounded-xl border border-ocean-600/20 px-4 text-sm font-semibold text-ocean-800 transition hover:bg-reef/40 dark:border-white/10 dark:bg-[#172433]/80 dark:text-reef dark:hover:bg-[#213548]"
              >
                Verify Certificate
              </Link>
            </div>
          </div>
        ) : certificateEligible ? (
          <div className="mt-5 flex flex-col gap-3 rounded-xl border border-spice/30 bg-spice/10 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-spice/30 dark:bg-spice/10">
            <p className="text-sm text-muted dark:text-reef/90">
              Your course requirements are complete. Generate your official LearnCode certificate.
            </p>
            <Button
              variant="gradient"
              loading={generateMutation.isPending}
              onClick={() => generateMutation.mutate()}
            >
              Generate Certificate
            </Button>
          </div>
        ) : (
          <div className="mt-5 space-y-2 rounded-xl border border-ocean-600/10 bg-cream/80 p-4 text-sm text-muted dark:border-white/10 dark:bg-[#1b2b3b]/70 dark:text-reef/90">
            <p>Complete all required lessons and pass the final assessment to receive your certificate.</p>
            {certificateReasons.length > 0 ? (
              <ul className="list-inside list-disc">
                {certificateReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : null}
          </div>
        )}
      </Card>

      <Card variant="elevated" padding="md">
        <SectionHeader title="Lesson timeline" subtitle="Follow the sequence from top to bottom." />
        {lessons.length === 0 ? (
          <p className="mt-4 text-sm text-muted dark:text-muted">No lessons yet.</p>
        ) : (
          <ol className="mt-6">
            {lessons.map((lesson, index) => (
              <LessonTimelineItem
                key={lesson.id}
                lesson={lesson}
                index={index}
                lessons={lessons}
                onStudy={(lessonId) => navigate(`/lessons/${lessonId}`)}
                onQuiz={(lessonId) => navigate(`/lessons/${lessonId}/quiz`)}
              />
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
