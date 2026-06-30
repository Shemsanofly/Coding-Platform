"""Tests for AI_GENERATION_MODE=manual (no Celery/Redis required)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import LessonAIProcessing
from ai_engine.services.youtube_pipeline import (
    generate_quiz_for_youtube_lesson,
    maybe_auto_enqueue_youtube_quiz,
    run_youtube_quiz_generation_sync,
)
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict
from courses.models import Course, Lesson
from courses.views import AdminLessonViewSet
from quizzes.models import Quiz


@override_settings(AI_GENERATION_MODE="manual")
class ManualModeLessonCreateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="manual-create@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Manual Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_lesson_create_does_not_enqueue_celery(self, mock_delay):
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/",
            {
                "title": "Manual YT",
                "source_type": "youtube",
                "resource_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "content": "",
                "difficulty": "beginner",
                "estimated_minutes": 20,
                "tags": [],
                "learning_objective": "Learn",
                "topic_tag": "yt",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_delay.assert_not_called()

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_lesson_create_leaves_quiz_pending(self, mock_delay):
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/",
            {
                "title": "Pending YT",
                "source_type": "youtube",
                "resource_url": "https://www.youtube.com/watch?v=abc123xyz12",
                "content": "",
                "difficulty": "beginner",
                "estimated_minutes": 20,
                "tags": [],
                "learning_objective": "Learn",
                "topic_tag": "yt",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz = Quiz.objects.get(lesson_id=response.data["id"])
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.PENDING)

    @patch("ai_engine.services.youtube_pipeline.maybe_auto_enqueue_youtube_quiz")
    @patch("ai_engine.services.youtube_pipeline.bootstrap_youtube_processing")
    def test_maybe_start_pipeline_skips_enqueue_in_manual(
        self, mock_bootstrap, mock_enqueue
    ):
        lesson = Lesson.objects.create(
            course=self.course,
            title="YT",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        AdminLessonViewSet()._maybe_start_youtube_pipeline(lesson)
        mock_bootstrap.assert_called_once_with(lesson)
        mock_enqueue.assert_called_once_with(lesson.pk)


@override_settings(AI_GENERATION_MODE="manual")
class ManualGenerateEndpointTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="manual-gen@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Gen Course",
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

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_generate_endpoint_calls_pipeline(self, mock_transcript_cls, mock_gemini_cls):
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/{self.lesson.pk}/generate-quiz/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_transcript_cls.return_value.extract.assert_called_once()
        mock_gemini_cls.return_value.generate_quiz.assert_called_once()
        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_generate_endpoint_returns_success_payload(self, mock_transcript_cls, mock_gemini_cls):
        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/{self.lesson.pk}/generate-quiz/"
        )

        self.assertTrue(response.data["success"])
        self.assertIn("successfully", response.data["message"].lower())

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_generate_endpoint_handles_failure_cleanly(
        self, mock_transcript_cls, mock_gemini_cls
    ):
        from ai_engine.services.gemini_service import GeminiQuizError

        mock_transcript_cls.return_value.extract.return_value = " ".join(["lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.side_effect = GeminiQuizError("Invalid JSON")

        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/{self.lesson.pk}/generate-quiz/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "AI quiz generation failed.")
        self.assertIn("Invalid JSON", response.data["error"])
        self.assertNotIn("Traceback", str(response.data))

    def test_run_sync_wrapper_delegates_to_pipeline(self):
        with patch(
            "ai_engine.services.youtube_pipeline.generate_quiz_for_youtube_lesson",
            return_value=self.lesson.pk,
        ) as mock_gen:
            result = run_youtube_quiz_generation_sync(self.lesson.pk)
        mock_gen.assert_called_once_with(self.lesson.pk)
        self.assertTrue(result["success"])

    def test_generate_quiz_function_unchanged(self):
        self.assertTrue(callable(generate_quiz_for_youtube_lesson))


@override_settings(AI_GENERATION_MODE="celery")
class CeleryModeEnqueueTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="celery-mode@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Celery Course",
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

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_maybe_auto_enqueue_calls_celery(self, mock_delay):
        mock_delay.return_value = MagicMock()
        self.assertTrue(maybe_auto_enqueue_youtube_quiz(self.lesson.pk))
        mock_delay.assert_called_once_with(self.lesson.pk)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_lesson_create_enqueues_in_celery_mode(self, mock_delay):
        client = APIClient()
        client.force_authenticate(self.admin)
        mock_delay.return_value = MagicMock()
        response = client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/",
            {
                "title": "Celery YT",
                "source_type": "youtube",
                "resource_url": "https://www.youtube.com/watch?v=xyz123abc45",
                "content": "",
                "difficulty": "beginner",
                "estimated_minutes": 20,
                "tags": [],
                "learning_objective": "Learn",
                "topic_tag": "yt",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_delay.assert_called_once()
