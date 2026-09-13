from django.db.models import Avg, Count

from ai_engine.models import Recommendation, WeakTopic
from ai_engine.services.learning_path import generate_learning_path
from courses.models import Course, Lesson
from progress.models import Enrollment
from progress.serializers import EnrollmentSerializer, StudentAnalyticsSummarySerializer
from progress.services.completion import passed_lesson_ids_for_user
from quizzes.models import QuizResult


def build_student_analytics_summary(user):
    enrolled_course_ids = list(
        Enrollment.objects.filter(user=user).values_list("course_id", flat=True)
    )
    lesson_ids = list(
        Lesson.objects.filter(course_id__in=enrolled_course_ids).values_list("id", flat=True)
    )
    lessons_passed_quiz = len(passed_lesson_ids_for_user(user.id, lesson_ids))

    quiz_rows = QuizResult.objects.filter(user=user).select_related("quiz__lesson")
    attempts = quiz_rows.count()
    avg_score = quiz_rows.aggregate(value=Avg("score"))["value"] or 0
    recent_rows = quiz_rows.order_by("-taken_at")[:8]
    recent_quiz_scores = [
        {
            "score": row.score,
            "taken_at": row.taken_at,
            "lesson_title": (row.quiz.lesson.title if row.quiz and row.quiz.lesson else "") or "",
        }
        for row in recent_rows
    ]

    weak_tracked = WeakTopic.objects.filter(user=user).count()
    active_recs = Recommendation.objects.filter(user=user, status="active").count()
    total_lessons = len(lesson_ids)

    return {
        "enrolled_course_count": len(set(enrolled_course_ids)),
        "total_lessons_in_enrolled_courses": total_lessons,
        "lessons_passed_quiz": lessons_passed_quiz,
        "lessons_remaining": max(0, total_lessons - lessons_passed_quiz),
        "quiz_attempts_total": attempts,
        "avg_quiz_score": round(float(avg_score), 1),
        "weak_topics_tracked": weak_tracked,
        "active_recommendations_count": active_recs,
        "learning_level": getattr(user, "experience_level", None),
        "recent_quiz_scores": recent_quiz_scores,
    }


def build_student_enrollments(user):
    course_ids = list(Enrollment.objects.filter(user=user).values_list("course_id", flat=True))
    if not course_ids:
        return []

    courses = (
        Course.objects.filter(id__in=course_ids)
        .annotate(lesson_count=Count("lessons", distinct=True))
        .order_by("-created_at")
    )

    quiz_results = (
        QuizResult.objects.filter(user=user, quiz__lesson__course_id__in=course_ids)
        .select_related("quiz__lesson__course")
        .order_by("-taken_at")
    )
    by_course = {}
    for result in quiz_results:
        course_id = result.quiz.lesson.course_id
        if course_id not in by_course:
            by_course[course_id] = []
        by_course[course_id].append(result)

    payload = []
    for course in courses:
        rows = by_course.get(course.id, [])
        completed = len({row.quiz.lesson_id for row in rows})
        avg_score = round(sum(row.score for row in rows) / len(rows), 1) if rows else 0.0
        lesson_count = course.lesson_count or 0
        progress = round((completed / lesson_count) * 100, 1) if lesson_count else 0.0
        payload.append(
            {
                "id": course.id,
                "title": course.title,
                "level": course.level,
                "lesson_count": lesson_count,
                "lessons_completed": completed,
                "avg_quiz_score": avg_score,
                "progress": progress,
            }
        )
    return payload


def build_student_dashboard_payload(user):
    analytics = build_student_analytics_summary(user)
    enrollments = build_student_enrollments(user)
    learning_path = generate_learning_path(user.id)

    return {
        "analytics": StudentAnalyticsSummarySerializer(analytics).data,
        "enrollments": EnrollmentSerializer(enrollments, many=True).data,
        "learning_path": {
            "learning_path": learning_path.get("learning_path", []),
            "progress": learning_path.get("progress", {}),
        },
    }
