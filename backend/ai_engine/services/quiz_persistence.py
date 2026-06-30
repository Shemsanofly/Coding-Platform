"""Persist AI-generated quizzes into the existing quizzes schema."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from ai_engine.services.quiz_generator import question_to_model_fields
from quizzes.models import Question, Quiz

logger = logging.getLogger(__name__)


def ensure_quiz_for_lesson(lesson_id: int, *, passing_score: int = 60) -> Quiz:
    quiz, created = Quiz.objects.get_or_create(
        lesson_id=lesson_id,
        defaults={
            "passing_score": passing_score,
            "generation_status": Quiz.GenerationStatus.PENDING,
            "generation_error": "",
        },
    )
    if not created and quiz.generation_status == Quiz.GenerationStatus.DONE:
        pass
    return quiz


def set_quiz_status(
    quiz: Quiz,
    status: str,
    *,
    error: str = "",
) -> None:
    quiz.generation_status = status
    quiz.generation_error = (error or "")[:4000]
    quiz.save(update_fields=["generation_status", "generation_error"])


@transaction.atomic
def persist_generated_questions(
    lesson_id: int,
    generated: list[dict[str, Any]],
    *,
    publish: bool = False,
    passing_score: int = 60,
) -> Quiz:
    quiz = ensure_quiz_for_lesson(lesson_id, passing_score=passing_score)
    Question.objects.filter(quiz=quiz).delete()
    for order, item in enumerate(generated):
        fields = question_to_model_fields(item, is_published=publish)
        Question.objects.create(quiz=quiz, order=order, **fields)
    quiz.generation_status = Quiz.GenerationStatus.DONE
    quiz.generation_error = ""
    quiz.save(update_fields=["generation_status", "generation_error"])
    return quiz


@transaction.atomic
def publish_quiz_questions(quiz_id: int) -> int:
    updated = Question.objects.filter(quiz_id=quiz_id).update(is_published=True)
    return updated


@transaction.atomic
def rollback_quiz_generation(quiz: Quiz, error: str) -> None:
    set_quiz_status(quiz, Quiz.GenerationStatus.FAILED, error=error)


def _field_is_empty(value) -> bool:
    if isinstance(value, list):
        return len(value) == 0
    return not str(value or "").strip()


def _may_auto_fill(lesson, field_value) -> bool:
    return lesson.is_auto_generated or _field_is_empty(field_value)


def apply_lesson_intelligence(lesson, payload: dict[str, Any]) -> list[str]:
    """
    Map Gemini lesson intelligence onto existing Lesson fields.

    Only writes when the lesson is auto-generated or the target field is empty.
    Returns list of updated field names.
    """
    updated: list[str] = []
    summary = (payload.get("summary") or "").strip()
    objectives = payload.get("learning_objectives") or []
    topic_tags = payload.get("topic_tags") or []
    objective_text = "\n".join(f"• {o}" for o in objectives if str(o).strip())[:2000]

    if summary and _may_auto_fill(lesson, lesson.content):
        lesson.content = summary[:8000]
        updated.append("content")

    if objective_text and _may_auto_fill(lesson, lesson.learning_objective):
        lesson.learning_objective = objective_text
        updated.append("learning_objective")

    if topic_tags and _may_auto_fill(lesson, lesson.tags):
        lesson.tags = list(dict.fromkeys(str(t) for t in topic_tags))[:40]
        updated.append("tags")

    primary_topic = topic_tags[0] if topic_tags else ""
    if primary_topic and _may_auto_fill(lesson, lesson.topic_tag):
        lesson.topic_tag = str(primary_topic)[:100]
        updated.append("topic_tag")

    if updated:
        lesson.save(update_fields=updated)
    return updated


def update_lesson_metadata_from_questions(
    lesson,
    questions: list[dict[str, Any]],
    *,
    learning_objective: str = "",
) -> None:
    """Legacy helper — prefer apply_lesson_intelligence with full payload."""
    topic_tags = sorted({q["topic_tag"] for q in questions if q.get("topic_tag")})
    payload: dict[str, Any] = {
        "summary": "",
        "learning_objectives": [learning_objective] if learning_objective else [],
        "key_concepts": [],
        "topic_tags": topic_tags,
        "questions": questions,
    }
    if learning_objective and _may_auto_fill(lesson, lesson.learning_objective):
        apply_lesson_intelligence(
            lesson,
            {
                **payload,
                "learning_objectives": [learning_objective],
            },
        )
    elif topic_tags:
        if _may_auto_fill(lesson, lesson.tags):
            lesson.tags = list(dict.fromkeys(list(lesson.tags or []) + topic_tags))[:40]
        if topic_tags and _may_auto_fill(lesson, lesson.topic_tag):
            lesson.topic_tag = topic_tags[0][:100]
        lesson.save(update_fields=["tags", "topic_tag"])
