import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthProvider";
import { getDisplayName } from "@/shared/utils/userDisplay";
import {
  getAnalyticsSummary,
  getEnrollments,
  getLearningPath,
  getRecommendations,
  getWeaknesses,
} from "@/api/studentDashboard";
import MetricCard from "@/student/components/MetricCard";
import SectionHeader from "@/student/components/SectionHeader";
import LoadingState from "@/student/components/LoadingState";
import ProgressBar from "@/student/components/ProgressBar";
import Playground from "@/student/components/Playground";

const normalizeNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
};

const Icons = {
  courses: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6h16M4 12h16M4 18h7" strokeLinecap="round" />
    </svg>
  ),
  lessons: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" />
    </svg>
  ),
  quiz: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 6v6l4 2M12 22a10 10 0 100-20 10 10 0 000 20z" strokeLinecap="round" />
    </svg>
  ),
  weak: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" strokeLinecap="round" />
    </svg>
  ),
};

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatLevel(level) {
  if (!level) return null;
  const text = String(level).replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function pathStepSymbol(status) {
  if (status === "completed") return "✓";
  if (status === "next") return "→";
  return "○";
}

function PathProgressPreview({ steps }) {
  if (!steps.length) {
    return (
      <p className="text-sm text-muted dark:text-muted">
        Complete a quiz to generate your learning path.
      </p>
    );
  }

  return (
    <ul className="space-y-2" aria-label="Learning path progress">
      {steps.map((step) => (
        <li
          key={`${step.step}-${step.lesson_id}`}
          className={`flex items-center gap-3 text-sm ${
            step.status === "next"
              ? "font-semibold text-ink dark:text-sand"
              : "text-muted dark:text-muted"
          }`}
        >
          <span
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              step.status === "next"
                ? "bg-ocean-600/20 text-ocean-700 dark:text-reef"
                : step.status === "completed"
                  ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-200"
                  : "bg-reef/50 text-muted dark:bg-ocean-950/50 dark:text-muted/80"
            }`}
            aria-hidden="true"
          >
            {pathStepSymbol(step.status)}
          </span>
          <span className="min-w-0 truncate">{step.lesson_title}</span>
        </li>
      ))}
    </ul>
  );
}

const primaryButtonClass =
  "min-h-[48px] w-full rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:brightness-110 sm:w-auto sm:min-w-[180px]";

const linkButtonClass =
  "text-sm font-medium text-ocean-800 underline-offset-2 hover:underline dark:text-reef";

const formatTopicLabel = (tag) => String(tag || "").replace(/_/g, " ");

const featureLinks = [
  { to: "/playground", label: "Playground", description: "AI coding challenges, XP, and leaderboard" },
  { to: "/catalog", label: "Courses", description: "Browse and enroll in lessons" },
  { to: "/learning-path", label: "Learning path", description: "See your next recommended steps" },
  { to: "/recommendations", label: "Recommendations", description: "Personalized focus areas" },
  { to: "/weakness", label: "Weak topics", description: "Review topics to improve" },
  { to: "/analytics", label: "Analytics", description: "Track quiz and progress stats" },
  { to: "/profile", label: "Profile", description: "Account and learning level" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const enrollmentsQuery = useQuery({ queryKey: ["enrollments"], queryFn: getEnrollments });
  const analyticsQuery = useQuery({ queryKey: ["analytics-summary"], queryFn: getAnalyticsSummary });
  const recommendationsQuery = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => getRecommendations(),
  });
  const weaknessesQuery = useQuery({
    queryKey: ["weaknesses"],
    queryFn: () => getWeaknesses(),
  });
  const learningPathQuery = useQuery({ queryKey: ["learning-path"], queryFn: () => getLearningPath() });

  const enrollments = enrollmentsQuery.data ?? [];
  const analytics = analyticsQuery.data ?? {};
  const recommendations = recommendationsQuery.data ?? [];
  const weaknessPayload = weaknessesQuery.data ?? {};
  const learningPath = learningPathQuery.data ?? {};

  const isLoading =
    enrollmentsQuery.isLoading ||
    analyticsQuery.isLoading ||
    recommendationsQuery.isLoading ||
    weaknessesQuery.isLoading ||
    learningPathQuery.isLoading;

  const displayName = getDisplayName(user) || "Learner";
  const learningLevel = formatLevel(analytics.learning_level);

  const stats = useMemo(() => {
    const enrolledCount = enrollments.length;
    const lessonsCompleted = analytics.lessons_passed_quiz ?? 0;
    const avgQuizScore = Math.round(Number(analytics.avg_quiz_score) || 0);
    const weakTopicCount = analytics.weak_topics_tracked ?? 0;
    const completed = analytics.lessons_passed_quiz ?? 0;
    const remaining = analytics.lessons_remaining ?? 0;
    const total = analytics.total_lessons_in_enrolled_courses ?? completed + remaining;
    const courseCompletionPercent = total ? Math.round((completed / total) * 100) : 0;
    const courseAvgProgress = enrollments.length
      ? Math.round(
          enrollments.reduce((acc, c) => acc + normalizeNumber(c.progress), 0) / enrollments.length,
        )
      : 0;

    return {
      enrolledCount,
      lessonsCompleted,
      avgQuizScore,
      weakTopicCount,
      courseCompletionPercent,
      courseAvgProgress,
    };
  }, [enrollments, analytics]);

  const continueLearning = useMemo(() => {
    const path = learningPath?.learning_path ?? [];
    const progress = learningPath?.progress ?? {};
    const nextStep = path.find((s) => s.status === "next") ?? path[0];
    const lessonId = progress.next_lesson_id ?? nextStep?.lesson_id;

    if (lessonId && nextStep) {
      const stepLabel = nextStep.step ? `Lesson ${nextStep.step}: ` : "";
      return {
        courseTitle: nextStep.course_title || enrollments[0]?.title || "",
        lessonTitle: `${stepLabel}${nextStep.lesson_title ?? "Continue lesson"}`,
        progressPercent: Math.round(normalizeNumber(progress.percent_complete)),
        lessonId,
      };
    }

    const firstCourse = enrollments[0];
    if (firstCourse) {
      return {
        courseTitle: firstCourse.title,
        lessonTitle: "Open your course to start the next lesson",
        progressPercent: Math.round(normalizeNumber(firstCourse.progress)),
        courseId: firstCourse.id,
      };
    }

    return null;
  }, [learningPath, enrollments]);

  const topFocusArea = useMemo(() => {
    const lessonGroups = weaknessPayload.lesson_groups ?? [];
    if (lessonGroups.length) {
      const group = lessonGroups[0];
      const weakTopic = group.weak_topics?.[0];
      const recommended = group.recommended_lessons?.[0] ?? recommendations[0];
      return {
        focusLabel: formatTopicLabel(weakTopic?.topic_tag),
        fromLesson: group.lesson?.title,
        recommendedTitle: recommended?.title ?? recommended?.lesson_title,
        recommendedLessonId: recommended?.lesson_id ?? recommended?.lesson?.id,
      };
    }

    const topRec = recommendations[0];
    if (topRec) {
      return {
        focusLabel: topRec.focus_area || formatTopicLabel(topRec.weak_topic_tag),
        fromLesson: topRec.related_lessons_taken?.[0]?.title,
        recommendedTitle: topRec.lesson?.title ?? topRec.lesson_title,
        recommendedLessonId: topRec.lesson?.id ?? topRec.lesson_id,
      };
    }

    return null;
  }, [weaknessPayload, recommendations]);

  const pathPreviewSteps = useMemo(() => {
    const path = learningPath?.learning_path ?? [];
    if (!path.length) return [];
    const nextIndex = path.findIndex((s) => s.status === "next");
    const anchor = nextIndex >= 0 ? nextIndex : 0;
    const start = Math.max(0, anchor - 2);
    return path.slice(start, start + 4).map((step, index) => {
      const absoluteIndex = start + index;
      if (absoluteIndex < anchor) {
        return { ...step, status: "completed" };
      }
      return step;
    });
  }, [learningPath]);

  const motivationalMessage = useMemo(() => {
    if (!enrollments.length) return "Enroll in a course to start your personalized path.";
    if (stats.avgQuizScore >= 80) return "Excellent work — keep building on your momentum.";
    if (stats.weakTopicCount > 0) return "Focus on your next lesson — small steps add up.";
    return "Keep going — you're making great progress.";
  }, [enrollments.length, stats.avgQuizScore, stats.weakTopicCount]);

  return (
    <div className="space-y-5 p-4 pb-24 md:space-y-6 md:pb-6 md:p-6">
      {/* Section 1 — Welcome */}
      <header className="rounded-2xl border border-ocean-600/10 bg-white px-4 py-4 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <p className="text-xs font-medium uppercase tracking-wide text-muted dark:text-reef/80">
          {getGreeting()}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-ink dark:text-sand sm:text-2xl">
          Welcome back, {displayName}
        </h1>
        {learningLevel ? (
          <p className="mt-1 text-sm text-ocean-800 dark:text-reef">
            You are currently at <span className="font-semibold">{learningLevel} Level</span>.
          </p>
        ) : null}
        <p className="mt-1 text-sm text-muted dark:text-muted/90">{motivationalMessage}</p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Platform features">
        {featureLinks.map((item) => (
          <button
            key={item.to}
            type="button"
            onClick={() => navigate(item.to)}
            className="rounded-2xl border border-ocean-600/10 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-ocean-600/25 hover:shadow-panel dark:border-line/30 dark:bg-ocean-950/50"
          >
            <p className="font-semibold text-ocean-800 dark:text-reef">{item.label}</p>
            <p className="mt-1 text-sm text-muted dark:text-muted/90">{item.description}</p>
          </button>
        ))}
      </section>

      <Playground compact />

      {/* Section 2 — Continue Learning (priority 1) */}
      <section className="rounded-2xl border-2 border-ocean-200/50 bg-gradient-to-br from-reef/40 via-white to-sand p-5 shadow-lg dark:border-ocean-600/25 dark:from-ocean-600/10 dark:via-ocean-950/30 dark:to-coral/10 md:p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-ocean-800 dark:text-reef">
          Continue learning
        </p>
        {isLoading ? (
          <div className="mt-4">
            <LoadingState rows={2} />
          </div>
        ) : continueLearning ? (
          <div className="mt-4 space-y-4">
            <div className="min-w-0">
              <p className="text-lg font-bold text-ink dark:text-sand sm:text-xl">
                {continueLearning.courseTitle}
              </p>
              <p className="mt-1 text-sm text-ocean-800 dark:text-reef">{continueLearning.lessonTitle}</p>
            </div>
            <ProgressBar value={continueLearning.progressPercent} label="Progress" size="lg" />
            <button
              type="button"
              onClick={() =>
                continueLearning.lessonId
                  ? navigate(`/lessons/${continueLearning.lessonId}`)
                  : navigate(`/courses/${continueLearning.courseId}`)
              }
              className={primaryButtonClass}
            >
              {continueLearning.lessonId ? "Resume lesson" : "Open course"}
            </button>
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-muted dark:text-muted">
              No active lesson yet. Browse courses to begin.
            </p>
            <button type="button" onClick={() => navigate("/catalog")} className={primaryButtonClass}>
              Browse courses
            </button>
          </div>
        )}
      </section>

      {/* Section 3 — Learning Overview (4 metrics) */}
      <section aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="sr-only">
          Learning overview
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {isLoading ? (
            <div className="col-span-full">
              <LoadingState rows={2} />
            </div>
          ) : (
            <>
              <MetricCard title="Courses" value={stats.enrolledCount} icon={Icons.courses} color="blue" />
              <MetricCard title="Lessons" value={stats.lessonsCompleted} icon={Icons.lessons} color="green" />
              <MetricCard
                title="Avg score"
                value={`${stats.avgQuizScore}%`}
                icon={Icons.quiz}
                color="purple"
              />
              <MetricCard title="Weak topics" value={stats.weakTopicCount} icon={Icons.weak} color="amber" />
            </>
          )}
        </div>
      </section>

      {/* Section 4 — Top focus area */}
      <section className="rounded-2xl border border-amber-200/70 bg-amber-50/50 p-4 shadow-sm dark:border-amber-400/25 dark:bg-amber-500/10 md:p-5">
        <SectionHeader title="Top focus area" />
        {isLoading ? (
          <LoadingState rows={2} />
        ) : topFocusArea?.focusLabel ? (
          <div className="space-y-3">
            <p className="text-sm text-ocean-800 dark:text-muted">
              You are currently weak in:{" "}
              <span className="font-semibold text-ink dark:text-sand">{topFocusArea.focusLabel}</span>
            </p>
            {topFocusArea.fromLesson ? (
              <p className="text-sm text-muted dark:text-muted">
                From: <span className="font-medium">{topFocusArea.fromLesson}</span>
              </p>
            ) : null}
            {topFocusArea.recommendedTitle ? (
              <p className="text-sm text-muted dark:text-muted">
                Recommended:{" "}
                <span className="font-medium text-ink dark:text-sand">{topFocusArea.recommendedTitle}</span>
              </p>
            ) : null}
            <button
              type="button"
              onClick={() =>
                topFocusArea.recommendedLessonId
                  ? navigate(`/lessons/${topFocusArea.recommendedLessonId}`)
                  : navigate("/recommendations")
              }
              className={primaryButtonClass}
            >
              Continue
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted dark:text-muted">
              Finish a quiz to unlock your top focus area.
            </p>
            <button type="button" onClick={() => navigate("/recommendations")} className={linkButtonClass}>
              View recommendations
            </button>
          </div>
        )}
      </section>

      {/* Section 5 — Learning path progress (priority 4) */}
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <SectionHeader title="Learning path" subtitle="Current step" />
        {learningPathQuery.isLoading ? (
          <LoadingState rows={2} />
        ) : (
          <>
            <PathProgressPreview steps={pathPreviewSteps} />
            <button type="button" onClick={() => navigate("/learning-path")} className={`mt-4 ${linkButtonClass}`}>
              View full learning path
            </button>
          </>
        )}
      </section>

      {/* Section 6 — Performance snapshot (priority 5) */}
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
        <SectionHeader title="Performance snapshot" />
        {isLoading ? (
          <LoadingState rows={2} />
        ) : (
          <div className="space-y-4">
            <ProgressBar value={stats.avgQuizScore} label="Average quiz score" size="sm" />
            <ProgressBar
              value={stats.courseAvgProgress || stats.courseCompletionPercent}
              label="Course completion"
              size="sm"
            />
          </div>
        )}
      </section>
    </div>
  );
}
