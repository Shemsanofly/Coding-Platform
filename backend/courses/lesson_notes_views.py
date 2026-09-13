"""API endpoints for AI-generated PDF study notes."""

from __future__ import annotations

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from ai_engine.services.lesson_notes import (
    TranscriptUnavailableError,
    generate_lesson_pdf_notes,
)
from ai_engine.services.pdf_service import PDFGenerationError
from courses.models import Course, Lesson
from courses.services import lesson_unlocked
from progress.models import Enrollment, LessonProgress


def _validate_pdf_bytes(header: bytes) -> bool:
    return header.startswith(b"%PDF-")


def _resolve_lesson_pdf(lesson: Lesson):
    """Return an open file handle or raise with a user-facing error message."""
    if not lesson.pdf_notes:
        return (
            None,
            "PDF study notes are not available for this lesson yet.",
            status.HTTP_404_NOT_FOUND,
        )

    try:
        file_handle = lesson.pdf_notes.open("rb")
    except FileNotFoundError:
        return None, "PDF file is missing on the server.", status.HTTP_404_NOT_FOUND
    except OSError:
        return None, "Could not open PDF file.", status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        header = file_handle.read(5)
        file_handle.seek(0)
        if not _validate_pdf_bytes(header):
            file_handle.close()
            return (
                None,
                "PDF file appears to be corrupted or invalid.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
    except OSError:
        file_handle.close()
        return None, "Could not read PDF file.", status.HTTP_500_INTERNAL_SERVER_ERROR

    return file_handle, None, status.HTTP_200_OK


def _record_notes_activity(
    user, lesson: Lesson, *, opened: bool = False, downloaded: bool = False
) -> None:
    """Record PDF notes analytics on existing LessonProgress fields."""
    if user.role != User.Role.STUDENT:
        return

    progress, _created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    update_fields: list[str] = []

    if opened and progress.notes_viewed_at is None:
        progress.notes_viewed_at = timezone.now()
        update_fields.append("notes_viewed_at")

    if downloaded:
        progress.notes_downloaded_at = timezone.now()
        update_fields.append("notes_downloaded_at")

    if update_fields:
        progress.save(update_fields=update_fields)
    elif opened or downloaded:
        progress.save(update_fields=["last_opened_at"])


def _student_can_access_lesson(user, lesson: Lesson) -> tuple[bool, str | None, int]:
    course = lesson.course
    if course.status not in (Course.Status.READY, Course.Status.PUBLISHED):
        return False, "Course not available.", status.HTTP_404_NOT_FOUND
    if not Enrollment.objects.filter(user=user, course=course).exists():
        return False, "Enroll in this course to access lessons.", status.HTTP_403_FORBIDDEN
    if not lesson_unlocked(course, user, lesson):
        return (
            False,
            "Complete prior lessons and quizzes to unlock this lesson.",
            status.HTTP_403_FORBIDDEN,
        )
    return True, None, status.HTTP_200_OK


def _admin_owns_lesson(user, lesson: Lesson) -> bool:
    return (
        user.is_authenticated
        and user.role == User.Role.ADMIN
        and lesson.course.created_by_id == user.pk
    )


class LessonGenerateNotesView(APIView):
    """POST /api/lessons/{id}/generate-notes/ — admin only."""

    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        if request.user.role != User.Role.ADMIN:
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)
        if not _admin_owns_lesson(request.user, lesson):
            return Response({"detail": "Lesson not found."}, status=status.HTTP_404_NOT_FOUND)

        if lesson.source_type != Lesson.SourceType.YOUTUBE:
            return Response(
                {"detail": "PDF notes generation applies to YouTube lessons only."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generate_lesson_pdf_notes(lesson)
        except TranscriptUnavailableError as exc:
            return Response(
                {
                    "detail": exc.message,
                    "error_code": "transcript_unavailable",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except PDFGenerationError as exc:
            return Response(
                {"detail": str(exc), "error_code": "pdf_generation_failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {
                    "detail": f"Could not generate study notes: {exc}",
                    "error_code": "ai_service_failed",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        lesson.refresh_from_db()
        pdf_url = request.build_absolute_uri(lesson.pdf_notes.url) if lesson.pdf_notes else ""
        return Response(
            {
                "detail": "PDF study notes generated successfully.",
                "lesson_id": lesson.id,
                "notes_generated_at": lesson.notes_generated_at,
                "pdf_url": pdf_url,
                "has_pdf_notes": bool(lesson.pdf_notes),
            },
            status=status.HTTP_201_CREATED,
        )


class LessonNotesView(APIView):
    """GET /api/lessons/{id}/notes/ — enrolled students (and owning admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)

        if request.user.role == User.Role.ADMIN:
            if not _admin_owns_lesson(request.user, lesson):
                return Response({"detail": "Lesson not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            allowed, detail, code = _student_can_access_lesson(request.user, lesson)
            if not allowed:
                return Response({"detail": detail}, status=code)

        if not lesson.pdf_notes and not lesson.ai_summary:
            return Response(
                {
                    "detail": "PDF study notes are not available for this lesson yet.",
                    "has_pdf_notes": False,
                    "has_ai_summary": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.role == User.Role.STUDENT:
            _record_notes_activity(request.user, lesson, opened=True)

        pdf_url = ""
        if lesson.pdf_notes:
            pdf_url = request.build_absolute_uri(
                reverse("lesson-view-notes", kwargs={"lesson_id": lesson.id})
            )

        progress = None
        if request.user.role == User.Role.STUDENT:
            progress = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()

        return Response(
            {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "video_url": lesson.resource_url,
                "embedded_url": lesson.embedded_url or "",
                "source_type": lesson.source_type,
                "difficulty_level": lesson.difficulty,
                "topic_tags": lesson.tags or [],
                "estimated_time": lesson.estimated_minutes,
                "ai_summary": lesson.ai_summary or {},
                "has_pdf_notes": bool(lesson.pdf_notes),
                "pdf_url": pdf_url,
                "view_url": pdf_url,
                "notes_generated_at": lesson.notes_generated_at,
                "activity": {
                    "notes_viewed_at": progress.notes_viewed_at if progress else None,
                    "notes_opened_at": progress.notes_viewed_at if progress else None,
                    "notes_downloaded_at": progress.notes_downloaded_at if progress else None,
                    "pdf_reading_seconds": progress.seconds_engaged if progress else 0,
                },
            }
        )


class LessonViewNotesView(APIView):
    """GET /api/lessons/{id}/view-notes/ — inline authenticated PDF for in-platform reader."""

    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)

        if request.user.role == User.Role.ADMIN:
            if not _admin_owns_lesson(request.user, lesson):
                raise Http404("Lesson not found.")
        else:
            allowed, detail, code = _student_can_access_lesson(request.user, lesson)
            if not allowed:
                return Response({"detail": detail}, status=code)

        file_handle, error_message, error_code = _resolve_lesson_pdf(lesson)
        if file_handle is None:
            return Response({"detail": error_message}, status=error_code)

        _record_notes_activity(request.user, lesson, opened=True)

        filename = f"{lesson.title or 'lesson'}_notes.pdf".replace("/", "-")
        response = FileResponse(
            file_handle,
            as_attachment=False,
            filename=filename,
            content_type="application/pdf",
        )
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class LessonDownloadNotesView(APIView):
    """GET /api/lessons/{id}/download-notes/ — enrolled students (and owning admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)

        if request.user.role == User.Role.ADMIN:
            if not _admin_owns_lesson(request.user, lesson):
                raise Http404("Lesson not found.")
        else:
            allowed, detail, code = _student_can_access_lesson(request.user, lesson)
            if not allowed:
                return Response({"detail": detail}, status=code)

        if not lesson.pdf_notes:
            return Response(
                {"detail": "PDF study notes are not available for this lesson yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.role == User.Role.STUDENT:
            _record_notes_activity(request.user, lesson, opened=False, downloaded=True)

        filename = f"{lesson.title or 'lesson'}_notes.pdf".replace("/", "-")
        file_handle, error_message, error_code = _resolve_lesson_pdf(lesson)
        if file_handle is None:
            return Response({"detail": error_message}, status=error_code)

        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )
