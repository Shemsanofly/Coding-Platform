# Legacy Django/DRF tests

This directory holds the test suites that were written against the original
Django + Django REST Framework backend (`accounts`, `courses`, `progress`,
`quizzes`, `ai_engine` views/serializers, and `core`'s API hardening tests).

The project has since migrated to a hand-rolled Flask backend
(`backend/flask_app.py`) that serves all live traffic. It talks to the same
SQLite/PostgreSQL schema via raw SQL, but does not call into the Django
views, serializers, or ViewSets these tests exercise. See
`../../ARCHITECTURE.md` for the full picture.

These tests are **not run by CI or `pytest`/`unittest` discovery** — they are
kept here for reference only, in case any of that DRF logic is ever ported
back or used to cross-check behavior while finishing the Flask migration
(notably: AI PDF note generation and AI quiz generation, which are currently
stubbed as "not ported to Flask yet" in `flask_app.py`).

Do not add new tests here. New backend tests belong in
`backend/core/tests/test_flask_runtime.py` (or new files alongside it),
testing `flask_app.py` directly.
