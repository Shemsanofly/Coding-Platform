"""Read-only aggregates for admin dashboards (no AI pipeline changes)."""

from __future__ import annotations

from django.db.models import Avg, Count, Q

from ai_engine.models import LessonAIProcessing, WeakTopic
from courses.models import Course, Lesson
from django.db.models.functions import TruncDate

from progress.models import Enrollment
from quizzes.models import Question, Quiz, QuizResult


def _lessons_for_courses(course_ids: list[int]):
    if not course_ids:
        return Lesson.objects.none()
    return Lesson.objects.filter(course_id__in=course_ids)


def course_stats_by_id(course_ids: list[int]) -> dict[int, dict]:
    if not course_ids:
        return {}

    lesson_rows = list(
        _lessons_for_courses(course_ids).values_list("id", "course_id", "created_at")
    )
    lesson_ids = [row[0] for row in lesson_rows]
    lessons_by_course: dict[int, list[int]] = {cid: [] for cid in course_ids}
    last_updated: dict[int, str | None] = {cid: None for cid in course_ids}

    for lid, cid, created_at in lesson_rows:
        lessons_by_course.setdefault(cid, []).append(lid)
        stamp = created_at.isoformat() if created_at else None
        if stamp and (last_updated[cid] is None or stamp > last_updated[cid]):
            last_updated[cid] = stamp

    enroll_map = {
        row["course_id"]: row["total"]
        for row in Enrollment.objects.filter(course_id__in=course_ids)
        .values("course_id")
        .annotate(total=Count("id"))
    }

    quiz_rows = list(
        Quiz.objects.filter(lesson_id__in=lesson_ids).values(
            "lesson_id",
            "generation_status",
        )
    )
    lesson_to_course = {row[0]: row[1] for row in lesson_rows}

    question_stats = {
        row["quiz__lesson_id"]: row
        for row in Question.objects.filter(quiz__lesson_id__in=lesson_ids)
        .values("quiz__lesson_id")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(is_published=True)),
        )
    }

    stats = {
        cid: {
            "enrolled_students": enroll_map.get(cid, 0),
            "quiz_lessons_done": 0,
            "quiz_lessons_failed": 0,
            "quiz_lessons_pending": 0,
            "pending_approval_count": 0,
            "failed_generation_count": 0,
            "last_updated": last_updated.get(cid),
        }
        for cid in course_ids
    }

    for quiz in quiz_rows:
        cid = lesson_to_course.get(quiz["lesson_id"])
        if cid is None:
            continue
        status = quiz["generation_status"]
        if status == Quiz.GenerationStatus.DONE:
            stats[cid]["quiz_lessons_done"] += 1
        elif status == Quiz.GenerationStatus.FAILED:
            stats[cid]["failed_generation_count"] += 1
            stats[cid]["quiz_lessons_failed"] += 1
        else:
            stats[cid]["quiz_lessons_pending"] += 1

        qmeta = question_stats.get(quiz["lesson_id"])
        if status == Quiz.GenerationStatus.DONE and qmeta:
            unpublished = (qmeta["total"] or 0) - (qmeta["published"] or 0)
            if unpublished > 0:
                stats[cid]["pending_approval_count"] += 1

    return stats


def lesson_ai_fields_by_id(lesson_ids: list[int]) -> dict[int, dict]:
    if not lesson_ids:
        return {}

    processing_map = {
        row.lesson_id: row
        for row in LessonAIProcessing.objects.filter(lesson_id__in=lesson_ids)
    }
    quiz_map = {row.lesson_id: row for row in Quiz.objects.filter(lesson_id__in=lesson_ids)}
    question_counts = {
        row["quiz__lesson_id"]: row
        for row in Question.objects.filter(quiz__lesson_id__in=lesson_ids)
        .values("quiz__lesson_id")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(is_published=True)),
        )
    }

    payload = {}
    for lid in lesson_ids:
        processing = processing_map.get(lid)
        quiz = quiz_map.get(lid)
        qmeta = question_counts.get(lid) or {}
        total_q = qmeta.get("total") or 0
        published_q = qmeta.get("published") or 0
        quiz_status = quiz.generation_status if quiz else "pending"
        ai_status = processing.status if processing else "pending"

        if published_q > 0:
            approval_status = "published"
        elif quiz_status == Quiz.GenerationStatus.DONE and total_q > published_q:
            approval_status = "pending_approval"
        elif quiz_status == Quiz.GenerationStatus.FAILED:
            approval_status = "failed"
        elif quiz_status in (Quiz.GenerationStatus.PENDING, Quiz.GenerationStatus.PROCESSING):
            approval_status = "generating"
        else:
            approval_status = "none"

        payload[lid] = {
            "ai_processing_status": ai_status,
            "quiz_generation_status": quiz_status,
            "transcript_status": "ready" if processing and processing.transcript_text else "pending",
            "generated_question_count": total_q,
            "published_question_count": published_q,
            "approval_status": approval_status,
            "generation_error": (quiz.generation_error if quiz else "") or "",
            "transcript_error": (processing.last_error if processing else "") or "",
        }
    return payload


def admin_dashboard_summary(admin_user) -> dict:
    courses = Course.objects.filter(created_by=admin_user)
    course_ids = list(courses.values_list("id", flat=True))
    lesson_ids = list(_lessons_for_courses(course_ids).values_list("id", flat=True))

    status_counts = {
        row["status"]: row["total"] for row in courses.values("status").annotate(total=Count("id"))
    }
    total_courses = courses.count()
    published_courses = status_counts.get(Course.Status.PUBLISHED, 0)
    draft_courses = status_counts.get(Course.Status.DRAFT, 0)
    ready_courses = status_counts.get(Course.Status.READY, 0)

    from django.contrib.auth import get_user_model

    User = get_user_model()
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    active_enrollments = Enrollment.objects.filter(course_id__in=course_ids).count()

    quiz_qs = Quiz.objects.filter(lesson_id__in=lesson_ids) if lesson_ids else Quiz.objects.none()
    ai_quizzes_generated = quiz_qs.filter(generation_status=Quiz.GenerationStatus.DONE).count()
    failed_ai_generations = quiz_qs.filter(generation_status=Quiz.GenerationStatus.FAILED).count()

    pending_approval = 0
    if lesson_ids:
        done_lessons = set(
            quiz_qs.filter(generation_status=Quiz.GenerationStatus.DONE).values_list("lesson_id", flat=True)
        )
        for lid in done_lessons:
            if Question.objects.filter(quiz__lesson_id=lid, is_published=False).exists():
                pending_approval += 1

    top_weak = list(
        WeakTopic.objects.values("topic_tag")
        .annotate(student_count=Count("user_id", distinct=True))
        .order_by("-student_count")[:8]
    )

    recent_activity = []
    if lesson_ids:
        for result in (
            QuizResult.objects.filter(quiz__lesson_id__in=lesson_ids)
            .select_related("user", "quiz__lesson")
            .order_by("-taken_at")[:10]
        ):
            recent_activity.append(
                {
                    "type": "quiz_attempt",
                    "student_email": result.user.email,
                    "lesson_title": result.quiz.lesson.title,
                    "score": result.score,
                    "taken_at": result.taken_at,
                }
            )

    return {
        "total_courses": total_courses,
        "published_courses": published_courses,
        "draft_courses": draft_courses,
        "ready_courses": ready_courses,
        "total_students": total_students,
        "active_enrollments": active_enrollments,
        "ai_quizzes_generated": ai_quizzes_generated,
        "pending_quiz_approvals": pending_approval,
        "failed_ai_generations": failed_ai_generations,
        "top_weak_topics": [
            {"topic_tag": row["topic_tag"], "student_count": row["student_count"]} for row in top_weak
        ],
        "recent_activity": recent_activity,
    }


def admin_analytics_overview(admin_user) -> dict:
    courses = Course.objects.filter(created_by=admin_user)
    course_ids = list(courses.values_list("id", flat=True))

    completion_buckets = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for course in courses.annotate(lesson_count=Count("lessons", distinct=True)):
        lc = course.lesson_count or 0
        if lc == 0:
            completion_buckets["0-25"] += 1
            continue
        passed_lessons = (
            QuizResult.objects.filter(quiz__lesson__course_id=course.id, score__gte=60)
            .values("quiz__lesson_id")
            .distinct()
            .count()
        )
        pct = round((passed_lessons / lc) * 100)
        if pct <= 25:
            completion_buckets["0-25"] += 1
        elif pct <= 50:
            completion_buckets["26-50"] += 1
        elif pct <= 75:
            completion_buckets["51-75"] += 1
        else:
            completion_buckets["76-100"] += 1

    top_weak = list(
        WeakTopic.objects.values("topic_tag")
        .annotate(student_count=Count("user_id", distinct=True))
        .order_by("-student_count")[:10]
    )

    avg_score_by_course = []
    for course in courses.order_by("title"):
        avg = QuizResult.objects.filter(quiz__lesson__course_id=course.id).aggregate(value=Avg("score"))[
            "value"
        ]
        avg_score_by_course.append(
            {
                "course_id": course.id,
                "course_title": course.title,
                "avg_score": round(float(avg), 1) if avg is not None else None,
            }
        )

    lesson_ids = list(_lessons_for_courses(course_ids).values_list("id", flat=True))
    quiz_qs = Quiz.objects.filter(lesson_id__in=lesson_ids) if lesson_ids else Quiz.objects.none()
    ai_generation = {
        "success": quiz_qs.filter(generation_status=Quiz.GenerationStatus.DONE).count(),
        "failed": quiz_qs.filter(generation_status=Quiz.GenerationStatus.FAILED).count(),
        "pending": quiz_qs.exclude(
            generation_status__in=[Quiz.GenerationStatus.DONE, Quiz.GenerationStatus.FAILED]
        ).count(),
    }

    enrollment_trend = []
    if course_ids:
        trend_rows = list(
            Enrollment.objects.filter(course_id__in=course_ids)
            .annotate(day=TruncDate("enrolled_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        for row in trend_rows[-14:]:
            day = row["day"]
            enrollment_trend.append(
                {"date": day.isoformat() if day else "", "count": row["count"]}
            )

    return {
        "course_completion_distribution": [
            {"bucket": key, "count": value} for key, value in completion_buckets.items()
        ],
        "top_weak_topics": [
            {"topic_tag": row["topic_tag"], "student_count": row["student_count"]} for row in top_weak
        ],
        "avg_quiz_score_by_course": avg_score_by_course,
        "ai_generation_counts": ai_generation,
        "enrollment_trend": enrollment_trend,
    }
