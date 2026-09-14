# AI-Based Adaptive E-Learning Platform

An adaptive e-learning platform with a Flask backend and React frontend.

Students can register, enroll in courses, study embedded lessons, read PDF notes, take quizzes,
track progress, generate certificates, and practice coding challenges. Admins can manage courses,
generate lesson notes, generate and approve quizzes, manage students, and download reports.

## Technology Stack

| Layer | Tools |
| --- | --- |
| Backend | Flask 3, SQLite for development, PostgreSQL for production |
| Frontend | React 18, Vite, Tailwind CSS, React Query, Zustand |
| PDF | ReportLab |
| AI integrations | Google Gemini API-ready configuration |
| Transcripts | youtube-transcript-api |
| Auth | Flask signed bearer tokens and httpOnly refresh cookie |

## Backend Setup

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python app.py
```

The backend runs at `http://127.0.0.1:8000/`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173/`.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Backend signing secret |
| `FLASK_DEBUG` | No | Enables Flask debug mode |
| `DATABASE_URL` | No | PostgreSQL URL for production; leave empty for SQLite |
| `DATABASE_PATH` | No | Optional SQLite path; defaults to `backend/db.sqlite3` |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key |
| `GEMINI_MODEL` | No | Gemini model name |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated frontend origins |

## Project Structure

```text
Coding_Platform/
├── backend/
│   ├── app.py
│   ├── flask_app.py
│   ├── core/
│   │   └── tests/
│   │       └── test_flask_runtime.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   └── package.json
└── docs/
    └── AI_QUIZ_GENERATION.md
```

## Testing

Backend:

```bash
cd backend
python -m pytest core/tests/test_flask_runtime.py -q
python -m ruff check .
```

Frontend:

```bash
cd frontend
npm run build
```

## Main Workflow

```text
Student registration
  -> Course enrollment
  -> Lesson learning
  -> Progress sync
  -> Quiz
  -> Weakness review
  -> Recommendations and learning path
  -> Certificate generation
```

## License

Academic project - Bachelor of Computer Science.
