export function formatCourseLevel(level) {
  if (!level) return "Beginner";
  const text = String(level).replace(/_/g, " ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}
