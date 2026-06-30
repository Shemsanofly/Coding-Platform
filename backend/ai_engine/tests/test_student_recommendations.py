"""Student weakness and recommendation API presentation fields."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import Recommendation, WeakTopic
from courses.models import Course, Lesson
from progress.models import Enrollment


class StudentWeaknessRecommendationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-rec@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-rec@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Java Basics",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Introduction to Java",
            order=0,
            topic_tag="java_compilation",
            tags=["java_compilation", "java"],
        )
        WeakTopic.objects.create(
            user=self.student,
            topic_tag="java_compilation",
            weakness_level="HIGH",
            attempt_count=5,
            correct_count=1,
        )
        Recommendation.objects.create(
            user=self.student,
            lesson=self.lesson,
            reason="Targets weak area 'java_compilation'.",
            weak_topic_tag="java_compilation",
            status="active",
        )
        self.weakness_url = reverse("weakness-list")
        self.recommendation_url = reverse("recommendation-list")

    def test_weakness_endpoint_returns_accuracy_data(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.weakness_url)
        self.assertEqual(response.status_code, 200)
        topics = response.data["topics"] if isinstance(response.data, dict) else response.data
        self.assertGreaterEqual(len(topics), 1)
        row = topics[0]
        self.assertEqual(row["topic_tag"], "java_compilation")
        self.assertEqual(row["attempt_count"], 5)
        self.assertEqual(row["correct_count"], 1)
        self.assertEqual(row["accuracy_percent"], 20.0)

    def test_recommendations_include_weak_topic_tag(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.recommendation_url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        row = next(item for item in response.data if item["lesson_id"] == self.lesson.id)
        self.assertEqual(row["weak_topic_tag"], "java_compilation")
        self.assertEqual(row["weakness_level"], "HIGH")
        self.assertEqual(row["accuracy_percent"], 20.0)
        self.assertEqual(row["attempt_count"], 5)
        self.assertEqual(row["correct_count"], 1)
