"""Tests for safe Celery enqueue when Redis/Celery is unavailable."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import LessonAIProcessing
from ai_engine.services.youtube_pipeline import (
    QUEUE_UNAVAILABLE_MESSAGE,
    enqueue_video_processing,
    generate_quiz_for_youtube_lesson,
    mark_video_processing_queue_failed,
)
from courses.models import Course, Lesson
from quizzes.models import Quiz


class SafeDelayTests(TestCase):
    def test_safe_delay_returns_result_on_success(self):
        from ai_engine.services.task_queue import safe_delay

        task = MagicMock()
        task.name = "test.task"
        expected = MagicMock()
        task.delay.return_value = expected

        self.assertIs(safe_delay(task, 1, foo="bar"), expected)
        task.delay.assert_called_once_with(1, foo="bar")

    def test_safe_delay_returns_none_and_calls_on_failure(self):
        from ai_engine.services.task_queue import safe_delay

        task = MagicMock()
        task.name = "test.task"
        task.delay.side_effect = ConnectionError("Error 10061 connecting to localhost:6379")
        handler = MagicMock()

        self.assertIsNone(safe_delay(task, 9, on_failure=handler))
        handler.assert_called_once()
        self.assertIsInstance(handler.call_args[0][0], ConnectionError)


class RunOrEnqueueTests(TestCase):
    def test_manual_mode_runs_task_synchronously(self):
        from ai_engine.services.task_queue import run_or_enqueue

        task = MagicMock()
        task.run.return_value = None

        self.assertTrue(run_or_enqueue(task, 1, 2, mode="manual", foo="bar"))
        task.run.assert_called_once_with(1, 2, foo="bar")

    def test_manual_mode_falls_back_to_direct_call(self):
        from ai_engine.services.task_queue import run_or_enqueue

        task = MagicMock(spec=[])
        task.side_effect = lambda a, b: setattr(task, "called", (a, b))

        self.assertTrue(run_or_enqueue(task, 3, 4, mode="manual"))
        self.assertEqual(task.called, (3, 4))

    def test_manual_mode_returns_false_on_failure(self):
        from ai_engine.services.task_queue import run_or_enqueue

        task = MagicMock()
        task.run.side_effect = RuntimeError("boom")
        handler = MagicMock()

        self.assertFalse(run_or_enqueue(task, 1, mode="manual", on_failure=handler))
        handler.assert_called_once()

    def test_celery_mode_uses_safe_delay(self):
        from ai_engine.services.task_queue import run_or_enqueue

        task = MagicMock()
        task.name = "test.task"
        expected = MagicMock()

        with patch("ai_engine.services.task_queue.safe_delay", return_value=expected) as mock_safe:
            self.assertTrue(run_or_enqueue(task, 7, mode="celery"))

        mock_safe.assert_called_once_with(task, 7, on_failure=None)

    def test_celery_mode_returns_false_when_enqueue_fails(self):
        from ai_engine.services.task_queue import run_or_enqueue

        task = MagicMock()
        task.name = "test.task"

        with patch("ai_engine.services.task_queue.safe_delay", return_value=None):
            self.assertFalse(run_or_enqueue(task, 9, mode="celery"))


@override_settings(AI_GENERATION_MODE="celery")
class EnqueueVideoProcessingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="queue@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Queue Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="YouTube",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_enqueue_returns_true_when_celery_available(self, mock_delay):
        mock_delay.return_value = MagicMock()
        self.assertTrue(enqueue_video_processing(self.lesson.pk))
        mock_delay.assert_called_once_with(self.lesson.pk)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_enqueue_marks_failed_when_broker_unavailable(self, mock_delay):
        mock_delay.side_effect = ConnectionError("Error 10061 connecting to localhost:6379")

        self.assertFalse(enqueue_video_processing(self.lesson.pk))

        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.FAILED)
        self.assertEqual(quiz.generation_error, QUEUE_UNAVAILABLE_MESSAGE)

        processing = LessonAIProcessing.objects.get(lesson=self.lesson)
        self.assertEqual(processing.status, LessonAIProcessing.Status.FAILED)
        self.assertEqual(processing.last_error, QUEUE_UNAVAILABLE_MESSAGE)

    def test_mark_video_processing_queue_failed_sets_readable_message(self):
        mark_video_processing_queue_failed(self.lesson.pk, ConnectionError("redis down"))
        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertIn("could not be queued", quiz.generation_error.lower())
        self.assertIn("Regenerate Quiz", quiz.generation_error)

    def test_generate_quiz_function_unchanged(self):
        self.assertTrue(callable(generate_quiz_for_youtube_lesson))


@override_settings(AI_GENERATION_MODE="celery")
class LessonCreateQueueFailureTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="lesson-queue@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Create Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_lesson_create_succeeds_when_queue_works(self, mock_delay):
        mock_delay.return_value = MagicMock()
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/",
            {
                "title": "New YT",
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
        mock_delay.assert_called_once()

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_lesson_create_succeeds_when_queue_raises(self, mock_delay):
        mock_delay.side_effect = ConnectionError("Error 10061 connecting to localhost:6379")
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/",
            {
                "title": "New YT Fail",
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
        lesson_id = response.data["id"]
        quiz = Quiz.objects.get(lesson_id=lesson_id)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.FAILED)
        self.assertEqual(quiz.generation_error, QUEUE_UNAVAILABLE_MESSAGE)


@override_settings(AI_GENERATION_MODE="celery")
class RegenerateQuizQueueTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="regen@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Regen Course",
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
    def test_regenerate_returns_queued_true_when_available(self, mock_delay):
        mock_delay.return_value = MagicMock()
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/{self.lesson.pk}/regenerate-quiz/"
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["queued"])
        self.assertIn("started", response.data["message"].lower())

    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_regenerate_returns_clean_response_when_queue_fails(self, mock_delay):
        mock_delay.side_effect = ConnectionError("Error 10061 connecting to localhost:6379")
        response = self.client.post(
            f"/api/admin/courses/{self.course.pk}/lessons/{self.lesson.pk}/regenerate-quiz/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["queued"])
        self.assertIn("could not be queued", response.data["message"].lower())
        self.assertIn("Redis/Celery", response.data["message"])


class SyncFallbackTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="sync@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Sync Course",
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

    @override_settings(AI_GENERATION_MODE="celery", AI_GENERATION_SYNC_FALLBACK=True)
    @patch("ai_engine.services.youtube_pipeline.generate_quiz_for_youtube_lesson")
    @patch("ai_engine.tasks.process_video_lesson.delay")
    def test_sync_fallback_runs_when_queue_unavailable(self, mock_delay, mock_generate):
        mock_delay.side_effect = ConnectionError("redis down")
        self.assertTrue(enqueue_video_processing(self.lesson.pk))
        mock_generate.assert_called_once_with(self.lesson.pk)
