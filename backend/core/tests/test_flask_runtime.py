import base64
import hashlib
import os
import sqlite3
import tempfile
import unittest


def legacy_pbkdf2_sha256(password, salt="testsalt", iterations=1000000):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    encoded = base64.b64encode(digest).decode("ascii").strip()
    return f"pbkdf2_sha256${iterations}${salt}${encoded}"


def init_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE accounts_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password varchar(128) NOT NULL,
            last_login datetime NULL,
            is_superuser bool NOT NULL DEFAULT 0,
            first_name varchar(150) NOT NULL DEFAULT '',
            last_name varchar(150) NOT NULL DEFAULT '',
            is_staff bool NOT NULL DEFAULT 0,
            is_active bool NOT NULL DEFAULT 1,
            date_joined datetime NOT NULL,
            email varchar(254) NOT NULL UNIQUE,
            role varchar(16) NOT NULL,
            created_at datetime NOT NULL,
            experience_level varchar(16) NULL,
            profile_image varchar(100) NULL
        );
        CREATE TABLE courses_course (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title varchar(255) NOT NULL,
            level varchar(16) NOT NULL,
            status varchar(16) NOT NULL,
            created_at datetime NOT NULL,
            created_by_id bigint NOT NULL
        );
        CREATE TABLE courses_lesson (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title varchar(255) NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            "order" integer unsigned NOT NULL DEFAULT 0,
            topic_tag varchar(100) NOT NULL DEFAULT '',
            is_auto_generated bool NOT NULL DEFAULT 1,
            created_at datetime NOT NULL,
            course_id bigint NOT NULL,
            source_type varchar(32) NOT NULL DEFAULT 'youtube',
            resource_url varchar(500) NOT NULL DEFAULT '',
            difficulty varchar(16) NOT NULL DEFAULT 'beginner',
            estimated_minutes smallint unsigned NOT NULL DEFAULT 15,
            tags TEXT NOT NULL DEFAULT '[]',
            learning_objective TEXT NOT NULL DEFAULT '',
            ai_summary TEXT NULL,
            embedded_url varchar(500) NOT NULL DEFAULT '',
            notes_generated_at datetime NULL,
            pdf_notes varchar(100) NOT NULL DEFAULT '',
            transcript_text TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE progress_enrollment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrolled_at datetime NOT NULL,
            course_id bigint NOT NULL,
            user_id bigint NOT NULL,
            completed_at datetime NULL,
            status varchar(16) NOT NULL DEFAULT 'ACTIVE',
            UNIQUE(user_id, course_id)
        );
        CREATE TABLE progress_lessonprogress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_opened_at datetime NOT NULL,
            last_opened_at datetime NOT NULL,
            completed_at datetime NULL,
            seconds_engaged integer unsigned NOT NULL DEFAULT 0,
            max_scroll_depth_pct integer unsigned NOT NULL DEFAULT 0,
            video_watch_pct integer unsigned NULL,
            notes_viewed_at datetime NULL,
            notes_downloaded_at datetime NULL,
            lesson_id bigint NOT NULL,
            user_id bigint NOT NULL,
            UNIQUE(user_id, lesson_id)
        );
        CREATE TABLE quizzes_quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passing_score integer unsigned NOT NULL DEFAULT 60,
            generation_status varchar(16) NOT NULL DEFAULT 'pending',
            generation_error TEXT NOT NULL DEFAULT '',
            created_at datetime NOT NULL,
            lesson_id bigint NOT NULL UNIQUE
        );
        CREATE TABLE quizzes_question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "order" integer unsigned NOT NULL DEFAULT 0,
            stem TEXT NOT NULL,
            choices TEXT NOT NULL,
            correct_index integer unsigned NOT NULL,
            topic_tag varchar(100) NOT NULL,
            question_type varchar(16) NOT NULL DEFAULT 'mcq',
            difficulty varchar(16) NULL,
            bloom_level varchar(16) NULL,
            explanation TEXT NOT NULL DEFAULT '',
            is_published bool NOT NULL DEFAULT 1,
            quiz_id bigint NOT NULL
        );
        CREATE TABLE quizzes_quizresult (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score integer unsigned NOT NULL,
            answers TEXT NOT NULL,
            taken_at datetime NOT NULL,
            quiz_id bigint NOT NULL,
            user_id bigint NOT NULL
        );
        CREATE TABLE ai_engine_lessonaiprocessing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status varchar(16) NOT NULL DEFAULT 'pending',
            transcript_text TEXT NOT NULL DEFAULT '',
            analysis_json TEXT NULL,
            last_error TEXT NOT NULL DEFAULT '',
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            lesson_id bigint NOT NULL UNIQUE
        );
        CREATE TABLE progress_certificate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_number varchar(40) NOT NULL UNIQUE,
            verification_code varchar(80) NOT NULL UNIQUE,
            student_id bigint NOT NULL,
            course_id bigint NOT NULL,
            enrollment_id bigint NOT NULL UNIQUE,
            student_name varchar(255) NOT NULL,
            course_title varchar(255) NOT NULL,
            issue_date datetime NOT NULL,
            completion_date datetime NULL,
            platform_name varchar(120) NOT NULL DEFAULT 'LearnCode',
            platform_website varchar(500) NOT NULL DEFAULT '',
            instructor_name varchar(255) NOT NULL DEFAULT '',
            course_duration varchar(80) NOT NULL DEFAULT '',
            verification_url varchar(500) NOT NULL DEFAULT '',
            ceo_name varchar(120) NOT NULL DEFAULT 'Shemsa Amin',
            ceo_title varchar(120) NOT NULL DEFAULT 'Chief Executive Officer',
            file varchar(100) NOT NULL DEFAULT '',
            status varchar(16) NOT NULL DEFAULT 'ACTIVE',
            revoked_at datetime NULL,
            created_at datetime NOT NULL
        );
        CREATE TABLE playground_playgroundchallenge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title varchar(200) NOT NULL,
            description TEXT NOT NULL,
            difficulty varchar(16) NOT NULL,
            starter_code TEXT NOT NULL,
            test_cases TEXT NOT NULL,
            xp_reward integer unsigned NOT NULL DEFAULT 50,
            status varchar(16) NOT NULL DEFAULT 'active',
            created_at datetime NOT NULL,
            solved_at datetime NULL,
            user_id bigint NOT NULL
        );
        CREATE TABLE playground_playgroundsubmission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            passed bool NOT NULL DEFAULT 0,
            test_results TEXT NOT NULL,
            xp_earned integer unsigned NOT NULL DEFAULT 0,
            submitted_at datetime NOT NULL,
            challenge_id bigint NOT NULL,
            user_id bigint NOT NULL
        );
        """)
    con.commit()
    con.close()


class FlaskRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.sqlite3")
        init_db(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def app(self):
        from flask_app import create_app

        return create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": self.db_path,
                "SECRET_KEY": "test-secret",
            }
        )

    def insert_user(self, email, password, role="student", level="beginner", **fields):
        now = "2026-08-24T00:00:00Z"
        con = sqlite3.connect(self.db_path)
        cur = con.execute(
            """
            INSERT INTO accounts_user
                (password, last_login, is_superuser, first_name, last_name, is_staff,
                 is_active, date_joined, email, role, created_at, experience_level, profile_image)
            VALUES (?, NULL, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, '')
            """,
            (
                legacy_pbkdf2_sha256(password),
                int(role == "admin"),
                fields.get("first_name", ""),
                fields.get("last_name", ""),
                int(role == "admin"),
                now,
                email,
                role,
                now,
                level,
            ),
        )
        con.commit()
        user_id = cur.lastrowid
        con.close()
        return user_id

    def login_headers(self, email, password):
        response = (
            self.app()
            .test_client()
            .post(
                "/auth/login/",
                json={"email": email, "password": password},
            )
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.get_json()['access']}"}

    def seed_course_lesson(self, admin_id, student_id=None, *, status="published"):
        now = "2026-08-24T00:00:00Z"
        con = sqlite3.connect(self.db_path)
        course_id = con.execute(
            """
            INSERT INTO courses_course (title, level, status, created_at, created_by_id)
            VALUES ('Python Fundamentals', 'beginner', ?, ?, ?)
            """,
            (status, now, admin_id),
        ).lastrowid
        lesson_id = con.execute(
            """
            INSERT INTO courses_lesson
                (title, content, "order", topic_tag, is_auto_generated, created_at, course_id,
                 source_type, resource_url, difficulty, estimated_minutes, tags, learning_objective,
                 ai_summary, embedded_url, notes_generated_at, pdf_notes, transcript_text)
            VALUES (
                'Variables', 'Variables store values in Python.', 0, 'python-basics', 0, ?, ?,
                'youtube', 'https://youtu.be/dQw4w9WgXcQ', 'beginner', 1, '["python"]',
                'Understand variables', NULL, '', NULL, '', 'Variables store reusable values.'
            )
            """,
            (now, course_id),
        ).lastrowid
        enrollment_id = None
        if student_id is not None:
            enrollment_id = con.execute(
                """
                INSERT INTO progress_enrollment
                    (enrolled_at, course_id, user_id, completed_at, status)
                VALUES (?, ?, ?, NULL, 'ACTIVE')
                """,
                (now, course_id, student_id),
            ).lastrowid
            con.execute(
                """
                INSERT INTO progress_lessonprogress
                    (first_opened_at, last_opened_at, completed_at, seconds_engaged,
                     max_scroll_depth_pct, video_watch_pct, lesson_id, user_id)
                VALUES (?, ?, ?, 60, 100, 100, ?, ?)
                """,
                (now, now, now, lesson_id, student_id),
            )
        con.commit()
        con.close()
        return course_id, lesson_id, enrollment_id

    def test_database_runtime_defaults_to_sqlite_when_database_url_is_empty(self):
        from flask_app import create_app

        app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": self.db_path,
                "SECRET_KEY": "test-secret",
            }
        )

        self.assertEqual(app.config["DATABASE_ENGINE"], "sqlite")
        self.assertEqual(app.config["DATABASE_PATH"], self.db_path)

    def test_database_runtime_uses_postgres_when_database_url_is_postgres(self):
        from flask_app import create_app

        database_url = "postgresql://learncode:secret@db.example.com:5432/learncode"
        app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": database_url,
                "SECRET_KEY": "test-secret",
            }
        )

        self.assertEqual(app.config["DATABASE_ENGINE"], "postgres")
        self.assertEqual(app.config["DATABASE_URL"], database_url)

    def test_postgres_queries_use_psycopg_placeholders(self):
        from flask_app import prepare_sql

        sql, params = prepare_sql(
            "SELECT * FROM accounts_user WHERE id=? AND lower(email)=lower(?)",
            (7, "student@example.com"),
            "postgres",
        )

        self.assertEqual(sql, "SELECT * FROM accounts_user WHERE id=%s AND lower(email)=lower(%s)")
        self.assertEqual(params, (7, "student@example.com"))

    def test_postgres_translates_sqlite_insert_or_ignore(self):
        from flask_app import prepare_sql

        sql, params = prepare_sql(
            """
            INSERT OR IGNORE INTO progress_enrollment (enrolled_at, course_id, user_id, completed_at, status)
            VALUES (?, ?, ?, NULL, 'ACTIVE')
            """,
            ("2026-09-13T00:00:00Z", 3, 5),
            "postgres",
        )

        self.assertIn("INSERT INTO progress_enrollment", sql)
        self.assertIn("VALUES (%s, %s, %s, NULL, 'ACTIVE')", sql)
        self.assertTrue(sql.strip().endswith("ON CONFLICT DO NOTHING"))
        self.assertEqual(params, ("2026-09-13T00:00:00Z", 3, 5))

    def test_postgres_queries_use_boolean_literals(self):
        from flask_app import prepare_sql

        sql, params = prepare_sql(
            "SELECT * FROM accounts_user WHERE is_active=1 AND is_staff=0 AND is_published=1",
            (),
            "postgres",
        )

        self.assertEqual(
            sql,
            "SELECT * FROM accounts_user WHERE is_active=TRUE AND is_staff=FALSE AND is_published=TRUE",
        )
        self.assertEqual(params, ())

    def test_flask_app_serves_health_check_from_flask_runtime(self):
        app = self.app()
        client = app.test_client()

        response = client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"backend": "flask", "status": "ok"})
        self.assertEqual(app.name, "flask_app")

    def test_register_login_me_and_refresh_are_flask_owned(self):
        client = self.app().test_client()

        created = client.post(
            "/auth/register/",
            json={
                "email": "student@example.com",
                "password": "Student2026!",
                "confirm_password": "Student2026!",
                "role": "student",
                "experience_level": "beginner",
            },
        )
        self.assertEqual(created.status_code, 201)

        login = client.post(
            "/auth/login/",
            json={"email": "student@example.com", "password": "Student2026!"},
        )
        self.assertEqual(login.status_code, 200)
        access = login.get_json()["access"]
        self.assertIn("ai_elearn_refresh", login.headers.get("Set-Cookie", ""))

        me = client.get("/auth/me/", headers={"Authorization": f"Bearer {access}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["email"], "student@example.com")
        self.assertEqual(me.get_json()["role"], "student")

        refreshed = client.post("/auth/refresh/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("access", refreshed.get_json())

    def test_existing_pbkdf2_sha256_passwords_can_login(self):
        con = sqlite3.connect(self.db_path)
        now = "2026-08-24T00:00:00Z"
        con.execute(
            """
            INSERT INTO accounts_user
                (password, last_login, is_superuser, first_name, last_name, is_staff,
                 is_active, date_joined, email, role, created_at, experience_level, profile_image)
            VALUES (?, NULL, 0, '', '', 0, 1, ?, 'admin@example.com', 'admin', ?, NULL, '')
            """,
            (legacy_pbkdf2_sha256("Admin2026!"), now, now),
        )
        con.commit()
        con.close()

        response = (
            self.app()
            .test_client()
            .post(
                "/auth/login/",
                json={"email": "admin@example.com", "password": "Admin2026!"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.get_json())

    def test_api_and_versioned_api_alias_require_flask_auth(self):
        client = self.app().test_client()

        legacy = client.get("/api/catalog/courses/")
        versioned = client.get("/api/v1/catalog/courses/")

        self.assertEqual(legacy.status_code, 401)
        self.assertEqual(versioned.status_code, 401)
        self.assertEqual(
            legacy.get_json()["detail"], "Authentication credentials were not provided."
        )
        self.assertEqual(
            versioned.get_json()["detail"], "Authentication credentials were not provided."
        )

    def test_admin_can_generate_lesson_notes_pdf_in_flask(self):
        admin_id = self.insert_user("admin@example.com", "Admin2026!", role="admin")
        _course_id, lesson_id, _enrollment_id = self.seed_course_lesson(admin_id)
        headers = self.login_headers("admin@example.com", "Admin2026!")
        client = self.app().test_client()

        response = client.post(f"/api/lessons/{lesson_id}/generate-notes/", headers=headers)

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["lesson_id"], lesson_id)
        self.assertTrue(payload["has_pdf_notes"])
        self.assertNotIn("not ported", payload.get("detail", "").lower())
        con = sqlite3.connect(self.db_path)
        pdf_notes = con.execute(
            "SELECT pdf_notes FROM courses_lesson WHERE id=?", (lesson_id,)
        ).fetchone()[0]
        con.close()
        self.assertTrue(pdf_notes.endswith(".pdf"))
        with open(os.path.join(os.path.dirname(self.db_path), "media", pdf_notes), "rb") as fh:
            self.assertEqual(fh.read(5), b"%PDF-")

    def test_admin_can_generate_and_approve_quiz_in_flask(self):
        admin_id = self.insert_user("admin@example.com", "Admin2026!", role="admin")
        course_id, lesson_id, _enrollment_id = self.seed_course_lesson(admin_id)
        headers = self.login_headers("admin@example.com", "Admin2026!")
        client = self.app().test_client()

        generated = client.post(
            f"/api/admin/courses/{course_id}/lessons/{lesson_id}/generate-quiz/",
            headers=headers,
        )
        self.assertEqual(generated.status_code, 200)
        payload = generated.get_json()
        self.assertEqual(payload["quiz_generation_status"], "done")
        self.assertGreaterEqual(payload["question_count"], 3)
        self.assertNotIn("not ported", payload.get("detail", "").lower())

        approved = client.post(
            f"/api/admin/courses/{course_id}/lessons/{lesson_id}/approve-quiz/",
            headers=headers,
        )
        self.assertEqual(approved.status_code, 200)
        self.assertGreaterEqual(approved.get_json()["published_question_count"], 3)

    def test_student_can_generate_certificate_after_completion(self):
        admin_id = self.insert_user("admin@example.com", "Admin2026!", role="admin")
        student_id = self.insert_user(
            "student@example.com",
            "Student2026!",
            first_name="Ada",
            last_name="Lovelace",
        )
        course_id, lesson_id, enrollment_id = self.seed_course_lesson(admin_id, student_id)
        con = sqlite3.connect(self.db_path)
        quiz_id = con.execute(
            """
            INSERT INTO quizzes_quiz
                (passing_score, generation_status, generation_error, created_at, lesson_id)
            VALUES (60, 'done', '', '2026-08-24T00:00:00Z', ?)
            """,
            (lesson_id,),
        ).lastrowid
        con.execute(
            """
            INSERT INTO quizzes_quizresult (score, answers, taken_at, quiz_id, user_id)
            VALUES (100, '{}', '2026-08-24T00:00:00Z', ?, ?)
            """,
            (quiz_id, student_id),
        )
        con.execute(
            "UPDATE progress_enrollment SET completed_at=?, status='COMPLETED' WHERE id=?",
            ("2026-08-24T00:00:00Z", enrollment_id),
        )
        con.commit()
        con.close()
        headers = self.login_headers("student@example.com", "Student2026!")

        response = (
            self.app()
            .test_client()
            .post(
                f"/api/student/courses/{course_id}/certificate/",
                headers=headers,
            )
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["student_name"], "Ada Lovelace")
        self.assertEqual(payload["course_title"], "Python Fundamentals")
        self.assertTrue(payload["verification_code"])
        self.assertNotIn("not ported", payload.get("detail", "").lower())

    def test_playground_generates_stores_submits_and_reports_leaderboard(self):
        self.insert_user("student@example.com", "Student2026!")
        headers = self.login_headers("student@example.com", "Student2026!")
        client = self.app().test_client()

        generated = client.post("/api/playground/challenge/generate/", headers=headers)
        self.assertEqual(generated.status_code, 201)
        challenge = generated.get_json()["challenge"]
        self.assertIsInstance(challenge["id"], int)

        solved = client.post(
            f"/api/playground/challenge/{challenge['id']}/submit/",
            headers=headers,
            json={"code": "def solution(a, b):\n    return a + b\n"},
        )
        self.assertEqual(solved.status_code, 200)
        self.assertTrue(solved.get_json()["passed"])

        leaderboard = client.get("/api/playground/leaderboard/", headers=headers)
        self.assertEqual(leaderboard.status_code, 200)
        self.assertEqual(leaderboard.get_json()["me"]["xp_earned"], challenge["xp_reward"])

    def test_reports_are_generated_as_pdf_by_flask(self):
        admin_id = self.insert_user("admin@example.com", "Admin2026!", role="admin")
        self.seed_course_lesson(admin_id)
        headers = self.login_headers("admin@example.com", "Admin2026!")

        response = self.app().test_client().get("/api/admin/reports/summary/", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.data[:5], b"%PDF-")


if __name__ == "__main__":
    unittest.main()
