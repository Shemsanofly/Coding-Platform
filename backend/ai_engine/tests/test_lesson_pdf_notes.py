"""Tests for AI-generated PDF study notes from YouTube transcripts."""

from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.services.ai_summary_service import generate_study_notes
from ai_engine.services.lesson_notes import generate_lesson_pdf_notes
from ai_engine.services.pdf_service import build_notes_pdf, save_notes_pdf
from ai_engine.services.transcript_service import (
    TRANSCRIPT_UNAVAILABLE_MESSAGE,
    TranscriptUnavailableError,
    extract_youtube_video_id,
    fetch_transcript,
)
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress


def _sample_transcript(min_chars: int = 600) -> str:
    base = (
        "Welcome to this lesson on Python programming fundamentals. "
        "Variables store data values and can be reassigned during execution. "
        "Functions group reusable logic and accept parameters. "
        "Control flow uses if statements and loops to branch program behavior. "
        "Lists and dictionaries are core data structures for organizing information. "
    )
    while len(base) < min_chars:
        base += "Students should practice reading code and tracing execution step by step. "
    return base


def _sample_summary(title: str = "Python Basics") -> dict:
    return {
        "lesson_title": title,
        "key_concepts": ["Variables", "Functions", "Control flow"],
        "definitions": [
            {"term": "Variable", "definition": "A named storage location for data."},
        ],
        "examples": ["Assigning x = 5 stores an integer in memory."],
        "important_points": ["Practice tracing code execution."],
        "revision_notes": ["Review variable naming rules."],
        "possible_quiz_points": ["What is a function?"],
    }


class YouTubeVideoIdExtractionNotesTests(TestCase):
    def test_watch_url(self):
        self.assertEqual(
            extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_short_url(self):
        self.assertEqual(
            extract_youtube_video_id("https://youtu.be/abc123XYZ_1"),
            "abc123XYZ_1",
        )


class TranscriptUnavailableNotesTests(TestCase):
    @patch("ai_engine.services.transcript_service.TranscriptService._fetch_transcript")
    def test_fetch_transcript_unavailable(self, mock_fetch):
        mock_fetch.side_effect = Exception("NoTranscriptFound")
        with self.assertRaises(TranscriptUnavailableError) as ctx:
            fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertIn("Transcript not available", str(ctx.exception.message))


class PDFGenerationNotesTests(TestCase):
    def test_build_notes_pdf_success(self):
        pdf_bytes = build_notes_pdf(_sample_summary())
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    @override_settings(MEDIA_ROOT="test_media_notes")
    def test_save_notes_pdf_success(self):
        path = save_notes_pdf(_sample_summary(), filename="test_lesson.pdf")
        self.assertTrue(path.startswith("pdf_notes/"))


class LessonNotesAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-notes@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student-notes@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title="Notes Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Intro Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )
        Enrollment.objects.create(user=self.student, course=self.course)

    @patch("ai_engine.services.lesson_notes.fetch_transcript")
    @patch("ai_engine.services.lesson_notes.generate_study_notes")
    @patch("ai_engine.services.lesson_notes.save_notes_pdf")
    def test_admin_can_generate_notes(self, mock_save, mock_summary, mock_transcript):
        mock_transcript.return_value = type("R", (), {"video_id": "dQw4w9WgXcQ", "text": _sample_transcript()})()
        mock_summary.return_value = _sample_summary(self.lesson.title)
        mock_save.return_value = f"pdf_notes/lesson_{self.lesson.pk}_notes.pdf"

        self.client.force_authenticate(user=self.admin)
        url = reverse("lesson-generate-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["has_pdf_notes"])

        self.lesson.refresh_from_db()
        self.assertIsNotNone(self.lesson.notes_generated_at)

    def test_student_cannot_generate_notes(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-generate-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    @patch("ai_engine.services.lesson_notes.fetch_transcript")
    def test_transcript_unavailable_response(self, mock_transcript):
        mock_transcript.side_effect = TranscriptUnavailableError()
        self.client.force_authenticate(user=self.admin)
        url = reverse("lesson-generate-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "transcript_unavailable")
        self.assertEqual(response.data["detail"], TRANSCRIPT_UNAVAILABLE_MESSAGE)

    def _attach_pdf(self):
        pdf_bytes = build_notes_pdf(_sample_summary(self.lesson.title))
        self.lesson.ai_summary = _sample_summary(self.lesson.title)
        self.lesson.transcript_text = _sample_transcript()
        self.lesson.pdf_notes.save(
            f"lesson_{self.lesson.pk}_notes.pdf",
            BytesIO(pdf_bytes),
            save=True,
        )
        self.lesson.notes_generated_at = self.lesson.created_at
        self.lesson.save()

    def test_enrolled_student_can_view_notes(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["has_pdf_notes"])
        self.assertIn("view_url", response.data)
        self.assertIn("activity", response.data)
        progress = LessonProgress.objects.get(user=self.student, lesson=self.lesson)
        self.assertIsNotNone(progress.notes_viewed_at)

    def test_enrolled_student_can_view_inline_pdf(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-view-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
        progress = LessonProgress.objects.get(user=self.student, lesson=self.lesson)
        self.assertIsNotNone(progress.notes_viewed_at)

    def test_view_notes_missing_pdf(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-view-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view_notes_corrupted_pdf(self):
        self.lesson.pdf_notes.save(
            f"lesson_{self.lesson.pk}_notes.pdf",
            BytesIO(b"NOT-A-PDF"),
            save=True,
        )
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-view-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 422)
        self.assertIn("corrupted", response.data["detail"].lower())

    def test_student_lesson_detail_exposes_notes_urls(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.student)
        url = reverse("student-lesson-detail", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["has_pdf_notes"])
        self.assertIn("/api/lessons/", response.data["pdf_notes_url"])
        self.assertIn("/view-notes/", response.data["pdf_notes_url"])

    def test_unenrolled_student_denied_view_notes(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.outsider)
        url = reverse("lesson-view-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unenrolled_student_denied(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.outsider)
        url = reverse("lesson-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_enrolled_student_can_download_notes(self):
        self._attach_pdf()
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-download-notes", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        progress = LessonProgress.objects.get(user=self.student, lesson=self.lesson)
        self.assertIsNotNone(progress.notes_downloaded_at)

    def test_lesson_works_without_pdf(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("student-lesson-detail", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_pdf_notes"])
        self.assertIn("youtube_embed_url", response.data)

    def test_existing_quiz_endpoint_still_works_without_pdf(self):
        from quizzes.models import Question, Quiz

        quiz = Quiz.objects.create(
            lesson=self.lesson,
            passing_score=60,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        Question.objects.create(
            quiz=quiz,
            order=0,
            stem="What is a variable?",
            choices=["Storage", "Loop", "Class", "Module"],
            correct_index=0,
            topic_tag="variables",
            is_published=True,
        )
        LessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson,
            seconds_engaged=3600,
            video_watch_pct=100,
        )
        self.client.force_authenticate(user=self.student)
        url = reverse("lesson-quiz", kwargs={"lesson_id": self.lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["questions"]), 1)

    @override_settings(GEMINI_API_KEY="")
    def test_rule_based_summary_fallback(self):
        summary = generate_study_notes(_sample_transcript(), lesson_title="Fallback Lesson")
        self.assertEqual(summary["lesson_title"], "Fallback Lesson")
        self.assertTrue(summary["key_concepts"])
        self.assertTrue(summary["possible_quiz_points"])

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("ai_engine.services.ai_summary_service._gemini_summarize_chunk")
    def test_long_transcript_uses_fast_summary_fallback(self, mock_gemini):
        summary = generate_study_notes(_sample_transcript(50_000), lesson_title="Long Lesson")

        mock_gemini.assert_not_called()
        self.assertEqual(summary["lesson_title"], "Long Lesson")
        self.assertTrue(summary["key_concepts"])

    @patch("ai_engine.services.lesson_notes.fetch_transcript")
    @patch("ai_engine.services.lesson_notes.generate_study_notes")
    @patch("ai_engine.services.lesson_notes.save_notes_pdf")
    def test_generate_lesson_pdf_notes_orchestration(self, mock_save, mock_summary, mock_transcript):
        mock_transcript.return_value = type("R", (), {"video_id": "abc123XYZ_1", "text": _sample_transcript()})()
        mock_summary.return_value = _sample_summary()
        mock_save.return_value = f"pdf_notes/lesson_{self.lesson.pk}_notes.pdf"

        generate_lesson_pdf_notes(self.lesson)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.transcript_text, _sample_transcript())
        self.assertIsNotNone(self.lesson.ai_summary)
        self.assertTrue(self.lesson.embedded_url.endswith("abc123XYZ_1?enablejsapi=1"))
