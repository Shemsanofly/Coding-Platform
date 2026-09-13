"""Generate coding playground challenges with Gemini or curated fallbacks."""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, TypedDict

from django.conf import settings

from ai_engine.services.gemini_service import is_invalid_gemini_api_key_error

logger = logging.getLogger(__name__)

PLAYGROUND_SYSTEM_PROMPT = """You are a Python coding coach for an e-learning platform.

Generate ONE small coding exercise. Return ONLY valid JSON (no markdown):
{
  "title": "Short title",
  "description": "Clear instructions with one example. Tell the student to implement `solution`.",
  "difficulty": "beginner|intermediate|advanced",
  "starter_code": "def solution(...):\\n    pass",
  "test_cases": [{"args": [1, 2], "expected": 3}],
  "xp_reward": 40
}

Rules:
- The student must implement a function named exactly `solution`.
- Use only Python built-ins (no imports).
- Provide 3 to 5 test_cases. Each has `args` (list of positional arguments) and `expected` (JSON value).
- `starter_code` must include the same `solution` signature used by the tests.
- Match difficulty to the requested learner level.
- xp_reward: beginner 30-50, intermediate 50-80, advanced 80-120.
- Keep problems solvable in under 20 lines.
- Do not repeat common textbook titles verbatim; vary topics (strings, lists, math, logic)."""


class ChallengePayload(TypedDict):
    title: str
    description: str
    difficulty: str
    starter_code: str
    test_cases: list[dict[str, Any]]
    xp_reward: int


FALLBACK_CHALLENGES: list[ChallengePayload] = [
    {
        "title": "Sum Two Numbers",
        "description": (
            "Write a function `solution(a, b)` that returns the sum of two numbers.\n\n"
            "Example: solution(2, 3) should return 5."
        ),
        "difficulty": "beginner",
        "starter_code": "def solution(a, b):\n    # Return the sum of a and b\n    pass\n",
        "test_cases": [
            {"args": [2, 3], "expected": 5},
            {"args": [0, 0], "expected": 0},
            {"args": [-4, 9], "expected": 5},
        ],
        "xp_reward": 40,
    },
    {
        "title": "Reverse a String",
        "description": (
            "Write `solution(text)` that returns the reverse of the given string.\n\n"
            "Example: solution('hello') returns 'olleh'."
        ),
        "difficulty": "beginner",
        "starter_code": "def solution(text):\n    # Return reversed text\n    pass\n",
        "test_cases": [
            {"args": ["hello"], "expected": "olleh"},
            {"args": [""], "expected": ""},
            {"args": ["abc"], "expected": "cba"},
        ],
        "xp_reward": 45,
    },
    {
        "title": "Count Vowels",
        "description": (
            "Write `solution(text)` that counts vowels (a, e, i, o, u) in a lowercase string.\n\n"
            "Example: solution('learncode') returns 4."
        ),
        "difficulty": "intermediate",
        "starter_code": "def solution(text):\n    # Count vowels in text\n    pass\n",
        "test_cases": [
            {"args": ["learncode"], "expected": 4},
            {"args": ["xyz"], "expected": 0},
            {"args": ["education"], "expected": 5},
        ],
        "xp_reward": 60,
    },
    {
        "title": "Unique Sorted List",
        "description": (
            "Write `solution(items)` that returns a sorted list of unique numbers.\n\n"
            "Example: solution([3, 1, 2, 1]) returns [1, 2, 3]."
        ),
        "difficulty": "intermediate",
        "starter_code": "def solution(items):\n    # Return sorted unique values\n    pass\n",
        "test_cases": [
            {"args": [[3, 1, 2, 1]], "expected": [1, 2, 3]},
            {"args": [[5, 5, 5]], "expected": [5]},
            {"args": [[]], "expected": []},
        ],
        "xp_reward": 65,
    },
    {
        "title": "Is Palindrome",
        "description": (
            "Write `solution(text)` that returns True if `text` reads the same forwards and backwards.\n\n"
            "Example: solution('level') returns True."
        ),
        "difficulty": "advanced",
        "starter_code": "def solution(text):\n    # Return True if text is a palindrome\n    pass\n",
        "test_cases": [
            {"args": ["level"], "expected": True},
            {"args": ["python"], "expected": False},
            {"args": ["racecar"], "expected": True},
        ],
        "xp_reward": 90,
    },
]


class ChallengeGenerationError(Exception):
    pass


def _parse_challenge_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ChallengeGenerationError("Challenge payload must be a JSON object.")
    return data


def _normalize_level(level: str | None) -> str:
    value = (level or "beginner").strip().lower()
    if value in {"intermediate", "advanced"}:
        return value
    return "beginner"


def _validate_test_cases(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) < 3:
        raise ChallengeGenerationError("test_cases must include at least 3 cases.")
    cases = []
    for item in raw[:5]:
        if not isinstance(item, dict):
            raise ChallengeGenerationError("Each test case must be an object.")
        args = item.get("args")
        if not isinstance(args, list):
            raise ChallengeGenerationError("Each test case needs an args list.")
        if "expected" not in item:
            raise ChallengeGenerationError("Each test case needs expected.")
        json.dumps({"args": args, "expected": item["expected"]})
        cases.append({"args": args, "expected": item["expected"]})
    return cases


def validate_challenge_payload(data: dict[str, Any]) -> ChallengePayload:
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    starter_code = str(data.get("starter_code", "")).strip()
    difficulty = str(data.get("difficulty", "beginner")).strip().lower()
    xp_reward = int(data.get("xp_reward", 50))

    if len(title) < 4:
        raise ChallengeGenerationError("title is too short.")
    if len(description) < 20:
        raise ChallengeGenerationError("description is too short.")
    if "def solution" not in starter_code:
        raise ChallengeGenerationError("starter_code must define solution().")
    if difficulty not in {"beginner", "intermediate", "advanced"}:
        difficulty = "beginner"
    if xp_reward < 20 or xp_reward > 150:
        xp_reward = {"beginner": 40, "intermediate": 60, "advanced": 90}[difficulty]

    test_cases = _validate_test_cases(data.get("test_cases"))
    return {
        "title": title[:200],
        "description": description[:4000],
        "difficulty": difficulty,
        "starter_code": starter_code[:8000],
        "test_cases": test_cases,
        "xp_reward": xp_reward,
    }


def _pick_fallback(level: str, *, exclude_titles: set[str] | None = None) -> ChallengePayload:
    exclude = exclude_titles or set()
    pool = [item for item in FALLBACK_CHALLENGES if item["title"] not in exclude]
    if level == "beginner":
        weighted = [item for item in pool if item["difficulty"] == "beginner"] or pool
    elif level == "intermediate":
        weighted = [
            item for item in pool if item["difficulty"] in {"beginner", "intermediate"}
        ] or pool
    else:
        weighted = pool
    return dict(random.choice(weighted or FALLBACK_CHALLENGES))


def generate_playground_challenge(
    *,
    experience_level: str | None,
    recent_titles: list[str] | None = None,
) -> ChallengePayload:
    level = _normalize_level(experience_level)
    exclude = set(recent_titles or [])

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info("playground_challenge_fallback reason=missing_api_key")
        return _pick_fallback(level, exclude_titles=exclude)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        model_name = (getattr(settings, "GEMINI_MODEL", "") or "").strip() or "gemini-3.5-flash"
        recent = ", ".join(recent_titles[:5]) if recent_titles else "none"
        prompt = (
            f"Learner level: {level}.\n"
            f"Avoid repeating these recent titles: {recent}.\n"
            "Generate a fresh Python function exercise."
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "system_instruction": PLAYGROUND_SYSTEM_PROMPT,
                "temperature": 0.65,
                "response_mime_type": "application/json",
            },
        )
        raw = (response.text or "").strip()
        data = _parse_challenge_json(raw)
        return validate_challenge_payload(data)
    except (ChallengeGenerationError, json.JSONDecodeError):
        logger.warning("playground_challenge_fallback reason=validation")
        return _pick_fallback(level, exclude_titles=exclude)
    except Exception as exc:
        if is_invalid_gemini_api_key_error(exc):
            logger.error("playground_gemini_key_invalid")
        else:
            logger.warning("playground_challenge_fallback reason=error %s", exc)
        return _pick_fallback(level, exclude_titles=exclude)
