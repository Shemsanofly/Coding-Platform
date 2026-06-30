import { create } from "zustand";

const initialState = {
  questions: [],
  currentIndex: 0,
  selectedAnswers: {},
  submitted: false,
  result: null,
};

const useQuizStore = create((set, get) => ({
  ...initialState,
  setQuestions: (questions = []) =>
    set({
      questions,
      currentIndex: 0,
      selectedAnswers: {},
      submitted: false,
      result: null,
    }),
  selectAnswer: (questionId, answerIndex) =>
    set((state) => ({
      selectedAnswers: {
        ...state.selectedAnswers,
        [questionId]: answerIndex,
      },
    })),
  nextQuestion: () =>
    set((state) => {
      const lastIndex = Math.max(state.questions.length - 1, 0);
      return {
        currentIndex: Math.min(state.currentIndex + 1, lastIndex),
      };
    }),
  submitQuiz: (result = null) =>
    set(() => ({
      submitted: true,
      result,
    })),
  resetQuiz: () => set(initialState),
  /** Ordered answer indices matching `questions` order (API expects list[int]). */
  getOrderedAnswerIndices: () => {
    const { questions, selectedAnswers } = get();
    return questions.map((question) => selectedAnswers[question.id]);
  },
  hasAllAnswersSelected: () => {
    const { questions, selectedAnswers } = get();
    if (!questions.length) {
      return false;
    }
    return questions.every((question) => selectedAnswers[question.id] !== undefined);
  },
}));

export default useQuizStore;
