"""Tests for quiz persistence helpers."""

from django.test import TestCase

from accounts.models import User
from ai_engine.services.quiz_persistence import (
    persist_generated_questions,
    update_lesson_metadata_from_questions,
)
from courses.models import Course, Lesson
from quizzes.models import Question, Quiz


def _generated_row(**overrides):
    base = {
        "question": "What is encapsulation in OOP?",
        "type": "mcq",
        "difficulty": "easy",
        "bloom_level": "understand",
        "topic_tag": "encapsulation",
        "options": ["Hiding data", "A loop", "A file", "A socket"],
        "correct_answer": "Hiding data",
        "explanation": "Encapsulation bundles data with methods that operate on it.",
    }
    base.update(overrides)
    return base


class QuizPersistenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="persist@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
        )

    def test_persist_creates_quiz_and_questions(self):
        rows = [_generated_row(), _generated_row(topic_tag="inheritance"), _generated_row(topic_tag="polymorphism")]
        quiz = persist_generated_questions(self.lesson.pk, rows, publish=False)

        self.assertEqual(quiz.generation_status, Quiz.GenerationStatus.DONE)
        self.assertEqual(quiz.questions.count(), 3)
        self.assertFalse(quiz.questions.filter(is_published=True).exists())

    def test_persist_replaces_old_questions(self):
        persist_generated_questions(self.lesson.pk, [_generated_row()] * 3)
        persist_generated_questions(
            self.lesson.pk,
            [_generated_row(question="What is inheritance in OOP?")] * 3,
        )
        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertEqual(quiz.questions.count(), 3)
        stems = list(quiz.questions.values_list("stem", flat=True))
        self.assertTrue(all("inheritance" in s for s in stems))

    def test_update_lesson_metadata_merges_tags(self):
        rows = [
            _generated_row(topic_tag="encapsulation"),
            _generated_row(topic_tag="inheritance"),
            _generated_row(topic_tag="polymorphism"),
        ]
        update_lesson_metadata_from_questions(
            self.lesson,
            rows,
            learning_objective="Understand core OOP pillars.",
        )
        self.lesson.refresh_from_db()
        self.assertIn("encapsulation", self.lesson.tags)
        self.assertEqual(self.lesson.topic_tag, "encapsulation")
        self.assertIn("OOP pillars", self.lesson.learning_objective)
