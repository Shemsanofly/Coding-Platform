import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthProvider";
import { getCourseCatalog, joinCourse } from "@/api/studentLearning";
import CourseCard from "@/student/components/CourseCard";
import EmptyState from "@/student/components/EmptyState";
import ErrorState from "@/shared/components/ErrorState";
import PageHeader from "@/shared/components/ui/PageHeader";
import Button from "@/shared/components/ui/Button";
import { formatCourseLevel } from "@/shared/components/course/CourseBadges";

const LEVEL_OPTIONS = [
  { value: "matched", label: "My level" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

function matchesSearch(course, query) {
  if (!query) return true;
  const text = `${course.title || ""} ${course.level || ""} ${course.status || ""}`.toLowerCase();
  return text.includes(query.toLowerCase());
}

export default function Catalog() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [joiningId, setJoiningId] = useState(null);
  const [levelFilter, setLevelFilter] = useState("matched");
  const [search, setSearch] = useState("");

  const catalogLevel = useMemo(() => {
    if (levelFilter === "matched") {
      return user?.experience_level || "beginner";
    }
    return levelFilter;
  }, [levelFilter, user?.experience_level]);

  const {
    data = [],
    isLoading,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["course-catalog", catalogLevel ?? "all"],
    queryFn: () => getCourseCatalog({ level: catalogLevel }),
  });

  const enrollMutation = useMutation({
    mutationFn: joinCourse,
    onSuccess: (_, courseId) => {
      toast.success("You are enrolled. Opening the course.", { id: "enroll-ok" });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
      queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["course-catalog"] });
      navigate(`/courses/${courseId}`);
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not enroll.", { id: "enroll-err" });
    },
    onSettled: () => setJoiningId(null),
  });

  const allCourses = useMemo(() => (Array.isArray(data) ? data : (data?.results ?? [])), [data]);
  const courses = useMemo(
    () => allCourses.filter((course) => matchesSearch(course, search.trim())),
    [allCourses, search],
  );
  const showSkeleton = isLoading || isPending;
  const enrolledCount = allCourses.filter((course) => course.is_enrolled).length;

  const subtitle = useMemo(() => {
    if (levelFilter === "matched" && user?.experience_level) {
      return `${formatCourseLevel(
        user.experience_level,
      )} courses matched to your profile. You can switch levels anytime.`;
    }
    return "Find a course, enroll, and continue directly into the lesson path.";
  }, [levelFilter, user?.experience_level]);

  return (
    <div className="space-y-5 p-4 md:p-6">
      <section className="rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#172433]/85">
        <PageHeader title="Course Catalog" subtitle={subtitle} />

        <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <label className="relative block">
            <span className="sr-only">Search courses</span>
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-muted">
              Search
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by course name, level, or status"
              className="lc-input pl-16"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            {LEVEL_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant={levelFilter === option.value ? "primary" : "ghost"}
                size="sm"
                onClick={() => setLevelFilter(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted dark:text-reef/75">
          <span>
            {allCourses.length} course{allCourses.length === 1 ? "" : "s"} available
          </span>
          <span>{enrolledCount} enrolled</span>
          {search.trim() ? <span>{courses.length} match search</span> : null}
        </div>
      </section>

      {showSkeleton ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="h-[220px] animate-pulse rounded-2xl bg-reef/50 dark:bg-ocean-950/60"
            />
          ))}
        </div>
      ) : null}

      {!showSkeleton && isError ? (
        <ErrorState message="Unable to load the catalog." onRetry={() => void refetch()} />
      ) : null}

      {!showSkeleton && !isError && courses.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {courses.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              enrolling={enrollMutation.isPending && joiningId === course.id}
              onOpen={(courseId) => navigate(`/courses/${courseId}`)}
              onEnroll={(courseId) => {
                setJoiningId(courseId);
                enrollMutation.mutate(courseId);
              }}
            />
          ))}
        </div>
      ) : null}

      {!showSkeleton && !isError && courses.length === 0 ? (
        <EmptyState
          title={search.trim() ? "No matching courses" : "No courses available"}
          message={
            search.trim()
              ? "Clear the search or switch to another level."
              : "Published courses will appear here once an admin creates content."
          }
        />
      ) : null}
    </div>
  );
}
