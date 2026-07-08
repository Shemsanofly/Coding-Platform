import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_admin_can_update_student():
    admin = User.objects.create_user(email="admin-students@example.com", password="pass", role="admin")
    student = User.objects.create_user(
        email="learner@example.com",
        password="pass",
        role="student",
        experience_level="beginner",
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"/api/admin/students/{student.id}/",
        {"email": "learner-updated@example.com", "experience_level": "intermediate"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["email"] == "learner-updated@example.com"
    assert response.data["learning_level"] == "intermediate"

    student.refresh_from_db()
    assert student.email == "learner-updated@example.com"
    assert student.experience_level == "intermediate"


@pytest.mark.django_db
def test_admin_can_deactivate_student():
    admin = User.objects.create_user(email="admin-deact@example.com", password="pass", role="admin")
    student = User.objects.create_user(email="deact@example.com", password="pass", role="student")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.delete(f"/api/admin/students/{student.id}/")

    assert response.status_code == 200
    assert response.data["is_active"] is False

    student.refresh_from_db()
    assert student.is_active is False


@pytest.mark.django_db
def test_admin_cannot_deactivate_self():
    admin = User.objects.create_user(email="admin-self@example.com", password="pass", role="admin")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.delete(f"/api/admin/students/{admin.id}/")

    assert response.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_non_admin_cannot_update_or_delete_student():
    admin = User.objects.create_user(email="admin-other@example.com", password="pass", role="admin")
    student = User.objects.create_user(email="protected@example.com", password="pass", role="student")
    other_student = User.objects.create_user(email="other@example.com", password="pass", role="student")
    client = APIClient()
    client.force_authenticate(other_student)

    patch_response = client.patch(
        f"/api/admin/students/{student.id}/",
        {"email": "hacked@example.com"},
        format="json",
    )
    delete_response = client.delete(f"/api/admin/students/{student.id}/")

    assert patch_response.status_code in (403, 401)
    assert delete_response.status_code in (403, 401)

    student.refresh_from_db()
    assert student.email == "protected@example.com"
    assert student.is_active is True
    assert admin.is_active is True


@pytest.mark.django_db
def test_admin_users_filter_by_weakness_level():
    from ai_engine.models import WeakTopic

    admin = User.objects.create_user(email="admin-filter@example.com", password="pass", role="admin")
    high_student = User.objects.create_user(
        email="high-weak@example.com",
        password="pass",
        role="student",
    )
    User.objects.create_user(email="low-weak@example.com", password="pass", role="student")
    WeakTopic.objects.create(
        user=high_student,
        topic_tag="arrays",
        weakness_level="HIGH",
        attempt_count=5,
        correct_count=1,
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get("/api/admin/users/", {"weakness_level": "HIGH"})

    assert response.status_code == 200
    emails = {row["email"] for row in response.data["results"]}
    assert emails == {"high-weak@example.com"}


@pytest.mark.django_db
def test_admin_can_purge_inactive_student():
    admin = User.objects.create_user(email="admin-purge@example.com", password="pass", role="admin")
    student = User.objects.create_user(
        email="purge-me@example.com",
        password="pass",
        role="student",
        is_active=False,
    )
    student_id = student.id
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(f"/api/admin/students/{student_id}/purge/")

    assert response.status_code == 200
    assert not User.objects.filter(pk=student_id).exists()


@pytest.mark.django_db
def test_admin_cannot_purge_active_student():
    admin = User.objects.create_user(email="admin-purge-block@example.com", password="pass", role="admin")
    student = User.objects.create_user(email="still-active@example.com", password="pass", role="student")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(f"/api/admin/students/{student.id}/purge/")

    assert response.status_code == 400
    assert User.objects.filter(pk=student.id).exists()
