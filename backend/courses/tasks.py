import logging
import re

from ai_engine.services.transcript import (
    TranscriptError,
    TranscriptService,
    normalize_transcript_text,
)
from celery import chain, shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

WORD_CHUNK_MIN = 200
WORD_CHUNK_MAX = 350


def run_course_content_pipeline(course_id: int) -> None:
    """Run fetch then NLP as a Celery chain."""
    chain(
        fetch_course_content.s(course_id),
        process_lessons_nlp.s(),
    ).apply_async()


@shared_task
def fetch_course_content(course_id: int) -> int:
    from courses.models import Course, CourseSource, Lesson

    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        logger.error("fetch_course_content: Course id=%s not found", course_id)
        return course_id

    CourseSource.objects.filter(course_id=course_id).update(
        fetch_status=CourseSource.FetchStatus.FETCHING
    )

    Lesson.objects.filter(course_id=course_id, is_auto_generated=True).delete()

    next_order = 0
    for source in CourseSource.objects.filter(course_id=course_id).order_by("pk"):
        try:
            if source.source_type != CourseSource.SourceType.YOUTUBE:
                raise ValueError(f"Unsupported source_type: {source.source_type}")

            text = _fetch_youtube_transcript_text(source.url)
            text = _normalize_whitespace(text)
            chunks = _chunk_by_paragraph_word_bounds(text)

            with transaction.atomic():
                for chunk in chunks:
                    title = _title_from_first_sentence(chunk)
                    word_count = len(chunk.split())
                    estimated = min(45, max(8, word_count // 180 + 8))
                    Lesson.objects.create(
                        course=course,
                        title=title,
                        content=chunk,
                        source_type=Lesson.SourceType.YOUTUBE,
                        resource_url=source.url,
                        difficulty=course.level,
                        estimated_minutes=estimated,
                        tags=["ingested", source.source_type],
                        learning_objective="Synthesize the key ideas from the linked YouTube lesson.",
                        order=next_order,
                        is_auto_generated=True,
                    )
                    next_order += 1

                source.fetch_status = CourseSource.FetchStatus.DONE
                source.fetched_at = timezone.now()
                source.save(update_fields=["fetch_status", "fetched_at"])

        except Exception:
            logger.exception(
                "fetch_course_content failed for source id=%s url=%s",
                source.pk,
                source.url,
            )
            source.fetch_status = CourseSource.FetchStatus.FAILED
            source.save(update_fields=["fetch_status"])

    return course_id


@shared_task
def process_lessons_nlp(course_id: int) -> int:
    """Post-fetch NLP over generated lessons (extend in ai_engine as needed)."""
    from courses.models import Course

    if not Course.objects.filter(pk=course_id).exists():
        logger.warning("process_lessons_nlp: Course id=%s not found", course_id)
        return course_id
    logger.info("process_lessons_nlp: course_id=%s (placeholder)", course_id)
    return course_id


@shared_task
def check_course_ready(course_id: int) -> int:
    """Set course status to ready when every lesson has a completed quiz."""
    from courses.models import Course, Lesson
    from quizzes.models import Quiz

    if not Course.objects.filter(pk=course_id).exists():
        logger.warning("check_course_ready: Course id=%s not found", course_id)
        return course_id

    lesson_ids = list(
        Lesson.objects.filter(course_id=course_id).values_list("pk", flat=True)
    )
    if not lesson_ids:
        return course_id

    from django.db.models import Count, Q

    ready_lessons = set(
        Quiz.objects.filter(
            lesson_id__in=lesson_ids,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        .annotate(pub=Count("questions", filter=Q(questions__is_published=True)))
        .filter(pub__gt=0)
        .values_list("lesson_id", flat=True)
    )
    if set(lesson_ids) <= ready_lessons:
        Course.objects.filter(pk=course_id).update(status=Course.Status.READY)
    return course_id


def _fetch_youtube_transcript_text(url: str) -> str:
    try:
        return TranscriptService().extract(url)
    except TranscriptError as exc:
        raise ValueError(str(exc)) from exc


def _normalize_whitespace(text: str) -> str:
    return normalize_transcript_text(text)


def _word_count(s: str) -> int:
    return len(s.split())


def _split_oversized_paragraph(para: str) -> list[str]:
    if _word_count(para) <= WORD_CHUNK_MAX:
        return [para]
    sentences = re.split(r"(?<=[.!?])\s+", para)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        words = para.split()
        out = []
        for i in range(0, len(words), WORD_CHUNK_MAX):
            out.append(" ".join(words[i : i + WORD_CHUNK_MAX]))
        return out
    return sentences


def _paragraph_units(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n+", text)
    units: list[str] = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        units.extend(_split_oversized_paragraph(b))
    return units


def _chunk_by_paragraph_word_bounds(text: str) -> list[str]:
    units = _paragraph_units(text)
    if not units:
        return []
    chunks: list[str] = []
    current: list[str] = []
    cw = 0

    def flush():
        nonlocal current, cw
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            cw = 0

    for unit in units:
        uw = _word_count(unit)
        if uw > WORD_CHUNK_MAX:
            wds = unit.split()
            pos = 0
            while pos < len(wds):
                piece = " ".join(wds[pos : pos + WORD_CHUNK_MAX])
                pos += WORD_CHUNK_MAX
                pw = _word_count(piece)
                if cw + pw <= WORD_CHUNK_MAX and current:
                    current.append(piece)
                    cw += pw
                else:
                    flush()
                    current = [piece]
                    cw = pw
            continue

        if not current:
            current.append(unit)
            cw = uw
            if WORD_CHUNK_MIN <= cw <= WORD_CHUNK_MAX:
                flush()
            continue

        if cw + uw <= WORD_CHUNK_MAX:
            current.append(unit)
            cw += uw
            if cw >= WORD_CHUNK_MIN:
                flush()
            continue

        if cw >= WORD_CHUNK_MIN:
            flush()
            current.append(unit)
            cw = uw
            if WORD_CHUNK_MIN <= cw <= WORD_CHUNK_MAX:
                flush()
        else:
            current.append(unit)
            cw += uw

    flush()

    tail_merge = []
    for c in chunks:
        if tail_merge and _word_count(tail_merge[-1]) < WORD_CHUNK_MIN:
            tail_merge[-1] = tail_merge[-1] + "\n\n" + c
        else:
            tail_merge.append(c)
    return tail_merge


def _title_from_first_sentence(chunk: str, max_len: int = 80) -> str:
    chunk = chunk.strip()
    if not chunk:
        return "Lesson"
    m = re.search(r".+?[.!?](?:\s|$)", chunk)
    first = m.group(0).strip() if m else chunk.split("\n")[0].strip()
    first = re.sub(r"\s+", " ", first)
    if len(first) > max_len:
        first = first[: max_len - 1].rstrip() + "..."
    return first or "Lesson"
