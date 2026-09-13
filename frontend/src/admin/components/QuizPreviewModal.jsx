import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  approveAdminLessonQuiz,
  getAdminLessonProcessingStatus,
  getAdminLessonQuizPreview,
  regenerateAdminLessonQuiz,
} from "@/api/adminCourses";
import {
  handleRegenerateResponse,
  invalidateQuizPipelineQueries,
} from "@/admin/utils/regenerateQuizHandlers";
import { extractApiError } from "@/shared/utils/extractApiError";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import StatusBadge from "@/admin/components/StatusBadge";

export default function QuizPreviewModal({ courseId, lesson, onClose }) {
  const queryClient = useQueryClient();
  const lessonId = lesson?.id;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-quiz-preview", courseId, lessonId],
    queryFn: () => getAdminLessonQuizPreview(courseId, lessonId),
    enabled: Boolean(courseId && lessonId),
  });

  const statusQuery = useQuery({
    queryKey: ["admin-lesson-processing", courseId, lessonId],
    queryFn: () => getAdminLessonProcessingStatus(courseId, lessonId),
    enabled: Boolean(courseId && lessonId),
  });
  const isManualMode = (statusQuery.data?.ai_generation_mode ?? "manual") === "manual";

  const approveMutation = useMutation({
    mutationFn: () => approveAdminLessonQuiz(courseId, lessonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-lesson-processing", courseId, lessonId] });
      queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseId] });
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
      onClose?.();
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateAdminLessonQuiz(courseId, lessonId),
    onSuccess: (data) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lessonId);
      handleRegenerateResponse(data, { isManualMode });
      void refetch();
    },
    onError: (error) => {
      invalidateQuizPipelineQueries(queryClient, courseId, lessonId);
      toast.error(extractApiError(error, "Could not start quiz regeneration."), {
        id: "regen-quiz-err",
      });
    },
  });

  const questions = data?.questions || [];
  const canApprove = data?.generation_status === "done" && questions.some((q) => !q.is_published);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ocean-900/50 p-0 sm:items-center sm:p-4">
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-line bg-white shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quiz-preview-title"
      >
        <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-4 sm:px-6">
          <div className="min-w-0">
            <h2 id="quiz-preview-title" className="truncate text-lg font-semibold text-ink">
              Quiz preview — {lesson?.title}
            </h2>
            <p className="mt-1 text-xs text-muted">
              Unpublished questions are visible here only. Students see published questions after
              approval.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-xl border border-line text-muted hover:bg-cream"
            aria-label="Close preview"
          >
            ×
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
          {isLoading ? <LoadingState label="Loading quiz preview…" rows={4} /> : null}
          {isError ? (
            <ErrorState message="Could not load quiz preview." onRetry={() => refetch()} />
          ) : null}

          {!isLoading && !isError ? (
            <div className="space-y-5">
              <section className="rounded-xl border border-line/70 bg-cream p-4 text-sm">
                <p className="font-medium text-ink">Lesson summary</p>
                <p className="mt-2 text-ocean-800">{data?.summary || "No summary yet."}</p>
                {data?.learning_objectives?.length ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase text-muted">
                      Learning objectives
                    </p>
                    <ul className="mt-1 list-inside list-disc text-ocean-800">
                      {data.learning_objectives.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {data?.key_concepts?.length ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase text-muted">Key concepts</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {data.key_concepts.map((concept) => (
                        <span
                          key={concept}
                          className="rounded-full bg-white px-2 py-0.5 text-xs text-ocean-800 ring-1 ring-line"
                        >
                          {concept}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {data?.topic_tags?.length ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase text-muted">Topic tags</p>
                    <p className="mt-1 text-ocean-800">{data.topic_tags.join(", ")}</p>
                  </div>
                ) : null}
                <div className="mt-3">
                  <StatusBadge
                    status={data?.generation_status}
                    label={`Generation: ${data?.generation_status || "pending"}`}
                  />
                </div>
              </section>

              {questions.length === 0 ? (
                <p className="text-sm text-muted">No generated questions yet.</p>
              ) : (
                <ol className="space-y-4">
                  {questions.map((question, index) => (
                    <li
                      key={question.id ?? index}
                      className="rounded-xl border border-line bg-white p-4"
                    >
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                        <span className="font-semibold text-ocean-800">Q{index + 1}</span>
                        <span className="rounded bg-sand px-2 py-0.5">
                          {question.question_type || "mcq"}
                        </span>
                        {question.difficulty ? (
                          <span className="rounded bg-sand px-2 py-0.5">{question.difficulty}</span>
                        ) : null}
                        {question.is_published ? (
                          <span className="text-emerald-700">Published</span>
                        ) : (
                          <span className="text-amber-700">Draft</span>
                        )}
                      </div>
                      <p className="mt-2 text-sm font-medium text-ink">{question.text}</p>
                      <ul className="mt-2 space-y-1 text-sm text-ocean-800">
                        {(question.options || []).map((option, optIndex) => (
                          <li
                            key={optIndex}
                            className={
                              optIndex === question.correct_index
                                ? "font-semibold text-emerald-700"
                                : ""
                            }
                          >
                            {optIndex === question.correct_index ? "✓ " : "• "}
                            {option}
                          </li>
                        ))}
                      </ul>
                      {question.explanation ? (
                        <p className="mt-2 text-xs text-muted">
                          <span className="font-semibold">Explanation:</span> {question.explanation}
                        </p>
                      ) : null}
                      {question.topic_tag ? (
                        <p className="mt-1 text-xs text-muted">Tag: {question.topic_tag}</p>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : null}
        </div>

        <footer className="sticky bottom-0 flex flex-wrap gap-2 border-t border-line bg-white px-4 py-3 sm:px-6">
          <button
            type="button"
            disabled={regenerateMutation.isPending}
            onClick={() => regenerateMutation.mutate()}
            className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl border border-line px-4 text-sm font-semibold text-ocean-800 hover:bg-cream disabled:opacity-50 sm:flex-none"
          >
            {regenerateMutation.isPending ? "Regenerating…" : "Regenerate Quiz"}
          </button>
          {canApprove ? (
            <button
              type="button"
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate()}
              className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 sm:flex-none"
            >
              Approve quiz
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl border border-line px-4 text-sm font-semibold text-muted hover:bg-cream sm:flex-none"
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}
