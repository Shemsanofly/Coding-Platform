import client from "./client";

export const getAnalyticsSummary = async () => {
  const response = await client.get("/api/analytics/summary/");
  return response.data ?? {};
};

export const getEnrollments = async () => {
  const response = await client.get("/api/enrollments/");
  return response.data ?? [];
};

const normalizeWeaknessPayload = (data) => {
  if (Array.isArray(data)) {
    return { topics: data, lesson_groups: [], courses: [] };
  }
  return {
    topics: data?.topics ?? [],
    lesson_groups: data?.lesson_groups ?? [],
    courses: data?.courses ?? [],
  };
};

export const getWeaknesses = async (options = {}) => {
  const params = {};
  if (options.courseId) params.course_id = options.courseId;
  const response = await client.get("/api/weaknesses/", { params });
  return normalizeWeaknessPayload(response.data);
};

export const getRecommendations = async (options = {}) => {
  const params = {};
  if (options.courseId) params.course_id = options.courseId;
  const response = await client.get("/api/recommendations/", { params });
  return response.data ?? [];
};

export const getLearningPath = async (options = {}) => {
  const params = {};
  if (options.explain) params.explain = "true";
  if (options.courseId) params.course_id = options.courseId;
  const response = await client.get("/api/learning-path/", { params });
  return response.data ?? {};
};

export const getPracticeLeaderboard = async () => {
  const response = await client.get("/api/practice/leaderboard/");
  return response.data ?? { leaderboard: [], total_students: 0, me: null };
};

export const getLessonWeaknessSummary = async (lessonId) => {
  const response = await client.get(`/api/student/lessons/${lessonId}/weakness-summary/`);
  return response.data ?? {};
};
