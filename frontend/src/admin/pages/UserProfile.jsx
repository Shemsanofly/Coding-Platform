import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import AdminMetricCard from "@/admin/components/AdminMetricCard";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import {
  getAdminUserProfile,
  getAdminUserQuizLog,
  getAdminUserRecommendations,
  getAdminUserWeaknesses,
} from "@/api/adminUsers";

const normalizeNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const parseDate = (value) => {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
};

const formatDateTime = (value) => {
  const date = parseDate(value);
  return date ? date.toLocaleString() : "N/A";
};

const getInitials = (name) => {
  const safeName = String(name || "").trim();
  if (!safeName) {
    return "NA";
  }
  const parts = safeName.split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() || "").join("");
};

function LevelBadge({ level }) {
  const normalized = typeof level === "string" ? level.toUpperCase() : "NONE";
  const styles = {
    HIGH: "bg-red-100 text-red-700 border-red-200",
    MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
    LOW: "bg-reef text-ocean-800 border-ocean-200",
    NONE: "bg-cream text-muted border-line",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${styles[normalized] || styles.NONE}`}
    >
      {normalized}
    </span>
  );
}

function AdminWeaknessMap({ topics }) {
  if (!topics.length) {
    return <p className="text-sm text-muted">No weakness topics available.</p>;
  }

  return (
    <div className="space-y-3">
      {topics.map((topic, index) => {
        const attempts = normalizeNumber(topic.attempt_count);
        const correct = normalizeNumber(topic.correct_count);
        const accuracy = attempts > 0 ? Math.round((correct / attempts) * 100) : 0;

        return (
          <article
            key={topic.id ?? `${topic.topic_tag || "topic"}-${index}`}
            className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/40 dark:bg-ocean-950/40"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-ink">{topic.topic_tag || "Unknown topic"}</p>
                <p className="mt-1 text-xs text-muted">
                  {attempts} attempts · {accuracy}% accuracy
                </p>
              </div>
              <LevelBadge level={topic.weakness_level} />
            </div>
          </article>
        );
      })}
    </div>
  );
}

function RecommendationsList({ items }) {
  if (!items.length) {
    return <p className="text-sm text-muted">No recommendations available.</p>;
  }

  return (
    <ul className="space-y-3">
      {items.map((item, index) => (
        <li
          key={item.id ?? `${item.lesson_title || "lesson"}-${index}`}
          className="rounded-xl border border-ocean-600/10 bg-white p-3 dark:border-line/40 dark:bg-ocean-950/40"
        >
          <p className="text-sm font-semibold text-ink">{item.lesson_title || item.title || "Untitled lesson"}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-reef/50 px-2 py-1 font-medium text-ocean-800">
              Triggered by: {item.triggered_by || "weakness"}
            </span>
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                String(item.status).toLowerCase() === "done"
                  ? "bg-green-100 text-green-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {String(item.status || "active")}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function QuizAttemptLog({ attempts }) {
  const [sortKey, setSortKey] = useState("taken_at");
  const [sortOrder, setSortOrder] = useState("desc");

  const sortedAttempts = useMemo(() => {
    const list = [...attempts];
    list.sort((a, b) => {
      const direction = sortOrder === "asc" ? 1 : -1;

      if (sortKey === "score") {
        return (normalizeNumber(a.score) - normalizeNumber(b.score)) * direction;
      }
      if (sortKey === "accuracy") {
        return (normalizeNumber(a.accuracy) - normalizeNumber(b.accuracy)) * direction;
      }

      const aTime = parseDate(a.taken_at)?.getTime() ?? 0;
      const bTime = parseDate(b.taken_at)?.getTime() ?? 0;
      return (aTime - bTime) * direction;
    });
    return list;
  }, [attempts, sortKey, sortOrder]);

  return (
    <section className="rounded-2xl border border-ocean-600/10 bg-white/90 p-4 shadow-panel backdrop-blur">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Quiz attempt log</h2>
        <div className="flex items-center gap-2">
          <select
            value={sortKey}
            onChange={(event) => setSortKey(event.target.value)}
            className="lc-input py-1.5 text-xs"
          >
            <option value="taken_at">Sort by date</option>
            <option value="score">Sort by score</option>
            <option value="accuracy">Sort by accuracy</option>
          </select>
          <select
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}
            className="lc-input py-1.5 text-xs"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full divide-y divide-line">
          <thead className="bg-reef/60">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                Quiz
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                Score
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                Accuracy
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                Taken at
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/70 bg-white">
            {sortedAttempts.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-sm text-muted" colSpan={4}>
                  No quiz attempts yet.
                </td>
              </tr>
            ) : (
              sortedAttempts.map((attempt, index) => (
                <tr key={attempt.id ?? `${attempt.quiz_title || "quiz"}-${index}`}>
                  <td className="px-3 py-2 text-sm text-ink">{attempt.quiz_title || "Quiz attempt"}</td>
                  <td className="px-3 py-2 text-sm text-ink">{normalizeNumber(attempt.score)}</td>
                  <td className="px-3 py-2 text-sm text-ink">{normalizeNumber(attempt.accuracy)}%</td>
                  <td className="px-3 py-2 text-sm text-muted">{formatDateTime(attempt.taken_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="space-y-2 md:hidden">
        {sortedAttempts.length === 0 ? (
          <p className="text-sm text-muted">No quiz attempts yet.</p>
        ) : (
          sortedAttempts.map((attempt, index) => (
            <article
              key={attempt.id ?? `${attempt.quiz_title}-${index}`}
              className="rounded-xl border border-ocean-600/10 bg-white p-3 text-sm dark:border-line/40 dark:bg-ocean-950/40"
            >
              <p className="font-medium text-ink">{attempt.quiz_title || "Quiz attempt"}</p>
              <p className="text-muted">
                Score {normalizeNumber(attempt.score)}% · {formatDateTime(attempt.taken_at)}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

export default function UserProfile() {
  const navigate = useNavigate();
  const { id } = useParams();

  const queryResults = useQueries({
    queries: [
      {
        queryKey: ["admin-user-profile", id],
        queryFn: () => getAdminUserProfile(id),
        enabled: Boolean(id),
      },
      {
        queryKey: ["admin-user-weaknesses", id],
        queryFn: () => getAdminUserWeaknesses(id),
        enabled: Boolean(id),
      },
      {
        queryKey: ["admin-user-recommendations", id],
        queryFn: () => getAdminUserRecommendations(id),
        enabled: Boolean(id),
      },
      {
        queryKey: ["admin-user-quiz-log", id],
        queryFn: () => getAdminUserQuizLog(id),
        enabled: Boolean(id),
      },
    ],
  });

  const [profileQuery, weaknessesQuery, recommendationsQuery, quizLogQuery] = queryResults;
  const isLoading = queryResults.some((query) => query.isLoading || query.isPending);
  const isError = queryResults.some((query) => query.isError);

  const profile = profileQuery.data || {};
  const weaknesses = Array.isArray(weaknessesQuery.data)
    ? weaknessesQuery.data
    : weaknessesQuery.data?.results || [];
  const recommendations = Array.isArray(recommendationsQuery.data)
    ? recommendationsQuery.data
    : recommendationsQuery.data?.results || [];
  const quizLog = Array.isArray(quizLogQuery.data) ? quizLogQuery.data : quizLogQuery.data?.results || [];

  return (
    <div className="space-y-5 p-4 md:p-6">
      <button
        type="button"
        onClick={() => navigate("/admin/users")}
        className="inline-flex items-center rounded-xl border border-ocean-600/20 bg-white/90 px-3 py-1.5 text-sm font-medium text-ocean-800 transition hover:bg-reef/60"
      >
        {"\u2190"} Back to users
      </button>

      {isLoading ? <LoadingState label="Loading user profile…" rows={3} /> : null}
      {isError ? (
        <ErrorState title="Profile unavailable" message="Failed to load one or more profile sections." />
      ) : null}

      {!isLoading && !isError ? (
        <>
          <header className="rounded-2xl border border-ocean-600/10 bg-white/90 p-5 shadow-panel backdrop-blur">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-reef text-sm font-bold text-ocean-800">
                  {getInitials(profile.name || profile.full_name)}
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-ink">
                    {profile.name || profile.full_name || "Unknown student"}
                  </h1>
                  <p className="text-sm text-muted">{profile.email || "No email provided"}</p>
                  <p className="mt-1 text-xs capitalize text-muted">
                    Learning level: {profile.learning_level || "not set"}
                  </p>
                </div>
              </div>
              <p className="text-sm text-muted">Last active: {formatDateTime(profile.last_active)}</p>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <AdminMetricCard title="Enrolled" value={profile.enrolled_count ?? 0} color="blue" />
              <AdminMetricCard title="Lessons completed" value={profile.completed_lessons ?? 0} color="green" />
              <AdminMetricCard
                title="Avg score"
                value={
                  profile.avg_score != null
                    ? `${Math.round(normalizeNumber(profile.avg_score))}%`
                    : "N/A"
                }
                color="purple"
              />
              <AdminMetricCard title="Quiz attempts" value={profile.quiz_attempts ?? quizLog.length} color="slate" />
              <AdminMetricCard
                title="Weak topics"
                value={profile.weak_topics_count ?? weaknesses.length}
                color="amber"
              />
            </div>

            <p className="mt-4 rounded-xl border border-line/70 bg-cream px-3 py-2 text-sm text-ocean-800">
              <span className="font-semibold text-ink">Learning path summary: </span>
              {recommendations.length > 0
                ? `${recommendations.length} active recommendation(s) targeting weak areas.`
                : "No active recommendations — student is on track or has not triggered adaptive suggestions."}
              {weaknesses.length > 0
                ? ` ${weaknesses.length} weakness topic(s) tracked.`
                : " No weakness topics recorded yet."}
            </p>
          </header>

          <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <article className="rounded-2xl border border-ocean-600/10 bg-white/90 p-4 shadow-panel backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-ink">Weakness map</h2>
              <AdminWeaknessMap topics={weaknesses} />
            </article>

            <article className="rounded-2xl border border-ocean-600/10 bg-white/90 p-4 shadow-panel backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-ink">Recommendations</h2>
              <RecommendationsList items={recommendations} />
            </article>
          </section>

          <QuizAttemptLog attempts={quizLog} />
        </>
      ) : null}
    </div>
  );
}
