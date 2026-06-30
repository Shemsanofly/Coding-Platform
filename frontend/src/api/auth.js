import client, { setAccessToken } from "./client";

export const login = async ({ email, password }) => {
  const { data } = await client.post("/auth/login/", { email, password });
  return data;
};

export const register = async ({ email, password, confirm_password, role, admin_code, experience_level }) => {
  const body = {
    email,
    password,
    confirm_password,
    role,
    admin_code,
  };
  if (experience_level) {
    body.experience_level = experience_level;
  }
  const { data } = await client.post("/auth/register/", body);
  return data;
};

export const refreshAccessToken = async () => {
  const { data } = await client.post("/auth/refresh/");
  return data;
};

export const logout = async () => {
  await client.post("/auth/logout/");
  setAccessToken(null);
};

export const fetchMe = async () => {
  const { data } = await client.get("/auth/me/");
  return data;
};

export const updateProfile = async (payload) => {
  const { data } = await client.patch("/auth/me/", payload);
  return data;
};
