"""Course and lesson domain helpers (unlock rules, gating)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count

from courses.models import Course, Lesson
from quizzes.models import Quiz, QuizResult

User = get_user_model()


@dataclass(frozen=True)
class LessonGate:
    lesson_id: int
    order: int
    unlocked: bool
    quiz_passed: bool
    quiz_ready: bool


def lesson_gates_for_user(course: Course, user: User) -> list[LessonGate]:
    """
    Sequential unlock: lesson 0 is always reachable; lesson n requires passing the quiz
    for lesson n-1 (when that quiz exists and is generated).
    """
    lessons: Iterable[Lesson] = course.lessons.order_by("order", "pk")
    rows: list[LessonGate] = []
    previous_passed = True

    quiz_rows = (
        Quiz.objects.filter(lesson__course_id=course.id)
        .annotate(published_count=Count("questions", filter=models.Q(questions__is_published=True)))
        .select_related("lesson")
    )
    quiz_by_lesson: dict[int, Quiz] = {}
    published_count_by_lesson: dict[int, int] = {}
    for q in quiz_rows:
        quiz_by_lesson[q.lesson_id] = q
        published_count_by_lesson[q.lesson_id] = q.published_count

    best_score: dict[int, int] = {}
    for result in QuizResult.objects.filter(
        user=user, quiz__lesson__course_id=course.id
    ).select_related("quiz"):
        lid = result.quiz.lesson_id
        best_score[lid] = max(best_score.get(lid, 0), result.score)

    for lesson in lessons:
        unlocked = previous_passed
        quiz = quiz_by_lesson.get(lesson.id)
        pub_count = published_count_by_lesson.get(lesson.id, 0)
        quiz_ready = bool(
            quiz and quiz.generation_status == Quiz.GenerationStatus.DONE and pub_count > 0
        )
        passed = False
        if quiz_ready and quiz is not None:
            score = best_score.get(lesson.id)
            passed = score is not None and score >= quiz.passing_score

        if quiz is None or not quiz_ready:
            chain_released = unlocked
        else:
            chain_released = passed

        rows.append(
            LessonGate(
                lesson_id=lesson.id,
                order=lesson.order,
                unlocked=unlocked,
                quiz_passed=passed,
                quiz_ready=quiz_ready,
            )
        )
        previous_passed = chain_released

    return rows


def lesson_unlocked(course: Course, user: User, lesson: Lesson) -> bool:
    gates = {g.lesson_id: g for g in lesson_gates_for_user(course, user)}
    gate = gates.get(lesson.id)
    return bool(gate and gate.unlocked)
