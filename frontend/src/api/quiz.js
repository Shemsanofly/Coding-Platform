import client from "./client";

export const getLessonQuiz = async (lessonId) => {
  const response = await client.get(`/api/lessons/${lessonId}/quiz/`);
  return response.data ?? {};
};

export const submitQuizAttempt = async (quizId, answers) => {
  const response = await client.post(`/api/quizzes/${quizId}/submit/`, { answers });
  return response.data ?? {};
};
