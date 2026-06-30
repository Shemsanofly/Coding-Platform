"""Orchestrate transcript → AI summary → PDF for lesson study notes."""

from __future__ import annotations

from django.utils import timezone

from ai_engine.services.ai_summary_service import generate_study_notes
from ai_engine.services.pdf_service import save_notes_pdf
from ai_engine.services.transcript_service import (
    TRANSCRIPT_UNAVAILABLE_MESSAGE,
    TranscriptUnavailableError,
    fetch_transcript,
)
from courses.models import Lesson


def build_embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"


def generate_lesson_pdf_notes(lesson: Lesson) -> Lesson:
    """
    Fetch transcript, summarize, and attach a PDF to the lesson.

    Raises TranscriptUnavailableError, PDFGenerationError, or ValueError.
    """
    url = (lesson.resource_url or "").strip()
    if not url:
        raise ValueError("Lesson does not have a YouTube URL.")

    transcript_result = fetch_transcript(url)
    summary = generate_study_notes(
        transcript_result.text,
        lesson_title=lesson.title or "Lesson Study Notes",
    )

    if lesson.pdf_notes:
        lesson.pdf_notes.delete(save=False)

    relative_path = save_notes_pdf(
        summary,
        filename=f"lesson_{lesson.pk}_notes.pdf",
    )

    lesson.transcript_text = transcript_result.text
    lesson.ai_summary = summary
    lesson.embedded_url = build_embed_url(transcript_result.video_id)
    lesson.notes_generated_at = timezone.now()
    lesson.pdf_notes.name = relative_path
    lesson.save(
        update_fields=[
            "transcript_text",
            "ai_summary",
            "embedded_url",
            "notes_generated_at",
            "pdf_notes",
        ]
    )
    return lesson


__all__ = [
    "TRANSCRIPT_UNAVAILABLE_MESSAGE",
    "TranscriptUnavailableError",
    "generate_lesson_pdf_notes",
]
