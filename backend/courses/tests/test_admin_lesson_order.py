import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

from courses.models import Course, Lesson

User = get_user_model()


@pytest.fixture(autouse=True)
def _mock_youtube_pipeline():
    with (
        patch("ai_engine.services.youtube_pipeline.maybe_auto_enqueue_youtube_quiz"),
        patch("ai_engine.services.youtube_pipeline.bootstrap_youtube_processing"),
    ):
        yield

LESSON_PAYLOAD = {
    "title": "Test Lesson",
    "source_type": "youtube",
    "resource_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "content": "",
    "difficulty": "beginner",
    "estimated_minutes": 15,
    "tags": [],
    "learning_objective": "Learn something",
    "topic_tag": "test",
    "is_auto_generated": False,
}


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email="lesson-admin@example.com", password="pass", role="admin")


@pytest.fixture
def api_client(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


def _create_course(admin_user, title="Course"):
    return Course.objects.create(
        title=title,
        level=Course.Level.BEGINNER,
        status=Course.Status.DRAFT,
        created_by=admin_user,
    )


def _post_lesson(client, course_id, **extra):
    payload = {**LESSON_PAYLOAD, **extra}
    return client.post(f"/api/admin/courses/{course_id}/lessons/", payload, format="json")


@pytest.mark.django_db
def test_first_lesson_gets_order_one(api_client, admin_user):
    course = _create_course(admin_user, "Course A")
    response = _post_lesson(api_client, course.id)
    assert response.status_code == 201
    assert response.data["order"] == 1


@pytest.mark.django_db
def test_second_lesson_in_same_course_gets_order_two(api_client, admin_user):
    course = _create_course(admin_user, "Course A")
    _post_lesson(api_client, course.id, title="Lesson 1")
    response = _post_lesson(api_client, course.id, title="Lesson 2")
    assert response.status_code == 201
    assert response.data["order"] == 2
    orders = list(Lesson.objects.filter(course=course).order_by("order").values_list("order", flat=True))
    assert orders == [1, 2]


@pytest.mark.django_db
def test_first_lesson_in_another_course_gets_order_one(api_client, admin_user):
    course_a = _create_course(admin_user, "Course A")
    course_b = _create_course(admin_user, "Course B")
    _post_lesson(api_client, course_a.id, title="A1")
    _post_lesson(api_client, course_a.id, title="A2")
    response = _post_lesson(api_client, course_b.id, title="B1")
    assert response.status_code == 201
    assert response.data["order"] == 1
    assert Lesson.objects.filter(course=course_b).count() == 1


@pytest.mark.django_db
def test_client_sent_order_ignored_on_create(api_client, admin_user):
    course = _create_course(admin_user)
    response = _post_lesson(api_client, course.id, order=99)
    assert response.status_code == 201
    assert response.data["order"] == 1
    assert Lesson.objects.get(course=course).order == 1


@pytest.mark.django_db
def test_duplicate_order_update_rejected(api_client, admin_user):
    course = _create_course(admin_user)
    first = _post_lesson(api_client, course.id, title="First")
    second = _post_lesson(api_client, course.id, title="Second")
    lesson_one_id = first.data["id"]
    response = api_client.patch(
        f"/api/admin/courses/{course.id}/lessons/{second.data['id']}/",
        {"order": 1},
        format="json",
    )
    assert response.status_code == 400
    assert "order" in response.data
    assert Lesson.objects.get(pk=lesson_one_id).order == 1


@pytest.mark.django_db
def test_same_order_allowed_in_different_course(api_client, admin_user):
    course_a = _create_course(admin_user, "Course A")
    course_b = _create_course(admin_user, "Course B")
    lesson_a = _post_lesson(api_client, course_a.id)
    lesson_b = _post_lesson(api_client, course_b.id)
    assert lesson_a.data["order"] == 1
    assert lesson_b.data["order"] == 1


@pytest.mark.django_db
def test_lesson_list_only_returns_selected_course(api_client, admin_user):
    course_a = _create_course(admin_user, "Course A")
    course_b = _create_course(admin_user, "Course B")
    _post_lesson(api_client, course_a.id, title="Only A")
    _post_lesson(api_client, course_b.id, title="Only B")

    response_a = api_client.get(f"/api/admin/courses/{course_a.id}/lessons/")
    response_b = api_client.get(f"/api/admin/courses/{course_b.id}/lessons/")

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    titles_a = {row["title"] for row in response_a.data}
    titles_b = {row["title"] for row in response_b.data}
    assert titles_a == {"Only A"}
    assert titles_b == {"Only B"}
