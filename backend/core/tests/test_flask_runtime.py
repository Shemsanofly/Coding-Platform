from django.test import TestCase


class FlaskRuntimeTests(TestCase):
    def test_flask_app_reexecs_from_local_venv_when_launched_with_global_python(self):
        from pathlib import Path
        from unittest.mock import patch

        import flask_app

        project_python = Path(flask_app.__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"

        with (
            patch("sys.executable", "C:\\Python313\\python.exe"),
            patch("os.execv") as execv,
        ):
            flask_app._reexec_from_local_venv()

        execv.assert_called_once_with(str(project_python), [str(project_python), *flask_app.sys.argv])

    def test_flask_app_serves_health_check(self):
        from flask_app import create_app

        app = create_app()
        client = app.test_client()

        response = client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"backend": "flask", "status": "ok"})

    def test_flask_app_preserves_existing_auth_route(self):
        from flask_app import create_app

        app = create_app()
        client = app.test_client()

        response = client.post(
            "/auth/register/",
            json={"email": "not-an-email", "password": "short", "role": "student"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["detail"], "Validation failed.")

    def test_flask_app_preserves_versioned_api_alias(self):
        from flask_app import create_app

        app = create_app()
        client = app.test_client()

        legacy = client.get("/api/catalog/courses/")
        versioned = client.get("/api/v1/catalog/courses/")

        self.assertEqual(legacy.status_code, 401)
        self.assertEqual(versioned.status_code, 401)
