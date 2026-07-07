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
import Card from "@/shared/components/ui/Card";
import Button from "@/shared/components/ui/Button";

const LEVEL_OPTIONS = [
  { value: "matched", label: "My level" },
  { value: "all", label: "All levels" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

function formatLevel(level) {
  if (!level) return null;
  const text = String(level).replace(/_/g, " ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

export default function Catalog() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [joiningId, setJoiningId] = useState(null);
  const [levelFilter, setLevelFilter] = useState("matched");

  const catalogLevel = useMemo(() => {
    if (levelFilter === "matched") {
      return user?.experience_level || undefined;
    }
    if (levelFilter === "all") {
      return "all";
    }
    return levelFilter;
  }, [levelFilter, user?.experience_level]);

  const { data = [], isLoading, isPending, isError, refetch } = useQuery({
    queryKey: ["course-catalog", catalogLevel ?? "default"],
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

  const items = useMemo(() => (Array.isArray(data) ? data : data?.results ?? []), [data]);
  const showSkeleton = isLoading || isPending;

  const subtitle = useMemo(() => {
    if (levelFilter === "all") {
      return "Browse all published courses and enroll to unlock lessons, quizzes, and your personalized study plan.";
    }
    if (levelFilter === "matched" && user?.experience_level) {
      return `Showing ${formatLevel(user.experience_level)} courses matched to your learning level. Enrolled courses always stay visible.`;
    }
    return "Browse published courses and enroll to unlock lessons, quizzes, and your personalized study plan.";
  }, [levelFilter, user?.experience_level]);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <Card variant="elevated">
        <PageHeader
          title="Course catalog"
          subtitle={subtitle}
          actions={
            <div className="flex flex-wrap gap-2">
              {LEVEL_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  variant={levelFilter === option.value ? "gradient" : "ghost"}
                  size="sm"
                  onClick={() => setLevelFilter(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          }
        />
      </Card>

      {showSkeleton ? (
        <div className="space-y-3" aria-busy="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-2xl bg-reef/50 dark:bg-ocean-950/60" />
          ))}
        </div>
      ) : null}

      {!showSkeleton && isError ? (
        <ErrorState message="Unable to load the catalog." onRetry={() => void refetch()} />
      ) : null}

      {!showSkeleton && !isError && items.length > 0 ? (
        <ul className="space-y-3">
          {items.map((course) => (
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
        </ul>
      ) : null}

      {!showSkeleton && !isError && items.length === 0 ? (
        <EmptyState
          title="No courses available"
          message={
            levelFilter === "matched"
              ? "No published courses match your learning level yet. Try showing all levels."
              : "Published courses will appear here once an admin creates content."
          }
        />
      ) : null}
    </div>
  );
}
