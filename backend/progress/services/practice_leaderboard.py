"""Practice XP and leaderboard derived from quiz attempts and lesson completion."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from progress.models import LessonProgress
from progress.services.completion import quiz_passed_for_lesson
from quizzes.models import Quiz, QuizResult

PRACTICE_TIERS = (
    (0, "Novice", "🌱"),
    (100, "Apprentice", "⌨️"),
    (300, "Coder", "💻"),
    (700, "Builder", "🛠️"),
    (1500, "Pro", "🚀"),
    (3000, "Expert", "🏆"),
)


def _display_name(user) -> str:
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if full:
        return full
    return (user.email or "Student").split("@")[0]


def _tier_for_xp(xp: int) -> dict:
    current = PRACTICE_TIERS[0]
    next_tier = None
    for index, tier in enumerate(PRACTICE_TIERS):
        if xp >= tier[0]:
            current = tier
            next_tier = PRACTICE_TIERS[index + 1] if index + 1 < len(PRACTICE_TIERS) else None
    xp_floor, title, icon = current
    if next_tier:
        next_xp, next_title, _ = next_tier
        span = max(1, next_xp - xp_floor)
        progress_pct = round(min(100, max(0, ((xp - xp_floor) / span) * 100)))
    else:
        next_title = None
        next_xp = None
        progress_pct = 100
    return {
        "title": title,
        "icon": icon,
        "xp_floor": xp_floor,
        "next_title": next_title,
        "next_xp": next_xp,
        "progress_pct": progress_pct,
    }


def _compute_streak(user_id: int, now=None) -> int:
    now = now or timezone.now()
    attempt_days = {
        row.date()
        for row in QuizResult.objects.filter(user_id=user_id).values_list("taken_at", flat=True)
        if row
    }
    if not attempt_days:
        return 0
    streak = 0
    day = now.date()
    while day in attempt_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _weekly_activity(user_id: int, now=None) -> list[dict]:
    now = now or timezone.now()
    start = (now - timedelta(days=6)).date()
    counts = defaultdict(int)
    for taken_at in QuizResult.objects.filter(user_id=user_id, taken_at__date__gte=start).values_list(
        "taken_at", flat=True
    ):
        if taken_at:
            counts[taken_at.date()] += 1
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    payload = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        payload.append(
            {
                "label": labels[day.weekday()],
                "date": day.isoformat(),
                "attempts": counts.get(day, 0),
            }
        )
    max_attempts = max((item["attempts"] for item in payload), default=0) or 1
    for item in payload:
        item["height_pct"] = round((item["attempts"] / max_attempts) * 100)
    return payload


def build_student_practice_stats(user_id: int) -> dict:
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return {}

    results = list(
        QuizResult.objects.filter(user_id=user_id)
        .select_related("quiz")
        .order_by("-taken_at")
    )
    quiz_attempts = len(results)
    scores = [row.score for row in results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    best_by_lesson: dict[int, int] = {}
    for row in results:
        lesson_id = row.quiz.lesson_id
        best_by_lesson[lesson_id] = max(best_by_lesson.get(lesson_id, 0), row.score)

    exercises_passed = 0
    for lesson_id, best_score in best_by_lesson.items():
        quiz = Quiz.objects.filter(lesson_id=lesson_id).only("passing_score", "generation_status").first()
        if quiz and quiz.generation_status == Quiz.GenerationStatus.DONE and best_score >= quiz.passing_score:
            exercises_passed += 1

    lessons_mastered = sum(
        1
        for lesson_id in best_by_lesson
        if quiz_passed_for_lesson(user_id, lesson_id)
    )
    official_completed = LessonProgress.objects.filter(user_id=user_id, completed_at__isnull=False).count()

    xp = quiz_attempts * 10
    for best_score in best_by_lesson.values():
        xp += 15 + best_score
    xp += exercises_passed * 40
    xp += official_completed * 25

    tier = _tier_for_xp(xp)
    return {
        "user_id": user.id,
        "display_name": _display_name(user),
        "learning_level": user.experience_level,
        "practice_xp": xp,
        "quiz_attempts": quiz_attempts,
        "exercises_passed": exercises_passed,
        "lessons_mastered": lessons_mastered,
        "lessons_completed": official_completed,
        "avg_score": avg_score,
        "streak_days": _compute_streak(user_id),
        "tier_title": tier["title"],
        "tier_icon": tier["icon"],
        "tier_progress_pct": tier["progress_pct"],
        "next_tier_title": tier["next_title"],
        "next_tier_xp": tier["next_xp"],
        "weekly_activity": _weekly_activity(user_id),
    }


def build_practice_leaderboard(*, current_user_id: int, limit: int = 25) -> dict:
    students = User.objects.filter(role=User.Role.STUDENT, is_active=True).order_by("id")
    rows = []
    for student in students:
        stats = build_student_practice_stats(student.id)
        if stats:
            rows.append(stats)

    rows.sort(
        key=lambda row: (
            -row["practice_xp"],
            -row["exercises_passed"],
            -row["avg_score"],
            row["display_name"].lower(),
        )
    )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    current = next((row for row in rows if row["user_id"] == current_user_id), None)
    if current is None and current_user_id:
        current = build_student_practice_stats(current_user_id)
        if current:
            current["rank"] = None

    return {
        "leaderboard": rows[:limit],
        "total_students": len(rows),
        "me": current,
    }
