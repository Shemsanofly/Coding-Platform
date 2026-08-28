"""Quiz generation flow tests from the quizzes app perspective (mocked AI)."""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import LessonAIProcessing, WeakTopic
from ai_engine.services.quiz_persistence import persist_generated_questions, publish_quiz_questions
from ai_engine.services.youtube_pipeline import bootstrap_youtube_processing, generate_quiz_for_youtube_lesson
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress
from quizzes.models import Question, Quiz


def _generated_rows():
    return _full_payload_dict()["questions"]


class TranscriptGeminiQuizFlowTests(TestCase):
    """End-to-end quiz generation with mocked TranscriptService and GeminiService."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email="quiz-admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="quiz-student@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Quiz Flow Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="OOP Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        bootstrap_youtube_processing(self.lesson)
        Enrollment.objects.create(user=self.student, course=self.course)
        self.client = APIClient()

    @patch("ai_engine.services.youtube_pipeline.GeminiService")
    @patch("ai_engine.services.youtube_pipeline.TranscriptService")
    def test_transcript_and_gemini_mock_success(self, mock_transcript_cls, mock_gemini_cls):
        mock_transcript_cls.return_value.extract.return_value = " ".join(["OOP content"] * 80)
        mock_gemini_cls.return_value.generate_quiz.return_value = _full_payload_dict()

        result = generate_quiz_for_youtube_lesson(self.lesson.pk)
        self.assertEqual(result, self.lesson.pk)

        processing = LessonAIProcessing.objects.get(lesson=self.lesson)
        self.assertEqual(processing.status, LessonAIProcessing.Status.COMPLETED)
        self.assertTrue(processing.transcript_text)

        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)
        self.assertEqual(quiz.questions.count(), 3)

    def test_quiz_persistence_and_question_fields(self):
        quiz = persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        question = quiz.questions.order_by("order").first()
        self.assertFalse(question.is_published)
        self.assertEqual(question.question_type, Question.QuestionType.MCQ)
        self.assertEqual(question.correct_index, 0)
        self.assertEqual(question.topic_tag, "python_classes")
        self.assertEqual(len(question.choices), 4)

    def test_correct_index_and_topic_tag_mapping(self):
        rows = _generated_rows()
        quiz = persist_generated_questions(self.lesson.pk, rows, publish=False)
        by_tag = {q.topic_tag: q for q in quiz.questions.all()}
        self.assertIn("python_classes", by_tag)
        self.assertIn("inheritance", by_tag)
        self.assertIn("encapsulation", by_tag)
        self.assertEqual(by_tag["inheritance"].correct_index, 0)

    def test_quiz_approval_publishes_questions(self):
        quiz = persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        self.assertEqual(quiz.questions.filter(is_published=True).count(), 0)

        self.client.force_authenticate(user=self.admin)
        url = reverse(
            "admin-lesson-approve-quiz",
            kwargs={"course_pk": self.course.pk, "lesson_pk": self.lesson.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        quiz.refresh_from_db()
        self.assertEqual(quiz.questions.filter(is_published=True).count(), 3)

    def test_student_fetches_approved_quiz(self):
        quiz = persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        publish_quiz_questions(quiz.pk)
        LessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson,
            seconds_engaged=3600,
            video_watch_pct=100,
        )

        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-quiz", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["questions"]), 3)

    @override_settings(AI_GENERATION_MODE="manual")
    def test_quiz_submit_updates_weak_topic_in_manual_mode(self):
        quiz = persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        publish_quiz_questions(quiz.pk)
        LessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson,
            seconds_engaged=3600,
            video_watch_pct=100,
        )
        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        wrong_answers = [(q.correct_index + 1) % len(q.choices) for q in questions]

        self.client.force_authenticate(user=self.student)
        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": wrong_answers}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["weakness_detection_triggered"])
        self.assertGreater(WeakTopic.objects.filter(user=self.student).count(), 0)
