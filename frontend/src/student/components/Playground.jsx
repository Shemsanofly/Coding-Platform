import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  generatePlaygroundChallenge,
  getPlaygroundChallenge,
  getPlaygroundLeaderboard,
  submitPlaygroundSolution,
} from "@/api/playground";
import LoadingState from "@/student/components/LoadingState";
import ProgressBar from "@/student/components/ProgressBar";

function initials(name) {
  const parts = String(name || "?")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function rankBadge(rank) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
}

function TestResults({ results }) {
  if (!results?.length) {
    return null;
  }
  return (
    <ul className="mt-3 space-y-2">
      {results.map((result) => (
        <li
          key={result.case ?? result.error ?? JSON.stringify(result)}
          className={`rounded-xl border px-3 py-2 text-sm ${
            result.passed
              ? "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100"
              : "border-red-200 bg-red-50 text-red-900 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-100"
          }`}
        >
          {result.error ? (
            <span>{result.error}</span>
          ) : (
            <span>
              Test {result.case}: {result.passed ? "Passed" : "Failed"}
              {!result.passed && result.expected !== undefined ? (
                <span className="block text-xs opacity-80">
                  Expected {JSON.stringify(result.expected)}, got {JSON.stringify(result.actual)}
                </span>
              ) : null}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function Playground({ compact = false }) {
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [testResults, setTestResults] = useState(null);

  const challengeQuery = useQuery({
    queryKey: ["playground-challenge"],
    queryFn: getPlaygroundChallenge,
  });

  const leaderboardQuery = useQuery({
    queryKey: ["playground-leaderboard"],
    queryFn: getPlaygroundLeaderboard,
  });

  const challenge = challengeQuery.data;
  const me = leaderboardQuery.data?.me;
  const leaderboard = leaderboardQuery.data?.leaderboard ?? [];

  useEffect(() => {
    if (challenge?.starter_code) {
      setCode(challenge.starter_code);
      setTestResults(null);
    }
  }, [challenge?.id, challenge?.starter_code]);

  const generateMutation = useMutation({
    mutationFn: generatePlaygroundChallenge,
    onSuccess: () => {
      toast.success("New AI challenge ready!", { id: "pg-generate-ok" });
      setTestResults(null);
      queryClient.invalidateQueries({ queryKey: ["playground-challenge"] });
    },
    onError: () => toast.error("Could not generate a challenge.", { id: "pg-generate-err" }),
  });

  const submitMutation = useMutation({
    mutationFn: submitPlaygroundSolution,
    onSuccess: (data) => {
      setTestResults(data.test_results ?? []);
      if (data.passed) {
        toast.success(`+${data.xp_earned} XP earned!`, { id: "pg-submit-ok" });
        queryClient.invalidateQueries({ queryKey: ["playground-challenge"] });
        queryClient.invalidateQueries({ queryKey: ["playground-leaderboard"] });
      } else {
        toast.error("Not quite — check the test results.", { id: "pg-submit-fail" });
      }
    },
    onError: () => toast.error("Could not run your code.", { id: "pg-submit-err" }),
  });

  const isLoading = challengeQuery.isLoading || leaderboardQuery.isLoading;

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-panel dark:border-line/30 dark:bg-ocean-950/50">
        <LoadingState label="Loading playground…" rows={4} />
      </section>
    );
  }

  return (
    <div className={`grid gap-5 ${compact ? "" : "xl:grid-cols-[1.4fr_1fr]"}`}>
      <section
        className={`overflow-hidden rounded-[22px] border-2 border-ocean-200/60 bg-gradient-to-br from-reef/50 via-white to-sand shadow-card dark:border-ocean-600/30 dark:from-ocean-950/80 dark:via-ocean-950/60 dark:to-ocean-900/40 ${
          compact ? "p-4" : "p-5 md:p-6"
        }`}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="lc-tag">AI coding playground</p>
            <h2 className="mt-1 text-xl font-bold text-ocean-950 dark:text-sand md:text-2xl">
              {challenge?.title ?? "Ready to code?"}
            </h2>
            <p className="mt-1 text-sm text-muted">
              Gemini generates a challenge — implement <code className="rounded bg-reef/60 px-1">solution()</code> and
              pass all tests to earn XP.
            </p>
          </div>
          <button
            type="button"
            disabled={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
            className="lc-btn-primary shrink-0"
          >
            {generateMutation.isPending ? "Generating…" : challenge ? "New challenge" : "Generate challenge"}
          </button>
        </div>

        {!challenge ? (
          <div className="mt-6 rounded-xl border border-dashed border-line bg-cream/80 p-8 text-center dark:border-line/40 dark:bg-ocean-950/40">
            <p className="text-sm text-muted">No active challenge yet.</p>
            <button
              type="button"
              disabled={generateMutation.isPending}
              onClick={() => generateMutation.mutate()}
              className="lc-btn-primary mt-4"
            >
              Generate your first challenge
            </button>
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <article className="rounded-2xl border border-ocean-600/10 bg-white/90 p-4 dark:border-line/30 dark:bg-ocean-950/70">
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef">
                <span className="rounded-full bg-reef px-2 py-0.5 capitalize dark:bg-ocean-900">{challenge.difficulty}</span>
                <span className="text-coral">{challenge.xp_reward} XP reward</span>
                {challenge.status === "solved" ? (
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100">
                    Solved
                  </span>
                ) : null}
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink dark:text-sand">
                {challenge.description}
              </p>
            </article>

            <div>
              <label htmlFor="playground-code" className="mb-2 block text-sm font-semibold text-ocean-800 dark:text-reef">
                Your Python solution
              </label>
              <textarea
                id="playground-code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                disabled={challenge.status === "solved"}
                spellCheck={false}
                className="min-h-[220px] w-full resize-y rounded-xl border border-ocean-600/20 bg-ocean-950 px-4 py-3 font-mono text-sm leading-relaxed text-reef shadow-inner focus:border-ocean-600 focus:outline-none focus:ring-2 focus:ring-ocean-600/30 disabled:opacity-70"
              />
            </div>

            {challenge.status !== "solved" ? (
              <button
                type="button"
                disabled={submitMutation.isPending || !code.trim()}
                onClick={() =>
                  submitMutation.mutate({
                    challengeId: challenge.id,
                    code,
                  })
                }
                className="lc-btn-primary"
              >
                {submitMutation.isPending ? "Running tests…" : "Run & submit"}
              </button>
            ) : null}

            <TestResults results={testResults} />
          </div>
        )}
      </section>

      {!compact ? (
        <aside className="space-y-5">
          {me ? (
            <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
              <h3 className="text-lg font-semibold text-ocean-950 dark:text-sand">Your progress</h3>
              <div className="mt-4 flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-lc-primary text-sm font-bold text-white">
                  {initials(me.display_name)}
                </span>
                <div>
                  <p className="font-bold text-ink dark:text-sand">{me.display_name}</p>
                  <p className="text-sm text-muted">
                    {me.tier_icon} {me.tier_title} · Rank {me.rank ? `#${me.rank}` : "—"}
                  </p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-reef/40 p-3 dark:bg-ocean-900/50">
                  <p className="text-xs text-muted">Playground XP</p>
                  <p className="text-xl font-bold text-ocean-950 dark:text-sand">{me.practice_xp}</p>
                </div>
                <div className="rounded-xl bg-reef/40 p-3 dark:bg-ocean-900/50">
                  <p className="text-xs text-muted">Solved</p>
                  <p className="text-xl font-bold text-ocean-950 dark:text-sand">{me.challenges_solved}</p>
                </div>
              </div>
              <div className="mt-4">
                <ProgressBar
                  value={me.tier_progress_pct}
                  label={
                    me.next_tier_title
                      ? `Progress to ${me.next_tier_title} (${me.next_tier_xp} XP)`
                      : "Max tier reached"
                  }
                  size="lg"
                />
              </div>
            </section>
          ) : null}

          <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-line/30 dark:bg-ocean-950/40">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-ocean-950 dark:text-sand">Leaderboard</h3>
              <span className="text-xs text-muted">{leaderboard.length} ranked</span>
            </div>
            {leaderboard.length === 0 ? (
              <p className="text-sm text-muted">Solve a challenge to appear on the board.</p>
            ) : (
              <ul className="space-y-2">
                {leaderboard.map((entry) => {
                  const isMe = entry.user_id === me?.user_id;
                  return (
                    <li
                      key={entry.user_id}
                      className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${
                        isMe
                          ? "border-coral/40 bg-coral/10 dark:border-coral/30 dark:bg-coral/10"
                          : "border-line bg-cream dark:border-line/30 dark:bg-ocean-950/50"
                      }`}
                    >
                      <span className="w-8 text-center text-sm font-bold">{rankBadge(entry.rank)}</span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-ink dark:text-sand">
                          {entry.display_name}
                          {isMe ? <span className="ml-1 text-xs text-coral">You</span> : null}
                        </p>
                        <p className="text-xs text-muted">{entry.challenges_solved} solved</p>
                      </div>
                      <span className="text-sm font-bold text-ocean-800 dark:text-reef">{entry.practice_xp} XP</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </aside>
      ) : null}
    </div>
  );
}
