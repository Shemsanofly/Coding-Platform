from django.urls import path

from playground.views import (
    PlaygroundChallengeView,
    PlaygroundGenerateChallengeView,
    PlaygroundLeaderboardView,
    PlaygroundSubmitView,
)

urlpatterns = [
    path("playground/challenge/", PlaygroundChallengeView.as_view(), name="playground-challenge"),
    path(
        "playground/challenge/generate/",
        PlaygroundGenerateChallengeView.as_view(),
        name="playground-generate-challenge",
    ),
    path(
        "playground/challenge/<int:challenge_id>/submit/",
        PlaygroundSubmitView.as_view(),
        name="playground-submit",
    ),
    path(
        "playground/leaderboard/",
        PlaygroundLeaderboardView.as_view(),
        name="playground-leaderboard",
    ),
]
