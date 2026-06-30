import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from courses.models import Course

User = get_user_model()


@pytest.mark.django_db
def test_admin_dashboard_summary_requires_admin():
    admin = User.objects.create_user(email="admin@example.com", password="pass", role="admin")
    student = User.objects.create_user(email="student@example.com", password="pass", role="student")
    client = APIClient()

    client.force_authenticate(student)
    response = client.get("/api/admin/courses/dashboard-summary/")
    assert response.status_code in (403, 401)

    client.force_authenticate(admin)
    Course.objects.create(
        title="Test Course",
        level="beginner",
        status=Course.Status.DRAFT,
        created_by=admin,
    )
    response = client.get("/api/admin/courses/dashboard-summary/")
    assert response.status_code == 200
    assert response.data["total_courses"] == 1
    assert "pending_quiz_approvals" in response.data
