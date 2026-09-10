import client from "./client";

export const askStudentSupport = async ({ question, history = [], pagePath = "" }) => {
  const { data } = await client.post("/api/student/ai-support/", {
    question,
    history,
    page_path: pagePath,
  });
  return data;
};
