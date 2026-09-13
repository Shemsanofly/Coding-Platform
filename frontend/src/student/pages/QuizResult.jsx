import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ScoreBadge from "@/student/components/ScoreBadge";
import SectionHeader from "@/student/components/SectionHeader";
const PASS_THRESHOLD = 60;

export default function QuizResult() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const { lessonId } = useParams();
  const result = location.state?.result;
  const [showRecommendationsButton, setShowRecommendationsButton] = useState(false);

  const score = Number(result?.score ?? 0);
  const total = Number(result?.total_questions ?? result?.total ?? 0);
  const correct = Number(result?.correct_answers ?? result?.correct ?? 0);
  const wrong = Math.max(0, total - correct);
  const passed = typeof result?.passed === "boolean" ? result.passed : score >= PASS_THRESHOLD;
  const explanations = Array.isArray(result?.explanations) ? result.explanations : [];

  const affectedTopics = useMemo(() => {
    const tags = new Set();
    explanations.forEach((item) => {
      if (item.topic_tag) tags.add(item.topic_tag);
    });
    return [...tags];
  }, [explanations]);

  useEffect(() => {
    if (passed) return undefined;
    const timer = window.setTimeout(() => setShowRecommendationsButton(true), 1500);
    return () => window.clearTimeout(timer);
  }, [passed]);

  useEffect(() => {
    const lid = Number(lessonId);
    queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["enrollments"] });
    queryClient.invalidateQueries({ queryKey: ["weaknesses"] });
    queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
    queryClient.invalidateQueries({ queryKey: ["learning-path"] });
    if (Number.isFinite(lid)) {
      queryClient.invalidateQueries({ queryKey: ["student-lesson", lid] });
    }
  }, [lessonId, queryClient]);

  if (!result) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 md:p-6">
        <p className="text-sm text-muted dark:text-muted">
          No quiz result data. Take the quiz first.
        </p>
        <button
          type="button"
          onClick={() => navigate(`/lessons/${lessonId}/quiz`)}
          className="min-h-[44px] rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Go to quiz
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 overflow-x-hidden p-4 md:p-6">
      <div className="rounded-2xl border border-ocean-600/10 bg-white p-6 text-center shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
        <p className="text-sm uppercase tracking-wider text-muted dark:text-muted">Quiz result</p>
        <p className="mt-2 text-5xl font-bold tabular-nums text-ink dark:text-sand sm:text-6xl">
          {score}%
        </p>
        <div className="mt-4 flex justify-center">
          <ScoreBadge score={score} passed={passed} threshold={PASS_THRESHOLD} />
        </div>
        <div className="mt-6 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-xl bg-emerald-50 px-3 py-2 dark:bg-emerald-500/15">
            <p className="text-xs text-muted dark:text-reef/90">Correct</p>
            <p className="text-lg font-bold text-emerald-800 dark:text-emerald-100">{correct}</p>
          </div>
          <div className="rounded-xl bg-rose-50 px-3 py-2 dark:bg-rose-500/15">
            <p className="text-xs text-muted dark:text-reef/90">Wrong</p>
            <p className="text-lg font-bold text-rose-800 dark:text-rose-100">{wrong}</p>
          </div>
          <div className="col-span-2 rounded-xl bg-cream px-3 py-2 sm:col-span-1 dark:bg-black/20">
            <p className="text-xs text-muted dark:text-reef/90">Total</p>
            <p className="text-lg font-bold text-ink dark:text-sand">{total}</p>
          </div>
        </div>
      </div>

      {explanations.length > 0 ? (
        <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 md:p-5">
          <SectionHeader title="Answer explanations" subtitle="Review what you missed and why." />
          <ul className="space-y-3 text-sm">
            {explanations.map((item, index) => (
              <li
                key={item.question_id ?? index}
                className="rounded-xl border border-line/70 bg-cream px-3 py-3 dark:border-line/20 dark:bg-black/20"
              >
                {item.topic_tag ? (
                  <p className="text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
                    {item.topic_tag.replace(/_/g, " ")}
                  </p>
                ) : null}
                <p className="mt-1 text-ocean-800 dark:text-muted">
                  {item.explanation || "No explanation provided."}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {affectedTopics.length > 0 ? (
        <section className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-400/30 dark:bg-amber-500/10">
          <SectionHeader
            title="Weak topics affected"
            subtitle="These tags may update after analytics refresh."
          />
          <div className="flex flex-wrap gap-2">
            {affectedTopics.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-amber-300/60 bg-white px-3 py-1 text-xs font-medium text-amber-950 dark:border-amber-400/40 dark:bg-black/20 dark:text-amber-100"
              >
                {tag.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 dark:border-line/40 dark:bg-ocean-950/50">
        <SectionHeader
          title="Recommended next action"
          subtitle={
            passed
              ? "Great work — keep momentum on your path."
              : "Strengthen weak areas before moving on."
          }
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          {passed ? (
            <>
              <button
                type="button"
                onClick={() => navigate("/learning-path")}
                className="min-h-[44px] rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white"
              >
                View learning path
              </button>
              <button
                type="button"
                onClick={() => navigate("/")}
                className="min-h-[44px] rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink dark:border-line/40 dark:text-sand"
              >
                Dashboard
              </button>
            </>
          ) : (
            <>
              {!showRecommendationsButton ? (
                <p className="text-sm text-amber-900 dark:text-amber-100">
                  Updating weakness profile…
                </p>
              ) : null}
              {showRecommendationsButton ? (
                <button
                  type="button"
                  onClick={() => navigate("/recommendations")}
                  className="min-h-[44px] rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 px-4 py-2 text-sm font-semibold text-white"
                >
                  View recommendations
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => navigate("/weakness")}
                className="min-h-[44px] rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink dark:border-line/40 dark:text-sand"
              >
                Review weak topics
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => navigate(`/lessons/${lessonId}/quiz`)}
            className="min-h-[44px] rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink dark:border-line/40 dark:text-sand"
          >
            {passed ? "Retry quiz" : "Try again"}
          </button>
          <button
            type="button"
            onClick={() => navigate(`/lessons/${lessonId}`)}
            className="min-h-[44px] rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink dark:border-line/40 dark:text-sand"
          >
            Back to lesson
          </button>
        </div>
      </section>
    </div>
  );
}
