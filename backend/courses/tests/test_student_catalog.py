from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course
from progress.models import Enrollment


class StudentCourseCatalogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-catalog@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-catalog@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            experience_level=User.ExperienceLevel.BEGINNER,
        )
        self.beginner_course = Course.objects.create(
            title="Beginner Python",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.advanced_course = Course.objects.create(
            title="Advanced Python",
            level=Course.Level.ADVANCED,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.draft_course = Course.objects.create(
            title="Draft Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )

    def test_catalog_filters_by_student_level_by_default(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("student-course-catalog"))

        self.assertEqual(response.status_code, 200)
        titles = [row["title"] for row in response.data]
        self.assertEqual(titles, ["Beginner Python"])

    def test_catalog_level_all_returns_visible_courses(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("student-course-catalog"), {"level": "all"})

        self.assertEqual(response.status_code, 200)
        titles = sorted(row["title"] for row in response.data)
        self.assertEqual(titles, ["Advanced Python", "Beginner Python"])

    def test_catalog_keeps_enrolled_courses_when_level_differs(self):
        Enrollment.objects.create(user=self.student, course=self.advanced_course)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("student-course-catalog"))

        self.assertEqual(response.status_code, 200)
        titles = sorted(row["title"] for row in response.data)
        self.assertEqual(titles, ["Advanced Python", "Beginner Python"])

    def test_catalog_explicit_level_filter(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("student-course-catalog"), {"level": "advanced"})

        self.assertEqual(response.status_code, 200)
        titles = [row["title"] for row in response.data]
        self.assertEqual(titles, ["Advanced Python"])
