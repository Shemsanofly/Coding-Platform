import client from "./client";

const cleanParams = (params) => {
  const entries = Object.entries(params || {}).filter(([, value]) => {
    if (value === undefined || value === null) {
      return false;
    }
    return String(value).trim() !== "";
  });
  return Object.fromEntries(entries);
};

export const getAdminUsers = async (filters = {}) => {
  const response = await client.get("/api/admin/users/", {
    params: cleanParams({
      search: filters.search,
      weakness_level: filters.weaknessLevel,
      ordering: filters.ordering,
    }),
  });
  return response.data ?? [];
};

export const getAdminUserProfile = async (userId) => {
  const response = await client.get(`/api/admin/users/${userId}/profile/`);
  return response.data ?? {};
};

export const getAdminUserWeaknesses = async (userId) => {
  const response = await client.get(`/api/admin/users/${userId}/weaknesses/`);
  return response.data ?? [];
};

export const getAdminUserRecommendations = async (userId) => {
  const response = await client.get(`/api/admin/users/${userId}/recommendations/`);
  return response.data ?? [];
};

export const getAdminUserQuizLog = async (userId) => {
  const response = await client.get(`/api/admin/users/${userId}/quiz-log/`);
  return response.data ?? [];
};

export const updateAdminStudent = async (userId, payload) => {
  const response = await client.patch(`/api/admin/students/${userId}/`, payload);
  return response.data;
};

export const deactivateAdminStudent = async (userId) => {
  const response = await client.delete(`/api/admin/students/${userId}/`);
  return response.data;
};

export const purgeAdminStudent = async (userId) => {
  const response = await client.post(`/api/admin/students/${userId}/purge/`);
  return response.data;
};
