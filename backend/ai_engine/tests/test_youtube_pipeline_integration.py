from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.models import User
from ai_engine.models import LessonAIProcessing
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict
from ai_engine.services.youtube_pipeline import bootstrap_youtube_processing, is_youtube_lesson
from courses.models import Course, Lesson
from quizzes.models import Question, Quiz


class YouTubePipelineIntegrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="AI Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )

    def test_is_youtube_lesson(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title="Video",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        self.assertTrue(is_youtube_lesson(lesson))

    def test_bootstrap_creates_quiz_and_processing(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title="Video",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        bootstrap_youtube_processing(lesson)
        self.assertTrue(Quiz.objects.filter(lesson=lesson).exists())
        self.assertTrue(LessonAIProcessing.objects.filter(lesson=lesson).exists())

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_process_video_lesson_persists_questions(
        self, mock_transcript_cls, mock_gemini_cls
    ):
        lesson = Lesson.objects.create(
            course=self.course,
            title="OOP Video",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        bootstrap_youtube_processing(lesson)

        mock_transcript_cls.return_value.extract.return_value = " ".join(["education"] * 120)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        from ai_engine.services.youtube_pipeline import generate_quiz_for_youtube_lesson

        generate_quiz_for_youtube_lesson(lesson.pk)

        processing = LessonAIProcessing.objects.get(lesson=lesson)
        self.assertEqual(processing.status, LessonAIProcessing.Status.COMPLETED)
        quiz = Quiz.objects.get(lesson=lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)
        self.assertEqual(quiz.questions.count(), 3)
        self.assertFalse(quiz.questions.filter(is_published=True).exists())
