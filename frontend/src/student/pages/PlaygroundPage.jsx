import { useNavigate } from "react-router-dom";
import Playground from "@/student/components/Playground";
import PageHeader from "@/shared/components/ui/PageHeader";
import Button from "@/shared/components/ui/Button";

export default function PlaygroundPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-4 p-4 md:space-y-6 md:p-6">
      <PageHeader
        title="AI coding playground"
        subtitle="Gemini creates coding exercises. Pass all tests to earn XP and climb the leaderboard."
        actions={
          <Button variant="ghost" onClick={() => navigate("/")}>
            Back to dashboard
          </Button>
        }
      />
      <Playground />
    </div>
  );
}
