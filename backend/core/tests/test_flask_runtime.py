import base64
import hashlib
import os
import sqlite3
import tempfile
import unittest


def django_pbkdf2(password, salt="testsalt", iterations=1000000):
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
            {"TESTING": True, "DATABASE_PATH": self.db_path, "SECRET_KEY": "test-secret"}
        )

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

    def test_flask_app_serves_health_check_without_django_fallback(self):
        app = self.app()
        client = app.test_client()

        response = client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"backend": "flask", "status": "ok"})
        self.assertNotIn("django", type(app.wsgi_app).__name__.lower())

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

    def test_existing_django_pbkdf2_passwords_can_login(self):
        con = sqlite3.connect(self.db_path)
        now = "2026-08-24T00:00:00Z"
        con.execute(
            """
            INSERT INTO accounts_user
                (password, last_login, is_superuser, first_name, last_name, is_staff,
                 is_active, date_joined, email, role, created_at, experience_level, profile_image)
            VALUES (?, NULL, 0, '', '', 0, 1, ?, 'admin@example.com', 'admin', ?, NULL, '')
            """,
            (django_pbkdf2("Admin2026!"), now, now),
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


if __name__ == "__main__":
    unittest.main()
