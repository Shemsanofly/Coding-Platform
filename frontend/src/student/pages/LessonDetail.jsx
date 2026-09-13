import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  downloadLessonNotes,
  getLessonNotes,
  getStudentLesson,
  postLessonProgress,
} from "@/api/studentLearning";
import { getLearningPath } from "@/api/studentDashboard";
import LessonYouTubeEmbed, { extractYoutubeVideoId } from "@/student/components/LessonYouTubeEmbed";
import PdfNotesReader from "@/student/components/PdfNotesReader";
import ProgressBar from "@/student/components/ProgressBar";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

export default function LessonDetail() {
  const { lessonId } = useParams();
  const navigate = useNavigate();
  const id = Number(lessonId);
  const queryClient = useQueryClient();
  const maxVideoPctRef = useRef(0);
  const maxPdfScrollRef = useRef(0);
  const visibilityRef = useRef(typeof document !== "undefined" ? !document.hidden : true);
  const [contentTab, setContentTab] = useState("video");

  const { data: learningPath } = useQuery({
    queryKey: ["learning-path"],
    queryFn: () => getLearningPath(),
    enabled: Number.isFinite(id),
  });

  const {
    data: lesson,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["student-lesson", id],
    queryFn: () => getStudentLesson(id),
    enabled: Number.isFinite(id),
    retry: false,
    refetchInterval: (query) => {
      const row = query.state.data;
      if (!row) return false;
      const ai = row.ai_processing_status;
      const quiz = row.quiz_generation_status;
      const active =
        ai === "pending" || ai === "processing" || quiz === "pending" || quiz === "processing";
      return active ? 4000 : false;
    },
  });

  const hasPdfNotes = Boolean(lesson?.has_pdf_notes);

  const { data: lessonNotes } = useQuery({
    queryKey: ["lesson-notes", id],
    queryFn: () => getLessonNotes(id),
    enabled: Number.isFinite(id) && hasPdfNotes && contentTab === "notes",
    retry: false,
  });

  useEffect(() => {
    maxVideoPctRef.current = 0;
    maxPdfScrollRef.current = 0;
  }, [lessonId]);

  useEffect(() => {
    if (!hasPdfNotes && contentTab === "notes") {
      setContentTab("video");
    }
  }, [hasPdfNotes, contentTab]);

  const onYoutubeWatchPct = useCallback((pct) => {
    maxVideoPctRef.current = Math.max(maxVideoPctRef.current, pct);
  }, []);

  const progressMutation = useMutation({
    mutationFn: (payload) => postLessonProgress(id, payload),
    onError: () => {
      toast.error("Could not sync study activity.", { id: "lp-err" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student-lesson", id] });
    },
  });

  const downloadNotesMutation = useMutation({
    mutationFn: () => downloadLessonNotes(id),
    onSuccess: (response) => {
      triggerBlobDownload(response, `${lesson?.title || "lesson"}_notes.pdf`);
      toast.success("PDF notes downloaded.", { id: "notes-dl-ok" });
    },
    onError: () => {
      toast.error("Could not download PDF notes.", { id: "notes-dl-err" });
    },
  });

  const flushProgress = useCallback(
    (deltaSeconds) => {
      if (!Number.isFinite(id) || !lesson?.id) {
        return;
      }
      progressMutation.mutate({
        delta_seconds: deltaSeconds,
        scroll_depth_pct: contentTab === "notes" ? maxPdfScrollRef.current : 0,
        video_watch_pct: contentTab === "video" ? maxVideoPctRef.current : undefined,
      });
    },
    [id, lesson?.id, progressMutation, contentTab],
  );

  const handlePdfScrollDepth = useCallback((pct) => {
    maxPdfScrollRef.current = Math.max(maxPdfScrollRef.current, pct);
  }, []);

  const handlePdfOpened = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["lesson-notes", id] });
    queryClient.invalidateQueries({ queryKey: ["student-lesson", id] });
  }, [queryClient, id]);

  useEffect(() => {
    const onVis = () => {
      visibilityRef.current = !document.hidden;
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  useEffect(() => {
    if (!lesson?.id) {
      return undefined;
    }
    const tickMs = 12000;
    const handle = window.setInterval(() => {
      if (!visibilityRef.current) {
        return;
      }
      flushProgress(Math.round(tickMs / 1000));
    }, tickMs);
    return () => window.clearInterval(handle);
  }, [lesson?.id, contentTab, flushProgress]);

  if (!Number.isFinite(id)) {
    return (
      <div className="p-6 text-sm text-red-600 dark:text-red-200">
        Invalid lesson id.{" "}
        <Link className="font-medium text-ocean-800 underline dark:text-reef" to="/">
          Dashboard
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return <p className="p-6 text-sm text-muted dark:text-muted">Loading lesson…</p>;
  }

  if (isError) {
    const code = error?.response?.status;
    const detail = error?.response?.data?.detail;
    return (
      <div className="space-y-3 p-6 text-sm text-red-600 dark:text-red-200">
        <p>{typeof detail === "string" ? detail : "Unable to open this lesson."}</p>
        {code === 403 ? (
          <p className="text-ocean-800 dark:text-muted">
            <Link className="font-medium text-ocean-800 underline dark:text-reef" to="/catalog">
              Enroll from the catalog
            </Link>{" "}
            or finish earlier quizzes to unlock the next step.
          </p>
        ) : null}
        <Link to="/" className="font-medium text-ocean-800 underline dark:text-reef">
          Dashboard
        </Link>
      </div>
    );
  }

  if (!lesson) {
    return null;
  }

  const ytEmbed = (lesson.youtube_embed_url || "").trim();
  const ytVideoId = extractYoutubeVideoId(ytEmbed);
  const resourceUrl = (lesson.resource_url || "").trim();
  const sourceType = lesson.source_type || "youtube";
  const isYoutubeLesson = sourceType === "youtube";
  const summaryText = (lesson.summary || lesson.content || "").trim();
  const learningObjectives = Array.isArray(lesson.learning_objectives)
    ? lesson.learning_objectives
    : [];
  const keyConcepts = Array.isArray(lesson.key_concepts) ? lesson.key_concepts : [];

  const engaged = lesson.seconds_engaged ?? 0;
  const requiredSec = lesson.engagement_required_seconds ?? 0;
  const timePct = requiredSec ? Math.min(100, Math.round((engaged / requiredSec) * 100)) : 0;

  const quizStatus = lesson.quiz_generation_status || "pending";
  const aiStatus = lesson.ai_processing_status || "pending";
  const quizProcessing = quizStatus === "pending" || quizStatus === "processing";
  const quizFailed = quizStatus === "failed";
  const studyComplete = Boolean(lesson.lesson_officially_completed || lesson.engagement_satisfied);
  const quizAvailable = Boolean(lesson.quiz_available);
  const quizReady = quizAvailable && studyComplete;
  const nextPathStep = (learningPath?.learning_path ?? []).find((s) => s.status === "next");
  const showNextCta = nextPathStep && nextPathStep.lesson_id !== lesson.id;
  const aiSummary = lessonNotes?.ai_summary || {};
  const notesActivity = lessonNotes?.activity || {};

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <header className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:backdrop-blur-xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-ocean-800 dark:text-reef">
          {lesson.course_title}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink dark:text-sand">{lesson.title}</h1>
        <div className="mt-4">
          <ProgressBar value={timePct} label="Engagement progress" size="sm" />
        </div>
        {learningObjectives.length > 0 ? (
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
              Learning objectives
            </p>
            <ul className="mt-1 list-inside list-disc text-sm text-muted dark:text-muted">
              {learningObjectives.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : lesson.learning_objective ? (
          <p className="mt-2 text-sm text-muted dark:text-muted">
            Objective: {lesson.learning_objective}
          </p>
        ) : null}
      </header>

      <section className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl md:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold text-ink dark:text-sand">Quiz readiness</p>
          {quizReady ? (
            <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-500/25 dark:text-emerald-100">
              Ready
            </span>
          ) : quizProcessing ? (
            <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800 dark:bg-blue-500/25 dark:text-blue-100">
              Generating
            </span>
          ) : quizFailed ? (
            <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-800 dark:bg-red-500/25 dark:text-red-100">
              Failed
            </span>
          ) : (
            <span className="rounded-full bg-sand px-2.5 py-1 text-xs font-semibold text-ocean-800 dark:bg-ocean-950/60 dark:text-sand">
              Pending
            </span>
          )}
        </div>
        <div className="mb-4 grid gap-3 text-xs text-muted sm:grid-cols-3 dark:text-muted">
          <div className="rounded-xl bg-sand px-3 py-2 dark:bg-black/20">
            <p className="font-semibold text-ocean-800 dark:text-reef">Engaged time</p>
            <p className="mt-1 text-ink dark:text-sand">
              {Math.round(engaged / 60)} / {Math.max(1, Math.round(requiredSec / 60))} min goal
            </p>
          </div>
          <div className="rounded-xl bg-sand px-3 py-2 dark:bg-black/20">
            <p className="font-semibold text-ocean-800 dark:text-reef">
              {isYoutubeLesson ? "Video watched" : "Time on lesson"}
            </p>
            <p className="mt-1 text-ink dark:text-sand">{lesson.video_watch_pct ?? 0}%</p>
          </div>
          <div className="rounded-xl bg-sand px-3 py-2 dark:bg-black/20">
            <p className="font-semibold text-ocean-800 dark:text-reef">Study status</p>
            <p className="mt-1 text-ink dark:text-sand">
              {lesson.lesson_officially_completed
                ? "Study done - take the quiz for certification"
                : "Reach 100% study progress to unlock the quiz"}
            </p>
          </div>
        </div>

        <p className="mb-4 text-sm text-muted dark:text-muted">
          {isYoutubeLesson
            ? "Watch the YouTube lesson below or read AI-generated PDF study notes from the transcript. At 100% study progress, the quiz unlocks. Pass the required quiz to earn your certificate."
            : "Open the lesson resource below and spend time engaging with the material. At 100% study progress, the quiz unlocks. Pass the required quiz to earn your certificate."}
        </p>

        <div className="mb-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setContentTab("video")}
            className={`inline-flex min-h-9 items-center rounded-xl px-4 py-2 text-sm font-semibold transition ${
              contentTab === "video"
                ? "bg-ocean-600 text-white"
                : "border border-line text-ocean-800 hover:bg-sand dark:border-line/40 dark:text-sand dark:hover:bg-ocean-900/50"
            }`}
          >
            {isYoutubeLesson ? "Watch Video" : "Lesson resource"}
          </button>
          {hasPdfNotes ? (
            <button
              type="button"
              onClick={() => setContentTab("notes")}
              className={`inline-flex min-h-9 items-center rounded-xl px-4 py-2 text-sm font-semibold transition ${
                contentTab === "notes"
                  ? "bg-ocean-600 text-white"
                  : "border border-line text-ocean-800 hover:bg-sand dark:border-line/40 dark:text-sand dark:hover:bg-ocean-900/50"
              }`}
            >
              Read PDF Notes
            </button>
          ) : null}
        </div>

        {contentTab === "video" ? (
          <div className="min-h-[320px] overflow-hidden rounded-xl border border-line bg-sand dark:border-line/20 dark:bg-black/30">
            {isYoutubeLesson && ytEmbed && ytVideoId ? (
              <LessonYouTubeEmbed
                key={`yt-${lesson.id}`}
                videoId={ytVideoId}
                title={lesson.title}
                onWatchPercent={onYoutubeWatchPct}
              />
            ) : isYoutubeLesson && ytEmbed ? (
              <iframe
                title={lesson.title}
                src={ytEmbed}
                className="aspect-video h-full min-h-[320px] w-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
              />
            ) : sourceType === "pdf" && resourceUrl ? (
              <div className="space-y-4 p-6">
                <p className="text-sm text-muted dark:text-muted">Read the PDF lesson material.</p>
                <a
                  href={resourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-10 items-center rounded-xl bg-ocean-600 px-4 text-sm font-semibold text-white hover:bg-ocean-700"
                >
                  Open PDF
                </a>
                <iframe
                  title={lesson.title}
                  src={resourceUrl}
                  className="h-[480px] w-full rounded-lg border border-line bg-white"
                />
              </div>
            ) : sourceType === "internal" ? (
              <div className="space-y-4 p-6">
                {summaryText ? (
                  <div className="prose prose-sm max-w-none whitespace-pre-wrap text-ink dark:text-sand">
                    {summaryText}
                  </div>
                ) : (
                  <p className="text-sm text-muted dark:text-muted">
                    Lesson content is being prepared.
                  </p>
                )}
                {resourceUrl ? (
                  <a
                    href={resourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex text-sm font-semibold text-ocean-800 underline dark:text-reef"
                  >
                    Open reference link
                  </a>
                ) : null}
              </div>
            ) : resourceUrl ? (
              <div className="space-y-4 p-6">
                <p className="text-sm text-muted dark:text-muted">
                  Open the {sourceType === "webpage" ? "web page" : "external resource"} for this
                  lesson.
                </p>
                <a
                  href={resourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-10 items-center rounded-xl bg-ocean-600 px-4 text-sm font-semibold text-white hover:bg-ocean-700"
                >
                  Open resource
                </a>
                {sourceType === "webpage" ? (
                  <iframe
                    title={lesson.title}
                    src={resourceUrl}
                    className="h-[480px] w-full rounded-lg border border-line bg-white"
                  />
                ) : null}
              </div>
            ) : (
              <p className="p-6 text-sm text-muted dark:text-muted">
                No resource configured for this lesson yet. Check back later.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4 rounded-xl border border-line bg-cream p-4 dark:border-line/20 dark:bg-black/20">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-ink dark:text-sand">PDF study notes</p>
                <p className="mt-1 text-xs text-muted dark:text-reef/70">
                  Read inside the platform — no external redirect required.
                </p>
              </div>
              <button
                type="button"
                disabled={downloadNotesMutation.isPending}
                onClick={() => downloadNotesMutation.mutate()}
                className="inline-flex min-h-9 items-center rounded-xl border border-ocean-200 bg-white px-4 py-2 text-sm font-semibold text-ocean-800 hover:bg-reef/40 disabled:opacity-50 dark:border-ocean-600/40 dark:bg-transparent dark:text-reef dark:hover:bg-ocean-600/10"
              >
                {downloadNotesMutation.isPending ? "Downloading…" : "Download PDF"}
              </button>
            </div>
            <p className="text-xs text-muted dark:text-reef/70">
              Notes are generated from YouTube transcript text only (not video image analysis).
            </p>
            <PdfNotesReader
              lessonId={lesson.id}
              lessonTitle={lesson.title}
              onOpened={handlePdfOpened}
              onScrollDepth={handlePdfScrollDepth}
            />
            {notesActivity.notes_viewed_at || notesActivity.notes_downloaded_at ? (
              <p className="text-xs text-muted dark:text-reef/70">
                {notesActivity.notes_viewed_at ? "Notes viewed in platform. " : ""}
                {notesActivity.notes_downloaded_at
                  ? "Download recorded for your learning analytics."
                  : ""}
              </p>
            ) : null}
            {Array.isArray(aiSummary.key_concepts) && aiSummary.key_concepts.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
                  Key concepts from notes
                </p>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {aiSummary.key_concepts.map((concept) => (
                    <li
                      key={concept}
                      className="rounded-full bg-reef/50 px-3 py-1 text-xs font-medium text-ocean-900 dark:bg-ocean-600/20 dark:text-reef"
                    >
                      {concept}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}

        {contentTab === "video" && summaryText ? (
          <article className="mt-4 max-h-[40vh] overflow-y-auto whitespace-pre-wrap rounded-xl border border-line bg-cream p-4 text-sm leading-relaxed text-ink dark:border-line/20 dark:bg-black/20 dark:text-sand">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
              Lesson summary
            </p>
            {summaryText}
          </article>
        ) : null}
        {contentTab === "video" && keyConcepts.length > 0 ? (
          <div className="mt-4 rounded-xl border border-line bg-white p-4 dark:border-line/20 dark:bg-black/20">
            <p className="text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
              Key concepts
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {keyConcepts.map((concept) => (
                <li
                  key={concept}
                  className="rounded-full bg-reef/50 px-3 py-1 text-xs font-medium text-ocean-900 dark:bg-ocean-600/20 dark:text-reef"
                >
                  {concept}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      {quizProcessing ? (
        <p className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-400/40 dark:bg-blue-500/10 dark:text-blue-100">
          Your quiz is being prepared — check back in a moment.
        </p>
      ) : null}
      {quizFailed ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-100">
          Quiz generation failed.{" "}
          {lesson.quiz_generation_error || "The quiz is not ready yet — try again later."}
        </p>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        {quizReady ? (
          <Link
            to={`/lessons/${lesson.id}/quiz`}
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
          >
            Take quiz
          </Link>
        ) : quizAvailable && !studyComplete ? (
          <span className="inline-flex min-h-[44px] items-center rounded-xl border border-line px-4 py-2 text-sm text-muted dark:border-line/40 dark:text-reef/70">
            Finish 100% study to unlock quiz
          </span>
        ) : (
          <span className="inline-flex min-h-[44px] items-center rounded-xl border border-line px-4 py-2 text-sm text-muted dark:border-line/40 dark:text-reef/70">
            Quiz not ready
          </span>
        )}
        {showNextCta ? (
          <button
            type="button"
            onClick={() => navigate(`/lessons/${nextPathStep.lesson_id}`)}
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-emerald-400/50 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-900 dark:border-emerald-400/40 dark:bg-emerald-500/15 dark:text-emerald-100"
          >
            Next: {nextPathStep.lesson_title}
          </button>
        ) : lesson.lesson_officially_completed && nextPathStep ? (
          <button
            type="button"
            onClick={() => navigate(`/lessons/${nextPathStep.lesson_id}`)}
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Continue to next lesson
          </button>
        ) : null}
        <Link
          to={`/courses/${lesson.course_id}`}
          className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-sand dark:border-line/40 dark:text-sand dark:hover:bg-white/20"
        >
          Back to course
        </Link>
      </div>
    </div>
  );
}
