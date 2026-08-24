import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  approveAdminLessonQuiz,
  generateAdminLessonNotes,
  generateAdminLessonQuiz,
  getAdminLessonProcessingStatus,
  regenerateAdminLessonQuiz,
} from "@/api/adminCourses";
import {
  handleGenerateResponse,
  handleRegenerateResponse,
  invalidateQuizPipelineQueries,
} from "@/admin/utils/regenerateQuizHandlers";
import { extractApiError } from "@/shared/utils/extractApiError";
import AIStatusBadge from "@/admin/components/AIStatusBadge";
import QuizPreviewModal from "@/admin/components/QuizPreviewModal";
import StatusBadge from "@/admin/components/StatusBadge";

export default function LessonAIStatusPanel({ courseId, lesson, onEdit }) {
  const queryClient = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const isYoutube = lesson?.source_type === "youtube";

  const { data: status } = useQuery({
    queryKey: ["admin-lesson-processing", courseId, lesson?.id],
    queryFn: () => getAdminLessonProcessingStatus(courseId, lesson.id),
    enabled: Boolean(courseId && lesson?.id && isYoutube),
    refetchInterval: (query) => {
      const ai = query.state.data?.ai_processing_status;
      const quiz = query.state.data?.quiz_generation_status;
      const active =
        ai === "pending" ||
        ai === "processing" ||
        quiz === "pending" ||
        quiz === "processing";
      return active ? 3000 : false;
    },
  });

  const merged = {
    source_type: lesson?.source_type,
    ai_processing_status: status?.ai_processing_status ?? lesson?.ai_processing_status,
    quiz_generation_status: status?.quiz_generation_status ?? lesson?.quiz_generation_status,
    transcript_status: status
      ? status.has_transcript
        ? "ready"
        : "pending"
      : lesson?.transcript_status,
    generated_question_count:
      status?.question_count ?? lesson?.generated_question_count ?? 0,
    published_question_count:
      status?.published_question_count ?? lesson?.published_question_count ?? 0,
    approval_status: status?.approval_status ?? lesson?.approval_status,
    generation_error: status?.generation_error || lesson?.generation_error,
    transcript_error: status?.last_error || lesson?.transcript_error,
  };

  const isManualMode = (status?.ai_generation_mode ?? "manual") === "manual";
  const showGenerateQuiz =
    isManualMode &&
    (merged.quiz_generation_status === "pending" || merged.quiz_generation_status === "failed");

  const generateMutation = useMutation({
    mutationFn: () => generateAdminLessonQuiz(courseId, lesson.id),
    onSuccess: (data) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      handleGenerateResponse(data);
    },
    onError: (error) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      toast.error(
        extractApiError(error, "Could not generate quiz.", {
          timeoutMessage:
            "Request timed out. Quiz generation can take up to two minutes. Try again or refresh status.",
        }),
        { id: "gen-quiz-err" }
      );
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateAdminLessonQuiz(courseId, lesson.id),
    onSuccess: (data) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      handleRegenerateResponse(data, { isManualMode });
    },
    onError: (error) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      toast.error(
        extractApiError(error, "Could not start quiz regeneration.", {
          timeoutMessage:
            "Request timed out. Quiz regeneration can take up to two minutes. Try again or refresh status.",
        }),
        {
          id: "regen-quiz-err",
        }
      );
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveAdminLessonQuiz(courseId, lesson.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lesson-processing", courseId, lesson.id] });
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseId] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
  });

  const generateNotesMutation = useMutation({
    mutationFn: () => generateAdminLessonNotes(lesson.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseId] });
      toast.success("PDF study notes generated successfully.", { id: "gen-notes-ok" });
    },
    onError: (error) => {
      const message = extractApiError(
        error,
        "Could not generate PDF notes. Transcript may be unavailable.",
        {
          timeoutMessage:
            "Request timed out. PDF notes can take a few minutes for long videos. Try again or refresh the lesson status.",
        }
      );
      toast.error(message, { id: "gen-notes-err" });
    },
  });

  if (!isYoutube) {
    return (
      <p className="text-xs text-muted">
        AI quiz pipeline applies to YouTube lessons. Students open{" "}
        <span className="font-medium capitalize">{lesson?.source_type}</span> resources from the lesson page.
      </p>
    );
  }

  const canApprove =
    merged.quiz_generation_status === "done" && (merged.published_question_count ?? 0) === 0;
  const isProcessing =
    merged.ai_processing_status === "processing" ||
    merged.quiz_generation_status === "processing";
  const isGenerating =
    generateMutation.isPending || regenerateMutation.isPending || isProcessing;
  const showRegenerateQuiz = !showGenerateQuiz && (!isManualMode || merged.quiz_generation_status === "done");
  const isQueueFailure =
    !isManualMode &&
    String(merged.generation_error || "")
      .toLowerCase()
      .includes("could not be queued");
  const approvalLabel =
    merged.approval_status ||
    (merged.published_question_count > 0 ? "published" : canApprove ? "pending_approval" : "none");
  const showTranscriptError =
    merged.transcript_error &&
    merged.transcript_error !== merged.generation_error &&
    !String(merged.transcript_error).toLowerCase().includes("api key");

  return (
    <>
      <div className="mt-2 space-y-2 rounded-lg border border-line bg-white p-3">
        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <p>
            <span className="text-muted">Source:</span>{" "}
            <span className="font-medium capitalize">{merged.source_type}</span>
          </p>
          <p>
            <span className="text-muted">Questions:</span>{" "}
            <span className="font-medium">
              {merged.generated_question_count} generated / {merged.published_question_count} published
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <AIStatusBadge kind="ai" status={merged.ai_processing_status} />
          <AIStatusBadge kind="transcript" status={merged.transcript_status} />
          <AIStatusBadge kind="quiz" status={merged.quiz_generation_status} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted">Approval</span>
          <StatusBadge status={approvalLabel} />
        </div>
        {isQueueFailure ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            <p className="font-medium">Lesson saved, but AI generation could not be queued.</p>
            <p className="mt-1">
              Start Redis and Celery, then click Regenerate Quiz.
            </p>
          </div>
        ) : null}
        {merged.generation_error && !isQueueFailure ? (
          <p className="text-xs text-red-600">Quiz: {merged.generation_error}</p>
        ) : null}
        {showTranscriptError ? (
          <p className="text-xs text-red-600">Transcript: {merged.transcript_error}</p>
        ) : null}
        {lesson?.has_pdf_notes ? (
          <p className="text-xs text-emerald-700">
            PDF study notes ready
            {lesson?.notes_generated_at ? ` (generated ${new Date(lesson.notes_generated_at).toLocaleString()})` : ""}
          </p>
        ) : null}
        {showGenerateQuiz && !isProcessing ? (
          <p className="text-xs text-muted">
            {status?.manual_hint || "AI quiz has not been generated yet."}
          </p>
        ) : null}
        {isProcessing || generateMutation.isPending ? (
          <p className="text-xs text-blue-700">Processing transcript and generating quiz…</p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          {merged.quiz_generation_status === "done" || merged.generated_question_count > 0 ? (
            <button
              type="button"
              onClick={() => setPreviewOpen(true)}
              className="inline-flex min-h-9 items-center rounded-lg border border-line px-3 text-xs font-semibold text-ocean-800 hover:bg-cream"
            >
              Preview quiz
            </button>
          ) : null}
          {canApprove ? (
            <button
              type="button"
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate()}
              className="inline-flex min-h-9 items-center rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              Approve
            </button>
          ) : null}
          {showGenerateQuiz ? (
            <button
              type="button"
              disabled={isGenerating}
              onClick={() => generateMutation.mutate()}
              className="inline-flex min-h-9 items-center rounded-lg bg-ocean-600 px-3 text-xs font-semibold text-white hover:bg-reef/400 disabled:opacity-50"
            >
              {generateMutation.isPending ? "Generating…" : "Generate Quiz"}
            </button>
          ) : null}
          {showRegenerateQuiz ? (
            <button
              type="button"
              disabled={isGenerating}
              onClick={() => regenerateMutation.mutate()}
              className="inline-flex min-h-9 items-center rounded-lg border border-line px-3 text-xs font-semibold text-ocean-800 hover:bg-cream disabled:opacity-50"
            >
              {regenerateMutation.isPending ? "Regenerating…" : "Regenerate Quiz"}
            </button>
          ) : null}
          <button
            type="button"
            disabled={generateNotesMutation.isPending}
            onClick={() => generateNotesMutation.mutate()}
            className="inline-flex min-h-9 items-center rounded-lg bg-ocean-600 px-3 text-xs font-semibold text-white hover:bg-ocean-700 disabled:opacity-50"
          >
            {generateNotesMutation.isPending ? "Generating PDF…" : "Generate PDF Notes"}
          </button>
          {onEdit ? (
            <button
              type="button"
              onClick={onEdit}
              className="inline-flex min-h-9 items-center rounded-lg border border-emerald-200 px-3 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
            >
              Edit lesson
            </button>
          ) : null}
        </div>
      </div>

      {previewOpen ? (
        <QuizPreviewModal
          courseId={courseId}
          lesson={lesson}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </>
  );
}
