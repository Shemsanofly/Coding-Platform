from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course
from progress.models import Enrollment


class StudentDashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-dashboard@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-dashboard@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            experience_level=User.ExperienceLevel.BEGINNER,
        )
        self.course = Course.objects.create(
            title="Intro Python",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        Enrollment.objects.create(user=self.student, course=self.course)

    def test_dashboard_returns_combined_payload(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("student-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("analytics", response.data)
        self.assertIn("enrollments", response.data)
        self.assertIn("learning_path", response.data)
        self.assertEqual(response.data["analytics"]["enrolled_course_count"], 1)
        self.assertEqual(len(response.data["enrollments"]), 1)
        self.assertEqual(response.data["enrollments"][0]["title"], "Intro Python")
        self.assertIn("learning_path", response.data["learning_path"])
        self.assertIn("progress", response.data["learning_path"])

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("student-dashboard"))
        self.assertEqual(response.status_code, 401)
