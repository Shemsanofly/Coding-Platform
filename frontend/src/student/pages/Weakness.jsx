import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getWeaknesses } from "@/api/studentDashboard";
import CourseFilterSelect from "@/student/components/CourseFilterSelect";
import SeverityBadge from "@/student/components/SeverityBadge";
import EmptyState from "@/student/components/EmptyState";
import LoadingState from "@/student/components/LoadingState";

const formatTopicLabel = (tag) => String(tag || "").replace(/_/g, " ");

function LessonWeaknessGroup({ group, onStartLesson }) {
  const recommended = group.recommended_lessons?.[0] ?? null;

  return (
    <article className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-line/30 dark:bg-ocean-950/40 md:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
        Course: {group.course?.title}
      </p>
      <h3 className="mt-2 text-lg font-semibold text-ink dark:text-sand">
        Lesson taken: {group.lesson?.title}
      </h3>
      {group.score != null ? (
        <p className="mt-1 text-sm text-muted dark:text-muted">Score: {group.score}%</p>
      ) : null}

      <div className="mt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/80">
          Weak topics
        </p>
        <ul className="mt-2 space-y-2">
          {(group.weak_topics ?? []).map((topic) => (
            <li
              key={topic.topic_tag}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ocean-600/10 bg-cream px-3 py-2 dark:border-line/20 dark:bg-ocean-950/40"
            >
              <span className="font-medium text-ink dark:text-sand">
                {formatTopicLabel(topic.topic_tag)}
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge level={topic.weakness_level} />
                <span className="text-xs text-muted dark:text-muted">
                  Accuracy {topic.accuracy ?? 0}%
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {recommended ? (
        <div className="mt-4 rounded-xl border border-ocean-200/70 bg-reef/60 p-3 dark:border-ocean-600/30 dark:bg-ocean-600/10">
          <p className="text-xs font-semibold uppercase tracking-wide text-ocean-900 dark:text-reef/90">
            Recommended next
          </p>
          <p className="mt-1 font-medium text-ink dark:text-sand">{recommended.title}</p>
          <p className="mt-1 text-sm text-muted dark:text-muted">{recommended.reason}</p>
          <button
            type="button"
            onClick={() => onStartLesson(recommended.lesson_id)}
            className="mt-3 min-h-[44px] rounded-xl bg-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-700"
          >
            Start lesson
          </button>
        </div>
      ) : null}
    </article>
  );
}

export default function Weakness() {
  const navigate = useNavigate();
  const [courseFilter, setCourseFilter] = useState("");

  const { data, isLoading, isPending } = useQuery({
    queryKey: ["weaknesses", courseFilter || "all"],
    queryFn: () => getWeaknesses({ courseId: courseFilter || undefined }),
  });

  const showLoading = isLoading || isPending;
  const topics = data?.topics ?? [];
  const lessonGroups = data?.lesson_groups ?? [];
  const courses = data?.courses ?? [];

  const groupedByCourse = useMemo(() => {
    const map = new Map();
    lessonGroups.forEach((group) => {
      const courseId = group.course?.id ?? "unknown";
      if (!map.has(courseId)) {
        map.set(courseId, { course: group.course, groups: [] });
      }
      map.get(courseId).groups.push(group);
    });
    return Array.from(map.values());
  }, [lessonGroups]);

  const stats = useMemo(() => {
    const highCount = topics.filter((item) => (item.weakness_level || "").toUpperCase() === "HIGH").length;
    const mediumCount = topics.filter((item) => (item.weakness_level || "").toUpperCase() === "MEDIUM").length;
    return { totalWeakTopics: topics.length, highCount, mediumCount };
  }, [topics]);

  return (
    <div className="space-y-6 p-4 pb-24 md:p-6 md:pb-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink dark:text-sand">Weak topics</h1>
          <p className="text-sm text-muted dark:text-reef/80">
            See which course and lesson revealed each weakness, and what to study next.
          </p>
        </div>
        <Link
          to="/recommendations"
          className="inline-flex min-h-[44px] items-center rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink shadow-sm transition hover:bg-cream dark:border-transparent dark:bg-ocean-950/60 dark:text-sand dark:hover:bg-ocean-900/70"
        >
          See recommendations
        </Link>
      </header>

      <CourseFilterSelect
        courses={courses}
        value={courseFilter}
        onChange={setCourseFilter}
        className="max-w-md"
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <article className="rounded-xl border border-blue-200 bg-white p-4 shadow-sm dark:border-blue-300/30 dark:bg-ocean-950/50">
          <p className="text-sm text-muted dark:text-reef">Total weak topics</p>
          <p className="mt-2 text-2xl font-bold text-ink dark:text-sand">{stats.totalWeakTopics}</p>
        </article>
        <article className="rounded-xl border border-red-200 bg-white p-4 shadow-sm dark:border-red-300/30 dark:bg-ocean-950/50">
          <p className="text-sm text-muted dark:text-reef">HIGH count</p>
          <p className="mt-2 text-2xl font-bold text-ink dark:text-sand">{stats.highCount}</p>
        </article>
        <article className="rounded-xl border border-amber-200 bg-white p-4 shadow-sm dark:border-amber-300/30 dark:bg-ocean-950/50">
          <p className="text-sm text-muted dark:text-reef">MEDIUM count</p>
          <p className="mt-2 text-2xl font-bold text-ink dark:text-sand">{stats.mediumCount}</p>
        </article>
      </section>

      {showLoading ? <LoadingState label="Loading weakness insights…" rows={4} /> : null}

      {!showLoading && !lessonGroups.length && !topics.length ? (
        <EmptyState
          title="No weak topics yet"
          message="Complete a quiz to discover topics that need more practice."
        />
      ) : null}

      {!showLoading && groupedByCourse.length > 0 ? (
        <section className="space-y-6">
          {groupedByCourse.map(({ course, groups }) => (
            <div key={course?.id ?? course?.title} className="space-y-4">
              <h2 className="text-lg font-semibold text-ink dark:text-sand">
                Course: {course?.title}
              </h2>
              {groups.map((group) => (
                <LessonWeaknessGroup
                  key={`${group.lesson?.id}-${group.quiz_result_id}`}
                  group={group}
                  onStartLesson={(lessonId) => navigate(`/lessons/${lessonId}`)}
                />
              ))}
            </div>
          ))}
        </section>
      ) : null}

      {!showLoading && topics.length > 0 && !lessonGroups.length ? (
        <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-lg dark:border-line/40 dark:bg-ocean-950/50">
          <h2 className="text-lg font-semibold text-ink dark:text-sand">Tracked weak topics</h2>
          <ul className="mt-4 divide-y divide-line dark:divide-line/30">
            {topics.map((topic) => (
              <li key={topic.id ?? topic.topic_tag} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="font-medium text-ink dark:text-sand">
                    {formatTopicLabel(topic.topic_tag)}
                  </p>
                  {topic.recent_lessons?.[0] ? (
                    <p className="text-xs text-muted dark:text-muted">
                      From: {topic.recent_lessons[0].title}
                    </p>
                  ) : null}
                </div>
                <div className="flex items-center gap-2">
                  <SeverityBadge level={topic.weakness_level} />
                  <span className="text-xs text-muted dark:text-muted">
                    Accuracy {topic.accuracy ?? topic.accuracy_percent ?? 0}%
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
