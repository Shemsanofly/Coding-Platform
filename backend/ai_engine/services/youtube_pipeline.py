"""Orchestration helpers for YouTube lesson AI quiz pipeline."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from ai_engine.models import LessonAIProcessing
from ai_engine.services.gemini_service import (
    GeminiQuizError,
    GeminiService,
    intelligence_for_storage,
)
from ai_engine.services.generation_mode import (
    get_ai_generation_mode,
    is_celery_mode,
    is_manual_mode,
)
from ai_engine.services.quiz_persistence import (
    apply_lesson_intelligence,
    ensure_quiz_for_lesson,
    persist_generated_questions,
    set_quiz_status,
)
from ai_engine.services.task_queue import safe_delay
from ai_engine.services.transcript import TranscriptError, TranscriptService
from courses.models import Lesson
from quizzes.models import Question, Quiz

logger = logging.getLogger(__name__)

QUEUE_UNAVAILABLE_MESSAGE = (
    "AI generation could not be queued because Redis/Celery is unavailable. "
    "Start Redis and Celery, then click Regenerate Quiz."
)

MANUAL_PENDING_HINT = "Lesson saved. Click Generate Quiz to create AI quiz."


def user_facing_generation_error(raw: str) -> str:
    """Map internal errors to admin-safe messages (no tracebacks or secrets)."""
    text = (raw or "").strip()
    lower = text.lower()
    if "429" in text or "quota" in lower or "rate limit" in lower or "resource exhausted" in lower:
        return "Gemini rate limit reached. Please wait and try again."
    if "api key" in lower or ("invalid" in lower and "key" in lower) or "api_key" in lower:
        return "Gemini API key is invalid. Check backend/.env and restart the backend."
    if "transcript" in lower or "caption" in lower or "subtitles" in lower:
        return "Transcript unavailable for this video. Try another video with captions."
    if "traceback" in lower:
        return "AI quiz generation failed."
    return text[:500] if text else "AI quiz generation failed."


@transaction.atomic
def reset_youtube_lesson_for_regeneration(
    lesson_id: int, *, for_async: bool = False
) -> LessonAIProcessing:
    """
    Clear prior quiz output and reset pipeline state before regeneration.

    Removes all existing questions (including published) so drafts cannot mix with old content.
    """
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id)
    quiz = ensure_quiz_for_lesson(lesson_id)
    Question.objects.filter(quiz=quiz).delete()

    quiz_status = Quiz.GenerationStatus.PENDING if for_async else Quiz.GenerationStatus.PROCESSING
    quiz.generation_status = quiz_status
    quiz.generation_error = ""
    quiz.save(update_fields=["generation_status", "generation_error"])

    processing, _ = LessonAIProcessing.objects.select_for_update().get_or_create(
        lesson=lesson,
        defaults={"status": LessonAIProcessing.Status.PENDING},
    )
    processing.status = (
        LessonAIProcessing.Status.PENDING if for_async else LessonAIProcessing.Status.PROCESSING
    )
    processing.last_error = ""
    processing.save(update_fields=["status", "last_error", "updated_at"])
    return processing


def is_youtube_lesson(lesson: Lesson) -> bool:
    return lesson.source_type == Lesson.SourceType.YOUTUBE and bool(
        (lesson.resource_url or "").strip()
    )


def bootstrap_youtube_processing(lesson: Lesson) -> LessonAIProcessing:
    """Create Quiz + LessonAIProcessing rows and return processing record."""
    ensure_quiz_for_lesson(lesson.pk)
    processing, _ = LessonAIProcessing.objects.get_or_create(
        lesson=lesson,
        defaults={"status": LessonAIProcessing.Status.PENDING},
    )
    if processing.status == LessonAIProcessing.Status.COMPLETED:
        processing.status = LessonAIProcessing.Status.PENDING
        processing.last_error = ""
        processing.save(update_fields=["status", "last_error", "updated_at"])
    quiz = Quiz.objects.get(lesson_id=lesson.pk)
    quiz.generation_status = Quiz.GenerationStatus.PENDING
    quiz.generation_error = ""
    quiz.save(update_fields=["generation_status", "generation_error"])
    return processing


def mark_video_processing_queue_failed(lesson_id: int, exc: Exception | None = None) -> None:
    """Record queue failure so admins can retry after starting Redis/Celery."""
    if exc:
        logger.warning(
            "mark_video_processing_queue_failed lesson_id=%s: %s",
            lesson_id,
            exc,
        )
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        logger.error("mark_video_processing_queue_failed: lesson %s not found", lesson_id)
        return

    ensure_quiz_for_lesson(lesson_id)
    processing, _ = LessonAIProcessing.objects.get_or_create(
        lesson=lesson,
        defaults={"status": LessonAIProcessing.Status.PENDING},
    )
    processing.status = LessonAIProcessing.Status.FAILED
    processing.last_error = QUEUE_UNAVAILABLE_MESSAGE
    processing.save(update_fields=["status", "last_error", "updated_at"])

    quiz = Quiz.objects.get(lesson_id=lesson_id)
    quiz.generation_status = Quiz.GenerationStatus.FAILED
    quiz.generation_error = QUEUE_UNAVAILABLE_MESSAGE
    quiz.save(update_fields=["generation_status", "generation_error"])


def maybe_auto_enqueue_youtube_quiz(lesson_id: int) -> bool:
    """Enqueue Celery task after lesson save when mode is celery; no-op in manual mode."""
    if not is_celery_mode():
        return False
    return enqueue_video_processing(lesson_id)


def enqueue_video_processing(lesson_id: int) -> bool:
    """
    Queue YouTube AI quiz generation. Returns True when queued (or sync fallback ran).
    """
    from django.conf import settings

    if not is_celery_mode():
        return False

    from ai_engine.tasks import process_video_lesson

    result = safe_delay(
        process_video_lesson,
        lesson_id,
        on_failure=lambda exc: mark_video_processing_queue_failed(lesson_id, exc),
    )
    if result is not None:
        return True

    if getattr(settings, "AI_GENERATION_SYNC_FALLBACK", False):
        logger.info(
            "AI_GENERATION_SYNC_FALLBACK: running generate_quiz_for_youtube_lesson "
            "synchronously for lesson_id=%s",
            lesson_id,
        )
        generate_quiz_for_youtube_lesson(lesson_id)
        return True

    return False


def _store_pipeline_failure(
    processing: LessonAIProcessing,
    quiz: Quiz,
    raw_error: str,
) -> str:
    """Persist user-safe failure on quiz + processing rows."""
    friendly = user_facing_generation_error(raw_error)
    processing.status = LessonAIProcessing.Status.FAILED
    processing.last_error = friendly
    processing.save(update_fields=["status", "last_error", "updated_at"])
    set_quiz_status(quiz, Quiz.GenerationStatus.FAILED, error=friendly)
    return friendly


def run_youtube_quiz_generation_sync(lesson_id: int) -> dict[str, Any]:
    """
    Run generate_quiz_for_youtube_lesson in-process for manual mode / regenerate.

    Returns API-safe dict (no tracebacks).
    """
    mode = get_ai_generation_mode()
    logger.info(
        "quiz_generation_sync_start lesson_id=%s ai_generation_mode=%s manual=%s",
        lesson_id,
        mode,
        is_manual_mode(),
    )
    try:
        result = generate_quiz_for_youtube_lesson(lesson_id)
    except Exception as exc:
        logger.exception("run_youtube_quiz_generation_sync failed lesson_id=%s", lesson_id)
        friendly = user_facing_generation_error(str(exc))
        quiz = Quiz.objects.filter(lesson_id=lesson_id).first()
        processing = LessonAIProcessing.objects.filter(lesson_id=lesson_id).first()
        if quiz and processing:
            _store_pipeline_failure(processing, quiz, str(exc))
        return {
            "success": False,
            "message": "AI quiz generation failed.",
            "error": friendly,
        }

    if result is not None:
        quiz = Quiz.objects.filter(lesson_id=lesson_id).first()
        question_count = Question.objects.filter(quiz=quiz).count() if quiz else 0
        logger.info(
            "quiz_generation_sync_success lesson_id=%s question_count=%s",
            lesson_id,
            question_count,
        )
        return {
            "success": True,
            "message": "AI quiz generated successfully.",
            "question_count": question_count,
        }

    quiz = Quiz.objects.filter(lesson_id=lesson_id).only("generation_error").first()
    error_msg = (quiz.generation_error if quiz else "") or "AI quiz generation failed."
    friendly = user_facing_generation_error(error_msg)
    logger.warning(
        "quiz_generation_sync_failed lesson_id=%s error=%s",
        lesson_id,
        friendly,
    )
    return {
        "success": False,
        "message": "AI quiz generation failed.",
        "error": friendly,
    }


def generate_quiz_for_youtube_lesson(lesson_id: int) -> int | None:
    """
    Transcript → Gemini → validate → persist questions → mark quiz done.

    On failure: quiz status failed + error message stored. Returns lesson_id on success.
    """
    try:
        lesson = Lesson.objects.select_related("course").get(pk=lesson_id)
    except Lesson.DoesNotExist:
        logger.error("generate_quiz_for_youtube_lesson: lesson %s not found", lesson_id)
        return None

    if not is_youtube_lesson(lesson):
        logger.info("generate_quiz_for_youtube_lesson: lesson %s skipped (not YouTube)", lesson_id)
        return None

    course_id = lesson.course_id
    logger.info(
        "generate_quiz_for_youtube_lesson_start lesson_id=%s course_id=%s mode=%s url=%s",
        lesson_id,
        course_id,
        get_ai_generation_mode(),
        (lesson.resource_url or "")[:80],
    )

    processing, _ = LessonAIProcessing.objects.get_or_create(
        lesson=lesson,
        defaults={"status": LessonAIProcessing.Status.PENDING},
    )
    quiz = ensure_quiz_for_lesson(lesson_id)

    processing.status = LessonAIProcessing.Status.PROCESSING
    processing.last_error = ""
    processing.save(update_fields=["status", "last_error", "updated_at"])
    set_quiz_status(quiz, Quiz.GenerationStatus.PROCESSING)

    try:
        transcript_text = TranscriptService().extract(lesson.resource_url)
        logger.info(
            "generate_quiz_transcript_ok lesson_id=%s chars=%s",
            lesson_id,
            len(transcript_text),
        )
        processing.transcript_text = transcript_text
        processing.save(update_fields=["transcript_text", "updated_at"])

        payload = GeminiService().generate_quiz(transcript_text)
        logger.info(
            "generate_quiz_gemini_ok lesson_id=%s questions=%s",
            lesson_id,
            len(payload.get("questions") or []),
        )
        processing.analysis_json = intelligence_for_storage(payload)
        processing.save(update_fields=["analysis_json", "updated_at"])

        apply_lesson_intelligence(lesson, payload)
        quiz = persist_generated_questions(lesson_id, payload["questions"], publish=False)
        question_count = quiz.questions.count()
        logger.info(
            "generate_quiz_persist_ok lesson_id=%s quiz_id=%s question_count=%s published=%s",
            lesson_id,
            quiz.pk,
            question_count,
            quiz.questions.filter(is_published=True).count(),
        )

        processing.status = LessonAIProcessing.Status.COMPLETED
        processing.last_error = ""
        processing.save(update_fields=["status", "last_error", "updated_at"])

        from courses.tasks import check_course_ready

        check_course_ready(lesson.course_id)
        logger.info("generate_quiz_for_youtube_lesson: completed lesson_id=%s", lesson_id)
        return lesson_id

    except (TranscriptError, GeminiQuizError) as exc:
        friendly = _store_pipeline_failure(processing, quiz, str(exc))
        logger.warning(
            "generate_quiz_for_youtube_lesson failed lesson_id=%s error=%s",
            lesson_id,
            friendly,
        )
        return None
    except Exception as exc:
        friendly = _store_pipeline_failure(processing, quiz, str(exc))
        logger.exception(
            "generate_quiz_for_youtube_lesson unexpected failure lesson_id=%s error=%s",
            lesson_id,
            friendly,
        )
        return None
