import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STUDENT_ACCESS
from ai_engine.services.generation_mode import get_ai_generation_mode
from ai_engine.services.task_queue import run_or_enqueue
from ai_engine.tasks import detect_weaknesses
from courses.services import lesson_unlocked
from progress.models import Enrollment, LessonProgress
from progress.services import engagement_met, refresh_lesson_official_completion
from progress.services.certificates import maybe_generate_certificate_for_lesson
from quizzes.models import Quiz, QuizResult

logger = logging.getLogger(__name__)


def _study_completed_for_lesson(user, lesson) -> bool:
    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    return bool(progress and (progress.completed_at or engagement_met(lesson, progress)))


class LessonQuizView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request, lesson_id):
        try:
            quiz = Quiz.objects.select_related("lesson__course").get(
                lesson_id=lesson_id,
                generation_status=Quiz.GenerationStatus.DONE,
            )
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not available for this lesson."},
                status=status.HTTP_404_NOT_FOUND,
            )

        course = quiz.lesson.course
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "You are not enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not lesson_unlocked(course, request.user, quiz.lesson):
            return Response(
                {"detail": "This lesson is locked until prior quizzes are completed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not _study_completed_for_lesson(request.user, quiz.lesson):
            return Response(
                {"detail": "Study this lesson to 100% before taking the quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        published = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        if not published:
            return Response(
                {"detail": "Quiz not available for this lesson."},
                status=status.HTTP_404_NOT_FOUND,
            )
        questions = [
            {
                "id": question.id,
                "text": question.stem,
                "options": question.choices,
                "question_type": question.question_type or "mcq",
            }
            for question in published
        ]
        return Response(
            {
                "id": quiz.id,
                "quiz_id": quiz.id,
                "lesson_id": quiz.lesson_id,
                "quiz_generation_status": quiz.generation_status,
                "questions": questions,
            }
        )


class QuizSubmitView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request, quiz_id):
        try:
            quiz = Quiz.objects.select_related("lesson__course").get(pk=quiz_id)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        course = quiz.lesson.course
        if not Enrollment.objects.filter(
            user=request.user,
            course=course,
        ).exists():
            return Response(
                {"detail": "You are not enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not lesson_unlocked(course, request.user, quiz.lesson):
            return Response(
                {"detail": "This lesson is locked until prior quizzes are completed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not _study_completed_for_lesson(request.user, quiz.lesson):
            return Response(
                {"detail": "Study this lesson to 100% before submitting the quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        raw_answers = request.data.get("answers")
        if not isinstance(raw_answers, list):
            return Response(
                {"detail": "answers must be a list of integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            answers = [int(a) for a in raw_answers]
        except (TypeError, ValueError):
            return Response(
                {"detail": "answers must be a list of integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        total = len(questions)
        if total == 0:
            return Response(
                {"detail": "This quiz has no questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(answers) != total:
            return Response(
                {
                    "detail": f"Expected {total} answer(s) (one per question), "
                    f"got {len(answers)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        correct_count = sum(1 for i, q in enumerate(questions) if answers[i] == q.correct_index)
        score = round((correct_count / total) * 100)
        passed = score >= quiz.passing_score

        logger.info(
            "QuizSubmit quiz_id=%s question_count=%s answers=%s score=%s correct=%s",
            quiz_id,
            total,
            answers,
            score,
            correct_count,
        )

        result = QuizResult.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            answers=answers,
            taken_at=timezone.now(),
        )
        refresh_lesson_official_completion(request.user.pk, quiz.lesson_id)
        maybe_generate_certificate_for_lesson(request.user, quiz.lesson_id)
        weakness_detection_triggered = run_or_enqueue(
            detect_weaknesses,
            request.user.pk,
            result.pk,
            mode=get_ai_generation_mode(),
        )

        explanations = [
            {
                "question_id": q.id,
                "explanation": q.explanation or "",
                "topic_tag": q.topic_tag,
            }
            for q in questions
        ]
        return Response(
            {
                "score": score,
                "correct": correct_count,
                "total": total,
                "passed": passed,
                "weakness_detection_triggered": weakness_detection_triggered,
                "explanations": explanations,
            },
            status=status.HTTP_200_OK,
        )
