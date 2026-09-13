"""Tests for PDF report generation endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from ai_engine.models import WeakTopic
from courses.models import Course, Lesson
from progress.models import Enrollment
from quizzes.models import Quiz, QuizResult

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email="admin-report@example.com", password="pass", role="admin")


@pytest.fixture
def student_user(db):
    return User.objects.create_user(
        email="student-report@example.com",
        password="pass",
        role="student",
        experience_level="beginner",
    )


@pytest.fixture
def course_with_data(admin_user, student_user):
    course = Course.objects.create(
        title="Report Course",
        level=Course.Level.BEGINNER,
        status=Course.Status.PUBLISHED,
        created_by=admin_user,
    )
    lesson = Lesson.objects.create(
        course=course,
        title="Lesson A",
        source_type=Lesson.SourceType.YOUTUBE,
        resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        order=0,
        topic_tag="python_basics",
    )
    quiz = Quiz.objects.create(lesson=lesson, generation_status=Quiz.GenerationStatus.DONE)
    Enrollment.objects.create(user=student_user, course=course)
    QuizResult.objects.create(
        user=student_user, quiz=quiz, score=75, answers=[0], taken_at=timezone.now()
    )
    WeakTopic.objects.create(
        user=student_user,
        topic_tag="python_basics",
        attempt_count=2,
        correct_count=1,
        weakness_level="MEDIUM",
    )
    return course


@pytest.mark.django_db
def test_admin_summary_report_requires_admin(admin_user, student_user, course_with_data):
    client = APIClient()
    client.force_authenticate(student_user)
    response = client.get("/api/admin/reports/summary/")
    assert response.status_code == 403

    client.force_authenticate(admin_user)
    response = client.get("/api/admin/reports/summary/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


@pytest.mark.django_db
def test_admin_courses_report_invalid_course(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    response = client.get("/api/admin/reports/courses/?course_id=99999")
    assert response.status_code == 404
    assert "Invalid course id" in response.data["detail"]


@pytest.mark.django_db
def test_admin_students_report_invalid_student(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    response = client.get("/api/admin/reports/students/?student_id=99999")
    assert response.status_code == 404
    assert "Invalid student id" in response.data["detail"]


@pytest.mark.django_db
def test_student_progress_report_own_data_only(admin_user, student_user, course_with_data):
    client = APIClient()
    client.force_authenticate(admin_user)
    response = client.get("/api/reports/my-progress/")
    assert response.status_code == 403

    client.force_authenticate(student_user)
    response = client.get("/api/reports/my-progress/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


@pytest.mark.django_db
def test_student_quiz_report_no_data(student_user):
    client = APIClient()
    client.force_authenticate(student_user)
    response = client.get("/api/reports/my-quiz-performance/")
    assert response.status_code == 404
    assert "No quiz performance data" in response.data["detail"]


@pytest.mark.django_db
def test_admin_ai_generation_report(admin_user, course_with_data):
    client = APIClient()
    client.force_authenticate(admin_user)
    response = client.get("/api/admin/reports/ai-generation/")
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"
