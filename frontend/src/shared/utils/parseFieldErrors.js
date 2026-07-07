/**
 * Map API validation errors to field keys for inline form display.
 */
export function parseFieldErrors(error) {
  const data = error?.response?.data;
  if (!data || typeof data !== "object") {
    if (!error?.response) {
      return { form: "Cannot reach the server. Ensure the backend is running." };
    }
    return {};
  }

  if (typeof data.detail === "string") {
    return { form: data.detail };
  }

  const fields = {};
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value) && value[0]) {
      fields[key] = String(value[0]);
    } else if (typeof value === "string") {
      fields[key] = value;
    }
  }
  return fields;
}
