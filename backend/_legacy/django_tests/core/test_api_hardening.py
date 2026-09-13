from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course
from progress.models import Enrollment


class PaginatedCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-paginate@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-paginate@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            experience_level=User.ExperienceLevel.BEGINNER,
        )
        for index in range(3):
            Course.objects.create(
                title=f"Course {index}",
                level=Course.Level.BEGINNER,
                status=Course.Status.PUBLISHED,
                created_by=self.admin,
            )

    def test_catalog_returns_paginated_envelope(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(
            reverse("student-course-catalog"), {"level": "all", "page_size": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])

    def test_catalog_v1_alias_matches_api(self):
        self.client.force_authenticate(user=self.student)
        legacy = self.client.get("/api/catalog/courses/", {"level": "all"})
        versioned = self.client.get("/api/v1/catalog/courses/", {"level": "all"})

        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(versioned.status_code, 200)
        self.assertEqual(legacy.data["count"], versioned.data["count"])
        self.assertEqual(
            [row["title"] for row in legacy.data["results"]],
            [row["title"] for row in versioned.data["results"]],
        )


class PaginatedEnrollmentsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-enroll@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-enroll@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        for index in range(2):
            course = Course.objects.create(
                title=f"Enrolled {index}",
                level=Course.Level.BEGINNER,
                status=Course.Status.PUBLISHED,
                created_by=self.admin,
            )
            Enrollment.objects.create(user=self.student, course=course)

    def test_enrollments_returns_paginated_envelope(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get("/api/enrollments/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)


class PaginatedAdminUsersTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-users-paginate@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        for index in range(25):
            User.objects.create_user(
                email=f"student-{index}@example.com",
                password="pass12345",
                role=User.Role.STUDENT,
            )

    def test_admin_users_paginated_by_default(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/users/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])


class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_validation_errors_use_consistent_envelope(self):
        response = self.client.post(
            "/auth/register/",
            {"email": "not-an-email", "password": "short", "role": "student"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Validation failed.")
        self.assertIn("errors", response.data)
        self.assertIn("email", response.data["errors"])
