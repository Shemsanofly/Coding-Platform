import os

from flask_app import app


if __name__ == "__main__":
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "8000")))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
