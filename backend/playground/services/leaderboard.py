"""Playground XP totals and student leaderboard."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from playground.models import PlaygroundChallenge, PlaygroundSubmission

PLAYGROUND_TIERS = (
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
    current = PLAYGROUND_TIERS[0]
    next_tier = None
    for index, tier in enumerate(PLAYGROUND_TIERS):
        if xp >= tier[0]:
            current = tier
            next_tier = PLAYGROUND_TIERS[index + 1] if index + 1 < len(PLAYGROUND_TIERS) else None
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
    solve_days = {
        row.date()
        for row in PlaygroundChallenge.objects.filter(
            user_id=user_id,
            status=PlaygroundChallenge.Status.SOLVED,
            solved_at__isnull=False,
        ).values_list("solved_at", flat=True)
        if row
    }
    if not solve_days:
        return 0
    streak = 0
    day = now.date()
    while day in solve_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _weekly_activity(user_id: int, now=None) -> list[dict]:
    now = now or timezone.now()
    start = (now - timedelta(days=6)).date()
    counts = defaultdict(int)
    for submitted_at in PlaygroundSubmission.objects.filter(
        user_id=user_id,
        submitted_at__date__gte=start,
    ).values_list("submitted_at", flat=True):
        if submitted_at:
            counts[submitted_at.date()] += 1
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


def build_student_playground_stats(user_id: int) -> dict:
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return {}

    solved_qs = PlaygroundChallenge.objects.filter(
        user_id=user_id,
        status=PlaygroundChallenge.Status.SOLVED,
    )
    practice_xp = solved_qs.aggregate(total=Sum("xp_reward"))["total"] or 0
    challenges_solved = solved_qs.count()

    total_submissions = PlaygroundSubmission.objects.filter(user_id=user_id).count()
    passed_submissions = PlaygroundSubmission.objects.filter(user_id=user_id, passed=True).count()
    pass_rate = round((passed_submissions / total_submissions) * 100, 1) if total_submissions else 0.0

    tier = _tier_for_xp(practice_xp)
    return {
        "user_id": user.id,
        "display_name": _display_name(user),
        "learning_level": user.experience_level,
        "practice_xp": practice_xp,
        "challenges_solved": challenges_solved,
        "total_submissions": total_submissions,
        "pass_rate": pass_rate,
        "streak_days": _compute_streak(user_id),
        "tier_title": tier["title"],
        "tier_icon": tier["icon"],
        "tier_progress_pct": tier["progress_pct"],
        "next_tier_title": tier["next_title"],
        "next_tier_xp": tier["next_xp"],
        "weekly_activity": _weekly_activity(user_id),
    }


def build_playground_leaderboard(*, current_user_id: int, limit: int = 25) -> dict:
    students = User.objects.filter(role=User.Role.STUDENT, is_active=True).order_by("id")
    rows = []
    for student in students:
        stats = build_student_playground_stats(student.id)
        if stats and stats["challenges_solved"] > 0:
            rows.append(stats)

    rows.sort(
        key=lambda row: (
            -row["practice_xp"],
            -row["challenges_solved"],
            -row["pass_rate"],
            row["display_name"].lower(),
        )
    )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    current = next((row for row in rows if row["user_id"] == current_user_id), None)
    if current is None and current_user_id:
        current = build_student_playground_stats(current_user_id)
        if current:
            current["rank"] = None

    return {
        "leaderboard": rows[:limit],
        "total_students": len(rows),
        "me": current,
    }
