import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import SectionHeader from "@/student/components/SectionHeader";
import ProgressBar from "@/student/components/ProgressBar";

function formatShortDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

export function QuizScoreTrendChart({ scores = [] }) {
  const chartData = useMemo(
    () =>
      [...scores].reverse().map((row, index) => ({
        id: `${row.taken_at}-${index}`,
        label: formatShortDate(row.taken_at) || `#${index + 1}`,
        score: Number(row.score) || 0,
      })),
    [scores],
  );

  if (!chartData.length) {
    return (
      <p className="text-sm text-muted dark:text-muted">Complete a quiz to see your score trend.</p>
    );
  }

  return (
    <div className="h-52 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.35)" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
          <Tooltip
            formatter={(value) => [`${value}%`, "Score"]}
            contentStyle={{ borderRadius: "0.75rem", fontSize: "12px" }}
          />
          <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WeakTopicsSeverityChart({ weaknesses = [] }) {
  const chartData = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0, OTHER: 0 };
    weaknesses.forEach((topic) => {
      const level = (topic.weakness_level || topic.level || "").toString().toUpperCase();
      if (counts[level] !== undefined) {
        counts[level] += 1;
      } else {
        counts.OTHER += 1;
      }
    });
    return [
      { name: "High", count: counts.HIGH, fill: "#ef4444" },
      { name: "Medium", count: counts.MEDIUM, fill: "#f59e0b" },
      { name: "Low", count: counts.LOW, fill: "#3b82f6" },
      { name: "Other", count: counts.OTHER, fill: "#94a3b8" },
    ].filter((row) => row.count > 0);
  }, [weaknesses]);

  if (!chartData.length) {
    return <p className="text-sm text-muted dark:text-muted">No weak topics tracked yet.</p>;
  }

  return (
    <div className="h-52 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.35)" />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
          <Tooltip />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LessonsCompletedChart({ completed = 0, remaining = 0, total = 0 }) {
  const safeTotal = total || completed + remaining;
  const chartData = useMemo(
    () => [
      { name: "Completed", value: completed, fill: "#22c55e" },
      { name: "Remaining", value: remaining, fill: "#94a3b8" },
    ],
    [completed, remaining],
  );

  if (!safeTotal) {
    return (
      <p className="text-sm text-muted dark:text-muted">
        Enroll in a course to track lesson progress.
      </p>
    );
  }

  const percent = safeTotal ? Math.round((completed / safeTotal) * 100) : 0;

  return (
    <div className="space-y-4">
      <ProgressBar value={percent} label="Overall lesson completion" />
      <div className="h-40 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis
              type="category"
              dataKey="name"
              width={88}
              tick={{ fontSize: 11, fill: "#64748b" }}
            />
            <Tooltip />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#6366f1" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted dark:text-muted">
        {completed} completed · {remaining} remaining · {safeTotal} total in enrolled courses
      </p>
    </div>
  );
}

export default function DashboardAnalytics({ analytics, weaknesses, enrollments }) {
  const recentScores = Array.isArray(analytics?.recent_quiz_scores)
    ? analytics.recent_quiz_scores
    : [];
  const completed = analytics?.lessons_passed_quiz ?? 0;
  const remaining = analytics?.lessons_remaining ?? 0;
  const total = analytics?.total_lessons_in_enrolled_courses ?? completed + remaining;

  const courseAvgProgress = useMemo(() => {
    if (!enrollments?.length) return 0;
    const sum = enrollments.reduce((acc, c) => acc + (Number(c.progress) || 0), 0);
    return Math.round(sum / enrollments.length);
  }, [enrollments]);

  return (
    <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
      <SectionHeader
        title="Learning analytics"
        subtitle="Quiz trends, weak-topic severity, and completion across your enrolled courses."
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="min-w-0 rounded-xl border border-line/70 bg-cream/80 p-4 dark:border-line/20 dark:bg-black/20">
          <h3 className="text-sm font-semibold text-ink dark:text-sand">Quiz score trend</h3>
          <div className="mt-3">
            <QuizScoreTrendChart scores={recentScores} />
          </div>
        </div>
        <div className="min-w-0 rounded-xl border border-line/70 bg-cream/80 p-4 dark:border-line/20 dark:bg-black/20">
          <h3 className="text-sm font-semibold text-ink dark:text-sand">Weak topics by severity</h3>
          <div className="mt-3">
            <WeakTopicsSeverityChart weaknesses={weaknesses} />
          </div>
        </div>
        <div className="min-w-0 rounded-xl border border-line/70 bg-cream/80 p-4 dark:border-line/20 dark:bg-black/20">
          <h3 className="text-sm font-semibold text-ink dark:text-sand">Course completion</h3>
          <p className="mt-1 text-xs text-muted dark:text-muted">
            Average progress across enrollments: {courseAvgProgress}%
          </p>
          <div className="mt-3 space-y-3">
            {enrollments?.slice(0, 4).map((course) => (
              <ProgressBar key={course.id} label={course.title} value={course.progress} size="sm" />
            ))}
          </div>
        </div>
        <div className="min-w-0 rounded-xl border border-line/70 bg-cream/80 p-4 dark:border-line/20 dark:bg-black/20">
          <h3 className="text-sm font-semibold text-ink dark:text-sand">
            Lessons completed vs remaining
          </h3>
          <div className="mt-3">
            <LessonsCompletedChart completed={completed} remaining={remaining} total={total} />
          </div>
        </div>
      </div>
    </section>
  );
}
