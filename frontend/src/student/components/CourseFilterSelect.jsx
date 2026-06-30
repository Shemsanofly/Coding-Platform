export default function CourseFilterSelect({ courses, value, onChange, className = "" }) {
  return (
    <label className={`flex flex-col gap-1 text-sm ${className}`}>
      <span className="font-medium text-ocean-800 dark:text-reef">Filter by course</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-[44px] rounded-xl border border-line bg-white px-3 py-2 text-ink shadow-sm focus:border-ocean-600 focus:outline-none focus:ring-2 focus:ring-ocean-600/30 dark:border-line/40 dark:bg-ocean-950/50 dark:text-sand"
      >
        <option value="">All courses</option>
        {courses.map((course) => (
          <option key={course.id} value={String(course.id)}>
            {course.title}
          </option>
        ))}
      </select>
    </label>
  );
}
