import { useNavigate } from "react-router-dom";
import Playground from "@/student/components/Playground";

export default function PlaygroundPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-4 p-4 md:space-y-6 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="lc-tag">Playground</p>
          <h1 className="text-2xl font-bold text-ocean-950 dark:text-sand">AI coding playground</h1>
          <p className="mt-1 text-sm text-muted">
            Gemini creates coding exercises. Pass all tests to earn XP and climb the leaderboard.
          </p>
        </div>
        <button type="button" onClick={() => navigate("/")} className="lc-btn-ghost">
          Back to dashboard
        </button>
      </header>
      <Playground />
    </div>
  );
}
