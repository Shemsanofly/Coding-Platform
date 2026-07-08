from django.urls import include, path

urlpatterns = [
    path("", include("quizzes.urls")),
    path("", include("courses.urls")),
    path("", include("progress.urls")),
    path("", include("ai_engine.urls")),
    path("", include("playground.urls")),
]
