from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress
from quizzes.models import Question, Quiz, QuizResult


@override_settings(MEDIA_ROOT="/tmp/learncode-test-media")
class CertificateFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="certificate-admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            first_name="Ada",
            last_name="Admin",
        )
        self.student = User.objects.create_user(
            email="certificate-student@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="Grace",
            last_name="Hopper",
        )
        self.other_student = User.objects.create_user(
            email="certificate-other@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="Other",
            last_name="Student",
        )
        self.course = Course.objects.create(
            title="Certificate Python",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.lesson_one = Lesson.objects.create(
            course=self.course,
            title="Foundations",
            source_type=Lesson.SourceType.INTERNAL,
            content="Intro",
            order=1,
            estimated_minutes=1,
        )
        self.lesson_two = Lesson.objects.create(
            course=self.course,
            title="Final Assessment",
            source_type=Lesson.SourceType.INTERNAL,
            content="Final",
            order=2,
            estimated_minutes=1,
        )
        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        Enrollment.objects.create(user=self.other_student, course=self.course)
        self.quiz_one = self._quiz(self.lesson_one, passing_score=60)
        self.final_quiz = self._quiz(self.lesson_two, passing_score=70)

    def _quiz(self, lesson, passing_score=60):
        quiz = Quiz.objects.create(
            lesson=lesson,
            passing_score=passing_score,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        Question.objects.create(
            quiz=quiz,
            order=1,
            stem=f"{lesson.title} question",
            choices=["A", "B"],
            correct_index=0,
            topic_tag="certificate",
            is_published=True,
        )
        return quiz

    def _result(self, quiz, score, user=None):
        return QuizResult.objects.create(
            user=user or self.student,
            quiz=quiz,
            score=score,
            answers=[0],
            taken_at=timezone.now(),
        )

    def _complete_lesson(self, lesson, user=None):
        return LessonProgress.objects.create(
            user=user or self.student,
            lesson=lesson,
            seconds_engaged=60,
            completed_at=timezone.now(),
        )

    def _make_eligible(self):
        self._result(self.quiz_one, 100)
        self._result(self.final_quiz, 80)
        self._complete_lesson(self.lesson_one)
        self._complete_lesson(self.lesson_two)

    def test_incomplete_lessons_are_not_eligible(self):
        self._result(self.quiz_one, 100)
        self._result(self.final_quiz, 85)
        self._complete_lesson(self.lesson_one)
        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            reverse("student-course-certificate-eligibility", kwargs={"course_id": self.course.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["eligible"])
        self.assertIn("Complete all required lessons.", response.data["reasons"])

    def test_failed_final_assessment_is_not_eligible(self):
        self._result(self.quiz_one, 100)
        self._result(self.final_quiz, 60)
        self._complete_lesson(self.lesson_one)
        self._complete_lesson(self.lesson_two)
        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            reverse("student-course-certificate-eligibility", kwargs={"course_id": self.course.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["eligible"])
        self.assertIn("Pass the final assessment.", response.data["reasons"])

    def test_eligible_student_can_generate_certificate_for_course_with_no_assignments(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["student_name"], "Grace Hopper")
        self.assertEqual(response.data["course_title"], "Certificate Python")
        self.assertTrue(response.data["certificate_number"])
        self.assertTrue(response.data["verification_code"])
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.COMPLETED)
        self.assertIsNotNone(self.enrollment.completed_at)

    def test_duplicate_generation_returns_existing_certificate(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        first = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        second = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_one_student_cannot_download_another_students_certificate(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        self.client.force_authenticate(user=self.other_student)

        response = self.client.get(
            reverse("certificate-download", kwargs={"certificate_id": created.data["id"]})
        )

        self.assertEqual(response.status_code, 403)

    def test_public_verification_exposes_safe_certificate_data(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("certificate-verify", kwargs={"verification_code": created.data["verification_code"]})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["student_name"], "Grace Hopper")
        self.assertEqual(response.data["course_title"], "Certificate Python")
        self.assertEqual(response.data["certificate_status"], "ACTIVE")
        self.assertNotIn("student_id", response.data)

    def test_admin_can_revoke_certificate(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse("admin-certificate-revoke", kwargs={"certificate_id": created.data["id"]})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "REVOKED")
