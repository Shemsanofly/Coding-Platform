import client from "./client";
import { fetchAllPages, unwrapPaginated } from "./pagination";

export const getCourseCatalog = async ({ level, page, page_size: pageSize } = {}) => {
  const params = {};
  if (level) {
    params.level = level;
  }
  if (page) {
    params.page = page;
  }
  if (pageSize) {
    params.page_size = pageSize;
  }
  const { data } = await client.get("/api/catalog/courses/", { params });
  if (page || pageSize) {
    return unwrapPaginated(data);
  }
  if (data?.next) {
    return fetchAllPages(({ page: p, page_size: ps }) =>
      client
        .get("/api/catalog/courses/", { params: { ...params, level, page: p, page_size: ps } })
        .then((r) => r.data)
    );
  }
  return unwrapPaginated(data).results;
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
