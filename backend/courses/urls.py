from django.urls import include, path
from rest_framework.routers import DefaultRouter

from courses.views import (
    AdminCourseViewSet,
    AdminLessonViewSet,
    StudentCourseCatalogView,
    StudentCourseDetailView,
    StudentEnrollmentView,
    StudentLessonDetailView,
    StudentLessonProgressView,
)
from courses.lesson_notes_views import (
    LessonDownloadNotesView,
    LessonGenerateNotesView,
    LessonNotesView,
    LessonViewNotesView,
)

router = DefaultRouter()
router.register(r"admin/courses", AdminCourseViewSet, basename="admin-course")

admin_lesson_list = AdminLessonViewSet.as_view({"get": "list", "post": "create"})
admin_lesson_detail = AdminLessonViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("", include(router.urls)),
    path("admin/courses/<int:course_pk>/lessons/", admin_lesson_list),
    path("admin/courses/<int:course_pk>/lessons/<int:pk>/", admin_lesson_detail),
    path("catalog/courses/", StudentCourseCatalogView.as_view(), name="student-course-catalog"),
    path("enrollments/join/", StudentEnrollmentView.as_view(), name="student-enrollment-join"),
    path("student/courses/<int:course_id>/", StudentCourseDetailView.as_view(), name="student-course-detail"),
    path("student/lessons/<int:lesson_id>/", StudentLessonDetailView.as_view(), name="student-lesson-detail"),
    path(
        "student/lessons/<int:lesson_id>/progress/",
        StudentLessonProgressView.as_view(),
        name="student-lesson-progress",
    ),
    path(
        "lessons/<int:lesson_id>/generate-notes/",
        LessonGenerateNotesView.as_view(),
        name="lesson-generate-notes",
    ),
    path(
        "lessons/<int:lesson_id>/notes/",
        LessonNotesView.as_view(),
        name="lesson-notes",
    ),
    path(
        "lessons/<int:lesson_id>/view-notes/",
        LessonViewNotesView.as_view(),
        name="lesson-view-notes",
    ),
    path(
        "lessons/<int:lesson_id>/download-notes/",
        LessonDownloadNotesView.as_view(),
        name="lesson-download-notes",
    ),
]
