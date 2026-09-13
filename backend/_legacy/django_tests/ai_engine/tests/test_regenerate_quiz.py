"""Tests for admin quiz regeneration (manual + celery, mocked Gemini)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.services.quiz_persistence import persist_generated_questions, publish_quiz_questions
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict
from courses.models import Course, Lesson
from quizzes.models import Question, Quiz


def _regen_url(course_id, lesson_id):
    return f"/api/admin/courses/{course_id}/lessons/{lesson_id}/regenerate-quiz/"


@override_settings(AI_GENERATION_MODE="manual")
class ManualRegenerateQuizTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="regen-manual@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.other_admin = User.objects.create_user(
            email="other-admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="regen-student@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Regen Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="YT Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _seed_published_quiz(self):
        quiz = persist_generated_questions(
            self.lesson.pk, _full_payload_dict()["questions"], publish=False
        )
        publish_quiz_questions(quiz.pk)
        quiz.refresh_from_db()
        return quiz

    @patch("ai_engine.services.youtube_pipeline.generate_quiz_for_youtube_lesson")
    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_manual_regenerate_runs_synchronously(
        self, mock_transcript_cls, mock_gemini_cls, mock_generate
    ):
        self._seed_published_quiz()
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()
        mock_generate.return_value = self.lesson.pk

        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["queued"])
        self.assertTrue(response.data["success"])
        mock_generate.assert_called_once_with(self.lesson.pk)

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_manual_regenerate_replaces_old_questions(self, mock_transcript_cls, mock_gemini_cls):
        quiz = self._seed_published_quiz()
        old_ids = set(quiz.questions.values_list("id", flat=True))
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        new_payload = _full_payload_dict()
        new_payload["questions"][0]["question"] = "What is a Python module in OOP design?"
        mock_gemini_cls.return_value.generate_quiz.return_value = new_payload

        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        quiz.refresh_from_db()
        new_ids = set(quiz.questions.values_list("id", flat=True))
        self.assertEqual(quiz.questions.count(), 3)
        self.assertTrue(old_ids.isdisjoint(new_ids))
        self.assertTrue(quiz.questions.filter(stem__icontains="Python module").exists())

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_manual_regenerate_resets_approval_to_pending(
        self, mock_transcript_cls, mock_gemini_cls
    ):
        self._seed_published_quiz()
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["published_question_count"], 0)
        self.assertEqual(response.data["approval_status"], "pending_approval")
        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertFalse(quiz.questions.filter(is_published=True).exists())

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_manual_regenerate_clears_old_errors(self, mock_transcript_cls, mock_gemini_cls):
        quiz = persist_generated_questions(
            self.lesson.pk, _full_payload_dict()["questions"], publish=False
        )
        quiz.generation_status = Quiz.GenerationStatus.FAILED
        quiz.generation_error = "Previous failure"
        quiz.save(update_fields=["generation_status", "generation_error"])

        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertTrue(response.data["success"])
        quiz.refresh_from_db()
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)
        self.assertEqual(quiz.generation_error, "")

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_old_published_questions_do_not_remain(self, mock_transcript_cls, mock_gemini_cls):
        quiz = self._seed_published_quiz()
        self.assertEqual(quiz.questions.filter(is_published=True).count(), 3)
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        quiz.refresh_from_db()
        self.assertEqual(quiz.questions.count(), 3)
        self.assertEqual(quiz.questions.filter(is_published=True).count(), 0)
        self.assertEqual(quiz.questions.filter(is_published=False).count(), 3)

    def test_non_owner_admin_cannot_regenerate(self):
        self._seed_published_quiz()
        self.client.force_authenticate(self.other_admin)
        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_regenerate(self):
        self._seed_published_quiz()
        self.client.force_authenticate(self.student)
        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_youtube_lesson_cannot_regenerate(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title="Non YT",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="",
            order=1,
        )
        response = self.client.post(_regen_url(self.course.pk, lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(AI_GENERATION_MODE="celery")
class CeleryRegenerateQuizTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="regen-celery@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Celery Regen",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="YT",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_celery_regenerate_queues_task(self, mock_delay):
        mock_delay.return_value = MagicMock()
        quiz = persist_generated_questions(
            self.lesson.pk, _full_payload_dict()["questions"], publish=False
        )
        publish_quiz_questions(quiz.pk)

        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["queued"])
        mock_delay.assert_called_once_with(self.lesson.pk)
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 0)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_celery_regenerate_returns_queued_false_when_redis_unavailable(self, mock_delay):
        mock_delay.side_effect = ConnectionError("Error 10061 connecting to localhost:6379")
        response = self.client.post(_regen_url(self.course.pk, self.lesson.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["queued"])
        self.assertFalse(response.data["success"])
        self.assertIn("could not be queued", response.data["message"].lower())
