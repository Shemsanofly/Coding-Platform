import client from "./client";

const blobConfig = { responseType: "blob" };

export const downloadAdminSummaryReport = async (params = {}) =>
  client.get("/api/admin/reports/summary/", { ...blobConfig, params });

export const downloadAdminCoursesReport = async (params = {}) =>
  client.get("/api/admin/reports/courses/", { ...blobConfig, params });

export const downloadAdminStudentsReport = async (params = {}) =>
  client.get("/api/admin/reports/students/", { ...blobConfig, params });

export const downloadAdminWeaknessesReport = async (params = {}) =>
  client.get("/api/admin/reports/weaknesses/", { ...blobConfig, params });

export const downloadAdminAIGenerationReport = async () =>
  client.get("/api/admin/reports/ai-generation/", blobConfig);

export const downloadMyProgressReport = async () =>
  client.get("/api/reports/my-progress/", blobConfig);

export const downloadMyQuizPerformanceReport = async (params = {}) =>
  client.get("/api/reports/my-quiz-performance/", { ...blobConfig, params });

export const downloadMyWeaknessesReport = async () =>
  client.get("/api/reports/my-weaknesses/", blobConfig);

export const downloadMyLearningPathReport = async () =>
  client.get("/api/reports/my-learning-path/", blobConfig);
