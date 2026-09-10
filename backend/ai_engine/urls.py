from django.urls import path

from ai_engine.views import (
    AdminLessonApproveQuizView,
    AdminLessonGenerateQuizView,
    AdminLessonProcessingStatusView,
    AdminLessonQuizPreviewView,
    AdminLessonRegenerateQuizView,
    LearningPathView,
    StudentAISupportView,
)

urlpatterns = [
    path("learning-path/", LearningPathView.as_view(), name="learning-path"),
    path("student/ai-support/", StudentAISupportView.as_view(), name="student-ai-support"),
    path(
        "admin/courses/<int:course_pk>/lessons/<int:lesson_pk>/processing-status/",
        AdminLessonProcessingStatusView.as_view(),
        name="admin-lesson-processing-status",
    ),
    path(
        "admin/courses/<int:course_pk>/lessons/<int:lesson_pk>/quiz-preview/",
        AdminLessonQuizPreviewView.as_view(),
        name="admin-lesson-quiz-preview",
    ),
    path(
        "admin/courses/<int:course_pk>/lessons/<int:lesson_pk>/generate-quiz/",
        AdminLessonGenerateQuizView.as_view(),
        name="admin-lesson-generate-quiz",
    ),
    path(
        "admin/courses/<int:course_pk>/lessons/<int:lesson_pk>/regenerate-quiz/",
        AdminLessonRegenerateQuizView.as_view(),
        name="admin-lesson-regenerate-quiz",
    ),
    path(
        "admin/courses/<int:course_pk>/lessons/<int:lesson_pk>/approve-quiz/",
        AdminLessonApproveQuizView.as_view(),
        name="admin-lesson-approve-quiz",
    ),
]
