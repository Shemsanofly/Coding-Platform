"""Validation helpers for AI-generated quiz JSON (no Gemini API calls)."""

from __future__ import annotations

import re
from typing import Any

ALLOWED_TYPES = frozenset({"mcq", "true_false"})
ALLOWED_DIFFICULTIES = frozenset({"easy", "medium", "hard"})
ALLOWED_BLOOM = frozenset({"remember", "understand", "apply", "analyze"})
OPINION_PATTERNS = re.compile(
    r"\b(in your opinion|do you think|what do you prefer|best ever|worst ever)\b",
    re.IGNORECASE,
)


class QuizGenerationError(Exception):
    pass


def normalize_topic_tag(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "general")[:100]


def post_process_questions(items: list[Any]) -> list[dict[str, Any]]:
    seen_stems: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in items:
        try:
            q = validate_question(raw)
        except QuizGenerationError:
            continue
        stem_key = re.sub(r"\s+", " ", q["question"].lower())
        if stem_key in seen_stems:
            continue
        if OPINION_PATTERNS.search(q["question"]):
            continue
        seen_stems.add(stem_key)
        out.append(q)
    if len(out) < 3:
        raise QuizGenerationError("Not enough valid questions after validation.")
    return out


def validate_question(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QuizGenerationError("Question must be an object.")
    question = str(raw.get("question", "")).strip()
    if len(question) < 15 or "?" not in question:
        raise QuizGenerationError("Question stem invalid.")

    qtype = str(raw.get("type", "")).strip().lower()
    if qtype not in ALLOWED_TYPES:
        raise QuizGenerationError("Invalid question type.")

    topic_tag = normalize_topic_tag(str(raw.get("topic_tag", "")))
    if not topic_tag or topic_tag == "general":
        raise QuizGenerationError("topic_tag is required and must be specific.")

    difficulty = str(raw.get("difficulty", "medium")).strip().lower()
    if difficulty not in ALLOWED_DIFFICULTIES:
        difficulty = "medium"

    bloom = str(raw.get("bloom_level", "understand")).strip().lower()
    if bloom not in ALLOWED_BLOOM:
        bloom = "understand"

    explanation = str(raw.get("explanation", "")).strip()
    if len(explanation) < 10:
        raise QuizGenerationError("Explanation too short.")

    options = raw.get("options")
    if not isinstance(options, list):
        raise QuizGenerationError("options must be a list.")
    options = [str(o).strip() for o in options if str(o).strip()]

    correct_answer = str(raw.get("correct_answer", "")).strip()
    if qtype == "true_false":
        if options != ["True", "False"]:
            raise QuizGenerationError('true_false options must be exactly ["True", "False"].')
        if correct_answer not in options:
            raise QuizGenerationError("true_false correct_answer must be True or False.")
    else:
        if len(options) != 4:
            raise QuizGenerationError("MCQ requires exactly 4 options.")
        if correct_answer not in options:
            raise QuizGenerationError("correct_answer must match an option.")

    if len(set(o.lower() for o in options)) < len(options):
        raise QuizGenerationError("Duplicate options.")

    return {
        "question": question,
        "type": qtype,
        "difficulty": difficulty,
        "bloom_level": bloom,
        "topic_tag": topic_tag,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
    }


def question_to_model_fields(q: dict[str, Any], *, is_published: bool = False) -> dict[str, Any]:
    correct_index = q["options"].index(q["correct_answer"])
    return {
        "stem": q["question"],
        "choices": q["options"],
        "correct_index": correct_index,
        "topic_tag": q["topic_tag"],
        "question_type": q["type"],
        "difficulty": q["difficulty"],
        "bloom_level": q["bloom_level"],
        "explanation": q["explanation"],
        "is_published": is_published,
    }
