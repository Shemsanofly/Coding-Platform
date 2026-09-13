import client from "./client";

export const createAdminCourse = async (payload) => {
  const response = await client.post("/api/admin/courses/", payload);
  return response.data;
};

export const getAdminCoursePipelineStatus = async (courseId) => {
  const response = await client.get(`/api/admin/courses/${courseId}/pipeline-status/`);
  return response.data;
};

export const getAdminCourses = async () => {
  const response = await client.get("/api/admin/courses/");
  return response.data;
};

export const getAdminDashboardSummary = async () => {
  const response = await client.get("/api/admin/courses/dashboard-summary/");
  return response.data;
};

export const getAdminAnalyticsOverview = async () => {
  const response = await client.get("/api/admin/courses/analytics-overview/");
  return response.data;
};

export const updateAdminCourse = async (courseId, payload) => {
  const response = await client.patch(`/api/admin/courses/${courseId}/`, payload);
  return response.data;
};

export const deleteAdminCourse = async (courseId) => {
  await client.delete(`/api/admin/courses/${courseId}/`);
};

/** Course metadata including `level` (used so lesson source options track DB accurately). */
export const getAdminCourse = async (courseId) => {
  const response = await client.get(`/api/admin/courses/${courseId}/`);
  return response.data;
};

export const bootstrapCourseCatalog = async () => {
  const response = await client.post("/api/admin/courses/bootstrap-catalog/");
  return response.data;
};

export const getAdminLessons = async (courseId) => {
  const response = await client.get(`/api/admin/courses/${courseId}/lessons/`);
  return response.data ?? [];
};

export const createAdminLesson = async (courseId, payload) => {
  const response = await client.post(`/api/admin/courses/${courseId}/lessons/`, payload);
  return response.data;
};

export const updateAdminLesson = async (courseId, lessonId, payload) => {
  const response = await client.patch(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/`,
    payload,
  );
  return response.data;
};

export const deleteAdminLesson = async (courseId, lessonId) => {
  await client.delete(`/api/admin/courses/${courseId}/lessons/${lessonId}/`);
};

export const getAdminLessonProcessingStatus = async (courseId, lessonId) => {
  const response = await client.get(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/processing-status/`,
  );
  return response.data;
};

export const getAdminLessonQuizPreview = async (courseId, lessonId) => {
  const response = await client.get(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/quiz-preview/`,
  );
  return response.data;
};

/** Long-running AI pipeline calls (transcript + Gemini). */
const AI_PIPELINE_TIMEOUT_MS = 120000;
const PDF_NOTES_TIMEOUT_MS = 300000;

export const generateAdminLessonQuiz = async (courseId, lessonId) => {
  const response = await client.post(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/generate-quiz/`,
    {},
    { timeout: AI_PIPELINE_TIMEOUT_MS },
  );
  return response.data;
};

export const regenerateAdminLessonQuiz = async (courseId, lessonId) => {
  const response = await client.post(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/regenerate-quiz/`,
    {},
    { timeout: AI_PIPELINE_TIMEOUT_MS },
  );
  return response.data;
};

export const approveAdminLessonQuiz = async (courseId, lessonId) => {
  const response = await client.post(
    `/api/admin/courses/${courseId}/lessons/${lessonId}/approve-quiz/`,
  );
  return response.data;
};

export const generateAdminLessonNotes = async (lessonId) => {
  const response = await client.post(
    `/api/lessons/${lessonId}/generate-notes/`,
    {},
    { timeout: PDF_NOTES_TIMEOUT_MS },
  );
  return response.data;
};
