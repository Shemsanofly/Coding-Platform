import os
import sys
from pathlib import Path


def _reexec_from_local_venv():
    """Prefer the project virtualenv when launched with global Python."""
    project_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if not project_python.exists():
        return
    current_python = Path(sys.executable).resolve()
    if current_python == project_python.resolve():
        return
    os.execv(str(project_python), [str(project_python), *sys.argv])


_reexec_from_local_venv()

from flask import Flask, jsonify
from flask_cors import CORS


class CompatibilityFallbackMiddleware:
    """Route Flask-owned paths to Flask and preserve existing API paths."""

    def __init__(self, flask_wsgi_app, legacy_wsgi_app, flask_paths):
        self.flask_wsgi_app = flask_wsgi_app
        self.legacy_wsgi_app = legacy_wsgi_app
        self.flask_paths = tuple(flask_paths)

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path in self.flask_paths:
            return self.flask_wsgi_app(environ, start_response)
        return self.legacy_wsgi_app(environ, start_response)


def create_app():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    from django.core.wsgi import get_wsgi_application

    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    @app.get("/health/")
    def health():
        return jsonify({"backend": "flask", "status": "ok"})

    flask_wsgi_app = app.wsgi_app
    legacy_wsgi_app = get_wsgi_application()
    app.wsgi_app = CompatibilityFallbackMiddleware(
        flask_wsgi_app=flask_wsgi_app,
        legacy_wsgi_app=legacy_wsgi_app,
        flask_paths=("/health/",),
    )
    return app


app = create_app()


def run_dev_server():
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "8000")))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dev_server()
