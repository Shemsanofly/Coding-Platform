"""End-to-end test for generate_quiz_for_youtube_lesson (mocked Gemini + transcript)."""

from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from ai_engine.models import LessonAIProcessing
from ai_engine.services.youtube_pipeline import (
    bootstrap_youtube_processing,
    generate_quiz_for_youtube_lesson,
)
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict
from courses.models import Course, Lesson
from quizzes.models import Quiz


class GenerateQuizE2ETests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="e2e@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="E2E Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_full_pipeline_success(self, mock_transcript_cls, mock_gemini_cls):
        lesson = Lesson.objects.create(
            course=self.course,
            title="Python OOP",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        bootstrap_youtube_processing(lesson)

        mock_transcript_cls.return_value.extract.return_value = " ".join(["OOP lesson"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        result = generate_quiz_for_youtube_lesson(lesson.pk)

        self.assertEqual(result, lesson.pk)
        processing = LessonAIProcessing.objects.get(lesson=lesson)
        self.assertEqual(processing.status, LessonAIProcessing.Status.COMPLETED)
        quiz = Quiz.objects.get(lesson=lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)
        self.assertEqual(quiz.questions.count(), 3)
        lesson.refresh_from_db()
        self.assertIn("python_classes", lesson.tags)
        self.assertIn("object-oriented", lesson.content.lower())
        self.assertEqual(
            processing.analysis_json["key_concepts"],
            ["classes", "objects", "inheritance", "encapsulation"],
        )

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_pipeline_marks_failed_on_gemini_error(self, mock_transcript_cls, mock_gemini_cls):
        from ai_engine.services.gemini_service import GeminiQuizError

        lesson = Lesson.objects.create(
            course=self.course,
            title="Fail lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=1,
        )
        bootstrap_youtube_processing(lesson)
        mock_transcript_cls.return_value.extract.return_value = " ".join(["content"] * 80)
        mock_gemini_cls.return_value.generate_quiz.side_effect = GeminiQuizError("Invalid JSON")

        result = generate_quiz_for_youtube_lesson(lesson.pk)

        self.assertIsNone(result)
        quiz = Quiz.objects.get(lesson=lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.FAILED)
        self.assertIn("Invalid JSON", quiz.generation_error)
