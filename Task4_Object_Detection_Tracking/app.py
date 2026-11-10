"""Flask application factory.

Run with:  python app.py     (or: flask --app app run)
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import config


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).parent / "frontend"),
        static_url_path="/static",
    )
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        JWT_SECRET_KEY=config.JWT_SECRET_KEY,
        JWT_ACCESS_TOKEN_EXPIRES=config.JWT_ACCESS_TOKEN_EXPIRES,
        MAX_CONTENT_LENGTH=config.MAX_VIDEO_BYTES,
    )

    CORS(app)
    JWTManager(app)

    # Import here to avoid circulars (ml loads torch/ultralytics lazily)
    from backend.api import api_bp
    from backend.db import init_db

    init_db()
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        # Serve the SPA shell; the frontend JS takes over routing afterwards.
        return app.send_static_file("index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "traffic-violation-detection"}

    @app.errorhandler(413)
    def too_large(_):
        return {"error": f"Video exceeds the {config.MAX_VIDEO_MB} MB limit."}, 413

    @app.errorhandler(404)
    def not_found(_):
        return {"error": "Not found."}, 404

    return app


if __name__ == "__main__":
    create_app().run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
