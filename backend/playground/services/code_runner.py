"""Execute student Python solutions against hidden test cases."""

from __future__ import annotations

import json
from typing import Any

MAX_CODE_LENGTH = 8000
MAX_TEST_CASES = 8

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    True: True,
    False: False,
    None: None,
}

FORBIDDEN_TOKENS = (
    "import ",
    "__import__",
    "exec(",
    "eval(",
    "open(",
    "compile(",
    "globals(",
    "locals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "help(",
    "input(",
    "try:",
    "except ",
    "finally:",
    "with ",
    "raise ",
    "class ",
    "lambda ",
    "async ",
    "await ",
)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def validate_student_code(code: str) -> str | None:
    text = (code or "").strip()
    if not text:
        return "Write your solution before submitting."
    if len(text) > MAX_CODE_LENGTH:
        return "Code is too long."
    lowered = text.lower()
    for token in FORBIDDEN_TOKENS:
        if token in lowered:
            return f"Unsupported construct: `{token.strip()}`. Use only a `solution` function."
    if "def solution" not in text:
        return "Define a function named `solution`."
    return None


def run_solution(code: str, test_cases: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    validation_error = validate_student_code(code)
    if validation_error:
        return False, [{"passed": False, "error": validation_error}]

    if not isinstance(test_cases, list) or not test_cases:
        return False, [{"passed": False, "error": "Challenge has no test cases."}]
    if len(test_cases) > MAX_TEST_CASES:
        return False, [{"passed": False, "error": "Too many test cases."}]

    namespace: dict[str, Any] = {}
    try:
        exec(code, {"__builtins__": SAFE_BUILTINS}, namespace)
    except Exception as exc:
        return False, [{"passed": False, "error": f"Syntax/runtime error: {exc}"}]

    solution = namespace.get("solution")
    if not callable(solution):
        return False, [{"passed": False, "error": "Define a callable function named `solution`."}]

    results: list[dict[str, Any]] = []
    all_passed = True
    for index, test_case in enumerate(test_cases, start=1):
        if not isinstance(test_case, dict):
            all_passed = False
            results.append({"case": index, "passed": False, "error": "Invalid test case."})
            continue

        args = test_case.get("args", [])
        expected = test_case.get("expected")
        if not isinstance(args, list):
            all_passed = False
            results.append({"case": index, "passed": False, "error": "Invalid test arguments."})
            continue

        try:
            actual = solution(*args)
            passed = actual == expected
            if not passed:
                all_passed = False
            results.append(
                {
                    "case": index,
                    "passed": passed,
                    "expected": _json_safe(expected),
                    "actual": _json_safe(actual),
                }
            )
        except Exception as exc:
            all_passed = False
            results.append({"case": index, "passed": False, "error": str(exc)})

    return all_passed, results
