import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  bootstrapCourseCatalog,
  createAdminCourse,
  createAdminLesson,
  deleteAdminLesson,
  getAdminCourse,
  getAdminCourses,
  getAdminLessons,
  updateAdminCourse,
} from "@/api/adminCourses";
import EmptyState from "@/admin/components/EmptyState";
import LessonAIStatusPanel from "@/admin/components/LessonAIStatusPanel";
import LoadingState from "@/admin/components/LoadingState";
import PipelineStatus from "@/admin/components/PipelineStatus";
import SectionHeader from "@/student/components/SectionHeader";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import PageHeader from "@/shared/components/ui/PageHeader";
import { CourseLevelBadge, CourseMetric, CourseStatusPill } from "@/shared/components/course/CourseBadges";
import { formatSourceTypeLabel, getLessonSourceOption, LESSON_SOURCE_OPTIONS } from "@/shared/constants/lessonSources";

const LEVEL_OPTIONS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

function normalizeCourseLevel(raw) {
  const tier = String(raw ?? "").trim().toLowerCase();
  if (tier === "beginner" || tier === "intermediate" || tier === "advanced") {
    return tier;
  }
  return "beginner";
}

function extractApiError(error) {
  const data = error?.response?.data;
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return String(data.detail);
  const source = data.errors && typeof data.errors === "object" ? data.errors : data;
  return Object.entries(source)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`)
    .join(" ");
}

function tagsFromInput(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function LessonForm({
  selectedSource,
  lessonTitle,
  setLessonTitle,
  lessonSource,
  setLessonSource,
  lessonUrl,
  setLessonUrl,
  lessonContent,
  setLessonContent,
  lessonMinutes,
  setLessonMinutes,
  lessonTags,
  setLessonTags,
  lessonTopicTag,
  setLessonTopicTag,
  lessonObjective,
  setLessonObjective,
  lessonFormError,
  isSaving,
  onSubmit,
}) {
  return (
    <Card variant="elevated" padding="md">
      <PageHeader
        title="Add Lesson"
        subtitle="Choose a source, add metadata, and keep the sequence ready for students."
      />

      <form className="mt-5 space-y-4" onSubmit={onSubmit}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Lesson title
            </label>
            <input
              value={lessonTitle}
              onChange={(event) => setLessonTitle(event.target.value)}
              className="lc-input"
              required
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Source type
            </label>
            <select value={lessonSource} onChange={(event) => setLessonSource(event.target.value)} className="lc-input">
              {LESSON_SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted dark:text-reef/70">{selectedSource.help}</p>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              {selectedSource.urlLabel}
            </label>
            <input
              value={lessonUrl}
              onChange={(event) => setLessonUrl(event.target.value)}
              placeholder={selectedSource.placeholder}
              required={selectedSource.requiresUrl}
              className="lc-input"
            />
          </div>

          {lessonSource === "internal" ? (
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
                Lesson content
              </label>
              <textarea
                value={lessonContent}
                onChange={(event) => setLessonContent(event.target.value)}
                rows={5}
                placeholder="Write the lesson text students will read on the platform."
                className="lc-input"
              />
            </div>
          ) : null}

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Estimated minutes
            </label>
            <input
              type="number"
              min={5}
              max={600}
              value={lessonMinutes}
              onChange={(event) => setLessonMinutes(Number(event.target.value))}
              className="lc-input"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Topic tag
            </label>
            <input value={lessonTopicTag} onChange={(event) => setLessonTopicTag(event.target.value)} className="lc-input" />
          </div>

          <div className="md:col-span-2">
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Tags
            </label>
            <input
              value={lessonTags}
              onChange={(event) => setLessonTags(event.target.value)}
              placeholder="functions, loops, arrays"
              className="lc-input"
            />
          </div>

          <div className="md:col-span-2">
            <label className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
              Learning objective
            </label>
            <textarea
              value={lessonObjective}
              onChange={(event) => setLessonObjective(event.target.value)}
              rows={2}
              className="lc-input"
            />
          </div>
        </div>

        {lessonFormError ? <p className="text-sm font-medium text-red-600">{lessonFormError}</p> : null}
        <Button type="submit" loading={isSaving}>
          Add lesson
        </Button>
      </form>
    </Card>
  );
}

function LessonList({ courseId, lessons, loading, deletingId, onDelete }) {
  if (loading) {
    return <LoadingState label="Loading lessons..." rows={2} />;
  }

  if (!lessons.length) {
    return (
      <Card variant="subtle">
        <p className="text-sm text-muted dark:text-reef/75">No lessons yet. Add the first lesson above.</p>
      </Card>
    );
  }

  return (
    <ol className="space-y-3">
      {lessons.map((lesson, index) => (
        <li
          key={lesson.id}
          className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#172433]/85"
        >
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-reef text-xs font-bold text-ocean-800 dark:bg-ocean-600/25 dark:text-reef">
                  {index + 1}
                </span>
                <h3 className="font-semibold text-ink dark:text-sand">{lesson.title}</h3>
              </div>
              <p className="mt-2 text-sm text-muted dark:text-reef/75">
                {formatSourceTypeLabel(lesson.source_type)} | {lesson.difficulty} | {lesson.estimated_minutes} min
              </p>
              <div className="mt-3">
                <LessonAIStatusPanel courseId={courseId} lesson={lesson} />
              </div>
            </div>

            <Button
              variant="danger"
              size="sm"
              loading={deletingId === lesson.id}
              onClick={() => onDelete(lesson)}
              className="w-fit"
            >
              Delete
            </Button>
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function CourseSetup() {
  const { courseId: courseIdParam } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew =
    location.pathname === "/admin/courses/new" ||
    location.pathname.endsWith("/courses/new") ||
    courseIdParam === "new";
  const courseIdNum = !isNew && courseIdParam ? Number(courseIdParam) : null;
  const justCreated = Boolean(location.state?.courseCreated);

  const [title, setTitle] = useState("");
  const [level, setLevel] = useState(LEVEL_OPTIONS[0].value);
  const [formError, setFormError] = useState("");
  const [lessonTitle, setLessonTitle] = useState("");
  const [lessonSource, setLessonSource] = useState("youtube");
  const selectedSource = getLessonSourceOption(lessonSource);
  const [lessonUrl, setLessonUrl] = useState("");
  const [lessonContent, setLessonContent] = useState("");
  const [lessonMinutes, setLessonMinutes] = useState(20);
  const [lessonTags, setLessonTags] = useState("");
  const [lessonObjective, setLessonObjective] = useState("");
  const [lessonTopicTag, setLessonTopicTag] = useState("");
  const [lessonFormError, setLessonFormError] = useState("");
  const [deletingLessonId, setDeletingLessonId] = useState(null);

  const { data: courses = [] } = useQuery({
    queryKey: ["admin-courses"],
    queryFn: getAdminCourses,
    enabled: isNew,
  });

  const { data: selectedCourseDetail, isLoading: courseLoading } = useQuery({
    queryKey: ["admin-course-detail", courseIdNum],
    queryFn: () => getAdminCourse(courseIdNum),
    enabled: Number.isFinite(courseIdNum) && courseIdNum > 0,
  });

  const { data: lessons = [], isLoading: lessonsLoading } = useQuery({
    queryKey: ["admin-lessons", courseIdNum],
    queryFn: () => getAdminLessons(courseIdNum),
    enabled: Boolean(courseIdNum),
  });

  const createCourseMutation = useMutation({
    mutationFn: createAdminCourse,
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
      setFormError("");
      navigate(`/admin/courses/${created.id}/setup`, { state: { courseCreated: true } });
    },
    onError: (error) => {
      setFormError(extractApiError(error) || "Could not create course. Check your inputs and try again.");
    },
  });

  const bootstrapMutation = useMutation({
    mutationFn: bootstrapCourseCatalog,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      navigate("/admin/courses");
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => updateAdminCourse(courseIdNum, { status: "published" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-course-detail", courseIdNum] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
  });

  const createLessonMutation = useMutation({
    mutationFn: ({ courseId, payload }) => createAdminLesson(courseId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseIdNum] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      setLessonFormError("");
      setLessonTitle("");
      setLessonUrl("");
      setLessonContent("");
      setLessonTags("");
      setLessonObjective("");
      setLessonTopicTag("");
    },
    onError: (error) => {
      setLessonFormError(extractApiError(error) || "Could not create lesson. Check the required fields.");
    },
  });

  const deleteLessonMutation = useMutation({
    mutationFn: ({ courseId, lessonId }) => deleteAdminLesson(courseId, lessonId),
    onMutate: ({ lessonId }) => setDeletingLessonId(lessonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseIdNum] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
    onSettled: () => setDeletingLessonId(null),
  });

  const handleCreateCourse = (event) => {
    event.preventDefault();
    setFormError("");
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setFormError("Course topic is required.");
      return;
    }
    createCourseMutation.mutate({ title: trimmedTitle, level });
  };

  const lessonRows = useMemo(() => {
    const rows = Array.isArray(lessons) ? lessons : lessons?.results || [];
    return [...rows].sort((a, b) => {
      const orderDiff = (Number(a.order) || 0) - (Number(b.order) || 0);
      if (orderDiff !== 0) return orderDiff;
      return (a.id || 0) - (b.id || 0);
    });
  }, [lessons]);

  const handleLessonSubmit = (event) => {
    event.preventDefault();
    setLessonFormError("");
    if (!courseIdNum) {
      setLessonFormError("Select a course first.");
      return;
    }
    const trimmedTitle = lessonTitle.trim();
    if (!trimmedTitle) {
      setLessonFormError("Lesson title is required.");
      return;
    }
    if (selectedSource.requiresUrl && !lessonUrl.trim()) {
      setLessonFormError(`${selectedSource.urlLabel} is required for this source type.`);
      return;
    }
    if (!selectedSource.requiresUrl && !lessonUrl.trim() && !lessonContent.trim()) {
      setLessonFormError("Add lesson content or an optional reference URL.");
      return;
    }

    createLessonMutation.mutate({
      courseId: courseIdNum,
      payload: {
        title: trimmedTitle,
        source_type: lessonSource,
        resource_url: lessonUrl.trim(),
        content: lessonContent,
        difficulty: normalizeCourseLevel(selectedCourseDetail?.level ?? "beginner"),
        estimated_minutes: Number(lessonMinutes) || 15,
        tags: tagsFromInput(lessonTags),
        learning_objective: lessonObjective.trim(),
        topic_tag: lessonTopicTag.trim(),
        is_auto_generated: false,
      },
    });
  };

  if (isNew) {
    const existingCourses = Array.isArray(courses) ? courses : courses?.results || [];
    return (
      <div className="space-y-5 p-4 md:p-6">
        <Link to="/admin/courses" className="text-sm font-semibold text-ocean-700 hover:underline">
          Back to courses
        </Link>

        <Card as="form" onSubmit={handleCreateCourse} variant="elevated" className="max-w-2xl">
          <PageHeader
            title="Create Course"
            subtitle="Set the course title and level first. Lessons are added after the course exists."
          />

          <div className="mt-6 space-y-4">
            <div>
              <label htmlFor="course-topic" className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
                Course topic
              </label>
              <input
                id="course-topic"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Intro to Data Structures"
                className="lc-input"
                required
              />
            </div>

            <div>
              <label htmlFor="level" className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef">
                Level
              </label>
              <select id="level" value={level} onChange={(event) => setLevel(event.target.value)} className="lc-input">
                {LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {formError ? <p className="mt-4 text-sm font-medium text-red-600">{formError}</p> : null}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button type="submit" loading={createCourseMutation.isPending}>
              Create course
            </Button>
            <Button variant="ghost" loading={bootstrapMutation.isPending} onClick={() => bootstrapMutation.mutate()}>
              Load sample catalog
            </Button>
          </div>
        </Card>

        {existingCourses.length > 0 ? (
          <p className="text-sm text-muted">
            {existingCourses.length} existing course(s).{" "}
            <Link to="/admin/courses" className="font-semibold text-ocean-700 underline">
              View all
            </Link>
          </p>
        ) : null}
      </div>
    );
  }

  if (!courseIdNum) {
    return (
      <div className="p-4 md:p-6">
        <EmptyState title="Course not found" message="Pick a course from the list to manage lessons." />
      </div>
    );
  }

  if (courseLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading course..." />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 p-4 md:p-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="space-y-5">
        {justCreated ? (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100">
            Course created. Add lessons below to build the learning path.
          </p>
        ) : null}

        <Card variant="elevated">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <Link to="/admin/courses" className="text-sm font-semibold text-ocean-700 hover:underline dark:text-reef">
                Courses
              </Link>
              <h1 className="mt-2 text-2xl font-bold text-ink dark:text-sand">{selectedCourseDetail?.title}</h1>
              <div className="mt-3 flex flex-wrap gap-2">
                <CourseLevelBadge level={selectedCourseDetail?.level} />
                <CourseStatusPill status={selectedCourseDetail?.status} />
              </div>
            </div>

            {selectedCourseDetail?.status !== "published" ? (
              <Button loading={publishMutation.isPending} onClick={() => publishMutation.mutate()}>
                Publish course
              </Button>
            ) : null}
          </div>

          <div className="mt-5 grid gap-4 border-t border-line/70 pt-4 sm:grid-cols-3 dark:border-white/10">
            <CourseMetric label="Lessons" value={selectedCourseDetail?.lesson_count ?? lessonRows.length} />
            <CourseMetric label="Status" value={selectedCourseDetail?.status ?? "draft"} />
            <CourseMetric label="Level" value={selectedCourseDetail?.level ?? "beginner"} />
          </div>
        </Card>

        <LessonForm
          selectedSource={selectedSource}
          lessonTitle={lessonTitle}
          setLessonTitle={setLessonTitle}
          lessonSource={lessonSource}
          setLessonSource={setLessonSource}
          lessonUrl={lessonUrl}
          setLessonUrl={setLessonUrl}
          lessonContent={lessonContent}
          setLessonContent={setLessonContent}
          lessonMinutes={lessonMinutes}
          setLessonMinutes={setLessonMinutes}
          lessonTags={lessonTags}
          setLessonTags={setLessonTags}
          lessonTopicTag={lessonTopicTag}
          setLessonTopicTag={setLessonTopicTag}
          lessonObjective={lessonObjective}
          setLessonObjective={setLessonObjective}
          lessonFormError={lessonFormError}
          isSaving={createLessonMutation.isPending}
          onSubmit={handleLessonSubmit}
        />

        <section className="space-y-3">
          <SectionHeader title="Lessons" subtitle="Review lesson order and generation status." />
          <LessonList
            courseId={courseIdNum}
            lessons={lessonRows}
            loading={lessonsLoading}
            deletingId={deletingLessonId}
            onDelete={(lesson) => {
              if (window.confirm(`Delete "${lesson.title}"?`)) {
                deleteLessonMutation.mutate({ courseId: courseIdNum, lessonId: lesson.id });
              }
            }}
          />
        </section>
      </section>

      <aside className="space-y-4">
        <PipelineStatus courseId={courseIdNum} />
        <Card variant="subtle" padding="md">
          <p className="font-semibold text-ink dark:text-sand">Approval workflow</p>
          <p className="mt-2 text-sm text-muted dark:text-reef/75">
            Generate or preview quiz questions from a lesson, then approve them before students can take the quiz.
          </p>
        </Card>
      </aside>
    </div>
  );
}
