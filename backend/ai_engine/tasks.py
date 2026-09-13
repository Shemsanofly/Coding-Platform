import logging
from collections import defaultdict

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from ai_engine.services.generation_mode import get_ai_generation_mode
from ai_engine.services.task_queue import run_or_enqueue

logger = logging.getLogger(__name__)


@shared_task
def detect_weaknesses(user_id, quiz_result_id):
    from ai_engine.models import WeakTopic
    from ai_engine.tasks import generate_recommendations
    from quizzes.models import QuizResult

    try:
        result = QuizResult.objects.select_related("quiz").get(id=quiz_result_id)
    except QuizResult.DoesNotExist:
        logger.warning("detect_weaknesses: quiz result %s not found", quiz_result_id)
        return

    questions = result.quiz.questions.all().order_by("id")
    answers = result.answers or []

    topic_outcomes = defaultdict(lambda: {"correct": 0, "total": 0})
    for i, q in enumerate(questions):
        tag = q.topic_tag
        topic_outcomes[tag]["total"] += 1
        if i < len(answers) and answers[i] == q.correct_index:
            topic_outcomes[tag]["correct"] += 1

    for tag, counts in topic_outcomes.items():
        wt, _ = WeakTopic.objects.get_or_create(
            user_id=user_id,
            topic_tag=tag,
            defaults={"attempt_count": 0, "correct_count": 0},
        )
        wt.attempt_count += counts["total"]
        wt.correct_count += counts["correct"]

        accuracy = wt.correct_count / wt.attempt_count if wt.attempt_count else 0
        if accuracy >= 0.80:
            wt.weakness_level = None
        elif accuracy >= 0.55:
            wt.weakness_level = "LOW"
        elif accuracy >= 0.35:
            wt.weakness_level = "MEDIUM"
        else:
            wt.weakness_level = "HIGH"

        wt.last_updated = now()
        wt.save()

    run_or_enqueue(
        generate_recommendations,
        user_id,
        mode=get_ai_generation_mode(),
    )

    from progress.services import maybe_adjust_experience_level

    maybe_adjust_experience_level(user_id)


def _clear_user_recommendations(user_id):
    from ai_engine.models import Recommendation

    Recommendation.objects.filter(user_id=user_id).delete()


def _lesson_tag_tokens(lesson):

    tags = list(lesson.tags or [])
    if lesson.topic_tag:
        tags.append(lesson.topic_tag)
    out = set()
    for raw in tags:
        token = (raw or "").strip().lower()
        if token:
            out.add(token)
    return out


def _best_scores_by_lesson(user_id):
    best = {}
    from quizzes.models import QuizResult

    for row in QuizResult.objects.filter(user_id=user_id).select_related("quiz"):
        lid = row.quiz.lesson_id
        best[lid] = max(best.get(lid, 0), row.score)
    return best


def _passed_lesson_ids(user_id, best_scores):
    from quizzes.models import Quiz

    passed = set()
    for lid, score in best_scores.items():
        quiz = Quiz.objects.filter(lesson_id=lid).only("passing_score").first()
        if quiz and score >= quiz.passing_score:
            passed.add(lid)
    return passed


@shared_task
def generate_recommendations(user_id):
    from ai_engine.models import Recommendation, WeakTopic
    from courses.models import Lesson
    from progress.models import Enrollment, LessonProgress
    from quizzes.models import QuizResult

    User = get_user_model()
    _clear_user_recommendations(user_id)

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return 0

    weak_topics = list(
        WeakTopic.objects.filter(user_id=user_id, weakness_level__in=["HIGH", "MEDIUM"]).order_by(
            "-last_updated"
        )
    )
    weak_tag_set = {w.topic_tag.strip().lower() for w in weak_topics if w.topic_tag}

    enrolled_ids = list(
        Enrollment.objects.filter(user_id=user_id).values_list("course_id", flat=True)
    )
    if not enrolled_ids:
        return 0

    best_scores = _best_scores_by_lesson(user_id)
    passed_ids = _passed_lesson_ids(user_id, best_scores)

    recent_scores = list(
        QuizResult.objects.filter(user_id=user_id)
        .order_by("-taken_at")
        .values_list("score", flat=True)[:5]
    )
    recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else None

    all_scores = list(QuizResult.objects.filter(user_id=user_id).values_list("score", flat=True))
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else None

    first_enroll = Enrollment.objects.filter(user_id=user_id).order_by("enrolled_at").first()
    days_active = 1
    if first_enroll:
        days_active = max(1, (now() - first_enroll.enrolled_at).days + 1)
    attempt_rate = len(all_scores) / days_active

    exp = (getattr(user, "experience_level", None) or "").lower()
    slow_learner = attempt_rate < 0.12 and len(all_scores) >= 2
    struggling = (recent_avg is not None and recent_avg < 50 and len(recent_scores) >= 2) or (
        overall_avg is not None and overall_avg < 55 and len(all_scores) >= 3
    )
    performing_well = (recent_avg is not None and recent_avg >= 82) or (
        overall_avg is not None and overall_avg >= 85
    )

    lessons = Lesson.objects.filter(course_id__in=enrolled_ids).select_related("course")
    ranked = {}

    for lesson in lessons:
        score = 0
        reasons = []
        tokens = _lesson_tag_tokens(lesson)

        for wt in weak_topics:
            tag = (wt.topic_tag or "").strip().lower()
            if not tag:
                continue
            if tag in tokens:
                score += 55
                reasons.append(f"Targets weak area '{wt.topic_tag}'.")
                break

        if weak_tag_set & tokens:
            score += 10

        if struggling and lesson.difficulty == Lesson.Difficulty.BEGINNER:
            score += 35
            reasons.append("Beginner-friendly material because recent quiz scores are low.")

        if struggling and lesson.source_type == Lesson.SourceType.YOUTUBE:
            score += 20
            reasons.append("Video lesson to rebuild fundamentals.")

        if slow_learner and lesson.estimated_minutes <= 18:
            score += 25
            reasons.append("Short lesson to match a slower study pace.")

        if performing_well and lesson.difficulty == Lesson.Difficulty.ADVANCED:
            score += 40
            reasons.append("Advanced stretch goal while you are performing strongly.")

        if performing_well and lesson.source_type == Lesson.SourceType.YOUTUBE:
            score += 10
            reasons.append("Video deep-dive for strong learners.")

        if exp == "beginner" and lesson.difficulty == Lesson.Difficulty.BEGINNER:
            score += 8
        if exp == "advanced" and lesson.difficulty == Lesson.Difficulty.ADVANCED:
            score += 8

        if lesson.id not in passed_ids:
            score += 5

        if LessonProgress.objects.filter(
            user_id=user_id, lesson=lesson, completed_at__isnull=False
        ).exists():
            score -= 8

        if score <= 0:
            continue

        reason = (
            "; ".join(dict.fromkeys(reasons))
            if reasons
            else "Adaptive match for your learning path."
        )
        prev = ranked.get(lesson.id)
        if not prev or score > prev[0]:
            ranked[lesson.id] = (score, lesson, reason)

    ordered = sorted(ranked.values(), key=lambda row: (-row[0], row[1].course_id, row[1].order))
    created = 0
    for _score, lesson, reason in ordered[:8]:
        weak_tag = ""
        for wt in weak_topics:
            t = (wt.topic_tag or "").strip().lower()
            if t and t in _lesson_tag_tokens(lesson):
                weak_tag = wt.topic_tag
                break
        Recommendation.objects.create(
            user_id=user_id,
            lesson=lesson,
            reason=reason,
            weak_topic_tag=weak_tag,
            status="active",
        )
        created += 1

    if created == 0:
        fallback = (
            Lesson.objects.filter(course_id__in=enrolled_ids)
            .exclude(id__in=passed_ids)
            .order_by("course_id", "order", "pk")[:3]
        )
        for lesson in fallback:
            Recommendation.objects.create(
                user_id=user_id,
                lesson=lesson,
                reason="Suggested next lesson in your enrolled path.",
                weak_topic_tag="",
                status="active",
            )
            created += 1

    return created


@shared_task
def process_video_lesson(lesson_id: int) -> int | None:
    """Thin Celery entry point — all AI logic lives in youtube_pipeline."""
    from ai_engine.services.youtube_pipeline import generate_quiz_for_youtube_lesson

    return generate_quiz_for_youtube_lesson(lesson_id)
