# Architecture

The backend is Flask-only.

## Runtime

`backend/app.py` starts the server and imports the Flask app from `backend/flask_app.py`.

`backend/flask_app.py` contains:

- The `create_app()` factory
- Authentication and refresh-cookie handling
- Course, lesson, quiz, progress, certificate, report, and playground routes
- SQLite and PostgreSQL access through raw SQL
- PDF generation through ReportLab
- Compatibility handling for existing PBKDF2-SHA256 password hashes

There is no second backend framework, no ORM layer, and no separate route stack.

## Data

The app supports SQLite for local development and PostgreSQL for production through
`DATABASE_URL`.

The current table names remain stable for existing data compatibility, for example:

- `accounts_user`
- `courses_course`
- `courses_lesson`
- `progress_enrollment`
- `progress_lessonprogress`
- `quizzes_quiz`
- `quizzes_question`
- `quizzes_quizresult`
- `progress_certificate`
- `playground_playgroundchallenge`
- `playground_playgroundsubmission`

## Tests

The live backend test suite is `backend/core/tests/test_flask_runtime.py`.

Run it from `backend/`:

```bash
python -m pytest core/tests/test_flask_runtime.py -q
```

## Quality Checks

From `backend/`:

```bash
python -m ruff check .
python -m pytest core/tests/test_flask_runtime.py -q
```

From `frontend/`:

```bash
npm run build
```
