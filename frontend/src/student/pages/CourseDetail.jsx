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
import {
  CourseLevelBadge,
  CourseMetric,
  CourseStatusPill,
} from "@/shared/components/course/CourseBadges";
import { formatSourceTypeLabel } from "@/shared/constants/lessonSources";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

function lessonState(lesson) {
  if (lesson.quiz_passed) {
    return {
      label: "Complete",
      className:
        "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
    };
  }
  if (!lesson.unlocked) {
    return {
      label: "Locked",
      className:
        "border-slate-200 bg-slate-50 text-slate-700 dark:border-white/10 dark:bg-white/10 dark:text-reef",
    };
  }
  if (lesson.quiz_generation_status === "failed") {
    return {
      label: "Quiz failed",
      className:
        "border-red-200 bg-red-50 text-red-700 dark:border-red-400/30 dark:bg-red-500/15 dark:text-red-100",
    };
  }
  if (lesson.lesson_officially_completed && (lesson.quiz_available || lesson.quiz_ready)) {
    return {
      label: "Quiz required",
      className:
        "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-400/30 dark:bg-blue-500/15 dark:text-blue-100",
    };
  }
  if (lesson.lesson_officially_completed) {
    return {
      label: "Studied",
      className:
        "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
    };
  }
  if (lesson.quiz_available || lesson.quiz_ready) {
    return {
      label: "Study first",
      className:
        "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100",
    };
  }
  return {
    label: "Studying",
    className:
      "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100",
  };
}

function LessonRow({ lesson, index, previousLesson, onStudy, onQuiz }) {
  const state = lessonState(lesson);
  const quizAvailable = Boolean(lesson.quiz_available ?? lesson.quiz_ready);
  const studyComplete = Boolean(lesson.lesson_officially_completed || lesson.quiz_passed);

  return (
    <li className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#172433]/85">
      <div className="grid gap-4 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-reef text-sm font-bold text-ocean-800 dark:bg-ocean-600/25 dark:text-reef">
          {lesson.quiz_passed ? "OK" : index + 1}
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-ink dark:text-sand">{lesson.title}</h3>
            <span
              className={`inline-flex min-h-6 items-center rounded-full border px-2.5 text-xs font-semibold ${state.className}`}
            >
              {state.label}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted dark:text-reef/75">
            {formatSourceTypeLabel(lesson.source_type)}
            {lesson.estimated_minutes ? ` | ${lesson.estimated_minutes} min` : ""}
            {lesson.learning_objective ? ` | ${lesson.learning_objective}` : ""}
          </p>
          {!lesson.unlocked ? (
            <p className="mt-2 text-xs text-muted dark:text-reef/70">
              {previousLesson
                ? `Pass "${previousLesson.title}" to unlock this lesson.`
                : "Pass the prior quiz to unlock this lesson."}
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Button
            variant="ghost"
            size="sm"
            disabled={!lesson.unlocked}
            onClick={() => onStudy(lesson.id)}
          >
            Study
          </Button>
          <Button
            variant="gradient"
            size="sm"
            disabled={!lesson.unlocked || !quizAvailable || !studyComplete}
            onClick={() => onQuiz(lesson.id)}
          >
            Quiz
          </Button>
        </div>
      </div>
    </li>
  );
}

function CertificatePanel({
  courseProgress,
  certificate,
  eligible,
  reasons,
  onGenerate,
  onDownload,
  generating,
  downloading,
}) {
  const issueDate = certificate?.issue_date
    ? new Date(certificate.issue_date).toLocaleDateString()
    : "";

  return (
    <Card variant="subtle" padding="md">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <SectionHeader
            title="Certificate"
            subtitle={`Completion record for this course - ${courseProgress}% progress`}
          />
          {certificate ? (
            <p className="mt-3 text-sm text-muted dark:text-reef/75">
              Certificate {certificate.certificate_number}
              {issueDate ? ` issued ${issueDate}` : ""}.
            </p>
          ) : eligible ? (
            <p className="mt-3 text-sm text-muted dark:text-reef/75">
              Requirements are complete. Generate your certificate when ready.
            </p>
          ) : (
            <div className="mt-3 space-y-1 text-sm text-muted dark:text-reef/75">
              <p>Complete the course requirements to unlock your certificate.</p>
              {reasons.map((reason) => (
                <p key={reason}>{reason}</p>
              ))}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          {certificate ? (
            <>
              <Link
                to={`/certificates/${certificate.id}`}
                className="lc-btn-ghost min-h-9 px-3 py-2 text-xs"
              >
                View
              </Link>
              <Button
                variant="gradient"
                size="sm"
                loading={downloading}
                onClick={() => onDownload(certificate.id)}
              >
                Download
              </Button>
            </>
          ) : eligible ? (
            <Button variant="gradient" size="sm" loading={generating} onClick={onGenerate}>
              Generate
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
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
      toast.error(typeof detail === "string" ? detail : "Enrollment failed.", {
        id: "cd-enroll-err",
      });
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
    onError: () =>
      toast.error("Could not download certificate.", { id: "certificate-download-error" }),
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
        <LoadingState label="Loading course..." rows={4} />
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
            <Link to="/catalog" className="lc-btn-ghost">
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
    Number(course.completed_lessons) ||
    lessons.filter((lesson) => lesson.lesson_officially_completed || lesson.quiz_passed).length;
  const courseProgress =
    typeof course.progress_percent === "number"
      ? Math.round(course.progress_percent)
      : lessons.length
        ? Math.round((completedCount / lessons.length) * 100)
        : 0;
  const certificate = generateMutation.data ?? course.certificate ?? null;
  const certificateEligible = Boolean(course.certificate_eligible || certificate);
  const certificateReasons = Array.isArray(course.certificate_reasons)
    ? course.certificate_reasons
    : [];
  const readyQuizzes = lessons.filter(
    (lesson) => lesson.quiz_available || lesson.quiz_ready,
  ).length;

  return (
    <div className="space-y-5 p-4 md:p-6">
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#172433]/85">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-end">
          <div className="min-w-0">
            <Link
              to="/catalog"
              className="text-sm font-semibold text-ocean-700 hover:underline dark:text-reef"
            >
              Back to catalog
            </Link>
            <div className="mt-3 flex flex-wrap gap-2">
              <CourseLevelBadge level={course.level} />
              <CourseStatusPill status={course.status || "published"} />
            </div>
            <h1 className="mt-3 text-2xl font-bold text-ink dark:text-sand md:text-3xl">
              {course.title}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted dark:text-reef/75">
              Work through the lessons in order, then use the quizzes to confirm mastery and unlock
              completion.
            </p>
          </div>

          <div className="rounded-xl border border-line/70 bg-cream p-4 dark:border-white/10 dark:bg-ocean-950/35">
            <ProgressBar
              value={courseProgress}
              label={`${completedCount} of ${lessons.length} lessons complete`}
            />
          </div>
        </div>

        <div className="mt-5 grid gap-4 border-t border-line/70 pt-4 sm:grid-cols-3 dark:border-white/10">
          <CourseMetric label="Lessons" value={lessons.length} />
          <CourseMetric label="Quizzes ready" value={`${readyQuizzes}/${lessons.length}`} />
          <CourseMetric label="Progress" value={`${courseProgress}%`} />
        </div>
      </section>

      <CertificatePanel
        courseProgress={courseProgress}
        certificate={certificate}
        eligible={certificateEligible}
        reasons={certificateReasons}
        generating={generateMutation.isPending}
        downloading={downloadMutation.isPending}
        onGenerate={() => generateMutation.mutate()}
        onDownload={(certificateId) => downloadMutation.mutate(certificateId)}
      />

      <section className="space-y-3">
        <SectionHeader title="Lessons" subtitle="Study, then take the quiz when it is ready." />
        {lessons.length === 0 ? (
          <Card variant="subtle">
            <p className="text-sm text-muted dark:text-reef/75">No lessons have been added yet.</p>
          </Card>
        ) : (
          <ol className="space-y-3">
            {lessons.map((lesson, index) => (
              <LessonRow
                key={lesson.id}
                lesson={lesson}
                index={index}
                previousLesson={lessons[index - 1]}
                onStudy={(lessonId) => navigate(`/lessons/${lessonId}`)}
                onQuiz={(lessonId) => navigate(`/lessons/${lessonId}/quiz`)}
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
