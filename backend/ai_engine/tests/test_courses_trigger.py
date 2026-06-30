"""Verify courses app only enqueues ai_engine — no Gemini logic in courses."""

from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from courses.models import Course, Lesson
from courses.views import AdminLessonViewSet


class CoursesYouTubeTriggerTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="trigger@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Trigger Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )

    @patch("ai_engine.services.youtube_pipeline.maybe_auto_enqueue_youtube_quiz")
    @patch("ai_engine.services.youtube_pipeline.bootstrap_youtube_processing")
    def test_maybe_start_youtube_pipeline_enqueues_ai_engine(
        self, mock_bootstrap, mock_enqueue
    ):
        lesson = Lesson.objects.create(
            course=self.course,
            title="YouTube Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        view = AdminLessonViewSet()
        view._maybe_start_youtube_pipeline(lesson)

        mock_bootstrap.assert_called_once_with(lesson)
        mock_enqueue.assert_called_once_with(lesson.pk)

    @patch("ai_engine.services.youtube_pipeline.maybe_auto_enqueue_youtube_quiz")
    @patch("ai_engine.services.youtube_pipeline.bootstrap_youtube_processing")
    def test_non_youtube_lesson_skips_pipeline(self, mock_bootstrap, mock_enqueue):
        lesson = Lesson.objects.create(
            course=self.course,
            title="No URL",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="",
            order=1,
        )
        AdminLessonViewSet()._maybe_start_youtube_pipeline(lesson)

        mock_bootstrap.assert_not_called()
        mock_enqueue.assert_not_called()

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_enqueue_video_processing_calls_celery_task(self, mock_delay):
        from django.test import override_settings

        from ai_engine.services.youtube_pipeline import enqueue_video_processing

        mock_delay.return_value = object()
        with override_settings(AI_GENERATION_MODE="celery"):
            self.assertTrue(enqueue_video_processing(42))
        mock_delay.assert_called_once_with(42)
