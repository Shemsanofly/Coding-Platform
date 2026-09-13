"""Weak topic and recommendation context APIs."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import Recommendation, WeakTopic
from courses.models import Course, Lesson
from progress.models import Enrollment
from quizzes.models import Question, Quiz, QuizResult


class WeaknessContextAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-weak-ctx@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-weak-ctx@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            email="other-weak-ctx@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.java_course = Course.objects.create(
            title="Java Programming",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.python_course = Course.objects.create(
            title="Python Basics",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        Enrollment.objects.create(user=self.student, course=self.java_course)
        Enrollment.objects.create(user=self.student, course=self.python_course)

        self.intro_lesson = Lesson.objects.create(
            course=self.java_course,
            title="Introduction to Variables",
            order=0,
            topic_tag="java_variables",
            tags=["java_variables", "data_types"],
        )
        self.practice_lesson = Lesson.objects.create(
            course=self.java_course,
            title="Java Variables Practice",
            order=1,
            topic_tag="java_variables",
            tags=["java_variables"],
        )
        self.python_lesson = Lesson.objects.create(
            course=self.python_course,
            title="Python Loops",
            order=0,
            topic_tag="python_loops",
            tags=["python_loops"],
        )

        self.intro_quiz = Quiz.objects.create(
            lesson=self.intro_lesson, generation_status=Quiz.GenerationStatus.DONE
        )
        Question.objects.create(
            quiz=self.intro_quiz,
            order=0,
            stem="What is a variable?",
            choices=["Storage", "Loop", "Class", "Module"],
            correct_index=0,
            topic_tag="java_variables",
        )
        Question.objects.create(
            quiz=self.intro_quiz,
            order=1,
            stem="What is int?",
            choices=["Integer type", "String", "Boolean", "List"],
            correct_index=0,
            topic_tag="data_types",
        )
        QuizResult.objects.create(
            user=self.student,
            quiz=self.intro_quiz,
            score=44,
            answers=[1, 1],
            taken_at=timezone.now(),
        )

        WeakTopic.objects.create(
            user=self.student,
            topic_tag="java_variables",
            weakness_level="HIGH",
            attempt_count=5,
            correct_count=1,
        )
        WeakTopic.objects.create(
            user=self.student,
            topic_tag="python_loops",
            weakness_level="MEDIUM",
            attempt_count=4,
            correct_count=2,
        )
        Recommendation.objects.create(
            user=self.student,
            lesson=self.practice_lesson,
            reason="Beginner-friendly material because recent quiz scores are low.",
            weak_topic_tag="java_variables",
            status="active",
        )

        self.weakness_url = reverse("weakness-list")
        self.recommendation_url = reverse("recommendation-list")
        self.summary_url = reverse(
            "student-lesson-weakness-summary", kwargs={"lesson_id": self.intro_lesson.id}
        )

    def test_weakness_api_includes_course_context(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.weakness_url)
        self.assertEqual(response.status_code, 200)
        row = next(
            item for item in response.data["topics"] if item["topic_tag"] == "java_variables"
        )
        self.assertEqual(row["courses"][0]["title"], "Java Programming")
        self.assertEqual(row["courses"][0]["id"], self.java_course.id)

    def test_weakness_api_includes_recent_lesson_context(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.weakness_url)
        row = next(
            item for item in response.data["topics"] if item["topic_tag"] == "java_variables"
        )
        self.assertEqual(row["recent_lessons"][0]["title"], "Introduction to Variables")
        self.assertEqual(row["recent_lessons"][0]["course_title"], "Java Programming")

    def test_weakness_api_filters_by_course(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.weakness_url, {"course_id": self.java_course.id})
        self.assertEqual(response.status_code, 200)
        tags = {row["topic_tag"] for row in response.data["topics"]}
        self.assertIn("java_variables", tags)
        self.assertNotIn("python_loops", tags)

    def test_recommendation_api_filters_by_course(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.recommendation_url, {"course_id": self.java_course.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(row["course_id"] == self.java_course.id for row in response.data))

    def test_recommendation_api_includes_weakness_level(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.recommendation_url)
        row = next(item for item in response.data if item["lesson_id"] == self.practice_lesson.id)
        self.assertEqual(row["weakness_level"], "HIGH")
        self.assertEqual(row["accuracy_percent"], 20.0)

    def test_recommendation_api_includes_related_lesson_taken(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.recommendation_url)
        row = next(item for item in response.data if item["lesson_id"] == self.practice_lesson.id)
        self.assertEqual(row["related_lessons_taken"][0]["title"], "Introduction to Variables")
        self.assertIn("Introduction to Variables", row["reason"])

    def test_student_cannot_filter_by_unenrolled_course(self):
        unenrolled = Course.objects.create(
            title="Hidden Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.client.force_authenticate(user=self.student)
        weakness_response = self.client.get(self.weakness_url, {"course_id": unenrolled.id})
        self.assertEqual(weakness_response.status_code, 403)
        recommendation_response = self.client.get(
            self.recommendation_url, {"course_id": unenrolled.id}
        )
        self.assertEqual(recommendation_response.status_code, 403)

    def test_lesson_weakness_summary_returns_lesson_topics(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["quiz_taken"])
        self.assertEqual(response.data["score"], 44)
        tags = {row["topic_tag"] for row in response.data["weak_topics"]}
        self.assertIn("java_variables", tags)
        self.assertIn("data_types", tags)

    def test_lesson_weakness_summary_without_quiz_returns_message(self):
        self.client.force_authenticate(user=self.student)
        url = reverse(
            "student-lesson-weakness-summary", kwargs={"lesson_id": self.practice_lesson.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["quiz_taken"])
        self.assertIn("Take the quiz", response.data["message"])
