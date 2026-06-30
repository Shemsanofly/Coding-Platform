"""Deterministic personalized learning paths from WeakTopic, Recommendation, and lessons."""

from __future__ import annotations

import logging
from typing import Any

from decouple import config

logger = logging.getLogger(__name__)

WEAKNESS_PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
MAX_PATH_STEPS = 12


def _lesson_tag_tokens(lesson) -> set[str]:
    tags = list(lesson.tags or [])
    if lesson.topic_tag:
        tags.append(lesson.topic_tag)
    out: set[str] = set()
    for raw in tags:
        token = (raw or "").strip().lower()
        if token:
            out.add(token)
    return out


def _topic_matches_lesson(topic_tag: str, lesson) -> bool:
    tag = (topic_tag or "").strip().lower()
    if not tag:
        return False
    return tag in _lesson_tag_tokens(lesson)


def _weak_topic_accuracy(wt) -> float:
    if not wt.attempt_count:
        return 100.0
    return (wt.correct_count / wt.attempt_count) * 100


def _best_scores_by_lesson(user_id: int) -> dict[int, int]:
    from quizzes.models import QuizResult

    best: dict[int, int] = {}
    for row in QuizResult.objects.filter(user_id=user_id).select_related("quiz"):
        lid = row.quiz.lesson_id
        best[lid] = max(best.get(lid, 0), row.score)
    return best


def _passed_lesson_ids(user_id: int, best_scores: dict[int, int]) -> set[int]:
    from quizzes.models import Quiz

    passed: set[int] = set()
    for lid, score in best_scores.items():
        quiz = Quiz.objects.filter(lesson_id=lid).only("passing_score").first()
        if quiz and score >= quiz.passing_score:
            passed.add(lid)
    return passed


def _completed_lesson_ids(user_id: int, passed_ids: set[int]) -> set[int]:
    from progress.models import LessonProgress

    completed = set(passed_ids)
    for lid in LessonProgress.objects.filter(
        user_id=user_id, completed_at__isnull=False
    ).values_list("lesson_id", flat=True):
        completed.add(lid)
    return completed


def _serialize_weak_topic(wt) -> dict[str, Any]:
    accuracy = round(_weak_topic_accuracy(wt), 1)
    return {
        "id": wt.id,
        "topic_tag": wt.topic_tag,
        "weakness_level": wt.weakness_level,
        "attempt_count": wt.attempt_count,
        "correct_count": wt.correct_count,
        "accuracy_percent": accuracy,
        "last_updated": wt.last_updated.isoformat() if wt.last_updated else None,
    }


def _serialize_lesson_brief(lesson, *, weak_topic_tag: str = "", reason: str = "") -> dict[str, Any]:
    course = lesson.course
    return {
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "course_id": course.id,
        "course_title": course.title,
        "topic_tag": lesson.topic_tag or "",
        "tags": list(lesson.tags or []),
        "difficulty": lesson.difficulty,
        "estimated_minutes": lesson.estimated_minutes,
        "order": lesson.order,
        "weak_topic_tag": weak_topic_tag,
        "reason": reason,
        "source_type": lesson.source_type,
        "resource_url": lesson.resource_url or "",
    }


def _sort_weak_topics(weak_topics: list) -> list:
    return sorted(
        weak_topics,
        key=lambda wt: (
            WEAKNESS_PRIORITY.get(wt.weakness_level or "", 99),
            _weak_topic_accuracy(wt),
            wt.topic_tag or "",
        ),
    )


def _build_learning_path_steps(
    user_id: int,
    weak_topics_sorted: list,
    lessons: list,
    completed_ids: set[int],
    recommendations: list,
) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []
    seen_lessons: set[int] = set()

    for wt in weak_topics_sorted:
        if len(path) >= MAX_PATH_STEPS:
            break
        matches = [
            lesson
            for lesson in lessons
            if lesson.id not in completed_ids
            and lesson.id not in seen_lessons
            and _topic_matches_lesson(wt.topic_tag, lesson)
        ]
        matches.sort(key=lambda lesson: (lesson.course_id, lesson.order, lesson.pk))
        if not matches:
            continue
        lesson = matches[0]
        seen_lessons.add(lesson.id)
        step = _serialize_lesson_brief(
            lesson,
            weak_topic_tag=wt.topic_tag,
            reason=f"Addresses {wt.weakness_level or 'weak'} weakness in {wt.topic_tag}.",
        )
        step["step"] = len(path) + 1
        step["weakness_level"] = wt.weakness_level
        step["status"] = "upcoming"
        path.append(step)

    for rec in recommendations:
        if len(path) >= MAX_PATH_STEPS:
            break
        lesson = rec.lesson
        if lesson.id in completed_ids or lesson.id in seen_lessons:
            continue
        seen_lessons.add(lesson.id)
        step = _serialize_lesson_brief(
            lesson,
            weak_topic_tag=rec.weak_topic_tag or "",
            reason=rec.reason or "Recommended for your learning path.",
        )
        step["step"] = len(path) + 1
        step["weakness_level"] = ""
        step["status"] = "upcoming"
        path.append(step)

    for lesson in sorted(lessons, key=lambda row: (row.course_id, row.order, row.pk)):
        if len(path) >= MAX_PATH_STEPS:
            break
        if lesson.id in completed_ids or lesson.id in seen_lessons:
            continue
        if not any(_topic_matches_lesson(wt.topic_tag, lesson) for wt in weak_topics_sorted):
            continue
        seen_lessons.add(lesson.id)
        matched_tag = next(
            (wt.topic_tag for wt in weak_topics_sorted if _topic_matches_lesson(wt.topic_tag, lesson)),
            "",
        )
        step = _serialize_lesson_brief(
            lesson,
            weak_topic_tag=matched_tag,
            reason="Continues your personalized sequence.",
        )
        step["step"] = len(path) + 1
        step["weakness_level"] = ""
        step["status"] = "upcoming"
        path.append(step)

    if path:
        path[0]["status"] = "next"
    return path


def _path_progress(
    user_id: int,
    path: list[dict[str, Any]],
    completed_ids: set[int],
    *,
    course_ids: list[int] | None = None,
) -> dict[str, Any]:
    from courses.models import Lesson
    from progress.models import Enrollment

    enrolled_ids = list(
        Enrollment.objects.filter(user_id=user_id).values_list("course_id", flat=True)
    )
    if course_ids is not None:
        enrolled_ids = [cid for cid in enrolled_ids if cid in course_ids]
    total_enrolled = Lesson.objects.filter(course_id__in=enrolled_ids).count() if enrolled_ids else 0
    completed_count = len(completed_ids)
    percent = round((completed_count / total_enrolled) * 100, 1) if total_enrolled else 0.0
    next_lesson_id = path[0]["lesson_id"] if path else None

    return {
        "path_steps": len(path),
        "current_step": 1 if path else 0,
        "lessons_completed": completed_count,
        "total_enrolled_lessons": total_enrolled,
        "percent_complete": percent,
        "next_lesson_id": next_lesson_id,
    }


def generate_learning_path_explanation(
    weak_topics: list[dict[str, Any]],
    learning_path: list[dict[str, Any]],
) -> str:
    """Optional Gemini narrative; lesson order stays deterministic."""
    api_key = config("GEMINI_API_KEY", default="")
    if not api_key or not learning_path:
        return ""

    topics = [row.get("topic_tag") or row.get("topic") for row in weak_topics[:6]]
    topics = [t for t in topics if t]
    steps = [
        f"{row.get('step')}. {row.get('lesson_title')} ({row.get('weak_topic_tag') or row.get('topic_tag')})"
        for row in learning_path[:8]
    ]
    if not topics and not steps:
        return ""

    prompt = (
        "Write 2-3 short sentences explaining why this study order makes sense for a student. "
        "Mention prerequisite relationships when relevant (e.g. classes before inheritance). "
        "Do not suggest different lessons or reorder steps.\n"
        f"Weak areas: {', '.join(topics) or 'general practice'}\n"
        f"Planned sequence:\n" + "\n".join(steps)
    )

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_name = config("GEMINI_MODEL", default="gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.4, "max_output_tokens": 256},
        )
        text = (response.text or "").strip()
        return text[:1200] if text else ""
    except Exception as exc:
        logger.warning("learning_path explanation skipped: %s", exc)
        return ""


def generate_learning_path(
    user_id: int,
    *,
    include_explanation: bool = False,
    course_id: int | None = None,
) -> dict[str, Any]:
    """
    Build personalized path from existing WeakTopic, Recommendation, Lesson, and quiz data.

    Returns weak_topics, recommended_lessons, learning_path, progress, and optional explanation.
    """
    from ai_engine.models import Recommendation, WeakTopic
    from courses.models import Course, Lesson
    from progress.models import Enrollment
    from progress.services.weakness_context import build_topic_context_index, topic_matches_course

    course_ids = None
    if course_id is not None:
        course_ids = [course_id]

    context_index = build_topic_context_index(user_id, course_ids=course_ids)

    weak_rows = list(
        WeakTopic.objects.filter(user_id=user_id, weakness_level__isnull=False)
    )
    if course_id is not None:
        weak_rows = [
            wt
            for wt in weak_rows
            if topic_matches_course(wt.topic_tag, course_id, context_index)
            or any(_topic_matches_lesson(wt.topic_tag, lesson) for lesson in Lesson.objects.filter(course_id=course_id))
        ]

    weak_topics_sorted = _sort_weak_topics(weak_rows)
    weak_topics_payload = [_serialize_weak_topic(wt) for wt in weak_topics_sorted]

    enrolled_ids = list(
        Enrollment.objects.filter(user_id=user_id).values_list("course_id", flat=True)
    )
    if course_id is not None:
        enrolled_ids = [cid for cid in enrolled_ids if cid == course_id]

    lessons = list(
        Lesson.objects.filter(course_id__in=enrolled_ids).select_related("course")
    ) if enrolled_ids else []

    best_scores = _best_scores_by_lesson(user_id)
    passed_ids = _passed_lesson_ids(user_id, best_scores)
    completed_ids = _completed_lesson_ids(user_id, passed_ids)

    recommendations_qs = (
        Recommendation.objects.filter(user_id=user_id, status="active")
        .select_related("lesson__course")
        .order_by("-created_at")
    )
    if course_id is not None:
        recommendations_qs = recommendations_qs.filter(lesson__course_id=course_id)
    recommendations = list(recommendations_qs[:12])
    recommended_lessons = [
        _serialize_lesson_brief(
            rec.lesson,
            weak_topic_tag=rec.weak_topic_tag or "",
            reason=rec.reason or "",
        )
        for rec in recommendations
    ]

    learning_path = _build_learning_path_steps(
        user_id,
        weak_topics_sorted,
        lessons,
        completed_ids,
        recommendations,
    )
    progress = _path_progress(user_id, learning_path, completed_ids, course_ids=enrolled_ids or None)

    explanation = ""
    if include_explanation:
        explanation = generate_learning_path_explanation(weak_topics_payload, learning_path)

    payload = {
        "weak_topics": weak_topics_payload,
        "recommended_lessons": recommended_lessons,
        "learning_path": learning_path,
        "progress": progress,
        "explanation": explanation,
    }
    if course_id is not None:
        course = Course.objects.filter(pk=course_id).only("id", "title").first()
        payload["course_id"] = course_id
        payload["course_title"] = course.title if course else ""
    return payload
