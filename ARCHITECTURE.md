# Architecture

This project started as a Django + Django REST Framework backend (see the initial commit)
and later migrated to a hand-rolled Flask backend. The migration is **incomplete**, and the
repository currently contains two backend stacks side by side. This document explains what's
actually live, what's legacy, and what's genuinely still in progress.

## What serves live traffic

`backend/app.py` is the only server entrypoint, and it imports exactly one thing:

```python
from flask_app import app
```

`backend/flask_app.py` (~1,200 lines) is the entire live backend:
- A single `create_app()` factory containing every route, auth check, and SQL query as nested
  closures.
- All ~55 API routes are registered under both `/api/...` and `/api/v1/...` via a `route_api()`
  helper (there is no actual behavioral difference between the two versions today).
- Data access is raw SQL (`sqlite3` / `psycopg`) against tables named after Django's convention
  (`accounts_user`, `courses_lesson`, `quizzes_quiz`, etc.) — there is no ORM and no query
  builder.
- Auth is hand-rolled: `itsdangerous.URLSafeTimedSerializer` for access/refresh tokens, and a
  reimplementation of Django's PBKDF2 password hashing (`django_pbkdf2_hash`) so that passwords
  created under the old Django backend continue to work.
- Flask does **not** import anything from `accounts/`, `courses/`, `progress/`, `quizzes/`, or
  `ai_engine/`.

## What Django is still responsible for

Despite not handling any requests, the Django app tree is not fully dead:

- **Migrations.** `python manage.py migrate` is still the only mechanism that creates and
  evolves the SQLite/PostgreSQL schema that `flask_app.py` reads and writes via raw SQL. Django's
  `models.py` files in each app are effectively schema documentation now — treat changes to them
  (and their migrations) as the source of truth for the database shape.
- Nothing else. `views.py`, `serializers.py`, `urls.py`, `tasks.py`, `admin.py`, and the DRF
  ViewSets in every app are unused by the running system.

## What's not ported yet

Two features that exist in the Django app's `ai_engine`/`courses` services were never carried
over to Flask:

- **AI-generated PDF study notes** — `POST /lessons/<id>/generate-notes/` in `flask_app.py`
  returns `202 {"status": "pending", "detail": "PDF generation is not ported to Flask yet."}`.
- **AI quiz generation from transcripts** — `POST .../generate-quiz/` and `.../regenerate-quiz/`
  return the equivalent `202 pending` stub.

The README's feature list is written from the product's intended end state; treat these two
items as **not yet functional** until these routes are implemented against Gemini/ReportLab the
way the Django services already do.

## Tests

- `backend/core/tests/test_flask_runtime.py` is the only test suite that exercises the live
  Flask backend. Grow this file (or add siblings next to it) for any new backend work.
- `backend/_legacy/django_tests/` holds the original Django/DRF test suites (`accounts`,
  `courses`, `progress`, `quizzes`, `ai_engine`, plus `core`'s old API-hardening tests). They are
  **not** run by CI or by `python -m unittest` discovery from `backend/`. They're kept for
  reference in case the PDF-notes/quiz-generation logic they cover gets ported into Flask. See
  `backend/_legacy/README.md`.

## Known issue: `DATABASE_URL` overrides test isolation

`create_app(config=None)` reads `DATABASE_URL`/`DATABASE_PATH` from the environment first, then
only overrides them from the `config` argument if the environment value was empty:

```python
if config:
    app.config.update(config)
    app.config["DATABASE_URL"] = app.config.get("DATABASE_URL", "").strip()
    if not app.config["DATABASE_URL"]:
        app.config["DATABASE_URL"] = sqlite_database_url(app.config["DATABASE_PATH"])
    app.config["DATABASE_ENGINE"] = database_engine(app.config["DATABASE_URL"])
```

If `backend/.env` has a non-empty `DATABASE_URL` (e.g. a local Postgres connection string), the
test suite's `{"DATABASE_PATH": self.db_path, ...}` override in
`core/tests/test_flask_runtime.py` **does not take effect** — tests silently connect to whatever
real database `DATABASE_URL` points to instead of the isolated temp SQLite file, causing
`test_register_login_me_and_refresh_are_flask_owned` and
`test_existing_django_pbkdf2_passwords_can_login` to fail (or worse, pass against/mutate real
data). This is a pre-existing bug in the in-progress Postgres-support work, not related to
formatting or test-suite reorganization. Fix: `create_app` should force SQLite whenever
`config` explicitly provides a `DATABASE_PATH` without a `DATABASE_URL`, regardless of what's in
the environment.

## If you're deciding what to do next

1. Finish porting PDF notes / quiz generation to Flask (or explicitly cut them from the roadmap),
   using the existing `ai_engine`/`courses` Django services as reference implementations.
2. Fix the `DATABASE_URL` test-isolation bug above before relying on the test suite while
   Postgres support is in flight.
3. Once `flask_app.py` has real test coverage, split it into blueprints (`auth`, `courses`,
   `progress`, `quizzes`, `certificates`, `playground`) instead of one 1,200-line factory
   function — tests make that refactor safe to do.
