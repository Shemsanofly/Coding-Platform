import client from "./client";

export const getCourseCatalog = async () => {
  const { data } = await client.get("/api/catalog/courses/");
  return Array.isArray(data) ? data : [];
};

export const joinCourse = async (courseId) => {
  const { data } = await client.post("/api/enrollments/join/", { course_id: courseId });
  return data;
};

export const getStudentCourse = async (courseId) => {
  const { data } = await client.get(`/api/student/courses/${courseId}/`);
  return data;
};

export const getStudentLesson = async (lessonId) => {
  const { data } = await client.get(`/api/student/lessons/${lessonId}/`);
  return data;
};

export const postLessonProgress = async (lessonId, payload = {}) => {
  const { data } = await client.post(`/api/student/lessons/${lessonId}/progress/`, payload);
  return data;
};

export const getLessonNotes = async (lessonId) => {
  const { data } = await client.get(`/api/lessons/${lessonId}/notes/`);
  return data;
};

export const viewLessonNotes = async (lessonId) =>
  client.get(`/api/lessons/${lessonId}/view-notes/`, { responseType: "blob" });

export const downloadLessonNotes = async (lessonId) =>
  client.get(`/api/lessons/${lessonId}/download-notes/`, { responseType: "blob" });
