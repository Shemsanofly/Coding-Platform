# AI-Based Adaptive E-Learning Platform

An adaptive e-learning platform that delivers personalized learning through YouTube-based lessons, AI-generated study materials, automated quiz generation, progress tracking, weakness detection, and intelligent recommendations.

Students register with a learning level, enroll in courses, study embedded lessons, take quizzes, and receive adaptive guidance based on performance. Administrators create courses, generate AI content from YouTube transcripts, approve quizzes, and monitor student progress.

## Features

### Authentication
- Email registration and JWT login (access token in memory, refresh token in httpOnly cookie)
- Role-based access: **Student** and **Admin**
- Learning level selection at registration (Beginner, Intermediate, Advanced)

### Course Enrollment
- Level-filtered course catalog
- One-click enrollment
- Sequential lesson unlocking after passing prior quizzes

### Learning Experience
- **Embedded YouTube lessons** inside the platform
- **In-platform PDF reader** with scroll-depth and engagement tracking
- PDF download for offline revision
- **AI-generated PDF study notes** from YouTube transcript text (Gemini or rule-based fallback) —
  designed and implemented against the original Django backend; **not yet ported** to the live
  Flask backend (`POST /lessons/<id>/generate-notes/` currently returns `202 pending`). See
  [ARCHITECTURE.md](ARCHITECTURE.md).

### Assessment
- **Admin quiz approval** before questions are published to students
- Quiz result analysis with per-question explanations
- **Automatic quiz generation** from transcript text via Google Gemini — same status as above:
  built against Django, **not yet ported** to Flask (`generate-quiz`/`regenerate-quiz` currently
  return `202 pending`).

### Adaptive Learning
- **Progress tracking** — watch time, PDF engagement, completion status
- **Weakness detection** — topic-level accuracy with HIGH / MEDIUM / LOW severity
- **Personalized recommendations** matched to student level and weak topics
- **Learning path generation** — sequenced steps from weaknesses and recommendations
- **Adaptive level adjustment** — experience level updated based on quiz performance

## Technology Stack

| Layer | Tools |
|-------|--------|
| Backend | Flask 3 runtime, SQLite for development, PostgreSQL for production |
| Frontend | React 18, Vite, Tailwind CSS, React Query, Zustand |
| AI | Google Gemini API |
| PDF | ReportLab |
| Transcripts | youtube-transcript-api |
| Auth | Flask signed bearer tokens + httpOnly refresh cookie |
| Task queue | Celery + Redis (optional, for async AI generation) |

AI features process **YouTube transcript text only** — not raw video frames.

> **Architecture note:** this project migrated from Django + DRF to a hand-rolled Flask backend
> (`backend/flask_app.py`), which now serves all live traffic. Django is retained only to own
> database migrations/schema (`python manage.py migrate`); its views, serializers, and DRF routing
> are unused. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture, including which
> features (PDF notes, AI quiz generation) haven't been ported to Flask yet.

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis (optional — required only when `AI_GENERATION_MODE=celery`)

### 1. Clone the repository

```bash
git clone https://github.com/Shemsanofly/Coding-Platform.git
cd Coding-Platform
```

### 2. Backend setup

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python app.py
```

Backend runs at `http://127.0.0.1:8000/` — API base: `http://127.0.0.1:8000/api/`

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173/` with API requests proxied to the Flask backend (see `frontend/vite.config.js`).

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Backend signing secret |
| `DEBUG` | No | Enable debug mode (default: `True`) |
| `DATABASE_URL` | No | Leave empty for SQLite development; set to `postgresql://user:password@host:5432/dbname` in production |
| `DATABASE_PATH` | No | Optional custom SQLite database path when `DATABASE_URL` is empty; defaults to `backend/db.sqlite3` |
| `DATABASE_CONN_MAX_AGE` | No | Django persistent connection lifetime in seconds; useful for production PostgreSQL |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key for quiz and PDF notes |
| `GEMINI_MODEL` | No | Gemini model name (default: `gemini-3.5-flash`) |
| `ADMIN_REGISTRATION_CODE` | No | Code required for admin signup (default: `Admin2026`) |
| `AI_GENERATION_MODE` | No | `manual` (admin-triggered) or `celery` (async) |
| `AI_GENERATION_SYNC_FALLBACK` | No | Run generation in-process if Redis is down |
| `CELERY_BROKER_URL` | No | Redis URL for Celery (default: `redis://localhost:6379/0`) |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated frontend origins |
| `ALLOWED_HOSTS` | No | Comma-separated allowed hosts |

### Database Selection

The backend switches database by environment:

- Local development: leave `DATABASE_URL` unset or empty. The app uses SQLite at `backend/db.sqlite3`.
- Production: set `DATABASE_URL` to a PostgreSQL URL, for example `postgresql://user:password@host:5432/learncode`.

Run migrations after changing databases:

```bash
cd backend
python manage.py migrate
```

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | No | API base URL — leave unset to use Vite dev proxy |
| `VITE_DEV_SERVER_PORT` | No | Dev server port (default: `5173`) |

## Project Structure

```
Coding_Platform/
├── backend/
│   ├── accounts/          # User auth, roles, experience level
│   ├── ai_engine/         # Gemini, transcripts, quiz pipeline, learning path
│   ├── app.py             # Flask development server entrypoint
│   ├── flask_app.py       # Live backend: Flask app factory + all API routes (raw SQL)
│   ├── core/              # Django settings/migrations wiring + live Flask tests (core/tests/test_flask_runtime.py)
│   ├── courses/           # Django app: models.py drives migrations; views/serializers unused
│   ├── progress/          # Django app: models.py drives migrations; views/serializers unused
│   ├── quizzes/           # Django app: models.py drives migrations; views/serializers unused
│   ├── ai_engine/         # Django app: Gemini/transcript/quiz pipeline — not called by flask_app.py yet
│   ├── accounts/          # Django app: models.py drives migrations; views/serializers unused
│   ├── _legacy/           # Quarantined DRF test suites (see backend/_legacy/README.md)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── admin/         # Admin dashboard, course setup, AI status panel
│   │   ├── api/           # Axios API clients
│   │   ├── student/       # Catalog, lessons, PDF reader, quiz, recommendations
│   │   ├── shared/        # Auth, layouts, guards, common components
│   │   └── store/         # Zustand quiz session state
│   └── package.json
└── docs/
    └── AI_QUIZ_GENERATION.md
```

## Testing

### Backend

```bash
cd backend
python -m unittest core.tests.test_flask_runtime -v
```

This is the only test suite covering the live Flask backend. `backend/_legacy/` holds older
Django/DRF test suites that are not run by CI — see `backend/_legacy/README.md`.

### Frontend production build

```bash
cd frontend
npm run build
```

## Code Quality

```bash
# Backend — from backend/, with the virtualenv active
pip install -r requirements-dev.txt
ruff check .
black .

# Frontend — from frontend/
npm run lint
npm run format:check
```

A [pre-commit](https://pre-commit.com/) config (`.pre-commit-config.yaml`) runs all four checks
automatically on `git commit` once installed with `pre-commit install`. CI
(`.github/workflows/ci.yml`) enforces the same checks plus the backend test suite and a frontend
production build on every push and pull request.

## Main Workflow

```
Student Registration (with learning level)
        ↓
Course Enrollment
        ↓
Lesson Learning (YouTube video or in-platform PDF notes)
        ↓
Progress Sync (engagement + watch/read time)
        ↓
Quiz (after admin generates and approves questions)
        ↓
Weakness Detection
        ↓
Personalized Recommendations + Learning Path
        ↓
Adaptive Level Adjustment
```

### Admin setup flow

1. Register as Admin (requires registration code)
2. Create a course and set difficulty level
3. Add YouTube lessons with title, URL, and topic tags
4. Generate PDF notes and quiz from transcript
5. Preview and approve quiz questions
6. Publish the course

## License

Academic project — Bachelor of Computer Science.
