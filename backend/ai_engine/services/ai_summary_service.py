"""Structured study notes from transcript text (AI or rule-based fallback)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from django.conf import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 12_000
CHUNK_OVERLAP = 400


class StudyNotesPayload(TypedDict):
    lesson_title: str
    key_concepts: list[str]
    definitions: list[dict[str, str]]
    examples: list[str]
    important_points: list[str]
    revision_notes: list[str]
    possible_quiz_points: list[str]


NOTES_SYSTEM_PROMPT = """You are an expert educator creating revision-friendly study notes.

Summarize ONLY factual content from the transcript inside <transcript> tags.
Do not invent topics not supported by the transcript.
Do not claim to analyze video images — this is transcript text only.

Return a single JSON object with no markdown:
{
  "lesson_title": "",
  "key_concepts": [],
  "definitions": [{"term": "", "definition": ""}],
  "examples": [],
  "important_points": [],
  "revision_notes": [],
  "possible_quiz_points": []
}

Each list should contain concise, student-friendly strings. definitions must be objects with term and definition keys."""


def clean_transcript(text: str) -> str:
    from ai_engine.services.transcript import TranscriptService

    service = TranscriptService()
    return service.normalize(service.clean(text or ""))


def chunk_transcript(text: str, *, max_chars: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    cleaned = clean_transcript(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            boundary = cleaned.rfind("\n\n", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _rule_based_summary(transcript: str, *, default_title: str = "Lesson Study Notes") -> StudyNotesPayload:
    cleaned = clean_transcript(transcript)
    sentences = _sentences(cleaned)
    key_concepts = []
    for sentence in sentences[:8]:
        words = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", sentence)
        key_concepts.extend(words[:2])
    key_concepts = list(dict.fromkeys(key_concepts))[:10]
    if not key_concepts:
        key_concepts = ["Core lesson ideas", "Main vocabulary", "Practical applications"]

    definitions = []
    for concept in key_concepts[:5]:
        definitions.append(
            {
                "term": concept,
                "definition": f"{concept} is explained in the lesson transcript and supports the main learning goals.",
            }
        )

    examples = sentences[1:4] if len(sentences) > 1 else [cleaned[:240] + ("…" if len(cleaned) > 240 else "")]
    important_points = sentences[:6] or [cleaned[:300]]
    revision_notes = [
        "Review key concepts after watching the embedded video.",
        "Re-read definitions and connect them to examples from the transcript.",
        "Use possible quiz points as self-check questions before taking the lesson quiz.",
    ]
    possible_quiz_points = [
        f"What is the main idea behind {key_concepts[0]}?" if key_concepts else "What is the main topic of this lesson?",
        "Which example from the lesson best illustrates the concept?",
        "How would you explain this topic in your own words?",
    ]

    return StudyNotesPayload(
        lesson_title=default_title,
        key_concepts=key_concepts,
        definitions=definitions,
        examples=examples,
        important_points=important_points,
        revision_notes=revision_notes,
        possible_quiz_points=possible_quiz_points,
    )


def _parse_gemini_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _validate_payload(data: dict[str, Any], *, default_title: str) -> StudyNotesPayload:
    def _list(key: str, limit: int = 20) -> list[str]:
        value = data.get(key) or []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:limit]

    definitions_raw = data.get("definitions") or []
    definitions: list[dict[str, str]] = []
    if isinstance(definitions_raw, list):
        for item in definitions_raw[:15]:
            if isinstance(item, dict):
                term = str(item.get("term") or "").strip()
                definition = str(item.get("definition") or "").strip()
                if term and definition:
                    definitions.append({"term": term, "definition": definition})

    title = str(data.get("lesson_title") or default_title).strip() or default_title
    payload: StudyNotesPayload = {
        "lesson_title": title,
        "key_concepts": _list("key_concepts", 15) or ["Lesson themes"],
        "definitions": definitions,
        "examples": _list("examples", 10),
        "important_points": _list("important_points", 12),
        "revision_notes": _list("revision_notes", 10),
        "possible_quiz_points": _list("possible_quiz_points", 12),
    }
    if not payload["definitions"]:
        payload["definitions"] = [
            {"term": payload["key_concepts"][0], "definition": "Key term introduced in the lesson transcript."}
        ]
    return payload


def _gemini_summarize_chunk(chunk: str, *, default_title: str) -> StudyNotesPayload:
    import google.generativeai as genai

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Gemini API key not configured.")

    genai.configure(api_key=api_key)
    model_name = (getattr(settings, "GEMINI_MODEL", "") or "").strip() or "gemini-3.5-flash"
    model = genai.GenerativeModel(model_name)
    prompt = (
        f"{NOTES_SYSTEM_PROMPT}\n\n"
        f"<transcript>\n{chunk}\n</transcript>\n\n"
        f"Default lesson title if unclear: {default_title}"
    )
    response = model.generate_content(prompt)
    raw = getattr(response, "text", "") or ""
    data = _parse_gemini_json(raw)
    return _validate_payload(data, default_title=default_title)


def _merge_payloads(parts: list[StudyNotesPayload], *, default_title: str) -> StudyNotesPayload:
    if not parts:
        return _rule_based_summary("", default_title=default_title)
    if len(parts) == 1:
        return parts[0]

    def _uniq_lists(key: str) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for part in parts:
            for item in part.get(key, []):
                normalized = item.strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged.append(item.strip())
        return merged[:20]

    definitions: list[dict[str, str]] = []
    seen_terms: set[str] = set()
    for part in parts:
        for row in part.get("definitions", []):
            term = row.get("term", "").strip()
            if term and term.lower() not in seen_terms:
                seen_terms.add(term.lower())
                definitions.append(row)

    title = parts[0].get("lesson_title") or default_title
    return StudyNotesPayload(
        lesson_title=title,
        key_concepts=_uniq_lists("key_concepts"),
        definitions=definitions[:15],
        examples=_uniq_lists("examples"),
        important_points=_uniq_lists("important_points"),
        revision_notes=_uniq_lists("revision_notes"),
        possible_quiz_points=_uniq_lists("possible_quiz_points"),
    )


def generate_study_notes(
    transcript: str,
    *,
    lesson_title: str = "Lesson Study Notes",
) -> StudyNotesPayload:
    """
    Clean transcript, chunk if needed, and produce structured study notes.

    Uses Gemini when configured; otherwise falls back to rule-based structuring.
    """
    cleaned = clean_transcript(transcript)
    if not cleaned.strip():
        raise ValueError("Transcript is empty.")

    chunks = chunk_transcript(cleaned)
    api_key = getattr(settings, "GEMINI_API_KEY", "")

    if not api_key:
        logger.info("GEMINI_API_KEY missing; using rule-based study notes fallback.")
        return _rule_based_summary(cleaned, default_title=lesson_title)

    partials: list[StudyNotesPayload] = []
    for chunk in chunks:
        try:
            partials.append(_gemini_summarize_chunk(chunk, default_title=lesson_title))
        except Exception as exc:
            logger.warning("Gemini study notes chunk failed: %s", exc)
            partials.append(_rule_based_summary(chunk, default_title=lesson_title))

    return _merge_payloads(partials, default_title=lesson_title)
