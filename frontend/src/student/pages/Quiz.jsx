import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getLessonQuiz, submitQuizAttempt } from "@/api/quiz";
import useQuizStore from "@/store/quizStore";

function QuizCard({ question, selectedAnswer, onSelect }) {
  const options = question?.options ?? [];

  return (
    <div className="rounded-2xl border border-ocean-600/10 bg-white p-6 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
      <h2 className="text-lg font-semibold text-ink dark:text-sand">{question?.text ?? "Question"}</h2>
      <div className="mt-4 space-y-3">
        {options.map((option, index) => {
          const isSelected = selectedAnswer === index;
          return (
            <button
              key={`${question?.id}-${index}`}
              type="button"
              onClick={() => onSelect(question?.id, index)}
              className={`w-full rounded-xl border p-3 text-left transition ${
                isSelected
                  ? "border-ocean-600/50 bg-reef text-ink dark:border-ocean-600/40 dark:bg-ocean-600/15 dark:text-sand"
                  : "border-line bg-white text-ink hover:border-line hover:bg-cream dark:border-line/40 dark:bg-ocean-950/40 dark:text-reef dark:hover:border-line/50 dark:hover:bg-ocean-900/50"
              }`}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function Quiz() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { lessonId } = useParams();
  const {
    questions,
    currentIndex,
    selectedAnswers,
    setQuestions,
    selectAnswer,
    nextQuestion,
    submitQuiz,
    resetQuiz,
    getOrderedAnswerIndices,
    hasAllAnswersSelected,
  } = useQuizStore();

  const { data: quizData = {}, isLoading } = useQuery({
    queryKey: ["lesson-quiz", lessonId],
    queryFn: () => getLessonQuiz(lessonId),
    enabled: Boolean(lessonId),
  });

  useEffect(() => {
    resetQuiz();
  }, [lessonId, resetQuiz]);

  useEffect(() => {
    if (quizData?.questions?.length) {
      setQuestions(quizData.questions);
    }
  }, [quizData, setQuestions]);

  const submitMutation = useMutation({
    mutationFn: ({ quizId, answers }) => submitQuizAttempt(quizId, answers),
    onSuccess: (result) => {
      submitQuiz(result);
      const lid = Number(lessonId);
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      queryClient.invalidateQueries({ queryKey: ["weaknesses"] });
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
      queryClient.invalidateQueries({ queryKey: ["learning-path"] });
      if (Number.isFinite(lid)) {
        queryClient.invalidateQueries({ queryKey: ["student-lesson", lid] });
      }
      if (result?.weakness_detection_triggered === false) {
        toast.error(
          "Quiz submitted, but weakness analysis could not update. Try again later.",
          { id: "quiz-weakness-warn" },
        );
      }
      navigate(`/lessons/${lessonId}/quiz/result`, { replace: true, state: { result } });
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not submit quiz.", { id: "quiz-submit-err" });
    },
  });

  const currentQuestion = questions[currentIndex];
  const hasSelectedAnswer =
    currentQuestion && selectedAnswers[currentQuestion.id] !== undefined;
  const isLastQuestion = currentIndex >= questions.length - 1;
  const canSubmitFinal =
    isLastQuestion && hasAllAnswersSelected() && Boolean(quizData?.id ?? quizData?.quiz_id);
  const progressPercent = questions.length
    ? ((currentIndex + 1) / questions.length) * 100
    : 0;

  const handleNext = () => {
    if (!currentQuestion || !hasSelectedAnswer) return;

    if (!isLastQuestion) {
      nextQuestion();
      return;
    }

    const rawAnswers = getOrderedAnswerIndices();
    const quizId = quizData?.id ?? quizData?.quiz_id;
    if (!quizId || rawAnswers.some((value) => value === undefined)) {
      toast.error("Pick an answer for every question before submitting.", { id: "quiz-answers-err" });
      return;
    }

    submitMutation.mutate({
      quizId,
      answers: rawAnswers.map((value) => Math.trunc(Number(value))),
    });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-48 animate-pulse rounded-2xl bg-reef/50 dark:bg-white/20" />
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-ocean-600/10 bg-white p-6 text-muted shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:text-reef dark:shadow-xl dark:backdrop-blur-xl">
          No quiz questions available for this lesson.
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 overflow-x-hidden p-4 pb-8 md:p-6">
      <div className="rounded-2xl border border-ocean-600/10 bg-white p-4 shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl">
        <div className="mb-2 flex items-center justify-between text-sm text-muted dark:text-muted">
          <span>Progress</span>
          <span>
            {currentIndex + 1} / {questions.length}
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-reef/50 dark:bg-white/20">
          <div
            className="h-2 rounded-full bg-gradient-to-r from-coral to-ocean-600 transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <QuizCard
        question={currentQuestion}
        selectedAnswer={selectedAnswers[currentQuestion.id]}
        onSelect={selectAnswer}
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleNext}
          disabled={
            (!hasSelectedAnswer && !isLastQuestion) ||
            (isLastQuestion && !canSubmitFinal) ||
            submitMutation.isPending
          }
          className="min-h-[44px] rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-5 py-2.5 text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLastQuestion ? (submitMutation.isPending ? "Submitting..." : "Submit") : "Next"}
        </button>
      </div>
    </div>
  );
}
