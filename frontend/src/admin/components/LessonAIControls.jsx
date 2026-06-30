import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  approveAdminLessonQuiz,
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

const StatusBadge = ({ status }) => {
  const normalized = (status || "pending").toLowerCase();
  const styles = {
    pending: "bg-gray-100 text-gray-700",
    processing: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    done: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${styles[normalized] || styles.pending}`}
    >
      {normalized}
    </span>
  );
};

export default function LessonAIControls({ courseId, lesson }) {
  const queryClient = useQueryClient();
  const isYoutube = lesson?.source_type === "youtube";

  const { data: status } = useQuery({
    queryKey: ["admin-lesson-processing", courseId, lesson?.id],
    queryFn: () => getAdminLessonProcessingStatus(courseId, lesson.id),
    enabled: Boolean(courseId && lesson?.id && isYoutube),
    refetchInterval: (query) => {
      const ai = query.state.data?.ai_processing_status;
      const quiz = query.state.data?.quiz_generation_status;
      const active = ai === "pending" || ai === "processing" || quiz === "pending" || quiz === "processing";
      return active ? 3000 : false;
    },
  });

  const isManualMode = (status?.ai_generation_mode ?? "manual") === "manual";
  const showGenerateQuiz =
    isManualMode &&
    (status?.quiz_generation_status === "pending" || status?.quiz_generation_status === "failed");

  const generateMutation = useMutation({
    mutationFn: () => generateAdminLessonQuiz(courseId, lesson.id),
    onSuccess: (data) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      handleGenerateResponse(data);
    },
    onError: (error) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lesson.id);
      toast.error(extractApiError(error, "Could not generate quiz."), { id: "gen-quiz-err" });
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
      toast.error(extractApiError(error, "Could not start quiz regeneration."), {
        id: "regen-quiz-err",
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveAdminLessonQuiz(courseId, lesson.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lesson-processing", courseId, lesson.id] });
    },
  });

  if (!isYoutube) {
    return null;
  }

  const canApprove =
    status?.quiz_generation_status === "done" && (status?.published_question_count ?? 0) === 0;
  const isProcessing =
    status?.ai_processing_status === "processing" || status?.quiz_generation_status === "processing";

  return (
    <div className="mt-2 space-y-2 border-t border-line pt-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-gray-500">AI:</span>
        <StatusBadge status={status?.ai_processing_status} />
        <span className="text-gray-500">Quiz:</span>
        <StatusBadge status={status?.quiz_generation_status} />
      </div>
      {showGenerateQuiz && !isProcessing ? (
        <p className="text-xs text-muted">
          {status?.manual_hint || "AI quiz has not been generated yet."}
        </p>
      ) : null}
      {String(status?.generation_error || "")
        .toLowerCase()
        .includes("could not be queued") ? (
        <p className="text-xs text-amber-800">
          Lesson saved, but AI generation could not be queued. Start Redis and Celery, then click
          Regenerate Quiz.
        </p>
      ) : null}
      {status?.generation_error &&
      !String(status.generation_error).toLowerCase().includes("could not be queued") ? (
        <p className="text-xs text-red-600">{status.generation_error}</p>
      ) : null}
      {isProcessing ? (
        <p className="text-xs text-blue-700">Processing transcript and generating quiz…</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {showGenerateQuiz ? (
          <button
            type="button"
            disabled={generateMutation.isPending || isProcessing}
            onClick={() => generateMutation.mutate()}
            className="rounded-lg bg-ocean-600 px-2 py-1 text-xs font-semibold text-white hover:bg-reef/400 disabled:opacity-50"
          >
            {generateMutation.isPending ? "Generating…" : "Generate Quiz"}
          </button>
        ) : null}
        {!showGenerateQuiz && (!isManualMode || status?.quiz_generation_status === "done") ? (
          <button
            type="button"
            disabled={regenerateMutation.isPending || isProcessing}
            onClick={() => regenerateMutation.mutate()}
            className="rounded-lg border border-line px-2 py-1 text-xs font-semibold text-ocean-800 hover:bg-sand disabled:opacity-50"
          >
            {regenerateMutation.isPending ? "Regenerating…" : "Regenerate Quiz"}
          </button>
        ) : null}
        {canApprove ? (
          <button
            type="button"
            disabled={approveMutation.isPending}
            onClick={() => approveMutation.mutate()}
            className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Approve quiz
          </button>
        ) : null}
        {(status?.published_question_count ?? 0) > 0 ? (
          <span className="text-xs text-emerald-700">Published ({status.published_question_count} questions)</span>
        ) : null}
      </div>
    </div>
  );
}
