from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STUDENT_ACCESS
from playground.models import PlaygroundChallenge, PlaygroundSubmission
from playground.serializers import (
    PlaygroundChallengeSerializer,
    PlaygroundLeaderboardSerializer,
    PlaygroundSubmissionResultSerializer,
)
from playground.services.challenge_generator import generate_playground_challenge
from playground.services.code_runner import run_solution
from playground.services.leaderboard import build_playground_leaderboard


def _active_challenge(user):
    return (
        PlaygroundChallenge.objects.filter(
            user=user,
            status=PlaygroundChallenge.Status.ACTIVE,
        )
        .order_by("-created_at")
        .first()
    )


class PlaygroundChallengeView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        challenge = _active_challenge(request.user)
        if challenge is None:
            return Response({"challenge": None})
        return Response({"challenge": PlaygroundChallengeSerializer(challenge).data})


class PlaygroundGenerateChallengeView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request):
        PlaygroundChallenge.objects.filter(
            user=request.user,
            status=PlaygroundChallenge.Status.ACTIVE,
        ).update(status=PlaygroundChallenge.Status.ABANDONED)

        recent_titles = list(
            PlaygroundChallenge.objects.filter(user=request.user)
            .order_by("-created_at")
            .values_list("title", flat=True)[:8]
        )
        payload = generate_playground_challenge(
            experience_level=getattr(request.user, "experience_level", None),
            recent_titles=recent_titles,
        )
        challenge = PlaygroundChallenge.objects.create(
            user=request.user,
            title=payload["title"],
            description=payload["description"],
            difficulty=payload["difficulty"],
            starter_code=payload["starter_code"],
            test_cases=payload["test_cases"],
            xp_reward=payload["xp_reward"],
        )
        return Response(
            {"challenge": PlaygroundChallengeSerializer(challenge).data},
            status=status.HTTP_201_CREATED,
        )


class PlaygroundSubmitView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request, challenge_id):
        challenge = get_object_or_404(
            PlaygroundChallenge,
            pk=challenge_id,
            user=request.user,
        )
        if challenge.status == PlaygroundChallenge.Status.SOLVED:
            return Response(
                {"detail": "This challenge is already solved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = str(request.data.get("code", "")).strip()
        if not code:
            return Response({"detail": "Code is required."}, status=status.HTTP_400_BAD_REQUEST)

        passed, test_results = run_solution(code, challenge.test_cases)
        xp_earned = challenge.xp_reward if passed else 0
        PlaygroundSubmission.objects.create(
            challenge=challenge,
            user=request.user,
            code=code,
            passed=passed,
            test_results=test_results,
            xp_earned=xp_earned,
        )

        message = "All tests passed! XP earned." if passed else "Some tests failed. Keep trying!"
        if passed:
            challenge.status = PlaygroundChallenge.Status.SOLVED
            challenge.solved_at = timezone.now()
            challenge.save(update_fields=["status", "solved_at"])

        challenge.refresh_from_db()
        payload = {
            "passed": passed,
            "xp_earned": xp_earned,
            "test_results": test_results,
            "challenge": PlaygroundChallengeSerializer(challenge).data,
            "message": message,
        }
        return Response(PlaygroundSubmissionResultSerializer(payload).data)


class PlaygroundLeaderboardView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        payload = build_playground_leaderboard(current_user_id=request.user.id)
        return Response(PlaygroundLeaderboardSerializer(payload).data)
