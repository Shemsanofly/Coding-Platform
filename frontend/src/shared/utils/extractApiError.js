/**
 * Extract a readable message from an Axios or fetch error.
 */
export function extractApiError(error, fallback = "Request failed.") {
  if (!error) {
    return fallback;
  }

  if (error.code === "ECONNABORTED") {
    return "Request timed out. Quiz generation can take up to two minutes — try again or refresh status.";
  }

  if (!error.response) {
    const message = String(error.message || "");
    if (message.includes("Network Error") || message.includes("ECONNREFUSED")) {
      return "Cannot reach the API server. Ensure the Flask backend is running on http://127.0.0.1:8000.";
    }
    return message || fallback;
  }

  const data = error.response.data;
  if (typeof data === "string" && data.trim()) {
    return data;
  }
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  if (typeof data?.error === "string") {
    return data.error;
  }
  if (typeof data?.message === "string") {
    return data.message;
  }
  if (data && typeof data === "object") {
    const firstField = Object.values(data).find((value) => Array.isArray(value) && value[0]);
    if (firstField?.[0]) {
      return String(firstField[0]);
    }
  }

  return fallback;
}
