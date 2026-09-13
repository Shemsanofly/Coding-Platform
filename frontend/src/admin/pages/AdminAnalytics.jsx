import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAdminAnalyticsOverview } from "@/api/adminCourses";
import ErrorState from "@/admin/components/ErrorState";
import LoadingState from "@/admin/components/LoadingState";
import PageHeader from "@/shared/components/ui/PageHeader";
import Card from "@/shared/components/ui/Card";

const BUCKET_COLORS = ["#94a3b8", "#f59e0b", "#3b82f6", "#10b981"];

export default function AdminAnalytics() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-analytics-overview"],
    queryFn: getAdminAnalyticsOverview,
  });

  const completionData = useMemo(
    () =>
      (data?.course_completion_distribution || []).map((row, index) => ({
        name: `${row.bucket}%`,
        count: row.count,
        fill: BUCKET_COLORS[index % BUCKET_COLORS.length],
      })),
    [data],
  );

  const weakData = useMemo(
    () =>
      (data?.top_weak_topics || []).map((row) => ({
        name: row.topic_tag,
        students: row.student_count,
      })),
    [data],
  );

  const scoreData = useMemo(
    () =>
      (data?.avg_quiz_score_by_course || [])
        .filter((row) => row.avg_score != null)
        .map((row) => ({
          name:
            row.course_title?.length > 18 ? `${row.course_title.slice(0, 16)}…` : row.course_title,
          score: row.avg_score,
        })),
    [data],
  );

  const enrollmentData = useMemo(
    () =>
      (data?.enrollment_trend || []).map((row) => ({
        date: row.date
          ? new Date(row.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
          : "",
        count: row.count,
      })),
    [data],
  );

  const aiCounts = data?.ai_generation_counts || { success: 0, failed: 0, pending: 0 };

  if (isLoading) {
    return (
      <div className="p-4 md:p-6">
        <LoadingState label="Loading analytics…" rows={4} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState message="Could not load analytics." onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <PageHeader
        title="Learning analytics"
        subtitle="Completion, weaknesses, quiz performance, and AI pipeline health."
      />

      <div className="grid grid-cols-3 gap-3">
        <Card padding="sm" className="text-center">
          <p className="text-xs text-muted">AI success</p>
          <p className="mt-1 text-2xl font-bold text-ocean-700">{aiCounts.success ?? 0}</p>
        </Card>
        <Card padding="sm" className="text-center">
          <p className="text-xs text-muted">AI failed</p>
          <p className="mt-1 text-2xl font-bold text-red-600">{aiCounts.failed ?? 0}</p>
        </Card>
        <Card padding="sm" className="text-center">
          <p className="text-xs text-muted">AI in progress</p>
          <p className="mt-1 text-2xl font-bold text-ocean-600">{aiCounts.pending ?? 0}</p>
        </Card>
      </div>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard title="Course completion distribution" empty={!completionData.length}>
          <div className="h-52 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={completionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {completionData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Top weak topics (students affected)" empty={!weakData.length}>
          <div className="h-52 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weakData} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="students" fill="#6366f1" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Average quiz score by course" empty={!scoreData.length}>
          <div className="h-52 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => [`${value}%`, "Avg score"]} />
                <Bar dataKey="score" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Enrollment trend" empty={!enrollmentData.length}>
          <div className="h-52 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={enrollmentData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </section>
    </div>
  );
}

function ChartCard({ title, children, empty }) {
  return (
    <Card variant="subtle">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <div className="mt-4">
        {empty ? <p className="text-sm text-muted">Not enough data yet.</p> : children}
      </div>
    </Card>
  );
}
