const colorMap = {
  blue: "border-ocean-200/40 bg-reef/60",
  green: "border-ocean-200/40 bg-reef/50",
  purple: "border-coral/20 bg-sand",
  amber: "border-spice/30 bg-sand",
};

export default function StatCard({ label, value, color = "blue" }) {
  const palette = colorMap[color] || colorMap.blue;

  return (
    <article className={`rounded-2xl border p-4 shadow-panel ${palette}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-ocean-950">{value}</p>
    </article>
  );
}
