import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import AuthGuard from "@/shared/components/AuthGuard";
import GuestGuard from "@/shared/components/GuestGuard";
import RoleGuard from "@/shared/components/RoleGuard";

const StudentLayout = lazy(() => import("@/shared/components/StudentLayout"));
const AdminLayout = lazy(() => import("@/shared/components/AdminLayout"));
const Login = lazy(() => import("@/shared/pages/Login"));
const Register = lazy(() => import("@/shared/pages/Register"));
const NotFound = lazy(() => import("@/shared/pages/NotFound"));
const PlaygroundPage = lazy(() => import("@/student/pages/PlaygroundPage"));
const Dashboard = lazy(() => import("@/student/pages/Dashboard"));
const Weakness = lazy(() => import("@/student/pages/Weakness"));
const Recommendations = lazy(() => import("@/student/pages/Recommendations"));
const LearningPath = lazy(() => import("@/student/pages/LearningPath"));
const CourseDetail = lazy(() => import("@/student/pages/CourseDetail"));
const Catalog = lazy(() => import("@/student/pages/Catalog"));
const LessonDetail = lazy(() => import("@/student/pages/LessonDetail"));
const Quiz = lazy(() => import("@/student/pages/Quiz"));
const QuizResult = lazy(() => import("@/student/pages/QuizResult"));
const StudentAnalytics = lazy(() => import("@/student/pages/Analytics"));
const Profile = lazy(() => import("@/student/pages/Profile"));
const MyCertificates = lazy(() => import("@/student/pages/MyCertificates"));
const ProfileSettings = lazy(() => import("@/shared/pages/ProfileSettings"));
const CertificateVerification = lazy(() => import("@/shared/pages/CertificateVerification"));
const AdminReports = lazy(() => import("@/admin/pages/AdminReports"));
const AdminDashboard = lazy(() => import("@/admin/pages/AdminDashboard"));
const AdminAnalytics = lazy(() => import("@/admin/pages/AdminAnalytics"));
const CourseList = lazy(() => import("@/admin/pages/CourseList"));
const CourseSetup = lazy(() => import("@/admin/pages/CourseSetup"));
const UserList = lazy(() => import("@/admin/pages/UserList"));
const UserProfile = lazy(() => import("@/admin/pages/UserProfile"));

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ocean-950 px-4 text-sand">
      <p className="text-sm">Loading interface...</p>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        {/* Public-only routes: logged-in users are redirected away by GuestGuard. */}
        <Route element={<GuestGuard />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        <Route path="/verify-certificate" element={<CertificateVerification />} />
        <Route path="/verify-certificate/:verificationCode" element={<CertificateVerification />} />

        {/* Protected app routes: authentication is required below this boundary. */}
        <Route element={<AuthGuard />}>
          {/* Student experience routes — admins are redirected to the admin dashboard. */}
          <Route element={<RoleGuard allowedRoles={["student"]} redirectTo="/admin/dashboard" />}>
            <Route element={<StudentLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/weakness" element={<Weakness />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/learning-path" element={<LearningPath />} />
            <Route path="/analytics" element={<StudentAnalytics />} />
            <Route path="/certificates" element={<MyCertificates />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<ProfileSettings />} />
            <Route path="/courses/:courseId" element={<CourseDetail />} />
            <Route path="/lessons/:lessonId" element={<LessonDetail />} />
            <Route path="/lessons/:lessonId/quiz" element={<Quiz />} />
            <Route path="/lessons/:lessonId/quiz/result" element={<QuizResult />} />
            </Route>
          </Route>

          {/* Admin-only section, enforced centrally via role guard. */}
          <Route element={<RoleGuard allowedRoles={["admin"]} redirectTo="/" />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/analytics" element={<AdminAnalytics />} />
              <Route path="/admin/reports" element={<AdminReports />} />
              <Route path="/admin/courses" element={<CourseList />} />
              <Route path="/admin/courses/new" element={<CourseSetup />} />
              <Route path="/admin/courses/:courseId/setup" element={<CourseSetup />} />
              <Route path="/admin/users" element={<UserList />} />
              <Route path="/admin/users/:id" element={<UserProfile />} />
              <Route
                path="/admin/settings"
                element={
                  <ProfileSettings
                    heading="Account settings"
                    description="Update your name and profile photo for the admin console."
                  />
                }
              />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>

  );
}
