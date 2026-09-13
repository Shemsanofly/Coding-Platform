from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User


class StudentAISupportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            email="student-support@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            experience_level=User.ExperienceLevel.BEGINNER,
        )
        self.admin = User.objects.create_user(
            email="admin-support@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.url = reverse("student-ai-support")

    @patch("ai_engine.views.GeminiService")
    def test_student_can_ask_ai_support(self, mock_service_cls):
        mock_service_cls.return_value.generate_student_support_response.return_value = (
            "Try breaking the problem into input, process, and output steps."
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.url,
            {
                "question": "How do I solve a Python loop problem?",
                "history": [{"role": "student", "content": "I am stuck."}],
                "page_path": "/lessons/1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.data)
        mock_service_cls.return_value.generate_student_support_response.assert_called_once()

    def test_rejects_blank_question(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url, {"question": "   "}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Ask a question first.")

    def test_admin_forbidden(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.url, {"question": "Help?"}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_denied(self):
        response = self.client.post(self.url, {"question": "Help?"}, format="json")

        self.assertEqual(response.status_code, 401)
