import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getLessonQuiz, submitQuizAttempt } from "@/api/quiz";
import useQuizStore from "@/store/quizStore";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import ProgressBar from "@/student/components/ProgressBar";

function QuizCard({ question, selectedAnswer, onSelect, questionNumber, totalQuestions }) {
  const options = question?.options ?? [];

  return (
    <Card variant="elevated" padding="lg">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-muted">
        Question {questionNumber} of {totalQuestions}
      </p>
      <h2 className="mt-2 text-lg font-semibold text-ink dark:text-sand">
        {question?.text ?? "Question"}
      </h2>
      <div className="mt-4 space-y-3" role="radiogroup" aria-label={`Question ${questionNumber}`}>
        {options.map((option, index) => {
          const isSelected = selectedAnswer === index;
          return (
            <button
              key={`${question?.id}-${index}`}
              type="button"
              role="radio"
              aria-checked={isSelected}
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
    </Card>
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
      queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      queryClient.invalidateQueries({ queryKey: ["weaknesses"] });
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
      queryClient.invalidateQueries({ queryKey: ["learning-path"] });
      if (Number.isFinite(lid)) {
        queryClient.invalidateQueries({ queryKey: ["student-lesson", lid] });
      }
      if (result?.weakness_detection_triggered === false) {
        toast.error("Quiz submitted, but weakness analysis could not update. Try again later.", {
          id: "quiz-weakness-warn",
        });
      }
      navigate(`/lessons/${lessonId}/quiz/result`, { replace: true, state: { result } });
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not submit quiz.", {
        id: "quiz-submit-err",
      });
    },
  });

  const currentQuestion = questions[currentIndex];
  const hasSelectedAnswer = currentQuestion && selectedAnswers[currentQuestion.id] !== undefined;
  const isLastQuestion = currentIndex >= questions.length - 1;
  const canSubmitFinal =
    isLastQuestion && hasAllAnswersSelected() && Boolean(quizData?.id ?? quizData?.quiz_id);
  const progressPercent = questions.length
    ? Math.round(((currentIndex + 1) / questions.length) * 100)
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
      toast.error("Pick an answer for every question before submitting.", {
        id: "quiz-answers-err",
      });
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
        <div className="h-48 animate-pulse rounded-2xl bg-reef/50 dark:bg-ocean-950/60" />
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="p-6">
        <Card variant="elevated" padding="lg" className="text-muted dark:text-reef">
          No quiz questions available for this lesson.
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 overflow-x-hidden p-4 pb-8 md:p-6">
      <Card variant="elevated" padding="md">
        <ProgressBar
          value={progressPercent}
          label={`Question ${currentIndex + 1} of ${questions.length}`}
          size="sm"
        />
      </Card>

      <QuizCard
        question={currentQuestion}
        selectedAnswer={selectedAnswers[currentQuestion.id]}
        onSelect={selectAnswer}
        questionNumber={currentIndex + 1}
        totalQuestions={questions.length}
      />

      <div className="flex justify-end">
        <Button
          variant="gradient"
          size="lg"
          loading={isLastQuestion && submitMutation.isPending}
          disabled={
            (!hasSelectedAnswer && !isLastQuestion) ||
            (isLastQuestion && !canSubmitFinal && !submitMutation.isPending)
          }
          onClick={handleNext}
        >
          {isLastQuestion ? "Submit quiz" : "Next question"}
        </Button>
      </div>
    </div>
  );
}
