"""Derive course/lesson context for weak topics and recommendations from quiz history."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.contrib.auth import get_user_model

from ai_engine.models import Recommendation, WeakTopic
from courses.models import Course, Lesson
from progress.models import Enrollment
from quizzes.models import QuizResult

User = get_user_model()


def normalize_topic_tag(tag: str) -> str:
    return (tag or "").strip().lower()


def parse_course_id_param(raw) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def format_topic_label(tag: str) -> str:
    return (tag or "").replace("_", " ").strip()


def get_enrolled_course_ids(user_id: int, course_id: int | None = None) -> list[int]:
    qs = Enrollment.objects.filter(user_id=user_id)
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    return list(qs.values_list("course_id", flat=True))


def ensure_enrolled_in_course(user, course_id: int | None):
    """Return error message if course_id is set but user is not enrolled."""
    if course_id is None:
        return None
    if not Enrollment.objects.filter(user=user, course_id=course_id).exists():
        return "You are not enrolled in this course."
    return None


def _topic_outcomes_for_result(result: QuizResult) -> dict[str, dict[str, int]]:
    """Per topic_tag counts for a single quiz attempt."""
    outcomes: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    questions = list(result.quiz.questions.all().order_by("order", "pk"))
    answers = result.answers or []
    for index, question in enumerate(questions):
        tag = normalize_topic_tag(question.topic_tag)
        if not tag:
            continue
        outcomes[tag]["total"] += 1
        if index < len(answers) and answers[index] == question.correct_index:
            outcomes[tag]["correct"] += 1
    return outcomes


def build_topic_context_index(user_id: int, course_ids: list[int] | None = None) -> dict[str, dict]:
    """
    Map topic_tag -> courses, recent_lessons, and quiz attempts where the topic appeared.
    """
    results_qs = (
        QuizResult.objects.filter(user_id=user_id)
        .select_related("quiz__lesson__course")
        .prefetch_related("quiz__questions")
        .order_by("-taken_at")
    )
    if course_ids is not None:
        results_qs = results_qs.filter(quiz__lesson__course_id__in=course_ids)

    index: dict[str, dict] = {}

    for result in results_qs:
        lesson = result.quiz.lesson
        course = lesson.course
        outcomes = _topic_outcomes_for_result(result)
        for tag, counts in outcomes.items():
            if counts["total"] <= 0:
                continue
            bucket = index.setdefault(
                tag,
                {
                    "courses": {},
                    "recent_lessons": [],
                    "lesson_ids_seen": set(),
                },
            )
            bucket["courses"][course.id] = {"id": course.id, "title": course.title}
            if lesson.id not in bucket["lesson_ids_seen"]:
                bucket["lesson_ids_seen"].add(lesson.id)
                bucket["recent_lessons"].append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "course_id": course.id,
                        "course_title": course.title,
                        "quiz_result_id": result.id,
                        "score": result.score,
                        "taken_at": result.taken_at,
                        "topic_attempts": counts["total"],
                        "topic_correct": counts["correct"],
                    }
                )

    for tag, bucket in index.items():
        bucket.pop("lesson_ids_seen", None)
        bucket["courses"] = list(bucket["courses"].values())
        bucket["recent_lessons"] = bucket["recent_lessons"][:5]
    return index


def build_lesson_weakness_groups(user_id: int, course_ids: list[int] | None = None) -> list[dict]:
    """Group quiz attempts by lesson with weak topics discovered in each attempt."""
    weak_lookup = {
        normalize_topic_tag(wt.topic_tag): wt
        for wt in WeakTopic.objects.filter(user_id=user_id)
    }

    results_qs = (
        QuizResult.objects.filter(user_id=user_id)
        .select_related("quiz__lesson__course")
        .prefetch_related("quiz__questions")
        .order_by("-taken_at")
    )
    if course_ids is not None:
        results_qs = results_qs.filter(quiz__lesson__course_id__in=course_ids)

    groups: dict[int, dict] = {}
    for result in results_qs:
        lesson = result.quiz.lesson
        course = lesson.course
        outcomes = _topic_outcomes_for_result(result)
        weak_in_attempt = []
        for tag, counts in outcomes.items():
            if counts["total"] <= 0:
                continue
            accuracy = round((counts["correct"] / counts["total"]) * 100, 1)
            wt = weak_lookup.get(tag)
            missed = counts["correct"] < counts["total"]
            if not missed and not wt:
                continue
            weak_in_attempt.append(
                {
                    "topic_tag": tag,
                    "weakness_level": wt.weakness_level if wt else None,
                    "accuracy": round((wt.correct_count / wt.attempt_count) * 100, 1)
                    if wt and wt.attempt_count
                    else accuracy,
                    "attempt_count": wt.attempt_count if wt else counts["total"],
                    "correct_count": wt.correct_count if wt else counts["correct"],
                }
            )
        if not weak_in_attempt:
            continue

        existing = groups.get(lesson.id)
        if existing and existing["taken_at"] >= result.taken_at:
            continue

        groups[lesson.id] = {
            "lesson": {"id": lesson.id, "title": lesson.title},
            "course": {"id": course.id, "title": course.title},
            "quiz_result_id": result.id,
            "score": result.score,
            "taken_at": result.taken_at,
            "weak_topics": sorted(
                weak_in_attempt,
                key=lambda row: (
                    {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get((row.get("weakness_level") or "").upper(), 99),
                    row["topic_tag"],
                ),
            ),
        }

    ordered = sorted(groups.values(), key=lambda row: row["taken_at"], reverse=True)
    for group in ordered:
        group["recommended_lessons"] = _recommendations_for_lesson_group(user_id, group)
    return ordered


def _recommendations_for_lesson_group(user_id: int, group: dict) -> list[dict]:
    course_id = group["course"]["id"]
    lesson_id = group["lesson"]["id"]
    tags = {normalize_topic_tag(row["topic_tag"]) for row in group["weak_topics"]}
    source_title = group["lesson"]["title"]

    recs = (
        Recommendation.objects.filter(user_id=user_id, status="active", lesson__course_id=course_id)
        .exclude(lesson_id=lesson_id)
        .select_related("lesson__course")
        .order_by("-created_at")
    )
    payload = []
    for rec in recs:
        rec_tag = normalize_topic_tag(rec.weak_topic_tag)
        if rec_tag and rec_tag not in tags:
            continue
        payload.append(
            {
                "id": rec.id,
                "lesson_id": rec.lesson_id,
                "title": rec.lesson.title,
                "course_id": rec.lesson.course_id,
                "course_title": rec.lesson.course.title,
                "reason": student_friendly_recommendation_reason(
                    weak_topic_tag=rec.weak_topic_tag or next(iter(tags), ""),
                    source_lesson_title=source_title,
                    recommended_lesson_title=rec.lesson.title,
                    fallback=rec.reason,
                ),
            }
        )
        if len(payload) >= 3:
            break

    if payload:
        return payload

    current_order = Lesson.objects.filter(pk=lesson_id).values_list("order", flat=True).first()
    next_lesson = None
    if current_order is not None:
        next_lesson = (
            Lesson.objects.filter(course_id=course_id, order__gt=current_order)
            .order_by("order")
            .first()
        )
    if next_lesson and next_lesson.id != lesson_id:
        primary_tag = group["weak_topics"][0]["topic_tag"] if group["weak_topics"] else ""
        payload.append(
            {
                "id": None,
                "lesson_id": next_lesson.id,
                "title": next_lesson.title,
                "course_id": course_id,
                "course_title": group["course"]["title"],
                "reason": student_friendly_recommendation_reason(
                    weak_topic_tag=primary_tag,
                    source_lesson_title=source_title,
                    recommended_lesson_title=next_lesson.title,
                ),
            }
        )
    return payload


def student_friendly_recommendation_reason(
    *,
    weak_topic_tag: str,
    source_lesson_title: str,
    recommended_lesson_title: str,
    fallback: str = "",
) -> str:
    label = format_topic_label(weak_topic_tag) or "this topic"
    source = source_lesson_title or "your recent quiz"
    target = recommended_lesson_title or "the recommended lesson"
    generic_markers = (
        "beginner-friendly material because recent quiz scores are low",
        "recommended because it targets your weak topics",
        "recommended as your next learning step",
        "adaptive match for your learning path",
    )
    normalized_fallback = (fallback or "").strip().lower().rstrip(".")
    if fallback and not any(
        normalized_fallback == marker or normalized_fallback.startswith(marker)
        for marker in generic_markers
    ):
        return fallback.strip()
    return (
        f"You struggled with {label} after taking {source}. "
        f"Review {target} to strengthen that topic."
    )


def enrich_weak_topic_payload(
    topic: WeakTopic,
    context_index: dict[str, dict],
) -> dict[str, Any]:
    accuracy = round((topic.correct_count / topic.attempt_count) * 100, 1) if topic.attempt_count else 0
    tag_key = normalize_topic_tag(topic.topic_tag)
    ctx = context_index.get(tag_key, {})
    recent = ctx.get("recent_lessons") or []
    return {
        "id": topic.id,
        "topic": topic.topic_tag,
        "topic_tag": topic.topic_tag,
        "level": topic.weakness_level,
        "weakness_level": topic.weakness_level,
        "attempt_count": topic.attempt_count,
        "correct_count": topic.correct_count,
        "score": accuracy,
        "accuracy": accuracy,
        "accuracy_percent": accuracy,
        "last_updated": topic.last_updated,
        "courses": ctx.get("courses") or [],
        "recent_lessons": [
            {
                "id": row["id"],
                "title": row["title"],
                "course_id": row["course_id"],
                "course_title": row["course_title"],
                "score": row.get("score"),
            }
            for row in recent
        ],
    }


def enrich_recommendation_payload(
    rec_row: dict,
    *,
    weakness_lookup: dict[str, WeakTopic],
    topic_index: dict[str, dict],
) -> dict:
    rec_row = _enrich_recommendation_weakness_fields(rec_row, weakness_lookup)
    weak_tag = normalize_topic_tag(rec_row.get("weak_topic_tag") or "")
    related = []
    if weak_tag and weak_tag in topic_index:
        related = [
            {"id": row["id"], "title": row["title"]}
            for row in topic_index[weak_tag].get("recent_lessons") or []
        ]

    source_title = related[0]["title"] if related else ""
    if not source_title and related:
        source_title = related[0].get("title", "")

    lesson_block = {
        "id": rec_row.get("lesson_id"),
        "title": rec_row.get("lesson_title") or "",
        "course_id": rec_row.get("course_id"),
        "course_title": rec_row.get("course_title") or "",
    }

    rec_row["lesson"] = lesson_block
    rec_row["related_lessons_taken"] = related[:3]
    rec_row["reason"] = student_friendly_recommendation_reason(
        weak_topic_tag=rec_row.get("weak_topic_tag") or "",
        source_lesson_title=source_title,
        recommended_lesson_title=rec_row.get("lesson_title") or "",
        fallback=rec_row.get("reason") or "",
    )
    rec_row["focus_area"] = format_topic_label(rec_row.get("weak_topic_tag") or "")
    return rec_row


def _enrich_recommendation_weakness_fields(rec_row: dict, weakness_lookup: dict[str, WeakTopic]) -> dict:
    weak_tag = (rec_row.get("weak_topic_tag") or rec_row.get("triggered_by") or "").strip()
    if weak_tag.lower() in ("adaptive_engine", "learning_path", "weakness_overlap", ""):
        weak_tag = rec_row.get("weak_topic_tag") or ""
    if not weak_tag:
        rec_row.setdefault("weak_topic_tag", "")
        rec_row.setdefault("weakness_level", None)
        rec_row.setdefault("accuracy_percent", None)
        rec_row.setdefault("attempt_count", None)
        rec_row.setdefault("correct_count", None)
        return rec_row

    rec_row["weak_topic_tag"] = weak_tag
    wt = weakness_lookup.get(normalize_topic_tag(weak_tag))
    if wt:
        accuracy = round((wt.correct_count / wt.attempt_count) * 100, 1) if wt.attempt_count else 0
        rec_row["weakness_level"] = wt.weakness_level
        rec_row["accuracy_percent"] = accuracy
        rec_row["attempt_count"] = wt.attempt_count
        rec_row["correct_count"] = wt.correct_count
    else:
        rec_row.setdefault("weakness_level", None)
        rec_row.setdefault("accuracy_percent", None)
        rec_row.setdefault("attempt_count", None)
        rec_row.setdefault("correct_count", None)
    return rec_row


def topic_matches_course(topic_tag: str, course_id: int, context_index: dict[str, dict]) -> bool:
    ctx = context_index.get(normalize_topic_tag(topic_tag), {})
    course_ids = {row["id"] for row in ctx.get("courses") or []}
    return course_id in course_ids


def recommendation_matches_course(rec: Recommendation, course_id: int) -> bool:
    return rec.lesson.course_id == course_id


def lesson_weakness_summary(user_id: int, lesson: Lesson) -> dict[str, Any]:
    course = lesson.course
    result = (
        QuizResult.objects.filter(user_id=user_id, quiz__lesson_id=lesson.id)
        .select_related("quiz")
        .prefetch_related("quiz__questions")
        .order_by("-taken_at")
        .first()
    )

    if not result:
        return {
            "lesson": {"id": lesson.id, "title": lesson.title},
            "course": {"id": course.id, "title": course.title},
            "quiz_taken": False,
            "message": "Take the quiz to discover weak topics for this lesson.",
            "score": None,
            "weak_topics": [],
            "recommended_lessons": [],
        }

    weak_lookup = {
        normalize_topic_tag(wt.topic_tag): wt
        for wt in WeakTopic.objects.filter(user_id=user_id)
    }
    outcomes = _topic_outcomes_for_result(result)
    weak_topics = []
    for tag, counts in outcomes.items():
        if counts["total"] <= 0:
            continue
        accuracy = round((counts["correct"] / counts["total"]) * 100, 1)
        wt = weak_lookup.get(tag)
        if counts["correct"] == counts["total"] and not wt:
            continue
        weak_topics.append(
            {
                "topic_tag": tag,
                "weakness_level": wt.weakness_level if wt else None,
                "accuracy": round((wt.correct_count / wt.attempt_count) * 100, 1)
                if wt and wt.attempt_count
                else accuracy,
            }
        )

    group = {
        "lesson": {"id": lesson.id, "title": lesson.title},
        "course": {"id": course.id, "title": course.title},
        "weak_topics": weak_topics,
    }
    recommended = _recommendations_for_lesson_group(user_id, group)

    return {
        "lesson": {"id": lesson.id, "title": lesson.title},
        "course": {"id": course.id, "title": course.title},
        "quiz_taken": True,
        "score": result.score,
        "quiz_result_id": result.id,
        "weak_topics": weak_topics,
        "recommended_lessons": recommended,
        "message": "",
    }


def list_enrolled_courses_for_filter(user_id: int) -> list[dict]:
    return list(
        Course.objects.filter(enrollments__user_id=user_id)
        .order_by("title")
        .values("id", "title")
        .distinct()
    )
