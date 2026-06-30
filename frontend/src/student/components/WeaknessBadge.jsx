import SeverityBadge from "@/student/components/SeverityBadge";

export default function WeaknessBadge({ value, level }) {
  return <SeverityBadge value={value} level={level ?? value} />;
}
