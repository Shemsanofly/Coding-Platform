import axios from "axios";

let accessToken = null;

export const setAccessToken = (token) => {
  accessToken = token;
};

const trimmedApiUrl =
  typeof import.meta.env.VITE_API_URL === "string"
    ? import.meta.env.VITE_API_URL.trim().replace(/\/$/, "")
    : "";

// Dev: empty base URL uses the Vite dev server origin so `/api` and `/auth` go through the proxy (avoids CORS).
// Prod: set VITE_API_URL or fall back to localhost for same-machine APIs.
const baseURL = trimmedApiUrl || (import.meta.env.DEV ? "" : "http://localhost:8000");

const client = axios.create({
  baseURL,
  withCredentials: true,
  timeout: 20000,
});

client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;

    if (error?.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshResponse = await client.post("/auth/refresh/");
        const newAccessToken = refreshResponse?.data?.access;

        setAccessToken(newAccessToken);
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

        return client(originalRequest);
      } catch (refreshError) {
        setAccessToken(null);
        window.location.assign("/login");
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default client;
