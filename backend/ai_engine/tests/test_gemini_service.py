"""Unit tests for GeminiService parsing and validation (no live API calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import SimpleTestCase, override_settings

from ai_engine.services.gemini_service import (
    GeminiQuizError,
    GeminiService,
    INVALID_GEMINI_API_KEY_MESSAGE,
    is_invalid_gemini_api_key_error,
    parse_gemini_questions_json,
    parse_gemini_response_json,
    validate_lesson_payload,
    validate_question_count,
)
from ai_engine.tests.test_lesson_intelligence import _full_payload_dict, _full_payload_json
from ai_engine.services.quiz_generator import (
    QuizGenerationError,
    post_process_questions,
    validate_question,
)


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


def _sample_payload(count: int = 3) -> str:
    questions = []
    for i in range(count):
        questions.append(
            _valid_mcq(
                question=f"What is concept {i} in Python?",
                topic_tag=f"topic_{i}",
            )
        )
    return _full_payload_json(questions=questions)


class ParseGeminiJsonTests(SimpleTestCase):
    def test_parses_full_response(self):
        data = parse_gemini_response_json(_full_payload_json())
        self.assertIn("summary", data)
        self.assertIn("questions", data)

    def test_parses_wrapped_questions(self):
        items = parse_gemini_questions_json(_sample_payload(3))
        self.assertEqual(len(items), 3)

    def test_parses_fenced_json(self):
        raw = f"```json\n{_sample_payload(3)}\n```"
        items = parse_gemini_questions_json(raw)
        self.assertEqual(len(items), 3)

    def test_rejects_invalid_json(self):
        with self.assertRaises(GeminiQuizError):
            parse_gemini_questions_json("not json")

    def test_rejects_missing_questions_key(self):
        with self.assertRaises(GeminiQuizError):
            parse_gemini_questions_json('{"items": []}')


class ValidateQuestionCountTests(SimpleTestCase):
    def test_rejects_too_few(self):
        with self.assertRaises(GeminiQuizError):
            validate_question_count([_valid_mcq()])

    def test_accepts_minimum(self):
        validate_question_count([_valid_mcq()] * 3)


class PostProcessTests(SimpleTestCase):
    def test_rejects_when_correct_answer_missing_from_options(self):
        bad = _valid_mcq(correct_answer="Not in list")
        with self.assertRaises(QuizGenerationError):
            post_process_questions([bad, _valid_mcq(), _valid_mcq()])

    def test_requires_explanation(self):
        bad = _valid_mcq(explanation="short")
        with self.assertRaises(QuizGenerationError):
            validate_question(bad)


class GeminiServiceGenerateTests(SimpleTestCase):
    @patch("google.genai.Client")
    def test_generate_quiz_returns_validated_questions(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.text = _sample_payload(4)
        mock_client_cls.return_value.models.generate_content.return_value = mock_response

        svc = GeminiService(api_key="test-key", model="gemini-2.5-flash")
        result = svc.generate_quiz(" ".join(["lesson content"] * 30))

        self.assertGreaterEqual(len(result["questions"]), 3)
        self.assertGreaterEqual(len(result["summary"]), 40)
        self.assertGreaterEqual(len(result["learning_objectives"]), 1)
        self.assertEqual(result["questions"][0]["type"], "mcq")
        self.assertIn("topic_tag", result["questions"][0])

    @patch("google.genai.Client")
    def test_generate_quiz_raises_on_malformed_json(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.text = '{"broken": true}'
        mock_client_cls.return_value.models.generate_content.return_value = mock_response

        svc = GeminiService(api_key="test-key")
        with self.assertRaises(GeminiQuizError):
            svc.generate_quiz(" ".join(["lesson content"] * 30))

    @patch("google.genai.Client")
    def test_generate_quiz_maps_invalid_api_key_error(self, mock_client_cls):
        from google.api_core.exceptions import InvalidArgument

        mock_client_cls.return_value.models.generate_content.side_effect = InvalidArgument(
            "400 API key not valid. Please pass a valid API key."
        )

        svc = GeminiService(api_key="bad-key")
        with self.assertRaises(GeminiQuizError) as ctx:
            svc.generate_quiz(" ".join(["lesson content"] * 30))

        self.assertEqual(str(ctx.exception), INVALID_GEMINI_API_KEY_MESSAGE)

    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_raises(self):
        with self.assertRaises(GeminiQuizError):
            GeminiService()

    @patch("google.genai.Client")
    def test_generate_student_support_response_returns_text(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.text = "Use a for loop when you know the collection you want to visit."
        mock_client_cls.return_value.models.generate_content.return_value = mock_response

        svc = GeminiService(api_key="test-key")
        result = svc.generate_student_support_response(
            "When should I use a for loop?",
            history=[{"role": "student", "content": "I am learning loops."}],
            student_level="beginner",
            page_path="/lessons/2",
        )

        self.assertIn("for loop", result)
        mock_client_cls.return_value.models.generate_content.assert_called_once()


@override_settings(GEMINI_API_KEY="fake-key")
def test_gemini_service_reads_api_key_from_settings():
    service = GeminiService()
    assert service.api_key == "fake-key"


@override_settings(GEMINI_API_KEY="fake-key")
def test_gemini_service_uses_available_default_model():
    service = GeminiService()
    assert service.model_name == "gemini-3.5-flash"


@override_settings(GEMINI_API_KEY="fake-key", GEMINI_MODEL="")
def test_gemini_service_uses_available_default_model_when_setting_blank():
    service = GeminiService()
    assert service.model_name == "gemini-3.5-flash"


@override_settings(GEMINI_API_KEY="", GOOGLE_API_KEY="google-key")
def test_gemini_service_falls_back_to_google_api_key_setting():
    service = GeminiService()
    assert service.api_key == "google-key"


@override_settings(GEMINI_API_KEY="replace_with_your_gemini_key")
def test_gemini_service_rejects_placeholder_key_from_settings():
    with pytest.raises(GeminiQuizError, match=INVALID_GEMINI_API_KEY_MESSAGE):
        GeminiService()


@override_settings(GEMINI_API_KEY="")
def test_gemini_service_raises_when_settings_key_empty():
    with pytest.raises(GeminiQuizError):
        GeminiService()


def test_is_invalid_gemini_api_key_error_detects_google_message():
    assert is_invalid_gemini_api_key_error(
        Exception("400 API key not valid. Please pass a valid API key.")
    )
    assert not is_invalid_gemini_api_key_error(Exception("network timeout"))
