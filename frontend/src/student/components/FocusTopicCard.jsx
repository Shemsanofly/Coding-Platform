import SeverityBadge from "@/student/components/SeverityBadge";
import RecommendationLessonCard from "@/student/components/RecommendationLessonCard";

function formatTopicLabel(tag) {
  return String(tag || "").replace(/_/g, " ");
}

function getAccuracyPercent(topic) {
  if (topic?.accuracy_percent != null) return topic.accuracy_percent;
  if (topic?.score != null) return topic.score;
  const attempts = Number(topic?.attempt_count) || 0;
  const correct = Number(topic?.correct_count) || 0;
  if (attempts <= 0) return 0;
  return Math.round((correct / attempts) * 1000) / 10;
}

function buildWhyItMatters(topic) {
  const label = formatTopicLabel(topic.topic_tag || topic.topic);
  const accuracy = getAccuracyPercent(topic);
  if (accuracy < 40) {
    return `You missed most questions related to ${label}, so you should review how these concepts work before moving forward.`;
  }
  return `You struggled with ${label} in your recent quizzes. Strengthen this area to improve your overall score.`;
}

function buildLessonReason(topic, lessonTitle) {
  const label = formatTopicLabel(topic?.topic_tag || topic?.topic);
  const title = lessonTitle || "this lesson";
  return `You struggled with ${label} in your recent quiz. Review ${title} first before moving forward.`;
}

export default function FocusTopicCard({ topic, recommendations, onStudyLesson }) {
  const label = formatTopicLabel(topic.topic_tag || topic.topic);
  const level = topic.weakness_level || topic.level;
  const accuracy = getAccuracyPercent(topic);
  const attempts = topic.attempt_count ?? 0;
  const correct = topic.correct_count ?? 0;
  const primary = recommendations[0] ?? null;

  return (
    <article className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
            Focus area
          </p>
          <h3 className="mt-1 text-lg font-semibold text-ink dark:text-sand">{label}</h3>
        </div>
        <SeverityBadge level={level} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/30 dark:bg-ocean-950/40">
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
            Accuracy
          </dt>
          <dd className="mt-0.5 text-sm font-bold text-ink dark:text-sand">{accuracy}%</dd>
        </div>
        <div className="rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/30 dark:bg-ocean-950/40">
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
            Attempts
          </dt>
          <dd className="mt-0.5 text-sm font-bold text-ink dark:text-sand">{attempts}</dd>
        </div>
        <div className="rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/30 dark:bg-ocean-950/40">
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
            Correct
          </dt>
          <dd className="mt-0.5 text-sm font-bold text-ink dark:text-sand">{correct}</dd>
        </div>
        <div className="rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/30 dark:bg-ocean-950/40">
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
            Weakness
          </dt>
          <dd className="mt-0.5 text-sm font-bold uppercase text-ink dark:text-sand">{level || "—"}</dd>
        </div>
      </dl>

      <div className="mt-4 rounded-xl border border-amber-200/70 bg-amber-50/60 p-3 dark:border-amber-400/30 dark:bg-amber-500/10">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-900 dark:text-amber-100/90">
          Why this matters
        </p>
        <p className="mt-1 text-sm leading-relaxed text-ocean-800 dark:text-muted">
          {buildWhyItMatters(topic)}
        </p>
      </div>

      {primary ? (
        <div className="mt-4">
          <RecommendationLessonCard
            lessonTitle={primary.lesson_title}
            courseTitle={primary.course_title}
            reason={buildLessonReason(topic, primary.lesson_title)}
            onStudy={() => onStudyLesson(primary)}
          />
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted dark:text-muted">
          No matching lesson found yet for this topic. Ask your instructor to tag lessons with &ldquo;{label}&rdquo;.
        </p>
      )}

      {recommendations.length > 1 ? (
        <ul className="mt-4 space-y-2 border-t border-line pt-4 dark:border-line/20">
          {recommendations.slice(1).map((item, index) => (
            <li key={item.id ?? `${item.lesson_id}-${index}`}>
              <button
                type="button"
                onClick={() => onStudyLesson(item)}
                className="min-h-[44px] text-left text-sm font-medium text-ocean-700 hover:underline dark:text-reef"
              >
                Also study: {item.lesson_title}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
