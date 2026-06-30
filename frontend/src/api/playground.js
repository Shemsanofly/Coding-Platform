import client from "./client";

export const getPlaygroundChallenge = async () => {
  const { data } = await client.get("/api/playground/challenge/");
  return data?.challenge ?? null;
};

export const generatePlaygroundChallenge = async () => {
  const { data } = await client.post("/api/playground/challenge/generate/");
  return data?.challenge ?? null;
};

export const submitPlaygroundSolution = async ({ challengeId, code }) => {
  const { data } = await client.post(`/api/playground/challenge/${challengeId}/submit/`, { code });
  return data;
};

export const getPlaygroundLeaderboard = async () => {
  const { data } = await client.get("/api/playground/leaderboard/");
  return data ?? { leaderboard: [], total_students: 0, me: null };
};
