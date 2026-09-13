from django.urls import path

from progress.report_views import (
    AdminAIGenerationReportView,
    AdminCoursesReportView,
    AdminStudentsReportView,
    AdminSummaryReportView,
    AdminWeaknessesReportView,
    StudentLearningPathReportView,
    StudentProgressReportView,
    StudentQuizPerformanceReportView,
    StudentWeaknessesReportView,
)
from progress.views import (
    AdminCertificateRevokeView,
    AdminStudentDetailView,
    AdminStudentPurgeView,
    AdminUserProfileView,
    AdminUserQuizLogView,
    AdminUserRecommendationsView,
    AdminUsersView,
    AdminUserWeaknessesView,
    CertificateDetailView,
    CertificateDownloadView,
    EnrollmentListView,
    LessonWeaknessSummaryView,
    MyCertificatesView,
    PublicCertificateVerifyView,
    RecommendationListView,
    StudentAnalyticsSummaryView,
    StudentCourseCertificateEligibilityView,
    StudentCourseCertificateView,
    StudentDashboardView,
    StudentPracticeLeaderboardView,
    WeaknessListView,
)

urlpatterns = [
    path("dashboard/", StudentDashboardView.as_view(), name="student-dashboard"),
    path(
        "analytics/summary/",
        StudentAnalyticsSummaryView.as_view(),
        name="student-analytics-summary",
    ),
    path(
        "practice/leaderboard/",
        StudentPracticeLeaderboardView.as_view(),
        name="student-practice-leaderboard",
    ),
    path("enrollments/", EnrollmentListView.as_view(), name="enrollment-list"),
    path(
        "student/courses/<int:course_id>/certificate/eligibility/",
        StudentCourseCertificateEligibilityView.as_view(),
        name="student-course-certificate-eligibility",
    ),
    path(
        "student/courses/<int:course_id>/certificate/",
        StudentCourseCertificateView.as_view(),
        name="student-course-certificate",
    ),
    path("certificates/my-certificates/", MyCertificatesView.as_view(), name="my-certificates"),
    path(
        "certificates/<int:certificate_id>/",
        CertificateDetailView.as_view(),
        name="certificate-detail",
    ),
    path(
        "certificates/<int:certificate_id>/download/",
        CertificateDownloadView.as_view(),
        name="certificate-download",
    ),
    path(
        "certificates/verify/<str:verification_code>/",
        PublicCertificateVerifyView.as_view(),
        name="certificate-verify",
    ),
    path("weaknesses/", WeaknessListView.as_view(), name="weakness-list"),
    path(
        "student/lessons/<int:lesson_id>/weakness-summary/",
        LessonWeaknessSummaryView.as_view(),
        name="student-lesson-weakness-summary",
    ),
    path("recommendations/", RecommendationListView.as_view(), name="recommendation-list"),
    path("admin/users/", AdminUsersView.as_view(), name="admin-user-list"),
    path(
        "admin/students/<int:user_id>/",
        AdminStudentDetailView.as_view(),
        name="admin-student-detail",
    ),
    path(
        "admin/students/<int:user_id>/purge/",
        AdminStudentPurgeView.as_view(),
        name="admin-student-purge",
    ),
    path(
        "admin/users/<int:user_id>/profile/",
        AdminUserProfileView.as_view(),
        name="admin-user-profile",
    ),
    path(
        "admin/users/<int:user_id>/weaknesses/",
        AdminUserWeaknessesView.as_view(),
        name="admin-user-weaknesses",
    ),
    path(
        "admin/users/<int:user_id>/recommendations/",
        AdminUserRecommendationsView.as_view(),
        name="admin-user-recommendations",
    ),
    path(
        "admin/users/<int:user_id>/quiz-log/",
        AdminUserQuizLogView.as_view(),
        name="admin-user-quiz-log",
    ),
    path(
        "admin/certificates/<int:certificate_id>/revoke/",
        AdminCertificateRevokeView.as_view(),
        name="admin-certificate-revoke",
    ),
    path("admin/reports/summary/", AdminSummaryReportView.as_view(), name="admin-report-summary"),
    path("admin/reports/courses/", AdminCoursesReportView.as_view(), name="admin-report-courses"),
    path(
        "admin/reports/students/", AdminStudentsReportView.as_view(), name="admin-report-students"
    ),
    path(
        "admin/reports/weaknesses/",
        AdminWeaknessesReportView.as_view(),
        name="admin-report-weaknesses",
    ),
    path(
        "admin/reports/ai-generation/",
        AdminAIGenerationReportView.as_view(),
        name="admin-report-ai-generation",
    ),
    path(
        "reports/my-progress/", StudentProgressReportView.as_view(), name="student-report-progress"
    ),
    path(
        "reports/my-quiz-performance/",
        StudentQuizPerformanceReportView.as_view(),
        name="student-report-quiz",
    ),
    path(
        "reports/my-weaknesses/",
        StudentWeaknessesReportView.as_view(),
        name="student-report-weaknesses",
    ),
    path(
        "reports/my-learning-path/",
        StudentLearningPathReportView.as_view(),
        name="student-report-learning-path",
    ),
]
