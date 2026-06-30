import SeverityBadge from "@/student/components/SeverityBadge";

const PRIORITY_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2 };

function formatTopicLabel(tag) {
  return String(tag || "").replace(/_/g, " ");
}

function sortWeakTopics(topics) {
  return [...topics].sort((a, b) => {
    const levelA = PRIORITY_ORDER[(a.weakness_level || a.level || "").toUpperCase()] ?? 99;
    const levelB = PRIORITY_ORDER[(b.weakness_level || b.level || "").toUpperCase()] ?? 99;
    if (levelA !== levelB) return levelA - levelB;
    return formatTopicLabel(a.topic_tag || a.topic).localeCompare(formatTopicLabel(b.topic_tag || b.topic));
  });
}

export default function WeaknessSummaryCard({ topics }) {
  const sorted = sortWeakTopics(topics);

  if (!sorted.length) {
    return (
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
        <h2 className="text-lg font-semibold text-ink dark:text-sand">Your focus summary</h2>
        <p className="mt-2 text-sm text-muted dark:text-muted">
          No weak topics detected yet. Complete quizzes to receive personalized recommendations.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-5">
      <h2 className="text-lg font-semibold text-ink dark:text-sand">Your focus summary</h2>
      <p className="mt-1 text-sm text-muted dark:text-muted">
        You need to focus on {sorted.length} topic{sorted.length === 1 ? "" : "s"}:
      </p>
      <ol className="mt-4 space-y-2">
        {sorted.map((topic, index) => {
          const label = formatTopicLabel(topic.topic_tag || topic.topic);
          const level = topic.weakness_level || topic.level;
          return (
            <li
              key={topic.id ?? `${label}-${index}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/30 dark:bg-ocean-950/40"
            >
              <span className="text-sm font-medium text-ink dark:text-sand">
                {index + 1}. {label}
              </span>
              <SeverityBadge level={level} />
            </li>
          );
        })}
      </ol>
    </section>
  );
}
