"""Unit tests for TranscriptService (no external API calls)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai_engine.services.transcript import (
    TranscriptExtractionError,
    TranscriptService,
    TranscriptValidationError,
    clean_transcript_text,
    normalize_transcript_text,
    youtube_video_id,
)


class _MockFetchedTranscript:
    """Simulate youtube-transcript-api FetchedTranscript (iterable snippets)."""

    def __init__(self, snippets, language_code: str = "en"):
        self.snippets = snippets
        self.language_code = language_code
        self.language = language_code

    def __iter__(self):
        return iter(self.snippets)


def _mock_fetched(snippets, language_code: str = "en"):
    return _MockFetchedTranscript(snippets, language_code=language_code)


def _mock_snippet(text: str, start: float = 0.0, duration: float = 3.0):
    return SimpleNamespace(text=text, start=start, duration=duration)


def _educational_text(min_chars: int = 600) -> str:
    base = (
        "In this lesson we explore object-oriented programming in Python. "
        "A class is a blueprint for creating objects with attributes and methods. "
        "Inheritance allows subclasses to reuse and extend parent behavior. "
        "Encapsulation hides internal state behind a public interface. "
        "Polymorphism enables one interface with many underlying implementations. "
    )
    while len(base) < min_chars:
        base += "Students should understand constructors, instance variables, and method resolution order. "
    return base


class VideoIdExtractionTests(SimpleTestCase):
    def test_watch_url(self):
        self.assertEqual(
            youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_youtu_be(self):
        self.assertEqual(
            youtube_video_id("https://youtu.be/abc123XYZ_1"),
            "abc123XYZ_1",
        )

    def test_embed_url(self):
        self.assertEqual(
            youtube_video_id("https://www.youtube.com/embed/abc123XYZ_1"),
            "abc123XYZ_1",
        )

    def test_shorts_url(self):
        self.assertEqual(
            youtube_video_id("https://www.youtube.com/shorts/abc123XYZ_1"),
            "abc123XYZ_1",
        )

    def test_rejects_non_youtube(self):
        with self.assertRaises(TranscriptExtractionError):
            youtube_video_id("https://example.com/video")

    def test_rejects_missing_id(self):
        with self.assertRaises(TranscriptExtractionError):
            youtube_video_id("https://www.youtube.com/watch")

    def test_rejects_empty_url(self):
        with self.assertRaises(TranscriptExtractionError):
            youtube_video_id("")


class TranscriptCleaningTests(SimpleTestCase):
    def test_removes_music_and_applause(self):
        raw = "[Music] Hello everyone [Applause] welcome to the course."
        cleaned = clean_transcript_text(raw)
        self.assertIn("Hello everyone", cleaned)
        self.assertNotIn("[Music]", cleaned)
        self.assertNotIn("[Applause]", cleaned)

    def test_removes_timestamps(self):
        raw = "0:12 Introduction 1:30 Variables and data types"
        cleaned = clean_transcript_text(raw)
        self.assertNotIn("0:12", cleaned)
        self.assertIn("Introduction", cleaned)


class TranscriptValidationTests(SimpleTestCase):
    def setUp(self):
        self.svc = TranscriptService()

    def test_rejects_empty(self):
        with self.assertRaises(TranscriptValidationError):
            self.svc.validate("   ")

    def test_rejects_too_short(self):
        with self.assertRaises(TranscriptValidationError) as ctx:
            self.svc.validate("short text " * 10)
        self.assertIn("too short", str(ctx.exception).lower())

    def test_rejects_too_long(self):
        with self.assertRaises(TranscriptValidationError) as ctx:
            self.svc.validate("word " * 30_000)
        self.assertIn("too long", str(ctx.exception).lower())

    def test_accepts_educational_text(self):
        self.svc.validate(_educational_text())

    def test_rejects_artifact_only(self):
        with self.assertRaises(TranscriptValidationError):
            self.svc.validate("[Music] [Applause] " * 80)


class TranscriptNormalizationTests(SimpleTestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(
            normalize_transcript_text("a   b\n\n\n\nc"),
            "a b\n\nc",
        )


class TranscriptExtractTests(SimpleTestCase):
    @patch.object(TranscriptService, "_fetch_transcript")
    @patch.object(TranscriptService, "_extract_video_id", return_value="abc123XYZ_1")
    def test_extract_success(self, _mock_vid, mock_fetch):
        mock_fetch.return_value = (
            [{"text": _educational_text(650), "start": 0.0}],
            "en",
        )
        text = TranscriptService().extract("https://www.youtube.com/watch?v=abc123XYZ_1")
        self.assertGreaterEqual(len(text), 500)

    @patch.object(TranscriptService, "_fetch_transcript")
    @patch.object(TranscriptService, "_extract_video_id", return_value="abc123XYZ_1")
    def test_transcripts_disabled(self, _mock_vid, mock_fetch):
        mock_fetch.side_effect = TranscriptExtractionError(
            "Transcripts are disabled for this video."
        )
        with self.assertRaises(TranscriptExtractionError) as ctx:
            TranscriptService().extract("https://www.youtube.com/watch?v=abc123XYZ_1")
        self.assertIn("disabled", str(ctx.exception).lower())

    @patch.object(TranscriptService, "_fetch_transcript")
    @patch.object(TranscriptService, "_extract_video_id", return_value="abc123XYZ_1")
    def test_video_unavailable(self, _mock_vid, mock_fetch):
        mock_fetch.side_effect = TranscriptExtractionError(
            "Video is unavailable, private, age-restricted, or removed."
        )
        with self.assertRaises(TranscriptExtractionError):
            TranscriptService().extract("https://www.youtube.com/watch?v=abc123XYZ_1")

    @patch.object(TranscriptService, "_fetch_transcript")
    @patch.object(TranscriptService, "_extract_video_id", return_value="abc123XYZ_1")
    def test_no_transcript(self, _mock_vid, mock_fetch):
        mock_fetch.side_effect = TranscriptExtractionError("Transcript unavailable.")
        with self.assertRaises(TranscriptExtractionError) as ctx:
            TranscriptService().extract("https://www.youtube.com/watch?v=abc123XYZ_1")
        self.assertIn("unavailable", str(ctx.exception).lower())


class ChunkMetadataDesignTests(SimpleTestCase):
    def test_design_documented(self):
        meta = TranscriptService.chunk_metadata_design()
        self.assertFalse(meta["implemented"])
        self.assertIn("recommended_max_chars", meta)


class FetchTranscriptApiTests(SimpleTestCase):
    def setUp(self):
        self.svc = TranscriptService()

    def test_fetched_to_blocks_converts_snippets(self):
        fetched = _mock_fetched(
            [
                _mock_snippet("Hello", 0.0, 2.5),
                _mock_snippet("world", 2.5, 1.5),
            ]
        )
        blocks = self.svc._fetched_to_blocks(fetched)
        self.assertEqual(
            blocks,
            [
                {"text": "Hello", "start": 0.0, "duration": 2.5},
                {"text": "world", "start": 2.5, "duration": 1.5},
            ],
        )

    def test_join_transcript_blocks_after_conversion(self):
        blocks = [
            {"text": "Part one.", "start": 0.0, "duration": 2.0},
            {"text": "Part two.", "start": 2.0, "duration": 3.0},
        ]
        joined = self.svc._join_transcript_blocks(blocks)
        self.assertEqual(joined, "Part one. Part two.")

    def test_fetch_transcript_uses_api_fetch(self):
        educational = _educational_text(650)
        api = MagicMock(spec=["fetch", "list"])
        api.fetch.return_value = _mock_fetched(
            [_mock_snippet(educational)],
            language_code="en-US",
        )

        with patch("youtube_transcript_api.YouTubeTranscriptApi", lambda: api):
            raw, language = self.svc._fetch_transcript("abc123XYZ_1")

        api.fetch.assert_called_once_with(
            "abc123XYZ_1",
            languages=["en", "en-US", "en-GB"],
        )
        self.assertEqual(raw[0]["text"], educational)
        self.assertEqual(raw[0]["start"], 0.0)
        self.assertIn("duration", raw[0])
        self.assertEqual(language, "en-US")

    def test_fetch_transcript_fallback_any_language(self):
        educational = _educational_text(650)
        api = MagicMock(spec=["fetch", "list"])
        fallback_transcript = MagicMock()
        fallback_transcript.fetch.return_value = _mock_fetched(
            [_mock_snippet(educational)],
            language_code="de",
        )
        api.list.return_value = iter([fallback_transcript])

        from youtube_transcript_api._errors import NoTranscriptFound

        api.fetch.side_effect = NoTranscriptFound("vid", ["en"], MagicMock())

        with patch("youtube_transcript_api.YouTubeTranscriptApi", lambda: api):
            raw, language = self.svc._fetch_transcript("abc123XYZ_1")

        api.list.assert_called_once_with("abc123XYZ_1")
        fallback_transcript.fetch.assert_called_once()
        self.assertEqual(raw[0]["text"], educational)
        self.assertEqual(language, "de")

    def test_no_transcript_found_raises_unavailable(self):
        from youtube_transcript_api._errors import NoTranscriptFound

        api = MagicMock(spec=["fetch", "list"])
        api.fetch.side_effect = NoTranscriptFound("vid", ["en"], MagicMock())
        api.list.return_value = iter([])

        with patch("youtube_transcript_api.YouTubeTranscriptApi", lambda: api):
            with self.assertRaises(TranscriptExtractionError) as ctx:
                self.svc._fetch_transcript("abc123XYZ_1")
        self.assertEqual(str(ctx.exception), "Transcript unavailable.")

    def test_transcripts_disabled_error(self):
        from youtube_transcript_api._errors import TranscriptsDisabled

        api = MagicMock(spec=["fetch", "list"])
        api.fetch.side_effect = TranscriptsDisabled("vid")

        with patch("youtube_transcript_api.YouTubeTranscriptApi", lambda: api):
            with self.assertRaises(TranscriptExtractionError) as ctx:
                self.svc._fetch_transcript("abc123XYZ_1")
        self.assertIn("disabled", str(ctx.exception).lower())

    def test_video_unavailable_error(self):
        from youtube_transcript_api._errors import VideoUnavailable

        api = MagicMock(spec=["fetch", "list"])
        api.fetch.side_effect = VideoUnavailable("vid")

        with patch("youtube_transcript_api.YouTubeTranscriptApi", lambda: api):
            with self.assertRaises(TranscriptExtractionError) as ctx:
                self.svc._fetch_transcript("abc123XYZ_1")
        self.assertIn("unavailable", str(ctx.exception).lower())

    @patch.object(TranscriptService, "_fetch_transcript")
    @patch.object(TranscriptService, "_extract_video_id", return_value="abc123XYZ_1")
    def test_extract_with_dict_blocks(self, _mock_vid, mock_fetch):
        educational = _educational_text(650)
        mock_fetch.return_value = (
            [
                {
                    "text": educational,
                    "start": 0.0,
                    "duration": 120.0,
                }
            ],
            "en",
        )
        text = TranscriptService().extract("https://www.youtube.com/watch?v=abc123XYZ_1")
        self.assertIn("object-oriented", text.lower())
        self.assertGreaterEqual(len(text), 500)
