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
import CourseStatusBadge from "@/admin/components/CourseStatusBadge";
import EmptyState from "@/admin/components/EmptyState";
import LessonAIStatusPanel from "@/admin/components/LessonAIStatusPanel";
import LoadingState from "@/admin/components/LoadingState";
import PipelineStatus from "@/admin/components/PipelineStatus";

const LEVEL_OPTIONS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const LESSON_SOURCE_OPTIONS = [{ value: "youtube", label: "YouTube" }];

function normalizeCourseLevel(raw) {
  const tier = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (tier === "beginner" || tier === "intermediate" || tier === "advanced") {
    return tier;
  }
  return "beginner";
}

function extractApiError(error) {
  const data = error?.response?.data;
  if (!data) {
    return "";
  }
  if (typeof data === "string") {
    return data;
  }
  if (data.detail) {
    return String(data.detail);
  }
  const parts = Object.entries(data).map(([key, value]) => {
    if (Array.isArray(value)) {
      return `${key}: ${value.join(" ")}`;
    }
    return `${key}: ${value}`;
  });
  return parts.join(" ");
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
  const [lessonUrl, setLessonUrl] = useState("");
  const [lessonContent, setLessonContent] = useState("");
  const [lessonMinutes, setLessonMinutes] = useState(20);
  const [lessonTags, setLessonTags] = useState("");
  const [lessonObjective, setLessonObjective] = useState("");
  const [lessonTopicTag, setLessonTopicTag] = useState("");
  const [lessonFormError, setLessonFormError] = useState("");

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
      setLessonFormError(
        extractApiError(error) || "Could not create lesson. Check required fields for the selected source type."
      );
    },
  });

  const deleteLessonMutation = useMutation({
    mutationFn: ({ courseId, lessonId }) => deleteAdminLesson(courseId, lessonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseIdNum] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
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
      if (orderDiff !== 0) {
        return orderDiff;
      }
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
    if (!lessonUrl.trim()) {
      setLessonFormError("A YouTube URL is required for each lesson.");
      return;
    }
    const tags = lessonTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    createLessonMutation.mutate({
      courseId: courseIdNum,
      payload: {
        title: trimmedTitle,
        source_type: lessonSource,
        resource_url: lessonUrl.trim(),
        content: lessonContent,
        difficulty: normalizeCourseLevel(selectedCourseDetail?.level ?? "beginner"),
        estimated_minutes: Number(lessonMinutes) || 15,
        tags,
        learning_objective: lessonObjective.trim(),
        topic_tag: lessonTopicTag.trim(),
        is_auto_generated: false,
      },
    });
  };

  if (isNew) {
    const existingCourses = Array.isArray(courses) ? courses : courses?.results || [];
    return (
      <div className="space-y-6 p-4 md:p-6">
        <Link to="/admin/courses" className="text-sm font-medium text-emerald-700 hover:underline">
          ← Back to courses
        </Link>
        <form
          onSubmit={handleCreateCourse}
          className="max-w-xl rounded-2xl border border-emerald-100 bg-white/90 p-5 shadow-lg backdrop-blur"
        >
          <h1 className="mb-5 text-xl font-semibold text-gray-900">Create new course</h1>
          <div className="space-y-4">
            <div>
              <label htmlFor="course-topic" className="mb-1 block text-sm font-medium text-gray-700">
                Course topic
              </label>
              <input
                id="course-topic"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Intro to Data Structures"
                className="w-full rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
                required
              />
            </div>
            <div>
              <label htmlFor="level" className="mb-1 block text-sm font-medium text-gray-700">
                Level
              </label>
              <select
                id="level"
                value={level}
                onChange={(event) => setLevel(event.target.value)}
                className="w-full rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
              >
                {LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {formError ? <p className="mt-4 text-sm text-red-600">{formError}</p> : null}
          <button
            type="submit"
            disabled={createCourseMutation.isPending}
            className="mt-6 inline-flex min-h-10 items-center rounded-xl bg-lc-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {createCourseMutation.isPending ? "Creating…" : "Create course"}
          </button>
          <button
            type="button"
            onClick={() => bootstrapMutation.mutate()}
            disabled={bootstrapMutation.isPending}
            className="ml-3 mt-6 inline-flex min-h-10 items-center rounded-xl border border-line px-4 py-2 text-sm font-semibold text-ocean-800"
          >
            Load sample catalog
          </button>
        </form>
        {existingCourses.length > 0 ? (
          <p className="text-sm text-muted">
            {existingCourses.length} existing course(s).{" "}
            <Link to="/admin/courses" className="font-semibold text-emerald-700 underline">
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
        <LoadingState label="Loading course…" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-4 md:p-6 xl:grid-cols-3">
      <section className="space-y-6 xl:col-span-2">
        {justCreated ? (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            Course created successfully. Add YouTube lessons below to start AI quiz generation.
          </p>
        ) : null}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link to="/admin/courses" className="text-sm font-medium text-emerald-700 hover:underline">
              ← Courses
            </Link>
            <h1 className="mt-2 text-xl font-semibold text-gray-900">{selectedCourseDetail?.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <CourseStatusBadge status={selectedCourseDetail?.status} />
              <span className="text-sm text-muted">{selectedCourseDetail?.lesson_count ?? 0} lessons</span>
            </div>
          </div>
          {selectedCourseDetail?.status !== "published" ? (
            <button
              type="button"
              disabled={publishMutation.isPending}
              onClick={() => publishMutation.mutate()}
              className="inline-flex min-h-10 items-center rounded-xl bg-ocean-600 px-4 text-sm font-semibold text-white hover:bg-ocean-700 disabled:opacity-50"
            >
              Publish course
            </button>
          ) : null}
        </div>

        <section className="rounded-2xl border border-line bg-white/95 p-5 shadow-lg backdrop-blur">
          <h2 className="text-lg font-semibold text-gray-900">Add lesson</h2>
          <p className="mt-1 text-sm text-gray-600">YouTube URL, objectives, and tags trigger AI quiz generation.</p>

          <form className="mt-6 space-y-4" onSubmit={handleLessonSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="mb-1 block text-sm font-medium text-gray-700">Lesson title</label>
                <input
                  value={lessonTitle}
                  onChange={(e) => setLessonTitle(e.target.value)}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Source type</label>
                <select
                  value={lessonSource}
                  onChange={(e) => setLessonSource(e.target.value)}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                >
                  {LESSON_SOURCE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">YouTube URL</label>
                <input
                  value={lessonUrl}
                  onChange={(e) => setLessonUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  required
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Estimated minutes</label>
                <input
                  type="number"
                  min={5}
                  max={600}
                  value={lessonMinutes}
                  onChange={(e) => setLessonMinutes(Number(e.target.value))}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-sm font-medium text-gray-700">Tags (comma-separated)</label>
                <input
                  value={lessonTags}
                  onChange={(e) => setLessonTags(e.target.value)}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Topic tag</label>
                <input
                  value={lessonTopicTag}
                  onChange={(e) => setLessonTopicTag(e.target.value)}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-sm font-medium text-gray-700">Learning objective</label>
                <textarea
                  value={lessonObjective}
                  onChange={(e) => setLessonObjective(e.target.value)}
                  rows={2}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                />
              </div>
            </div>
            {lessonFormError ? <p className="text-sm text-red-600">{lessonFormError}</p> : null}
            <button
              type="submit"
              disabled={createLessonMutation.isPending}
              className="inline-flex min-h-10 items-center rounded-xl bg-lc-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {createLessonMutation.isPending ? "Saving…" : "Add lesson"}
            </button>
          </form>

          <div className="mt-8 border-t border-line pt-4">
            <h3 className="text-sm font-semibold text-gray-900">Lessons & AI status</h3>
            {lessonsLoading ? <LoadingState label="Loading lessons…" rows={2} /> : null}
            {!lessonsLoading && lessonRows.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No lessons yet. Add a YouTube lesson above.</p>
            ) : null}
            <ul className="mt-3 space-y-3">
              {lessonRows.map((row) => (
                <li
                  key={row.id}
                  className="rounded-lg border border-line/70 bg-cream px-3 py-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900">
                        Lesson {row.order ?? "—"}: {row.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {row.source_type} · {row.difficulty} · ~{row.estimated_minutes}m
                      </p>
                      <LessonAIStatusPanel courseId={courseIdNum} lesson={row} />
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (window.confirm("Delete this lesson?")) {
                          deleteLessonMutation.mutate({ courseId: courseIdNum, lessonId: row.id });
                        }
                      }}
                      className="shrink-0 text-xs font-semibold text-red-600 hover:text-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </section>

      <aside className="space-y-4">
        <PipelineStatus courseId={courseIdNum} />
        <section className="rounded-2xl border border-emerald-100 bg-white/90 p-4 shadow-lg backdrop-blur text-sm text-muted">
          <p className="font-semibold text-ink">Approval workflow</p>
          <p className="mt-2">
            Preview generated questions, then approve to publish. Students only see published questions in quizzes.
          </p>
        </section>
      </aside>
    </div>
  );
}
