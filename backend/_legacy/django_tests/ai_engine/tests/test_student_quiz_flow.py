"""Student quiz API + WeakTopic trigger after submit (no live Gemini)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import Recommendation, WeakTopic
from ai_engine.services.quiz_persistence import persist_generated_questions, publish_quiz_questions
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress
from quizzes.models import Quiz


def _generated_rows():
    return [
        {
            "question": "What is encapsulation in OOP?",
            "type": "mcq",
            "difficulty": "easy",
            "bloom_level": "understand",
            "topic_tag": "encapsulation",
            "options": ["Hiding data", "A loop", "A file", "A socket"],
            "correct_answer": "Hiding data",
            "explanation": "Encapsulation bundles data with methods that operate on it.",
        },
        {
            "question": "Inheritance allows code reuse?",
            "type": "true_false",
            "difficulty": "medium",
            "bloom_level": "apply",
            "topic_tag": "inheritance",
            "options": ["True", "False"],
            "correct_answer": "True",
            "explanation": "Child classes inherit parent behavior.",
        },
        {
            "question": "Polymorphism enables many forms?",
            "type": "true_false",
            "difficulty": "easy",
            "bloom_level": "understand",
            "topic_tag": "polymorphism",
            "options": ["True", "False"],
            "correct_answer": "True",
            "explanation": "Polymorphism lets objects respond differently to the same call.",
        },
    ]


class StudentQuizFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-flow@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-flow@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Flow Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson 1",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
            tags=["encapsulation", "inheritance", "polymorphism"],
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)

    def _published_quiz(self):
        quiz = persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        publish_quiz_questions(quiz.pk)
        return quiz

    def _complete_study(self):
        return LessonProgress.objects.update_or_create(
            user=self.student,
            lesson=self.lesson,
            defaults={"seconds_engaged": 3600, "video_watch_pct": 100},
        )

    def test_student_cannot_fetch_unpublished_quiz(self):
        persist_generated_questions(self.lesson.pk, _generated_rows(), publish=False)
        self._complete_study()
        url = reverse("lesson-quiz", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_student_must_complete_study_before_fetching_published_quiz(self):
        self._published_quiz()
        url = reverse("lesson-quiz", kwargs={"lesson_id": self.lesson.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Study this lesson to 100% before taking the quiz."
        )

    def test_student_fetches_published_quiz_without_explanations(self):
        self._published_quiz()
        self._complete_study()
        url = reverse("lesson-quiz", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["questions"]), 3)
        for row in response.data["questions"]:
            self.assertIn("text", row)
            self.assertIn("options", row)
            self.assertNotIn("explanation", row)
            self.assertNotIn("correct_index", row)

    @override_settings(AI_GENERATION_MODE="celery")
    @patch("ai_engine.services.task_queue.safe_delay")
    def test_submit_triggers_weakness_detection(self, mock_safe_delay):
        mock_safe_delay.return_value = MagicMock()
        quiz = self._published_quiz()
        self._complete_study()
        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        answers = [q.correct_index for q in questions]

        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": answers}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["score"], 100)
        self.assertTrue(response.data["weakness_detection_triggered"])
        self.assertEqual(len(response.data["explanations"]), 3)
        mock_safe_delay.assert_called_once()


@override_settings(AI_GENERATION_MODE="manual")
class ManualModeQuizSubmitTests(StudentQuizFlowTests):
    def _wrong_answers(self, quiz):
        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        return [(q.correct_index + 1) % len(q.choices) for q in questions]

    def test_manual_submit_returns_weakness_detection_triggered_true(self):
        quiz = self._published_quiz()
        self._complete_study()
        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": self._wrong_answers(quiz)}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["weakness_detection_triggered"])

    def test_manual_submit_updates_weak_topic_immediately(self):
        quiz = self._published_quiz()
        self._complete_study()
        self.assertEqual(WeakTopic.objects.filter(user=self.student).count(), 0)

        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": self._wrong_answers(quiz)}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertGreater(WeakTopic.objects.filter(user=self.student).count(), 0)
        encapsulation = WeakTopic.objects.get(user=self.student, topic_tag="encapsulation")
        self.assertGreater(encapsulation.attempt_count, 0)

    def test_manual_submit_updates_recommendations_immediately(self):
        quiz = self._published_quiz()
        self._complete_study()
        self.assertEqual(Recommendation.objects.filter(user=self.student).count(), 0)

        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": self._wrong_answers(quiz)}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertGreater(Recommendation.objects.filter(user=self.student).count(), 0)

    def test_manual_submit_weakness_and_recommendation_apis_reflect_updates(self):
        quiz = self._published_quiz()
        self._complete_study()
        submit_url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        self.client.post(submit_url, {"answers": self._wrong_answers(quiz)}, format="json")

        weak_resp = self.client.get(reverse("weakness-list"))
        rec_resp = self.client.get(reverse("recommendation-list"))

        self.assertEqual(weak_resp.status_code, 200)
        weak_topics = (
            weak_resp.data.get("topics", weak_resp.data)
            if isinstance(weak_resp.data, dict)
            else weak_resp.data
        )
        self.assertGreater(len(weak_topics), 0)
        self.assertEqual(rec_resp.status_code, 200)
        self.assertGreater(len(rec_resp.data), 0)


@override_settings(AI_GENERATION_MODE="celery")
class CeleryModeQuizSubmitTests(StudentQuizFlowTests):
    @patch("ai_engine.services.task_queue.safe_delay")
    def test_celery_mode_enqueues_detect_weaknesses(self, mock_safe_delay):
        mock_safe_delay.return_value = MagicMock()
        quiz = self._published_quiz()
        self._complete_study()
        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        answers = [q.correct_index for q in questions]

        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": answers}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["weakness_detection_triggered"])
        mock_safe_delay.assert_called_once()

    @patch("ai_engine.services.task_queue.safe_delay")
    def test_celery_down_does_not_crash_quiz_submit(self, mock_safe_delay):
        mock_safe_delay.return_value = None
        quiz = self._published_quiz()
        self._complete_study()
        questions = list(quiz.questions.filter(is_published=True).order_by("order", "pk"))
        answers = [q.correct_index for q in questions]

        url = reverse("quiz-submit", kwargs={"quiz_id": quiz.pk})
        response = self.client.post(url, {"answers": answers}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["weakness_detection_triggered"])
