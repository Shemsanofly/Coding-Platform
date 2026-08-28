import base64
import functools
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from flask import Flask, Response, g, jsonify, make_response, request, send_file
from flask_cors import CORS
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "db.sqlite3"
ACCESS_TOKEN_MAX_AGE = 15 * 60
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 1000000


def load_dotenv(path=BASE_DIR / ".env"):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _reexec_from_local_venv():
    """Prefer the project virtualenv when launched with global Python."""
    project_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if not project_python.exists():
        return
    current_python = Path(sys.executable).resolve()
    if current_python == project_python.resolve():
        return
    os.execv(str(project_python), [str(project_python), *sys.argv])


_reexec_from_local_venv()


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_json(value, fallback=None):
    if value in (None, ""):
        return [] if fallback is None else fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return [] if fallback is None else fallback


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def django_pbkdf2_hash(password, salt=None, iterations=PASSWORD_ITERATIONS):
    salt = salt or secrets.token_urlsafe(16)[:22]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    encoded = base64.b64encode(digest).decode("ascii").strip()
    return f"pbkdf2_sha256${iterations}${salt}${encoded}"


def check_password(password, encoded):
    if not encoded or not password:
        return False
    if encoded.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = encoded.split("$", 3)
            candidate = django_pbkdf2_hash(password, salt=salt, iterations=int(iterations)).rsplit("$", 1)[1]
            return hmac.compare_digest(candidate, expected)
        except (TypeError, ValueError):
            return False
    return False


def make_paginated(items, page=1, page_size=20):
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 100), 1)
    count = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "count": count,
        "next": None if end >= count else str(page + 1),
        "previous": None if page <= 1 else str(page - 1),
        "results": items[start:end],
    }


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(
        DATABASE_PATH=os.environ.get("DATABASE_PATH", str(DEFAULT_DB_PATH)),
        SECRET_KEY=os.environ.get("SECRET_KEY", "flask-dev-secret-change-me"),
        REFRESH_COOKIE_NAME=os.environ.get("JWT_REFRESH_COOKIE_NAME", "ai_elearn_refresh"),
        TESTING=False,
    )
    if config:
        app.config.update(config)

    CORS(
        app,
        supports_credentials=True,
        origins=os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(","),
    )

    def serializer():
        return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="learncode-auth")

    def db():
        if "db" not in g:
            con = sqlite3.connect(app.config["DATABASE_PATH"])
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            g.db = con
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        con = g.pop("db", None)
        if con is not None:
            con.close()

    def query_one(sql, params=()):
        return db().execute(sql, params).fetchone()

    def query_all(sql, params=()):
        return db().execute(sql, params).fetchall()

    def execute(sql, params=()):
        con = db()
        cur = con.execute(sql, params)
        con.commit()
        return cur

    def table_exists(name):
        row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return bool(row)

    def json_error(detail, status=400, errors=None):
        body = {"detail": detail}
        if errors:
            body["errors"] = errors
        return jsonify(body), status

    def user_payload(user):
        first = user["first_name"] or ""
        last = user["last_name"] or ""
        full_name = f"{first} {last}".strip() or (user["email"].split("@")[0] if user["email"] else "User")
        image = user["profile_image"] or ""
        return {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "first_name": first,
            "last_name": last,
            "full_name": full_name,
            "experience_level": user["experience_level"],
            "profile_image_url": f"/media/{image}" if image else None,
            "created_at": user["created_at"],
        }

    def make_token(user_id, token_type):
        return serializer().dumps({"user_id": user_id, "type": token_type})

    def load_token(token, token_type, max_age):
        data = serializer().loads(token, max_age=max_age)
        if data.get("type") != token_type:
            raise BadSignature("Wrong token type")
        return data

    def current_user_from_request():
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.removeprefix("Bearer ").strip()
        try:
            data = load_token(token, "access", ACCESS_TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        return query_one(
            "SELECT * FROM accounts_user WHERE id=? AND is_active=1",
            (data.get("user_id"),),
        )

    def require_auth(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user_from_request()
            if user is None:
                return json_error("Authentication credentials were not provided.", 401)
            g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    def require_admin(view):
        @require_auth
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if g.current_user["role"] != "admin":
                return json_error("Admin access required.", 403)
            return view(*args, **kwargs)

        return wrapper

    def route_api(rule, **options):
        def decorator(view):
            app.route(f"/api{rule}", **options)(view)
            app.route(f"/api/v1{rule}", **options)(view)
            return view

        return decorator

    def lesson_count(course_id):
        return query_one("SELECT COUNT(*) AS c FROM courses_lesson WHERE course_id=?", (course_id,))["c"]

    def course_payload(course, include_admin=False):
        payload = {
            "id": course["id"],
            "title": course["title"],
            "level": course["level"],
            "status": course["status"],
            "lesson_count": lesson_count(course["id"]) if table_exists("courses_lesson") else 0,
            "created_at": course["created_at"],
        }
        if include_admin:
            enrolled = query_one(
                "SELECT COUNT(*) AS c FROM progress_enrollment WHERE course_id=?",
                (course["id"],),
            )["c"] if table_exists("progress_enrollment") else 0
            quiz_done = query_one(
                """
                SELECT COUNT(DISTINCT q.lesson_id) AS c
                FROM quizzes_quiz q
                JOIN quizzes_question qq ON qq.quiz_id=q.id
                JOIN courses_lesson l ON l.id=q.lesson_id
                WHERE l.course_id=? AND q.generation_status='done' AND qq.is_published=1
                """,
                (course["id"],),
            )["c"] if table_exists("quizzes_quiz") and table_exists("quizzes_question") else 0
            payload.update(
                {
                    "enrolled_students": enrolled,
                    "pending_approval_count": 0,
                    "failed_generation_count": 0,
                    "quiz_lessons_done": quiz_done,
                    "quiz_lessons_pending": max(payload["lesson_count"] - quiz_done, 0),
                    "last_updated": course["created_at"],
                }
            )
        return payload

    def youtube_embed_url(raw):
        raw = (raw or "").strip()
        if not raw:
            return ""
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        video_id = ""
        if "youtu.be" in host:
            video_id = (parsed.path or "").strip("/").split("/")[0]
        elif "youtube.com" in host or "youtube-nocookie.com" in host:
            parts = [p for p in (parsed.path or "").split("/") if p]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts"}:
                video_id = parts[1].split("?")[0]
            else:
                video_id = (parse_qs(parsed.query).get("v") or [""])[0]
        if not video_id:
            return ""
        origin = request.host_url.rstrip("/")
        return f"https://www.youtube.com/embed/{video_id}?enablejsapi=1&origin={quote(origin, safe='')}"

    def lesson_engagement_required_seconds(lesson):
        return max(60, int((lesson["estimated_minutes"] or 15) * 60 * 0.7))

    def lesson_study_complete(lesson, progress):
        if not progress:
            return False
        if progress["completed_at"]:
            return True
        if (progress["seconds_engaged"] or 0) < lesson_engagement_required_seconds(lesson):
            return False
        if progress["video_watch_pct"] is not None:
            return progress["video_watch_pct"] >= 70
        return True

    def lesson_payload(lesson, user_id=None, detail=False):
        progress = None
        if user_id and table_exists("progress_lessonprogress"):
            progress = query_one(
                "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
                (user_id, lesson["id"]),
            )
        quiz = query_one("SELECT * FROM quizzes_quiz WHERE lesson_id=?", (lesson["id"],)) if table_exists("quizzes_quiz") else None
        question_count = (
            query_one(
                "SELECT COUNT(*) AS c FROM quizzes_question WHERE quiz_id=? AND is_published=1",
                (quiz["id"],),
            )["c"]
            if quiz and table_exists("quizzes_question")
            else 0
        )
        quiz_passed = False
        if user_id and quiz and table_exists("quizzes_quizresult"):
            row = query_one(
                "SELECT MAX(score) AS score FROM quizzes_quizresult WHERE user_id=? AND quiz_id=?",
                (user_id, quiz["id"]),
            )
            quiz_passed = bool(row and row["score"] is not None and row["score"] >= quiz["passing_score"])
        ai = query_one("SELECT * FROM ai_engine_lessonaiprocessing WHERE lesson_id=?", (lesson["id"],)) if table_exists("ai_engine_lessonaiprocessing") else None
        analysis = parse_json(ai["analysis_json"], {}) if ai else {}
        content = lesson["content"] or ""
        base = {
            "id": lesson["id"],
            "title": lesson["title"],
            "source_type": lesson["source_type"],
            "resource_url": lesson["resource_url"],
            "content": content,
            "difficulty": lesson["difficulty"],
            "estimated_minutes": lesson["estimated_minutes"],
            "tags": parse_json(lesson["tags"], []),
            "learning_objective": lesson["learning_objective"],
            "order": lesson["order"],
            "topic_tag": lesson["topic_tag"],
            "quiz_generation_status": quiz["generation_status"] if quiz else "pending",
            "ai_processing_status": ai["status"] if ai else "pending",
            "quiz_generation_error": quiz["generation_error"] if quiz else "",
            "quiz_available": bool(quiz and quiz["generation_status"] == "done" and question_count),
            "quiz_ready": bool(quiz and quiz["generation_status"] == "done" and question_count),
            "quiz_passed": quiz_passed,
            "lesson_officially_completed": bool(progress and progress["completed_at"]),
            "unlocked": True,
            "has_pdf_notes": bool(lesson["pdf_notes"]),
            "pdf_notes_url": f"/api/lessons/{lesson['id']}/view-notes/" if lesson["pdf_notes"] else "",
        }
        if detail:
            course = query_one("SELECT * FROM courses_course WHERE id=?", (lesson["course_id"],))
            base.update(
                {
                    "course_id": lesson["course_id"],
                    "course_title": course["title"] if course else "",
                    "summary": (analysis.get("summary") if isinstance(analysis, dict) else None) or content,
                    "learning_objectives": (analysis.get("learning_objectives") if isinstance(analysis, dict) else None) or [],
                    "key_concepts": (analysis.get("key_concepts") if isinstance(analysis, dict) else None) or [],
                    "seconds_engaged": progress["seconds_engaged"] if progress else 0,
                    "max_scroll_depth_pct": progress["max_scroll_depth_pct"] if progress else 0,
                    "video_watch_pct": progress["video_watch_pct"] if progress else None,
                    "engagement_required_seconds": lesson_engagement_required_seconds(lesson),
                    "engagement_satisfied": lesson_study_complete(lesson, progress),
                    "youtube_embed_url": youtube_embed_url(lesson["resource_url"]) if lesson["source_type"] == "youtube" else "",
                    "notes_viewed_at": progress["notes_viewed_at"] if progress else None,
                    "notes_downloaded_at": progress["notes_downloaded_at"] if progress else None,
                }
            )
        return base

    @app.get("/health/")
    def health():
        return jsonify({"backend": "flask", "status": "ok"})

    @app.post("/auth/register/")
    def register():
        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        confirm = payload.get("confirm_password") or ""
        role = payload.get("role") or "student"
        level = payload.get("experience_level")
        errors = {}
        if "@" not in email:
            errors["email"] = "Enter a valid email address."
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        if role != "student":
            errors["role"] = "Public registration is for student accounts only."
        if not level:
            errors["experience_level"] = "Learning level is required for student accounts."
        if errors:
            return json_error("Validation failed.", 400, errors)
        if query_one("SELECT id FROM accounts_user WHERE lower(email)=lower(?)", (email,)):
            return json_error("Validation failed.", 400, {"email": "A user with this email already exists."})
        now = utcnow()
        execute(
            """
            INSERT INTO accounts_user
                (password, last_login, is_superuser, first_name, last_name, is_staff,
                 is_active, date_joined, email, role, created_at, experience_level, profile_image)
            VALUES (?, NULL, 0, '', '', 0, 1, ?, ?, 'student', ?, ?, '')
            """,
            (django_pbkdf2_hash(password), now, email, now, level),
        )
        return jsonify({"detail": "Account created successfully. Please sign in."}), 201

    @app.post("/auth/login/")
    def login():
        payload = request.get_json(silent=True) or {}
        user = query_one(
            "SELECT * FROM accounts_user WHERE lower(email)=lower(?) AND is_active=1",
            ((payload.get("email") or "").strip(),),
        )
        if not user or not check_password(payload.get("password") or "", user["password"]):
            return json_error("No active account found with the given credentials", 403)
        execute("UPDATE accounts_user SET last_login=? WHERE id=?", (utcnow(), user["id"]))
        refresh = make_token(user["id"], "refresh")
        response = jsonify({"access": make_token(user["id"], "access")})
        response.set_cookie(
            app.config["REFRESH_COOKIE_NAME"],
            refresh,
            max_age=REFRESH_TOKEN_MAX_AGE,
            httponly=True,
            secure=False,
            samesite="Lax",
            path="/",
        )
        return response

    @app.post("/auth/refresh/")
    def refresh():
        raw = request.cookies.get(app.config["REFRESH_COOKIE_NAME"])
        if not raw:
            return json_error("Refresh token not provided.", 401)
        try:
            data = load_token(raw, "refresh", REFRESH_TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            response = make_response(jsonify({"detail": "Invalid or expired refresh token."}), 401)
            response.delete_cookie(app.config["REFRESH_COOKIE_NAME"], path="/", samesite="Lax")
            return response
        user = query_one("SELECT * FROM accounts_user WHERE id=? AND is_active=1", (data.get("user_id"),))
        if not user:
            return json_error("Invalid or expired refresh token.", 401)
        return jsonify({"access": make_token(user["id"], "access")})

    @app.post("/auth/logout/")
    def logout():
        response = make_response("", 204)
        response.delete_cookie(app.config["REFRESH_COOKIE_NAME"], path="/", samesite="Lax")
        return response

    @app.get("/auth/me/")
    @require_auth
    def me():
        return jsonify(user_payload(g.current_user))

    @app.patch("/auth/me/")
    @require_auth
    def update_me():
        payload = request.get_json(silent=True) or {}
        first = payload.get("first_name", g.current_user["first_name"]) or ""
        last = payload.get("last_name", g.current_user["last_name"]) or ""
        level = payload.get("experience_level", g.current_user["experience_level"])
        execute(
            "UPDATE accounts_user SET first_name=?, last_name=?, experience_level=? WHERE id=?",
            (first, last, level, g.current_user["id"]),
        )
        user = query_one("SELECT * FROM accounts_user WHERE id=?", (g.current_user["id"],))
        return jsonify(user_payload(user))

    @route_api("/catalog/courses/", methods=["GET"])
    @require_auth
    def catalog_courses():
        level = request.args.get("level")
        sql = "SELECT * FROM courses_course WHERE status IN ('ready','published')"
        params = []
        if level:
            sql += " AND level=?"
            params.append(level)
        sql += " ORDER BY created_at DESC"
        courses = []
        enrolled = {
            row["course_id"]
            for row in query_all("SELECT course_id FROM progress_enrollment WHERE user_id=?", (g.current_user["id"],))
        } if table_exists("progress_enrollment") else set()
        for course in query_all(sql, params):
            item = course_payload(course)
            item["is_enrolled"] = course["id"] in enrolled
            courses.append(item)
        return jsonify(make_paginated(courses, request.args.get("page"), request.args.get("page_size")))

    @route_api("/enrollments/join/", methods=["POST"])
    @require_auth
    def join_course():
        course_id = (request.get_json(silent=True) or {}).get("course_id")
        course = query_one("SELECT * FROM courses_course WHERE id=?", (course_id,))
        if not course:
            return json_error("Course not found.", 404)
        now = utcnow()
        execute(
            """
            INSERT OR IGNORE INTO progress_enrollment (enrolled_at, course_id, user_id, completed_at, status)
            VALUES (?, ?, ?, NULL, 'ACTIVE')
            """,
            (now, course_id, g.current_user["id"]),
        )
        return jsonify({"detail": "Enrolled.", "course_id": int(course_id), "status": "ACTIVE"})

    @route_api("/enrollments/", methods=["GET"])
    @require_auth
    def enrollments():
        if not table_exists("progress_enrollment"):
            return jsonify(make_paginated([], request.args.get("page"), request.args.get("page_size")))
        rows = query_all(
            """
            SELECT c.*, e.enrolled_at, e.status AS enrollment_status
            FROM progress_enrollment e
            JOIN courses_course c ON c.id=e.course_id
            WHERE e.user_id=?
            ORDER BY e.enrolled_at DESC
            """,
            (g.current_user["id"],),
        )
        items = []
        for row in rows:
            item = course_payload(row)
            item.update({"progress": 0, "enrollment_status": row["enrollment_status"], "enrolled_at": row["enrolled_at"]})
            items.append(item)
        return jsonify(make_paginated(items, request.args.get("page"), request.args.get("page_size")))

    @route_api("/student/courses/<int:course_id>/", methods=["GET"])
    @require_auth
    def student_course(course_id):
        course = query_one("SELECT * FROM courses_course WHERE id=?", (course_id,))
        if not course:
            return json_error("Course not found.", 404)
        enrolled = query_one(
            "SELECT * FROM progress_enrollment WHERE user_id=? AND course_id=?",
            (g.current_user["id"], course_id),
        )
        if not enrolled and g.current_user["role"] != "admin":
            return json_error("Enrollment required.", 403)
        lessons = [
            lesson_payload(row, g.current_user["id"])
            for row in query_all("SELECT * FROM courses_lesson WHERE course_id=? ORDER BY \"order\", id", (course_id,))
        ]
        payload = course_payload(course)
        payload.update(
            {
                "lessons": lessons,
                "completed_lessons": sum(1 for lesson in lessons if lesson["quiz_passed"] or lesson["lesson_officially_completed"]),
                "progress_percent": 0 if not lessons else round(sum(1 for lesson in lessons if lesson["quiz_passed"] or lesson["lesson_officially_completed"]) / len(lessons) * 100),
                "certificate_eligible": False,
                "certificate_reasons": ["Complete every lesson and pass each quiz."],
                "certificate": None,
            }
        )
        return jsonify(payload)

    @route_api("/student/lessons/<int:lesson_id>/", methods=["GET"])
    @require_auth
    def student_lesson(lesson_id):
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,))
        if not lesson:
            return json_error("Lesson not found.", 404)
        enrolled = query_one(
            "SELECT id FROM progress_enrollment WHERE user_id=? AND course_id=?",
            (g.current_user["id"], lesson["course_id"]),
        )
        if not enrolled and g.current_user["role"] != "admin":
            return json_error("Enrollment required.", 403)
        return jsonify(lesson_payload(lesson, g.current_user["id"], detail=True))

    @route_api("/student/lessons/<int:lesson_id>/progress/", methods=["POST"])
    @require_auth
    def lesson_progress(lesson_id):
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,))
        if not lesson:
            return json_error("Lesson not found.", 404)
        payload = request.get_json(silent=True) or {}
        delta = max(int(payload.get("delta_seconds") or 0), 0)
        scroll = min(max(int(payload.get("scroll_depth_pct") or 0), 0), 100)
        video = payload.get("video_watch_pct")
        now = utcnow()
        existing = query_one(
            "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
            (g.current_user["id"], lesson_id),
        )
        if existing:
            execute(
                """
                UPDATE progress_lessonprogress
                SET last_opened_at=?, seconds_engaged=seconds_engaged+?,
                    max_scroll_depth_pct=max(max_scroll_depth_pct, ?),
                    video_watch_pct=CASE WHEN ? IS NULL THEN video_watch_pct ELSE max(coalesce(video_watch_pct, 0), ?) END
                WHERE id=?
                """,
                (now, delta, scroll, video, video, existing["id"]),
            )
        else:
            execute(
                """
                INSERT INTO progress_lessonprogress
                    (first_opened_at, last_opened_at, completed_at, lesson_id, user_id,
                     seconds_engaged, max_scroll_depth_pct, video_watch_pct, notes_downloaded_at, notes_viewed_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (now, now, lesson_id, g.current_user["id"], delta, scroll, video),
            )
        row = query_one(
            "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
            (g.current_user["id"], lesson_id),
        )
        if row and not row["completed_at"] and lesson_study_complete(lesson, row):
            execute("UPDATE progress_lessonprogress SET completed_at=? WHERE id=?", (now, row["id"]))
            row = query_one(
                "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
                (g.current_user["id"], lesson_id),
            )
        return jsonify(
            {
                "seconds_engaged": row["seconds_engaged"],
                "max_scroll_depth_pct": row["max_scroll_depth_pct"],
                "video_watch_pct": row["video_watch_pct"],
                "completed_at": row["completed_at"],
            }
        )

    @route_api("/dashboard/", methods=["GET"])
    @require_auth
    def dashboard():
        if g.current_user["role"] != "student":
            return json_error("This dashboard is available to student accounts only.", 403)
        enroll_response = enrollments().get_json()
        analytics = analytics_summary().get_json()
        path = learning_path().get_json()
        return jsonify({"enrollments": enroll_response.get("results", []), "analytics": analytics, "learning_path": path})

    @route_api("/analytics/summary/", methods=["GET"])
    @require_auth
    def analytics_summary():
        total_enrolled = query_one("SELECT COUNT(*) AS c FROM progress_enrollment WHERE user_id=?", (g.current_user["id"],))["c"] if table_exists("progress_enrollment") else 0
        quiz_rows = query_all("SELECT score FROM quizzes_quizresult WHERE user_id=?", (g.current_user["id"],)) if table_exists("quizzes_quizresult") else []
        avg_score = round(sum(row["score"] for row in quiz_rows) / len(quiz_rows), 1) if quiz_rows else 0
        return jsonify(
            {
                "learning_level": g.current_user["experience_level"],
                "enrolled_courses": total_enrolled,
                "lessons_passed_quiz": 0,
                "lessons_remaining": 0,
                "total_lessons_in_enrolled_courses": 0,
                "avg_quiz_score": avg_score,
                "weak_topics_tracked": 0,
            }
        )

    @route_api("/learning-path/", methods=["GET"])
    @require_auth
    def learning_path():
        rows = query_all(
            """
            SELECT l.*, c.title AS course_title
            FROM progress_enrollment e
            JOIN courses_lesson l ON l.course_id=e.course_id
            JOIN courses_course c ON c.id=l.course_id
            WHERE e.user_id=?
            ORDER BY c.created_at DESC, l."order", l.id
            """,
            (g.current_user["id"],),
        ) if table_exists("progress_enrollment") else []
        path = [
            {
                "step": index + 1,
                "lesson_id": row["id"],
                "lesson_title": row["title"],
                "course_id": row["course_id"],
                "course_title": row["course_title"],
                "status": "next" if index == 0 else "upcoming",
            }
            for index, row in enumerate(rows)
        ]
        return jsonify({"learning_path": path, "progress": {"percent_complete": 0, "next_lesson_id": path[0]["lesson_id"] if path else None}})

    @route_api("/weaknesses/", methods=["GET"])
    @require_auth
    def weaknesses():
        return jsonify({"topics": [], "lesson_groups": [], "courses": []})

    @route_api("/recommendations/", methods=["GET"])
    @require_auth
    def recommendations():
        return jsonify([])

    @route_api("/practice/leaderboard/", methods=["GET"])
    @require_auth
    def practice_leaderboard():
        return jsonify({"leaderboard": [], "total_students": 0, "me": None})

    @route_api("/student/lessons/<int:lesson_id>/weakness-summary/", methods=["GET"])
    @require_auth
    def lesson_weakness_summary(lesson_id):
        return jsonify({"lesson_id": lesson_id, "topics": [], "summary": "No weak topics recorded yet."})

    @route_api("/lessons/<int:lesson_id>/quiz/", methods=["GET"])
    @require_auth
    def lesson_quiz(lesson_id):
        quiz = query_one("SELECT * FROM quizzes_quiz WHERE lesson_id=?", (lesson_id,)) if table_exists("quizzes_quiz") else None
        if not quiz:
            return json_error("Quiz is not ready yet.", 404)
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,))
        progress = (
            query_one(
                "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
                (g.current_user["id"], lesson_id),
            )
            if table_exists("progress_lessonprogress")
            else None
        )
        if lesson and not lesson_study_complete(lesson, progress):
            return json_error("Study this lesson to 100% before taking the quiz.", 403)
        questions = [
            {
                "id": row["id"],
                "order": row["order"],
                "stem": row["stem"],
                "choices": parse_json(row["choices"], []),
                "topic_tag": row["topic_tag"],
                "question_type": row["question_type"],
                "difficulty": row["difficulty"],
                "bloom_level": row["bloom_level"],
            }
            for row in query_all("SELECT * FROM quizzes_question WHERE quiz_id=? AND is_published=1 ORDER BY \"order\", id", (quiz["id"],))
        ]
        return jsonify({"id": quiz["id"], "lesson_id": lesson_id, "passing_score": quiz["passing_score"], "questions": questions})

    @route_api("/quizzes/<int:quiz_id>/submit/", methods=["POST"])
    @require_auth
    def submit_quiz(quiz_id):
        quiz = query_one("SELECT * FROM quizzes_quiz WHERE id=?", (quiz_id,))
        if not quiz:
            return json_error("Quiz not found.", 404)
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (quiz["lesson_id"],))
        progress = (
            query_one(
                "SELECT * FROM progress_lessonprogress WHERE user_id=? AND lesson_id=?",
                (g.current_user["id"], quiz["lesson_id"]),
            )
            if table_exists("progress_lessonprogress")
            else None
        )
        if lesson and not lesson_study_complete(lesson, progress):
            return json_error("Study this lesson to 100% before submitting the quiz.", 403)
        answers = (request.get_json(silent=True) or {}).get("answers") or {}
        questions = query_all("SELECT * FROM quizzes_question WHERE quiz_id=? AND is_published=1 ORDER BY \"order\", id", (quiz_id,))
        correct = 0
        details = []
        for row in questions:
            answer = answers.get(str(row["id"]), answers.get(row["id"]))
            is_correct = int(answer) == row["correct_index"] if answer is not None else False
            correct += 1 if is_correct else 0
            details.append({"question_id": row["id"], "correct": is_correct, "correct_index": row["correct_index"], "explanation": row["explanation"]})
        score = round((correct / len(questions)) * 100) if questions else 0
        execute(
            "INSERT INTO quizzes_quizresult (score, answers, taken_at, quiz_id, user_id) VALUES (?, ?, ?, ?, ?)",
            (score, json.dumps(answers), utcnow(), quiz_id, g.current_user["id"]),
        )
        return jsonify({"score": score, "passed": score >= quiz["passing_score"], "correct_count": correct, "total_questions": len(questions), "results": details})

    @route_api("/lessons/<int:lesson_id>/notes/", methods=["GET"])
    @require_auth
    def lesson_notes(lesson_id):
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,))
        if not lesson or not lesson["pdf_notes"]:
            return json_error("PDF notes are not available.", 404)
        return jsonify({"lesson_id": lesson_id, "pdf_notes_url": f"/api/lessons/{lesson_id}/view-notes/", "ai_summary": {}, "activity": {}})

    @route_api("/lessons/<int:lesson_id>/view-notes/", methods=["GET"])
    @require_auth
    def view_notes(lesson_id):
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,))
        if not lesson or not lesson["pdf_notes"]:
            return json_error("PDF notes are not available.", 404)
        path = BASE_DIR / "media" / lesson["pdf_notes"]
        if not path.exists():
            return json_error("PDF file is missing.", 404)
        return send_file(path, mimetype="application/pdf")

    @route_api("/lessons/<int:lesson_id>/download-notes/", methods=["GET"])
    @require_auth
    def download_notes(lesson_id):
        return view_notes(lesson_id)

    @route_api("/lessons/<int:lesson_id>/generate-notes/", methods=["POST"])
    @require_admin
    def generate_notes(lesson_id):
        return jsonify({"lesson_id": lesson_id, "status": "pending", "detail": "PDF generation is not ported to Flask yet."}), 202

    @route_api("/admin/courses/", methods=["GET"])
    @require_admin
    def admin_courses():
        rows = query_all("SELECT * FROM courses_course ORDER BY created_at DESC")
        return jsonify([course_payload(row, include_admin=True) for row in rows])

    @route_api("/admin/courses/", methods=["POST"])
    @require_admin
    def create_course():
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        level = payload.get("level") or "beginner"
        if not title:
            return json_error("Validation failed.", 400, {"title": "This field is required."})
        cur = execute(
            "INSERT INTO courses_course (title, level, status, created_at, created_by_id) VALUES (?, ?, 'draft', ?, ?)",
            (title, level, utcnow(), g.current_user["id"]),
        )
        course = query_one("SELECT * FROM courses_course WHERE id=?", (cur.lastrowid,))
        return jsonify(course_payload(course, include_admin=True)), 201

    @route_api("/admin/courses/<int:course_id>/", methods=["GET"])
    @require_admin
    def admin_course(course_id):
        course = query_one("SELECT * FROM courses_course WHERE id=?", (course_id,))
        if not course:
            return json_error("Course not found.", 404)
        payload = course_payload(course, include_admin=True)
        payload["sources"] = rows_to_dicts(query_all("SELECT * FROM courses_coursesource WHERE course_id=?", (course_id,))) if table_exists("courses_coursesource") else []
        return jsonify(payload)

    @route_api("/admin/courses/<int:course_id>/", methods=["PATCH"])
    @require_admin
    def update_course(course_id):
        course = query_one("SELECT * FROM courses_course WHERE id=?", (course_id,))
        if not course:
            return json_error("Course not found.", 404)
        payload = request.get_json(silent=True) or {}
        title = payload.get("title", course["title"])
        level = payload.get("level", course["level"])
        status = payload.get("status", course["status"])
        execute("UPDATE courses_course SET title=?, level=?, status=? WHERE id=?", (title, level, status, course_id))
        return jsonify(course_payload(query_one("SELECT * FROM courses_course WHERE id=?", (course_id,)), include_admin=True))

    @route_api("/admin/courses/<int:course_id>/", methods=["DELETE"])
    @require_admin
    def delete_course(course_id):
        execute("DELETE FROM courses_course WHERE id=?", (course_id,))
        return "", 204

    @route_api("/admin/courses/<int:course_id>/lessons/", methods=["GET"])
    @require_admin
    def admin_lessons(course_id):
        rows = query_all("SELECT * FROM courses_lesson WHERE course_id=? ORDER BY \"order\", id", (course_id,))
        return jsonify([lesson_payload(row, detail=True) for row in rows])

    @route_api("/admin/courses/<int:course_id>/lessons/", methods=["POST"])
    @require_admin
    def create_lesson(course_id):
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        if not title:
            return json_error("Validation failed.", 400, {"title": "This field is required."})
        next_order = query_one("SELECT COALESCE(MAX(\"order\"), -1) + 1 AS n FROM courses_lesson WHERE course_id=?", (course_id,))["n"]
        cur = execute(
            """
            INSERT INTO courses_lesson
                (title, content, "order", topic_tag, is_auto_generated, created_at, course_id,
                 source_type, resource_url, difficulty, estimated_minutes, tags, learning_objective,
                 ai_summary, embedded_url, notes_generated_at, pdf_notes, transcript_text)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '', NULL, '', '')
            """,
            (
                title,
                payload.get("content") or "",
                next_order,
                payload.get("topic_tag") or "",
                utcnow(),
                course_id,
                payload.get("source_type") or "youtube",
                payload.get("resource_url") or payload.get("video_url") or "",
                payload.get("difficulty") or payload.get("difficulty_level") or "beginner",
                payload.get("estimated_minutes") or payload.get("estimated_time") or 15,
                json.dumps(payload.get("tags") or payload.get("topic_tags") or []),
                payload.get("learning_objective") or "",
            ),
        )
        return jsonify(lesson_payload(query_one("SELECT * FROM courses_lesson WHERE id=?", (cur.lastrowid,)), detail=True)), 201

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/", methods=["PATCH"])
    @require_admin
    def update_lesson(course_id, lesson_id):
        lesson = query_one("SELECT * FROM courses_lesson WHERE id=? AND course_id=?", (lesson_id, course_id))
        if not lesson:
            return json_error("Lesson not found.", 404)
        payload = request.get_json(silent=True) or {}
        execute(
            """
            UPDATE courses_lesson
            SET title=?, content=?, source_type=?, resource_url=?, difficulty=?,
                estimated_minutes=?, tags=?, learning_objective=?, topic_tag=?
            WHERE id=?
            """,
            (
                payload.get("title", lesson["title"]),
                payload.get("content", lesson["content"]),
                payload.get("source_type", lesson["source_type"]),
                payload.get("resource_url", payload.get("video_url", lesson["resource_url"])),
                payload.get("difficulty", payload.get("difficulty_level", lesson["difficulty"])),
                payload.get("estimated_minutes", payload.get("estimated_time", lesson["estimated_minutes"])),
                json.dumps(payload.get("tags", payload.get("topic_tags", parse_json(lesson["tags"], [])))),
                payload.get("learning_objective", lesson["learning_objective"]),
                payload.get("topic_tag", lesson["topic_tag"]),
                lesson_id,
            ),
        )
        return jsonify(lesson_payload(query_one("SELECT * FROM courses_lesson WHERE id=?", (lesson_id,)), detail=True))

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/", methods=["DELETE"])
    @require_admin
    def delete_lesson(course_id, lesson_id):
        execute("DELETE FROM courses_lesson WHERE id=? AND course_id=?", (lesson_id, course_id))
        return "", 204

    @route_api("/admin/courses/dashboard-summary/", methods=["GET"])
    @require_admin
    def admin_dashboard_summary():
        return jsonify(
            {
                "total_courses": query_one("SELECT COUNT(*) AS c FROM courses_course")["c"],
                "published_courses": query_one("SELECT COUNT(*) AS c FROM courses_course WHERE status='published'")["c"],
                "total_students": query_one("SELECT COUNT(*) AS c FROM accounts_user WHERE role='student'")["c"],
                "total_lessons": query_one("SELECT COUNT(*) AS c FROM courses_lesson")["c"],
            }
        )

    @route_api("/admin/courses/analytics-overview/", methods=["GET"])
    @require_admin
    def admin_analytics_overview():
        return jsonify({"courses": [], "students": [], "quiz_average": 0, "completion_rate": 0})

    @route_api("/admin/courses/bootstrap-catalog/", methods=["POST"])
    @require_admin
    def bootstrap_catalog():
        existing = query_one("SELECT COUNT(*) AS c FROM courses_course")["c"]
        if existing:
            return jsonify({"created_count": 0, "created_ids": []})
        cur = execute(
            "INSERT INTO courses_course (title, level, status, created_at, created_by_id) VALUES ('Python Fundamentals', 'beginner', 'published', ?, ?)",
            (utcnow(), g.current_user["id"]),
        )
        return jsonify({"created_count": 1, "created_ids": [cur.lastrowid]})

    @route_api("/admin/courses/<int:course_id>/pipeline-status/", methods=["GET"])
    @require_admin
    def pipeline_status(course_id):
        return jsonify({"course_id": course_id, "status": "ready", "lessons": []})

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/processing-status/", methods=["GET"])
    @require_admin
    def lesson_processing_status(course_id, lesson_id):
        return jsonify({"course_id": course_id, "lesson_id": lesson_id, "ai_processing_status": "pending", "quiz_generation_status": "pending"})

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/quiz-preview/", methods=["GET"])
    @require_admin
    def quiz_preview(course_id, lesson_id):
        quiz = query_one("SELECT * FROM quizzes_quiz WHERE lesson_id=?", (lesson_id,)) if table_exists("quizzes_quiz") else None
        questions = rows_to_dicts(query_all("SELECT * FROM quizzes_question WHERE quiz_id=? ORDER BY \"order\", id", (quiz["id"],))) if quiz and table_exists("quizzes_question") else []
        for question in questions:
            question["choices"] = parse_json(question.get("choices"), [])
        return jsonify({"lesson_id": lesson_id, "questions": questions})

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/generate-quiz/", methods=["POST"])
    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/regenerate-quiz/", methods=["POST"])
    @require_admin
    def generate_quiz(course_id, lesson_id):
        return jsonify({"course_id": course_id, "lesson_id": lesson_id, "status": "pending", "detail": "AI quiz generation is not ported to Flask yet."}), 202

    @route_api("/admin/courses/<int:course_id>/lessons/<int:lesson_id>/approve-quiz/", methods=["POST"])
    @require_admin
    def approve_quiz(course_id, lesson_id):
        return jsonify({"course_id": course_id, "lesson_id": lesson_id, "approval_status": "approved"})

    @route_api("/admin/users/", methods=["GET"])
    @require_admin
    def admin_users():
        search = (request.args.get("search") or "").strip().lower()
        sql = "SELECT * FROM accounts_user WHERE role='student'"
        params = []
        if search:
            sql += " AND (lower(email) LIKE ? OR lower(first_name || ' ' || last_name) LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        rows = query_all(sql + " ORDER BY created_at DESC", params)
        items = []
        for row in rows:
            item = user_payload(row)
            item.update({"is_active": bool(row["is_active"]), "enrolled_count": 0, "completed_lessons": 0, "average_score": 0, "weakness_count": 0})
            items.append(item)
        return jsonify(make_paginated(items, request.args.get("page"), request.args.get("page_size")))

    @route_api("/admin/users/<int:user_id>/profile/", methods=["GET"])
    @require_admin
    def admin_user_profile(user_id):
        user = query_one("SELECT * FROM accounts_user WHERE id=?", (user_id,))
        if not user:
            return json_error("User not found.", 404)
        payload = user_payload(user)
        payload.update({"enrolled_count": 0, "completed_lessons": 0, "average_score": 0, "quiz_attempts": 0})
        return jsonify(payload)

    @route_api("/admin/students/<int:user_id>/", methods=["PATCH"])
    @require_admin
    def update_student(user_id):
        payload = request.get_json(silent=True) or {}
        user = query_one("SELECT * FROM accounts_user WHERE id=? AND role='student'", (user_id,))
        if not user:
            return json_error("Student not found.", 404)
        execute(
            "UPDATE accounts_user SET first_name=?, last_name=?, email=?, experience_level=? WHERE id=?",
            (
                payload.get("first_name", user["first_name"]),
                payload.get("last_name", user["last_name"]),
                payload.get("email", user["email"]),
                payload.get("experience_level", user["experience_level"]),
                user_id,
            ),
        )
        return jsonify(user_payload(query_one("SELECT * FROM accounts_user WHERE id=?", (user_id,))))

    @route_api("/admin/students/<int:user_id>/", methods=["DELETE"])
    @require_admin
    def deactivate_student(user_id):
        execute("UPDATE accounts_user SET is_active=0 WHERE id=? AND role='student'", (user_id,))
        return jsonify({"detail": "Student deactivated."})

    @route_api("/admin/students/<int:user_id>/purge/", methods=["POST"])
    @require_admin
    def purge_student(user_id):
        execute("DELETE FROM accounts_user WHERE id=? AND role='student'", (user_id,))
        return jsonify({"detail": "Student deleted."})

    @route_api("/admin/users/<int:user_id>/weaknesses/", methods=["GET"])
    @route_api("/admin/users/<int:user_id>/recommendations/", methods=["GET"])
    @route_api("/admin/users/<int:user_id>/quiz-log/", methods=["GET"])
    @require_admin
    def empty_admin_user_detail(user_id):
        return jsonify([])

    @route_api("/certificates/my-certificates/", methods=["GET"])
    @require_auth
    def my_certificates():
        if not table_exists("progress_certificate"):
            return jsonify([])
        rows = query_all("SELECT * FROM progress_certificate WHERE student_id=? ORDER BY issue_date DESC", (g.current_user["id"],))
        return jsonify(rows_to_dicts(rows))

    @route_api("/certificates/<int:certificate_id>/", methods=["GET"])
    @require_auth
    def certificate_detail(certificate_id):
        cert = query_one("SELECT * FROM progress_certificate WHERE id=?", (certificate_id,))
        if not cert:
            return json_error("Certificate not found.", 404)
        return jsonify(dict(cert))

    @route_api("/certificates/<int:certificate_id>/download/", methods=["GET"])
    @require_auth
    def certificate_download(certificate_id):
        cert = query_one("SELECT * FROM progress_certificate WHERE id=?", (certificate_id,))
        if not cert or not cert["file"]:
            return json_error("Certificate file is not available.", 404)
        path = BASE_DIR / "media" / cert["file"]
        if not path.exists():
            return json_error("Certificate file is missing.", 404)
        return send_file(path, mimetype="application/pdf", as_attachment=True)

    @route_api("/certificates/verify/<verification_code>/", methods=["GET"])
    def certificate_verify(verification_code):
        cert = query_one("SELECT * FROM progress_certificate WHERE verification_code=?", (verification_code,)) if table_exists("progress_certificate") else None
        if not cert:
            return json_error("Certificate not found.", 404)
        return jsonify(dict(cert))

    @route_api("/student/courses/<int:course_id>/certificate/eligibility/", methods=["GET"])
    @require_auth
    def certificate_eligibility(course_id):
        return jsonify({"eligible": False, "reasons": ["Complete every lesson and pass each quiz."], "certificate": None})

    @route_api("/student/courses/<int:course_id>/certificate/", methods=["POST"])
    @require_auth
    def generate_certificate(course_id):
        return json_error("Certificate generation is not ported to Flask yet.", 501)

    @route_api("/playground/challenge/", methods=["GET"])
    @require_auth
    def playground_challenge():
        return jsonify({"id": None, "title": "Python Warmup", "description": "Write a function named solve.", "difficulty": "beginner", "starter_code": "def solve():\n    pass\n", "test_cases": [], "xp_reward": 0})

    @route_api("/playground/challenge/generate/", methods=["POST"])
    @require_auth
    def playground_generate():
        return playground_challenge()

    @route_api("/playground/challenge/<int:challenge_id>/submit/", methods=["POST"])
    @require_auth
    def playground_submit(challenge_id):
        return jsonify({"challenge_id": challenge_id, "passed": False, "test_results": [], "xp_earned": 0})

    @route_api("/playground/leaderboard/", methods=["GET"])
    @require_auth
    def playground_leaderboard():
        return jsonify({"leaderboard": [], "total_students": 0, "me": None})

    def report_response(name):
        csv = "section,value\nstatus,Flask report endpoint active\n"
        return Response(csv, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={name}.csv"})

    for report_path in (
        "/admin/reports/summary/",
        "/admin/reports/courses/",
        "/admin/reports/students/",
        "/admin/reports/weaknesses/",
        "/admin/reports/ai-generation/",
        "/reports/my-progress/",
        "/reports/my-quiz-performance/",
        "/reports/my-weaknesses/",
        "/reports/my-learning-path/",
    ):
        endpoint = "report_" + report_path.strip("/").replace("/", "_").replace("-", "_")
        app.add_url_rule(f"/api{report_path}", endpoint + "_legacy", require_auth(lambda report_path=report_path: report_response(report_path.strip("/").replace("/", "_"))))
        app.add_url_rule(f"/api/v1{report_path}", endpoint + "_v1", require_auth(lambda report_path=report_path: report_response(report_path.strip("/").replace("/", "_"))))

    @app.errorhandler(404)
    def not_found(_error):
        return json_error("Not found.", 404)

    @app.errorhandler(sqlite3.OperationalError)
    def database_error(error):
        return json_error(f"Database error: {error}", 500)

    return app


app = create_app()


def run_dev_server():
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "8000")))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dev_server()
