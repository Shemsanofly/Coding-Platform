import { useEffect, useMemo } from "react";

export default function CourseFilterSelect({ courses = [], value, onChange, className = "" }) {
  const firstCourseId = courses[0]?.id ? String(courses[0].id) : "";
  const validCourseIds = useMemo(
    () => new Set(courses.map((course) => String(course.id))),
    [courses],
  );
  const selectedValue = value && validCourseIds.has(String(value)) ? String(value) : firstCourseId;

  useEffect(() => {
    if (selectedValue && selectedValue !== value) {
      onChange(selectedValue);
    }
  }, [onChange, selectedValue, value]);

  return (
    <label className={`flex flex-col gap-1 text-sm ${className}`}>
      <span className="font-medium text-ocean-800 dark:text-reef">Filter by course</span>
      <select
        value={selectedValue}
        onChange={(event) => onChange(event.target.value)}
        disabled={!courses.length}
        className="min-h-[44px] rounded-xl border border-line bg-white px-3 py-2 text-ink shadow-sm focus:border-ocean-600 focus:outline-none focus:ring-2 focus:ring-ocean-600/30 dark:border-line/40 dark:bg-ocean-950/50 dark:text-sand"
      >
        {courses.length ? (
          courses.map((course) => (
            <option key={course.id} value={String(course.id)}>
              {course.title}
            </option>
          ))
        ) : (
          <option value="">No courses available</option>
        )}
      </select>
    </label>
  );
}
