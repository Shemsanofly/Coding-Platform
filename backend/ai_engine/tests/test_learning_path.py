"""Learning path engine, API, and optional Gemini explanation (mocked)."""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import Recommendation, WeakTopic
from ai_engine.services.learning_path import (
    WEAKNESS_PRIORITY,
    generate_learning_path,
    generate_learning_path_explanation,
)
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress
from quizzes.models import Quiz, QuizResult


class LearningPathServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin-path@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-path@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Python OOP",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.lesson_classes = Lesson.objects.create(
            course=self.course,
            title="Classes",
            order=0,
            topic_tag="classes",
            tags=["classes", "oop"],
        )
        self.lesson_inheritance = Lesson.objects.create(
            course=self.course,
            title="Inheritance",
            order=1,
            topic_tag="inheritance",
            tags=["inheritance", "oop"],
        )
        self.lesson_done = Lesson.objects.create(
            course=self.course,
            title="Done Lesson",
            order=2,
            topic_tag="polymorphism",
            tags=["polymorphism"],
        )

    def _weak(self, tag, level, *, correct=1, attempts=5):
        return WeakTopic.objects.create(
            user=self.student,
            topic_tag=tag,
            weakness_level=level,
            attempt_count=attempts,
            correct_count=correct,
        )

    def test_orders_weak_topics_high_before_medium_before_low(self):
        self._weak("inheritance", "LOW", correct=3, attempts=5)
        self._weak("classes", "HIGH", correct=0, attempts=5)
        self._weak("loops", "MEDIUM", correct=2, attempts=5)

        payload = generate_learning_path(self.student.id)
        levels = [row["weakness_level"] for row in payload["weak_topics"]]
        self.assertEqual(levels, ["HIGH", "MEDIUM", "LOW"])

    def test_learning_path_prioritizes_high_weakness_lessons_first(self):
        self._weak("inheritance", "HIGH", correct=0, attempts=5)
        self._weak("classes", "MEDIUM", correct=2, attempts=5)

        payload = generate_learning_path(self.student.id)
        path = payload["learning_path"]
        self.assertGreaterEqual(len(path), 2)
        self.assertEqual(path[0]["lesson_title"], "Inheritance")
        self.assertEqual(path[0]["weakness_level"], "HIGH")
        self.assertEqual(path[0]["status"], "next")
        self.assertEqual(path[1]["lesson_title"], "Classes")

    def test_excludes_completed_lessons_from_path(self):
        self._weak("classes", "HIGH", correct=0, attempts=5)
        self._weak("inheritance", "MEDIUM", correct=1, attempts=5)

        LessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson_classes,
            completed_at=timezone.now(),
        )

        payload = generate_learning_path(self.student.id)
        lesson_ids = [row["lesson_id"] for row in payload["learning_path"]]
        self.assertNotIn(self.lesson_classes.id, lesson_ids)
        self.assertIn(self.lesson_inheritance.id, lesson_ids)

    def test_excludes_quiz_passed_lessons(self):
        self._weak("polymorphism", "HIGH", correct=0, attempts=5)
        quiz = Quiz.objects.create(
            lesson=self.lesson_done,
            passing_score=70,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        QuizResult.objects.create(
            user=self.student,
            quiz=quiz,
            score=85,
            answers=[0],
            taken_at=timezone.now(),
        )

        payload = generate_learning_path(self.student.id)
        lesson_ids = [row["lesson_id"] for row in payload["learning_path"]]
        self.assertNotIn(self.lesson_done.id, lesson_ids)

    def test_includes_active_recommendations(self):
        self._weak("classes", "HIGH", correct=0, attempts=5)
        Recommendation.objects.create(
            user=self.student,
            lesson=self.lesson_inheritance,
            reason="Video rebuild for inheritance.",
            weak_topic_tag="inheritance",
            status="active",
        )

        payload = generate_learning_path(self.student.id)
        rec_ids = [row["lesson_id"] for row in payload["recommended_lessons"]]
        self.assertIn(self.lesson_inheritance.id, rec_ids)

    @patch("ai_engine.services.learning_path.generate_learning_path_explanation")
    def test_optional_explanation_flag(self, mock_explain):
        mock_explain.return_value = "Focus on classes before inheritance."
        self._weak("classes", "HIGH", correct=0, attempts=5)

        payload = generate_learning_path(self.student.id, include_explanation=True)
        self.assertEqual(payload["explanation"], "Focus on classes before inheritance.")
        mock_explain.assert_called_once()

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_explanation_generation_mocked(self, mock_model_cls):
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.return_value = type(
            "R", (), {"text": "Focus on Classes before Inheritance because inheritance builds on classes."}
        )()

        with patch("ai_engine.services.learning_path.config", side_effect=lambda key, default="": "key" if key == "GEMINI_API_KEY" else default):
            text = generate_learning_path_explanation(
                [{"topic_tag": "classes", "weakness_level": "HIGH"}],
                [
                    {"step": 1, "lesson_title": "Classes", "weak_topic_tag": "classes"},
                    {"step": 2, "lesson_title": "Inheritance", "weak_topic_tag": "inheritance"},
                ],
            )
        self.assertIn("Classes", text)
        mock_model.generate_content.assert_called_once()


class LearningPathAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-api-path@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-api-path@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="API Path Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        Lesson.objects.create(
            course=self.course,
            title="Lesson A",
            order=0,
            topic_tag="topic_a",
            tags=["topic_a"],
        )
        WeakTopic.objects.create(
            user=self.student,
            topic_tag="topic_a",
            weakness_level="HIGH",
            attempt_count=5,
            correct_count=1,
        )
        self.url = reverse("learning-path")

    def test_student_gets_learning_path(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("weak_topics", response.data)
        self.assertIn("recommended_lessons", response.data)
        self.assertIn("learning_path", response.data)
        self.assertIn("progress", response.data)
        self.assertGreaterEqual(len(response.data["weak_topics"]), 1)

    def test_admin_forbidden(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_empty_learning_path_returns_safe_response(self):
        self.client.force_authenticate(user=self.student)
        WeakTopic.objects.filter(user=self.student).delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["weak_topics"], [])
        self.assertEqual(response.data["learning_path"], [])
        self.assertEqual(response.data["recommended_lessons"], [])
        self.assertIn("path_steps", response.data["progress"])
        self.assertEqual(response.data["progress"]["path_steps"], 0)
        self.assertIsNone(response.data["progress"]["next_lesson_id"])


class WeaknessPriorityConstantTests(TestCase):
    def test_priority_order_constant(self):
        self.assertLess(WEAKNESS_PRIORITY["HIGH"], WEAKNESS_PRIORITY["MEDIUM"])
        self.assertLess(WEAKNESS_PRIORITY["MEDIUM"], WEAKNESS_PRIORITY["LOW"])
