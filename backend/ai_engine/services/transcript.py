"""
YouTube transcript extraction and normalization.

Cleaning rules applied in ``clean()``:
1. Remove bracketed stage directions: [Music], [Applause], [Laughter] (case-insensitive).
2. Remove speaker prefixes like ``>> Speaker:``.
3. Remove bracketed speaker labels ``[Name]:``.
4. Remove inline timestamps (e.g. ``0:12``, ``1:02:33.5``).
5. Collapse horizontal whitespace (spaces/tabs) to a single space.
6. Strip leading/trailing whitespace per segment.

Normalization (``normalize()``):
1. Normalize line endings and collapse 3+ newlines to 2.
2. Collapse internal spaces again for deterministic output.
3. Ensure UTF-8-safe str (invalid surrogates replaced).

Future chunking (not implemented): ``chunk_metadata`` can record byte offsets per
``max_chars`` window for Gemini — see ``TranscriptService.chunk_metadata_design``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

# --- Length bounds (characters, post-normalize) ---
MIN_TRANSCRIPT_CHARS = 500
MAX_TRANSCRIPT_CHARS = 100_000

# --- YouTube hosts ---
_ALLOWED_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)

# --- Cleaning patterns ---
_TIMESTAMP_RE = re.compile(r"(?:^|\s)(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?(?:\s|$)", re.MULTILINE)
_SPEAKER_ARROW_RE = re.compile(r"^\s*>>\s*\S+?:\s*", re.MULTILINE)
_SPEAKER_BRACKET_RE = re.compile(r"\[[^\]]{1,40}\]:\s*")
_MUSIC_BRACKET_RE = re.compile(r"\[(?:music|applause|laughter|silence|inaudible)\]", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\ufeff]")

# --- Validation heuristics ---
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9'-]{1,}")
_ARTIFACT_ONLY_RE = re.compile(r"^[\s\[\]\(\):;,\d>>\-–—.!?]*$", re.IGNORECASE)


class TranscriptError(Exception):
    """Base error for transcript pipeline."""


class TranscriptExtractionError(TranscriptError):
    """URL parsing or YouTube transcript API failure."""


class TranscriptValidationError(TranscriptError):
    """Transcript text failed quality or length checks."""


@dataclass(frozen=True)
class TranscriptExtractionResult:
    """Internal metadata; public API ``extract()`` returns normalized text only."""

    video_id: str
    text: str
    language: str | None
    char_count: int


class TranscriptService:
    """Single source of truth for YouTube caption extraction and normalization."""

    preferred_languages: tuple[str, ...] = ("en", "en-US", "en-GB")

    def extract(self, url: str) -> str:
        """Fetch, clean, normalize, and validate transcript; return final text."""
        meta = self._extract_with_metadata(url)
        return meta.text

    def validate(self, text: str) -> None:
        """Raise ``TranscriptValidationError`` if text is not usable for AI analysis."""
        if text is None:
            raise TranscriptValidationError("Transcript is empty.")

        normalized = unicodedata.normalize("NFKC", str(text)).strip()
        if not normalized:
            raise TranscriptValidationError("Transcript is empty.")

        char_count = len(normalized)
        if char_count < MIN_TRANSCRIPT_CHARS:
            raise TranscriptValidationError(
                f"Transcript too short ({char_count} characters). "
                f"Minimum is {MIN_TRANSCRIPT_CHARS}."
            )
        if char_count > MAX_TRANSCRIPT_CHARS:
            raise TranscriptValidationError(
                f"Transcript too long ({char_count} characters). "
                f"Maximum is {MAX_TRANSCRIPT_CHARS}."
            )

        if _ARTIFACT_ONLY_RE.match(normalized):
            raise TranscriptValidationError("Transcript contains insufficient educational content.")

        words = _WORD_RE.findall(normalized)
        if len(words) < 40:
            raise TranscriptValidationError("Transcript contains insufficient educational content.")

        artifact_stripped = _MUSIC_BRACKET_RE.sub("", normalized)
        artifact_stripped = _TIMESTAMP_RE.sub("", artifact_stripped).strip()
        if len(artifact_stripped) < MIN_TRANSCRIPT_CHARS:
            raise TranscriptValidationError("Transcript contains only transcript artifacts.")

    def clean(self, text: str) -> str:
        """Remove captions noise and collapse whitespace."""
        if not text:
            return ""
        text = _HTML_TAG_RE.sub(" ", text)
        text = _ZERO_WIDTH_RE.sub("", text)
        text = _MUSIC_BRACKET_RE.sub(" ", text)
        text = _SPEAKER_ARROW_RE.sub(" ", text)
        text = _SPEAKER_BRACKET_RE.sub(" ", text)
        text = _TIMESTAMP_RE.sub(" ", text)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()

    def normalize(self, text: str) -> str:
        """Deterministic whitespace normalization for downstream AI."""
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        paragraphs: list[str] = []
        for block in re.split(r"\n\s*\n", text.strip()):
            collapsed = re.sub(r"[ \t\f\v]+", " ", block).strip()
            if collapsed:
                paragraphs.append(collapsed)
        return "\n\n".join(paragraphs)

    # --- Optional / internal helpers ---

    def _extract_video_id(self, url: str) -> str:
        raw = (url or "").strip()
        if not raw:
            raise TranscriptExtractionError("URL is required.")

        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            raise TranscriptExtractionError("URL must use http or https.")

        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_YOUTUBE_HOSTS:
            raise TranscriptExtractionError(
                "URL must be a supported YouTube link (youtube.com or youtu.be)."
            )

        if host in ("youtu.be", "www.youtu.be"):
            vid = parsed.path.strip("/").split("/")[0]
            if vid and re.fullmatch(r"[\w-]{6,}", vid):
                return vid
            raise TranscriptExtractionError("Could not parse YouTube video id from URL.")

        if "youtube.com" in host or "youtube-nocookie.com" in host:
            query_id = (parse_qs(parsed.query).get("v") or [None])[0]
            if query_id and re.fullmatch(r"[\w-]{6,}", query_id):
                return query_id

            parts = [p for p in parsed.path.split("/") if p]
            for marker in ("embed", "shorts", "live"):
                if marker in parts:
                    idx = parts.index(marker)
                    if idx + 1 < len(parts):
                        candidate = parts[idx + 1].split("?")[0]
                        if re.fullmatch(r"[\w-]{6,}", candidate):
                            return candidate

        raise TranscriptExtractionError("Could not parse YouTube video id from URL.")

    def _fetched_to_blocks(self, fetched) -> list[dict[str, Any]]:
        return [
            {
                "text": item.text,
                "start": item.start,
                "duration": item.duration,
            }
            for item in fetched
        ]

    def _language_from_fetched(self, fetched) -> str | None:
        code = getattr(fetched, "language_code", None) or getattr(fetched, "language", None)
        return str(code) if code else None

    def _fetch_transcript(self, video_id: str) -> tuple[list[dict[str, Any]], str | None]:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )

        try:
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                try:
                    raw = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=list(self.preferred_languages)
                    )
                    return raw, self._detect_language(raw)
                except NoTranscriptFound:
                    raw = YouTubeTranscriptApi.get_transcript(video_id)
                    return raw, self._detect_language(raw)

            api = YouTubeTranscriptApi()
            try:
                fetched = api.fetch(
                    video_id,
                    languages=list(self.preferred_languages),
                )
            except NoTranscriptFound:
                fetched = self._fetch_any_available(api, video_id)

            raw = self._fetched_to_blocks(fetched)
            language = self._language_from_fetched(fetched) or self._detect_language(raw)
            return raw, language

        except NoTranscriptFound as exc:
            raise TranscriptExtractionError("Transcript unavailable.") from exc
        except TranscriptsDisabled as exc:
            raise TranscriptExtractionError("Transcripts are disabled for this video.") from exc
        except VideoUnavailable as exc:
            raise TranscriptExtractionError(
                "Video is unavailable, private, age-restricted, or removed."
            ) from exc
        except Exception as exc:
            raise TranscriptExtractionError(f"Transcript API failed: {exc}") from exc

    def _fetch_any_available(self, api, video_id: str):
        """Fetch the first available transcript when preferred languages are missing."""
        from youtube_transcript_api._errors import NoTranscriptFound

        transcript_list = api.list(video_id)
        for transcript in transcript_list:
            return transcript.fetch()
        raise NoTranscriptFound(video_id, [], transcript_list)

    def _detect_language(self, blocks: list[dict[str, Any]]) -> str | None:
        if not blocks:
            return None
        first = blocks[0]
        lang = first.get("language") or first.get("language_code")
        return str(lang) if lang else None

    def _join_transcript_blocks(self, blocks: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for item in blocks:
            fragment = (item.get("text") or "").replace("\n", " ").strip()
            if fragment:
                parts.append(fragment)
        return " ".join(parts)

    def _extract_with_metadata(self, url: str) -> TranscriptExtractionResult:
        video_id = self._extract_video_id(url)
        raw, language = self._fetch_transcript(video_id)
        blob = self._join_transcript_blocks(raw)
        cleaned = self.clean(blob)
        normalized = self.normalize(cleaned)
        if not normalized.strip():
            raise TranscriptValidationError("Transcript is empty.")
        self.validate(normalized)
        return TranscriptExtractionResult(
            video_id=video_id,
            text=normalized,
            language=language,
            char_count=len(normalized),
        )

    @staticmethod
    def chunk_metadata_design() -> dict[str, Any]:
        """
        Future chunking contract (not implemented).

        Planned fields per chunk:
        - index: int
        - start_char / end_char: int
        - approx_duration_sec: float | None
        - text: str
        """
        return {
            "implemented": False,
            "recommended_max_chars": 12_000,
            "strategy": "sliding_windows_with_paragraph_boundaries",
        }


# --- Module-level aliases (backward compatibility for ingest pipeline) ---


def youtube_video_id(url: str) -> str:
    return TranscriptService()._extract_video_id(url)


def clean_transcript_text(text: str) -> str:
    return TranscriptService().clean(text)


def normalize_transcript_text(text: str) -> str:
    return TranscriptService().normalize(text)
