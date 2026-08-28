"""Lesson engagement thresholds and study completion."""

from __future__ import annotations

from django.db.models import Max
from django.utils import timezone

from accounts.models import User
from courses.models import Lesson
from progress.models import Enrollment, LessonProgress
from quizzes.models import Quiz, QuizResult


def engagement_threshold_seconds(lesson: Lesson) -> int:
    """Minimum engaged seconds (~70% of estimated seat time)."""
    return max(60, int(lesson.estimated_minutes * 60 * 0.7))


def engagement_met(lesson: Lesson, progress: LessonProgress | None) -> bool:
    if progress is None:
        return False
    if progress.seconds_engaged < engagement_threshold_seconds(lesson):
        return False

    if progress.video_watch_pct is not None:
        return progress.video_watch_pct >= 70
    return True


def quiz_passed_for_lesson(user_id: int, lesson_id: int) -> bool:
    return lesson_id in passed_lesson_ids_for_user(user_id, [lesson_id])


def passed_lesson_ids_for_user(user_id: int, lesson_ids: list[int]) -> set[int]:
    if not lesson_ids:
        return set()

    quizzes = {
        quiz.lesson_id: quiz
        for quiz in Quiz.objects.filter(
            lesson_id__in=lesson_ids,
            generation_status=Quiz.GenerationStatus.DONE,
        ).only("id", "lesson_id", "passing_score")
    }
    if not quizzes:
        return set()

    best_scores = dict(
        QuizResult.objects.filter(user_id=user_id, quiz_id__in=[quiz.id for quiz in quizzes.values()])
        .values("quiz_id")
        .annotate(best=Max("score"))
        .values_list("quiz_id", "best")
    )

    passed: set[int] = set()
    for lesson_id, quiz in quizzes.items():
        best = best_scores.get(quiz.id)
        if best is not None and best >= quiz.passing_score:
            passed.add(lesson_id)
    return passed


def refresh_lesson_official_completion(user_id: int, lesson_id: int) -> bool:
    """
    Sets completed_at when study engagement rules pass.
    Never clears completed_at from here.
    """
    lesson = Lesson.objects.filter(pk=lesson_id).only(
        "id",
        "estimated_minutes",
        "source_type",
    ).first()
    if lesson is None:
        return False

    progress, _ = LessonProgress.objects.get_or_create(user_id=user_id, lesson_id=lesson.id)
    if progress.completed_at:
        return True

    if not engagement_met(lesson, progress):
        return False

    progress.completed_at = timezone.now()
    progress.save(update_fields=["completed_at"])
    return True


def student_completion_rate_percent(user_id: int) -> float | None:
    enrolled_course_ids = Enrollment.objects.filter(user_id=user_id).values_list("course_id", flat=True)
    lesson_ids = list(
        Lesson.objects.filter(course_id__in=enrolled_course_ids).values_list("id", flat=True)
    )
    if not lesson_ids:
        return None
    passed = len(passed_lesson_ids_for_user(user_id, lesson_ids))
    return round(100 * passed / len(lesson_ids), 2)


def maybe_adjust_experience_level(user_id: int) -> None:
    """Moves declared student level up/down based on aggregate quiz performance (adaptive engine)."""
    user = User.objects.filter(pk=user_id).only("id", "role", "experience_level").first()
    if user is None or user.role != User.Role.STUDENT:
        return

    scores = list(QuizResult.objects.filter(user_id=user_id).values_list("score", flat=True))
    if len(scores) < 2:
        return

    avg = sum(scores) / len(scores)
    completion = student_completion_rate_percent(user_id)
    failures_under_40 = QuizResult.objects.filter(user_id=user_id, score__lt=40).count()

    order = [
        User.ExperienceLevel.BEGINNER,
        User.ExperienceLevel.INTERMEDIATE,
        User.ExperienceLevel.ADVANCED,
    ]
    current = user.experience_level or User.ExperienceLevel.BEGINNER
    try:
        idx = order.index(current)
    except ValueError:
        idx = 0

    new_idx = idx
    if avg >= 80 and completion is not None and completion >= 85 and idx < len(order) - 1:
        new_idx = idx + 1
    elif avg < 40 and failures_under_40 >= 3 and idx > 0:
        new_idx = idx - 1
    else:
        return

    new_level = order[new_idx]
    if new_level != user.experience_level:
        user.experience_level = new_level
        user.save(update_fields=["experience_level"])


def apply_engagement_update(
    *,
    user_id: int,
    lesson_id: int,
    delta_seconds: int = 0,
    scroll_depth_pct: int | None = None,
    video_watch_pct: int | None = None,
) -> LessonProgress:
    progress, _ = LessonProgress.objects.get_or_create(user_id=user_id, lesson_id=lesson_id)

    delta_seconds = max(0, min(int(delta_seconds), 3600))
    if delta_seconds:
        progress.seconds_engaged = min(progress.seconds_engaged + delta_seconds, 86400)

    if scroll_depth_pct is not None:
        scroll_depth_pct = max(0, min(int(scroll_depth_pct), 100))
        progress.max_scroll_depth_pct = max(progress.max_scroll_depth_pct, scroll_depth_pct)

    if video_watch_pct is not None:
        video_watch_pct = max(0, min(int(video_watch_pct), 100))
        if progress.video_watch_pct is None:
            progress.video_watch_pct = video_watch_pct
        else:
            progress.video_watch_pct = max(progress.video_watch_pct, video_watch_pct)

    progress.save()
    refresh_lesson_official_completion(user_id, lesson_id)
    return progress
