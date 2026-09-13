"""Tests for lesson intelligence validation, enrichment, and admin preview."""

import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.models import LessonAIProcessing
from ai_engine.services.gemini_service import (
    GeminiQuizError,
    parse_gemini_response_json,
    validate_lesson_payload,
)
from ai_engine.services.quiz_persistence import apply_lesson_intelligence
from courses.models import Course, Lesson
from quizzes.models import Question, Quiz


def _valid_mcq(**overrides):
    base = {
        "question": "What is a class in Python?",
        "type": "mcq",
        "difficulty": "easy",
        "bloom_level": "understand",
        "topic_tag": "python_classes",
        "options": ["A blueprint", "A loop", "A file", "A socket"],
        "correct_answer": "A blueprint",
        "explanation": "Classes define object structure and behavior in Python.",
    }
    base.update(overrides)
    return base


def _full_payload_dict(**overrides):
    base = {
        "summary": (
            "This lesson introduces Python object-oriented programming, "
            "including classes, objects, and inheritance with practical examples."
        ),
        "learning_objectives": [
            "Explain what a Python class represents in object-oriented design.",
            "Describe how inheritance enables code reuse across types.",
            "Identify encapsulation as a core OOP principle.",
        ],
        "key_concepts": ["classes", "objects", "inheritance", "encapsulation"],
        "topic_tags": ["python_classes", "inheritance", "encapsulation"],
        "questions": [
            _valid_mcq(),
            _valid_mcq(
                question="What does inheritance provide in Python?",
                topic_tag="inheritance",
                options=["Code reuse", "Faster CPU", "More RAM", "Fewer files"],
                correct_answer="Code reuse",
                explanation="Child classes inherit attributes and methods from parents.",
            ),
            _valid_mcq(
                question="Encapsulation hides internal state?",
                type="true_false",
                topic_tag="encapsulation",
                options=["True", "False"],
                correct_answer="True",
                explanation="Encapsulation restricts direct access to internal data.",
            ),
        ],
    }
    base.update(overrides)
    return base


def _full_payload_json(**overrides) -> str:
    return json.dumps(_full_payload_dict(**overrides))


class LessonIntelligenceValidationTests(SimpleTestCase):
    def test_validates_full_payload(self):
        data = parse_gemini_response_json(_full_payload_json())
        payload = validate_lesson_payload(data)
        self.assertGreaterEqual(len(payload["summary"]), 40)
        self.assertGreaterEqual(len(payload["learning_objectives"]), 1)
        self.assertGreaterEqual(len(payload["key_concepts"]), 1)
        self.assertGreaterEqual(len(payload["topic_tags"]), 1)
        self.assertGreaterEqual(len(payload["questions"]), 3)

    def test_rejects_short_summary(self):
        data = _full_payload_dict(summary="Too short.")
        with self.assertRaises(GeminiQuizError):
            validate_lesson_payload(data)

    def test_legacy_questions_only_still_works(self):
        data = {"questions": _full_payload_dict()["questions"]}
        payload = validate_lesson_payload(data)
        self.assertIn("summary", payload)
        self.assertGreaterEqual(len(payload["questions"]), 3)


class ApplyLessonIntelligenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="intel@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(
            title="Intel Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )

    def test_fills_empty_lesson_fields(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title="OOP",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
            is_auto_generated=True,
        )
        payload = validate_lesson_payload(_full_payload_dict())
        apply_lesson_intelligence(lesson, payload)
        lesson.refresh_from_db()
        self.assertIn("object-oriented", lesson.content.lower())
        self.assertIn("•", lesson.learning_objective)
        self.assertIn("python_classes", lesson.tags)
        self.assertEqual(lesson.topic_tag, "python_classes")

    def test_does_not_overwrite_manual_content(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title="Manual",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=1,
            is_auto_generated=False,
            content="Instructor-authored summary that must remain.",
            learning_objective="Custom objective.",
            tags=["custom_tag"],
            topic_tag="custom_topic",
        )
        payload = validate_lesson_payload(_full_payload_dict())
        apply_lesson_intelligence(lesson, payload)
        lesson.refresh_from_db()
        self.assertEqual(lesson.content, "Instructor-authored summary that must remain.")
        self.assertEqual(lesson.learning_objective, "Custom objective.")
        self.assertEqual(lesson.tags, ["custom_tag"])
        self.assertEqual(lesson.topic_tag, "custom_topic")


class AdminPreviewIntelligenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="preview@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.course = Course.objects.create(
            title="Preview Course",
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            created_by=self.admin,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Preview Lesson",
            source_type=Lesson.SourceType.YOUTUBE,
            resource_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=0,
            content="Stored summary in lesson content field.",
        )
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        Question.objects.create(
            quiz=self.quiz,
            order=0,
            stem="What is OOP?",
            choices=["A", "B", "C", "D"],
            correct_index=0,
            topic_tag="oop",
            explanation="OOP organizes code around objects.",
        )
        LessonAIProcessing.objects.create(
            lesson=self.lesson,
            status=LessonAIProcessing.Status.COMPLETED,
            analysis_json={
                "summary": "AI summary from processing record.",
                "learning_objectives": ["Understand OOP basics."],
                "key_concepts": ["objects", "classes"],
                "topic_tags": ["oop", "classes"],
            },
        )

    def test_preview_includes_intelligence(self):
        url = reverse(
            "admin-lesson-quiz-preview",
            kwargs={"course_pk": self.course.pk, "lesson_pk": self.lesson.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"], "AI summary from processing record.")
        self.assertEqual(len(response.data["learning_objectives"]), 1)
        self.assertEqual(response.data["key_concepts"], ["objects", "classes"])
        self.assertEqual(len(response.data["questions"]), 1)
