import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import STUDENT_ACCESS
from ai_engine.models import LessonAIProcessing
from ai_engine.services.learning_path import generate_learning_path
from ai_engine.services.quiz_persistence import publish_quiz_questions
from ai_engine.services.generation_mode import get_ai_generation_mode, is_manual_mode
from ai_engine.services.youtube_pipeline import (
    MANUAL_PENDING_HINT,
    enqueue_video_processing,
    reset_youtube_lesson_for_regeneration,
    run_youtube_quiz_generation_sync,
    user_facing_generation_error,
)
from courses.models import Course, Lesson
from quizzes.models import Question, Quiz

logger = logging.getLogger(__name__)


def _quiz_generation_response(lesson: Lesson, result: dict) -> Response:
    quiz = Quiz.objects.filter(lesson=lesson).first()
    processing = LessonAIProcessing.objects.filter(lesson=lesson).first()
    published_count = (
        Question.objects.filter(quiz=quiz, is_published=True).count() if quiz else 0
    )
    payload = {
        **result,
        "lesson_id": lesson.id,
        "course_id": lesson.course_id,
        "ai_generation_mode": get_ai_generation_mode(),
        "quiz_generation_status": quiz.generation_status if quiz else "failed",
        "ai_processing_status": processing.status if processing else "pending",
        "generation_error": quiz.generation_error if quiz else "",
        "last_error": processing.last_error if processing else "",
        "question_count": Question.objects.filter(quiz=quiz).count() if quiz else 0,
        "published_question_count": published_count,
    }
    if (
        quiz
        and quiz.generation_status == Quiz.GenerationStatus.DONE
        and published_count == 0
    ):
        payload["approval_status"] = "pending_approval"
    return Response(payload, status=status.HTTP_200_OK)


class _AdminOnlyMixin:
    permission_classes = [IsAuthenticated]

    def _deny_if_not_admin(self, request):
        if not request.user.is_authenticated or request.user.role != User.Role.ADMIN:
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _admin_youtube_lesson(self, request, course_pk, lesson_pk):
        denied = self._deny_if_not_admin(request)
        if denied:
            return None, denied
        lesson = get_object_or_404(
            Lesson,
            pk=lesson_pk,
            course_id=course_pk,
            course__created_by=request.user,
        )
        if lesson.source_type != Lesson.SourceType.YOUTUBE or not (lesson.resource_url or "").strip():
            return None, Response(
                {"detail": "AI quiz generation is only supported for YouTube lessons."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return lesson, None


class AdminLessonProcessingStatusView(_AdminOnlyMixin, APIView):
    def get(self, request, course_pk, lesson_pk):
        denied = self._deny_if_not_admin(request)
        if denied:
            return denied
        lesson = get_object_or_404(
            Lesson,
            pk=lesson_pk,
            course_id=course_pk,
            course__created_by=request.user,
        )
        processing = LessonAIProcessing.objects.filter(lesson=lesson).first()
        quiz = Quiz.objects.filter(lesson=lesson).first()
        quiz_status = quiz.generation_status if quiz else "pending"
        mode = get_ai_generation_mode()
        payload = {
            "lesson_id": lesson.id,
            "ai_generation_mode": mode,
            "ai_processing_status": processing.status if processing else "pending",
            "last_error": processing.last_error if processing else "",
            "has_transcript": bool(processing and processing.transcript_text),
            "quiz_generation_status": quiz_status,
            "generation_error": quiz.generation_error if quiz else "",
            "question_count": Question.objects.filter(quiz=quiz).count() if quiz else 0,
            "published_question_count": (
                Question.objects.filter(quiz=quiz, is_published=True).count() if quiz else 0
            ),
        }
        if is_manual_mode() and quiz_status == Quiz.GenerationStatus.PENDING:
            payload["manual_hint"] = MANUAL_PENDING_HINT
        return Response(payload)


class AdminLessonQuizPreviewView(_AdminOnlyMixin, APIView):
    def get(self, request, course_pk, lesson_pk):
        denied = self._deny_if_not_admin(request)
        if denied:
            return denied
        lesson = get_object_or_404(
            Lesson,
            pk=lesson_pk,
            course_id=course_pk,
            course__created_by=request.user,
        )
        quiz = Quiz.objects.filter(lesson=lesson).first()
        if not quiz:
            return Response({"lesson_id": lesson.id, "questions": []})
        rows = quiz.questions.order_by("order", "pk")
        questions = [
            {
                "id": q.id,
                "order": q.order,
                "text": q.stem,
                "options": q.choices,
                "correct_index": q.correct_index,
                "topic_tag": q.topic_tag,
                "question_type": q.question_type or Question.QuestionType.MCQ,
                "difficulty": q.difficulty,
                "bloom_level": q.bloom_level,
                "explanation": q.explanation,
                "is_published": q.is_published,
            }
            for q in rows
        ]
        processing = LessonAIProcessing.objects.filter(lesson=lesson).first()
        intelligence = (processing.analysis_json if processing else None) or {}
        return Response(
            {
                "lesson_id": lesson.id,
                "quiz_id": quiz.id,
                "generation_status": quiz.generation_status,
                "summary": intelligence.get("summary") or (lesson.content or "").strip(),
                "learning_objectives": intelligence.get("learning_objectives") or [],
                "key_concepts": intelligence.get("key_concepts") or [],
                "topic_tags": intelligence.get("topic_tags") or list(lesson.tags or []),
                "questions": questions,
            }
        )


class AdminLessonGenerateQuizView(_AdminOnlyMixin, APIView):
    """Manual mode: run AI quiz generation synchronously (no Celery)."""

    def post(self, request, course_pk, lesson_pk):
        lesson, err = self._admin_youtube_lesson(request, course_pk, lesson_pk)
        if err:
            return err

        logger.info(
            "admin_generate_quiz course_id=%s lesson_id=%s admin=%s mode=%s",
            course_pk,
            lesson_pk,
            request.user.email,
            get_ai_generation_mode(),
        )
        # Do not call bootstrap here — it resets quiz to pending before sync runs.
        result = run_youtube_quiz_generation_sync(lesson.pk)
        return _quiz_generation_response(lesson, result)


class AdminLessonRegenerateQuizView(_AdminOnlyMixin, APIView):
    def post(self, request, course_pk, lesson_pk):
        lesson, err = self._admin_youtube_lesson(request, course_pk, lesson_pk)
        if err:
            return err

        if is_manual_mode():
            reset_youtube_lesson_for_regeneration(lesson.pk, for_async=False)
            result = run_youtube_quiz_generation_sync(lesson.pk)
            return _quiz_generation_response(lesson, {**result, "queued": False})

        reset_youtube_lesson_for_regeneration(lesson.pk, for_async=True)
        queued = enqueue_video_processing(lesson.pk)
        if queued:
            return Response(
                {
                    "queued": True,
                    "success": True,
                    "message": "AI quiz generation has started.",
                    "lesson_id": lesson.id,
                    "ai_generation_mode": get_ai_generation_mode(),
                    "quiz_generation_status": "pending",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        quiz = Quiz.objects.filter(lesson=lesson).first()
        error_msg = (quiz.generation_error if quiz else "") or (
            "AI generation could not be queued. Please start Redis/Celery and try again."
        )
        friendly = user_facing_generation_error(error_msg)
        return Response(
            {
                "queued": False,
                "success": False,
                "message": friendly,
                "error": friendly,
                "lesson_id": lesson.id,
                "ai_generation_mode": get_ai_generation_mode(),
                "quiz_generation_status": quiz.generation_status if quiz else "failed",
            },
            status=status.HTTP_200_OK,
        )


class AdminLessonApproveQuizView(_AdminOnlyMixin, APIView):
    def post(self, request, course_pk, lesson_pk):
        denied = self._deny_if_not_admin(request)
        if denied:
            return denied
        lesson = get_object_or_404(
            Lesson,
            pk=lesson_pk,
            course_id=course_pk,
            course__created_by=request.user,
        )
        quiz = Quiz.objects.filter(lesson=lesson).first()
        if not quiz or quiz.generation_status != Quiz.GenerationStatus.DONE:
            return Response(
                {"detail": "Quiz must be generated before approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        count = publish_quiz_questions(quiz.pk)
        if count == 0:
            return Response(
                {"detail": "No questions to publish."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "detail": "Quiz published.",
                "lesson_id": lesson.id,
                "published_question_count": count,
            }
        )


class LearningPathView(APIView):
    """Student-only personalized learning path from weaknesses and recommendations."""

    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from progress.models import Enrollment
        from progress.services.weakness_context import parse_course_id_param

        course_id = parse_course_id_param(request.query_params.get("course_id"))
        if course_id is not None and not Enrollment.objects.filter(
            user=request.user, course_id=course_id
        ).exists():
            return Response(
                {"detail": "You are not enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        include_explanation = request.query_params.get("explain", "").lower() in ("1", "true", "yes")
        payload = generate_learning_path(
            request.user.id,
            include_explanation=include_explanation,
            course_id=course_id,
        )
        return Response(payload)
