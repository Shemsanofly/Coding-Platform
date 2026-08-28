import re
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course, Lesson
from progress.models import Certificate, Enrollment, LessonProgress
from progress.services.certificates import certificate_qr_svg, format_certificate_date, official_person_name
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

    def test_study_completion_reaches_100_percent_before_final_quiz_for_certificate(self):
        course = Course.objects.create(
            title="Single Lesson Certificate",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        lesson = Lesson.objects.create(
            course=course,
            title="Final Lesson",
            source_type=Lesson.SourceType.INTERNAL,
            content="Final lesson",
            order=1,
            estimated_minutes=1,
        )
        Enrollment.objects.create(user=self.student, course=course)
        self._quiz(lesson, passing_score=70)
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            reverse("student-lesson-progress", kwargs={"lesson_id": lesson.pk}),
            {"delta_seconds": 60},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["completed_at"])

        response = self.client.get(reverse("student-course-detail", kwargs={"course_id": course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress_percent"], 100.0)
        self.assertEqual(response.data["completed_lessons"], 1)
        self.assertFalse(response.data["certificate_eligible"])
        self.assertIn("Pass the final assessment.", response.data["certificate_reasons"])

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

    def test_student_full_name_uses_profile_fields_with_spaces_and_title_case(self):
        self.student.first_name = "shemsa"
        self.student.last_name = "amin"
        self.student.save(update_fields=["first_name", "last_name"])
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["student_name"], "Shemsa Amin")
        self.assertNotEqual(response.data["student_name"], "shemsaamin")

    def test_usernames_and_email_prefixes_are_not_used_as_certificate_names(self):
        user = User.objects.create_user(
            email="lowercaseprefix@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="",
            last_name="",
        )

        self.assertEqual(official_person_name(user), "Certificate Recipient")

    def test_certificate_date_is_formal_readable_text(self):
        value = datetime(2026, 7, 19, 12, 30, tzinfo=datetime_timezone.utc)

        self.assertEqual(format_certificate_date(value), "19 July 2026")

    @patch("progress.services.certificates.timezone.now")
    def test_certificate_number_uses_readable_lc_date_format(self, mocked_now):
        mocked_now.return_value = datetime(2026, 7, 19, 9, 0, tzinfo=datetime_timezone.utc)
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.data["certificate_number"], r"^LC-2026-0719-[A-F0-9]{8}$")

    def test_certificate_snapshots_official_metadata_from_backend_records(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        certificate = Certificate.objects.get(pk=response.data["id"])
        self.assertEqual(certificate.platform_name, "LearnCode")
        self.assertIn("verify-certificate", certificate.verification_url)
        self.assertTrue(certificate.verification_url.endswith(certificate.verification_code))
        self.assertEqual(certificate.ceo_name, "Shemsa Amin")
        self.assertEqual(certificate.ceo_title, "Chief Executive Officer")
        self.assertEqual(certificate.instructor_name, "Ada Admin")
        self.assertEqual(certificate.completion_date.date(), certificate.issue_date.date())
        self.assertEqual(certificate.course_duration, "2 minutes")
        self.assertTrue(response.data["qr_code_data_url"].startswith("data:image/svg+xml;base64,"))

    def test_generated_pdf_is_one_page_a4_landscape(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        certificate = Certificate.objects.get(pk=response.data["id"])
        pdf_bytes = certificate.file.read()
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1)
        media_box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", pdf_bytes)
        self.assertIsNotNone(media_box)
        width = float(media_box.group(1))
        height = float(media_box.group(2))
        self.assertAlmostEqual(width, 841.89, delta=0.75)
        self.assertAlmostEqual(height, 595.28, delta=0.75)
        self.assertIn(b"OFFICIAL CERTIFICATE", pdf_bytes)
        self.assertIn(b"VERIFIED", pdf_bytes)
        self.assertIn(b"Shemsa Amin", pdf_bytes)
        self.assertIn(b"Chief Executive Officer", pdf_bytes)

    def test_generated_pdf_uses_official_learncode_completion_layout_text(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        certificate = Certificate.objects.get(pk=response.data["id"])
        pdf_bytes = certificate.file.read()
        self.assertIn(b"LEARNCODE OFFICIAL COMPLETION CREDENTIAL", pdf_bytes)
        self.assertIn(b"Awarded to", pdf_bytes)
        self.assertIn(b"Course completed", pdf_bytes)
        self.assertIn(b"Authorized signature", pdf_bytes)
        self.assertIn(b"Scan to verify at LearnCode", pdf_bytes)

    def test_download_uses_professional_sanitized_filename(self):
        self.student.first_name = "Grace / The"
        self.student.last_name = "Hopper: Pioneer"
        self.student.save(update_fields=["first_name", "last_name"])
        self.course.title = "Python <Foundations> & Final: Assessment?"
        self.course.save(update_fields=["title"])
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        response = self.client.get(reverse("certificate-download", kwargs={"certificate_id": created.data["id"]}))

        self.assertEqual(response.status_code, 200)
        disposition = response["Content-Disposition"]
        self.assertIn("Certificate_Grace_The_Hopper_Pioneer_Python_Foundations_Final_Assessment_", disposition)
        self.assertIn(created.data["certificate_number"], disposition)
        self.assertNotRegex(disposition, r'[<>:"/\\|?&]')

    def test_qr_code_svg_contains_public_verification_url_and_no_placeholder_text(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        certificate = Certificate.objects.get(pk=created.data["id"])

        svg = certificate_qr_svg(certificate)

        self.assertIn(certificate.verification_url, svg)
        self.assertIn("<svg", svg)
        self.assertNotIn("QR Code", svg)

    def test_long_student_name_and_course_title_still_generate_pdf(self):
        self.student.first_name = "Alexandria-Catherine"
        self.student.last_name = "Montgomery Kensington Worthington-Smythe the Third"
        self.student.save(update_fields=["first_name", "last_name"])
        self.course.title = (
            "Advanced Professional Software Engineering, Secure Web Architecture, "
            "Cloud Deployment, and Applied Artificial Intelligence Programme"
        )
        self.course.save(update_fields=["title"])
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        certificate = Certificate.objects.get(pk=response.data["id"])
        self.assertGreater(certificate.file.size, 2500)
        self.assertEqual(
            certificate.student_name,
            "Alexandria-Catherine Montgomery Kensington Worthington-Smythe The Third",
        )
        self.assertEqual(certificate.course_title, self.course.title)

    @override_settings(
        CERTIFICATE_LOGO_PATH="/missing/logo.png",
        CERTIFICATE_CEO_SIGNATURE_PATH="/missing/ceo-signature.png",
    )
    def test_missing_logo_and_signature_assets_use_safe_fallbacks(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)

        response = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        self.assertEqual(response.status_code, 201)
        certificate = Certificate.objects.get(pk=response.data["id"])
        self.assertTrue(certificate.file)
        self.assertGreater(certificate.file.size, 2500)

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
        self.assertEqual(response.data["verification_status"], "VALID")
        self.assertEqual(response.data["platform_name"], "LearnCode")
        self.assertEqual(
            response.data["verification_summary"],
            "Grace Hopper completed Certificate Python at LearnCode.",
        )
        self.assertIn("completion_date", response.data)
        self.assertNotIn("student_id", response.data)

    def test_public_verification_returns_not_found_state_for_invalid_code(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("certificate-verify", kwargs={"verification_code": "not-a-real-code"}))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["valid"])
        self.assertEqual(response.data["verification_status"], "NOT_FOUND")
        self.assertEqual(response.data["certificate_status"], "")
        self.assertEqual(response.data["student_name"], "")

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

    def test_public_verification_returns_revoked_state(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))
        self.client.force_authenticate(user=self.admin)
        self.client.patch(reverse("admin-certificate-revoke", kwargs={"certificate_id": created.data["id"]}))
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("certificate-verify", kwargs={"verification_code": created.data["verification_code"]})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["valid"])
        self.assertEqual(response.data["verification_status"], "REVOKED")
        self.assertEqual(response.data["certificate_status"], "REVOKED")
        self.assertEqual(response.data["certificate_number"], created.data["certificate_number"])

    def test_student_can_fetch_own_certificate_preview_but_not_another_students(self):
        self._make_eligible()
        self.client.force_authenticate(user=self.student)
        created = self.client.post(reverse("student-course-certificate", kwargs={"course_id": self.course.pk}))

        own_response = self.client.get(reverse("certificate-detail", kwargs={"certificate_id": created.data["id"]}))
        self.client.force_authenticate(user=self.other_student)
        other_response = self.client.get(reverse("certificate-detail", kwargs={"certificate_id": created.data["id"]}))

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.data["certificate_number"], created.data["certificate_number"])
        self.assertEqual(own_response.data["ceo_name"], "Shemsa Amin")
        self.assertEqual(other_response.status_code, 403)
