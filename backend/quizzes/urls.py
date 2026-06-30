from django.urls import path

from quizzes.views import LessonQuizView, QuizSubmitView

urlpatterns = [
    path(
        "lessons/<int:lesson_id>/quiz/",
        LessonQuizView.as_view(),
        name="lesson-quiz",
    ),
    path(
        "quizzes/<int:quiz_id>/submit/",
        QuizSubmitView.as_view(),
        name="quiz-submit",
    ),
]
