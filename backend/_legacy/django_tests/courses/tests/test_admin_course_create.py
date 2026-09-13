import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from courses.models import Course

User = get_user_model()


@pytest.mark.django_db
def test_admin_can_create_course_with_draft_status():
    admin = User.objects.create_user(
        email="admin-create@example.com", password="pass", role="admin"
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/admin/courses/",
        {"title": "New Admin Course", "level": "beginner"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["id"]
    assert response.data["title"] == "New Admin Course"
    assert response.data["status"] == "draft"

    course = Course.objects.get(pk=response.data["id"])
    assert course.created_by_id == admin.id
    assert course.status == Course.Status.DRAFT


@pytest.mark.django_db
def test_student_cannot_create_course():
    student = User.objects.create_user(
        email="student-create@example.com", password="pass", role="student"
    )
    client = APIClient()
    client.force_authenticate(student)

    response = client.post(
        "/api/admin/courses/",
        {"title": "Blocked Course", "level": "beginner"},
        format="json",
    )

    assert response.status_code in (403, 401)
    assert Course.objects.filter(title="Blocked Course").count() == 0
