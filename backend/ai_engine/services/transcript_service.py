"""YouTube transcript retrieval for PDF study notes (transcript text only)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engine.services.transcript import (
    TranscriptError,
    TranscriptExtractionError,
    TranscriptService,
    TranscriptValidationError,
    youtube_video_id,
)

TRANSCRIPT_UNAVAILABLE_MESSAGE = (
    "Transcript not available. Please upload notes manually or add another video."
)


class TranscriptUnavailableError(Exception):
    """Raised when captions cannot be retrieved for a YouTube video."""

    def __init__(self, message: str = TRANSCRIPT_UNAVAILABLE_MESSAGE):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class TranscriptResult:
    video_id: str
    text: str


def extract_youtube_video_id(url: str) -> str:
    """Parse a supported YouTube URL and return the video id."""
    return youtube_video_id(url)


def fetch_transcript(url: str) -> TranscriptResult:
    """
    Retrieve and normalize transcript text for a YouTube URL.

    Raises TranscriptUnavailableError when captions are missing or unusable.
    """
    service = TranscriptService()
    try:
        video_id = service._extract_video_id(url)
        raw, _language = service._fetch_transcript(video_id)
        blob = service._join_transcript_blocks(raw)
        cleaned = service.clean(blob)
        normalized = service.normalize(cleaned)
        if not normalized.strip():
            raise TranscriptUnavailableError()
        try:
            service.validate(normalized)
        except TranscriptValidationError as exc:
            if "empty" in str(exc).lower():
                raise TranscriptUnavailableError() from exc
            # Allow shorter transcripts for notes when captions exist but are brief.
            if len(normalized.strip()) < 80:
                raise TranscriptUnavailableError() from exc
        return TranscriptResult(video_id=video_id, text=normalized)
    except TranscriptUnavailableError:
        raise
    except TranscriptExtractionError as exc:
        msg = str(exc).lower()
        if "unavailable" in msg or "disabled" in msg or "could not parse" in msg:
            raise TranscriptUnavailableError() from exc
        raise TranscriptUnavailableError(str(exc)) from exc
    except TranscriptValidationError as exc:
        raise TranscriptUnavailableError() from exc
    except TranscriptError as exc:
        raise TranscriptUnavailableError(str(exc)) from exc
    except Exception as exc:
        raise TranscriptUnavailableError() from exc
