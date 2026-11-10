"""
Flask Web Application for Task 2: FAQ Chatbot
Provides REST API endpoints and an interactive web chat UI.
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import io
import os
import re
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_file, session
from src.bot_engine import FAQBotEngine
from src.auth import AuthManager
from src.creator_engine import get_generated_file, get_image_render, get_image_meta

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY", "faq-chatbot-universal-secret-key-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Initialize Bot Engine & Auth Manager
bot_engine = FAQBotEngine()
auth_manager = AuthManager()


def get_current_user():
    """Retrieves current user from session cookie or token header."""
    user_id = session.get("user_id")
    if user_id:
        u = auth_manager.get_user_by_id(user_id)
        if u:
            return u

    token = request.cookies.get("session_token")
    if token:
        u = auth_manager.get_user_by_session_token(token)
        if u:
            session["user_id"] = u["id"]
            return u

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        u = auth_manager.get_user_by_session_token(token)
        if u:
            return u

    return None


# -----------------------------------------------------------------------------
# AUTHENTICATION ROUTES (Register, Login, Logout, Profile)
# -----------------------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    full_name = data.get("full_name", "")

    ok, msg, user = auth_manager.register(username, email, password, full_name)
    if not ok:
        return jsonify({"success": False, "error": msg}), 400

    token = auth_manager.create_session(user["id"])
    session["user_id"] = user["id"]

    resp = make_response(jsonify({
        "success": True,
        "message": msg,
        "user": user,
        "token": token
    }))
    resp.set_cookie("session_token", token, max_age=30*24*3600, httponly=True, samesite="Lax")
    return resp


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username_or_email = data.get("username_or_email") or data.get("username") or data.get("email") or ""
    password = data.get("password", "")

    ok, msg, user = auth_manager.authenticate(username_or_email, password)
    if not ok:
        return jsonify({"success": False, "error": msg}), 401

    token = auth_manager.create_session(user["id"])
    session["user_id"] = user["id"]

    resp = make_response(jsonify({
        "success": True,
        "message": msg,
        "user": user,
        "token": token
    }))
    resp.set_cookie("session_token", token, max_age=30*24*3600, httponly=True, samesite="Lax")
    return resp


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    token = request.cookies.get("session_token")
    if token:
        auth_manager.delete_session(token)
    session.clear()
    resp = make_response(jsonify({
        "success": True,
        "message": "Signed out successfully."
    }))
    resp.delete_cookie("session_token")
    return resp


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if user:
        return jsonify({
            "success": True,
            "authenticated": True,
            "user": user
        })
    return jsonify({
        "success": True,
        "authenticated": False,
        "user": None
    })


@app.route("/login")
@app.route("/signup")
def auth_page():
    user = get_current_user()
    next_url = request.args.get("next") or "/"
    if user:
        return redirect(next_url)

    initial_mode = "register" if request.path == "/signup" or request.args.get("mode") == "register" else "login"
    return render_template("login.html", initial_mode=initial_mode, next_url=next_url)


@app.route("/api/image/render/<img_id>", methods=["GET"])
def render_image(img_id):
    img_bytes = get_image_render(img_id)
    if not img_bytes:
        return jsonify({"success": False, "error": "Image not found or generation failed."}), 404
    resp = send_file(
        io.BytesIO(img_bytes),
        mimetype="image/jpeg",
        as_attachment=False
    )
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/api/image/download/<img_id>", methods=["GET"])
def download_image(img_id):
    meta = get_image_meta(img_id) or {}
    img_bytes = get_image_render(img_id)
    if not img_bytes:
        return jsonify({"success": False, "error": "Image not found."}), 404
    raw_title = meta.get("prompt") or "artwork"
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_title[:30].strip())
    return send_file(
        io.BytesIO(img_bytes),
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=f"{slug}.jpg"
    )


@app.route("/api/download/pptx/<gen_id>", methods=["GET"])
def download_pptx(gen_id):
    file_info = get_generated_file(gen_id)
    if not file_info:
        return jsonify({"success": False, "error": "Presentation not found or expired."}), 404
    return send_file(
        io.BytesIO(file_info["bytes"]),
        mimetype=file_info["mime"],
        as_attachment=True,
        download_name=file_info["filename"]
    )


@app.route("/api/download/pdf/<gen_id>", methods=["GET"])
def download_pdf(gen_id):
    file_info = get_generated_file(gen_id)
    if not file_info:
        return jsonify({"success": False, "error": "PDF document not found or expired."}), 404
    return send_file(
        io.BytesIO(file_info["bytes"]),
        mimetype=file_info["mime"],
        as_attachment=True,
        download_name=file_info["filename"]
    )


@app.route("/")
def index():
    categories = bot_engine.get_categories()
    faqs = bot_engine.get_all_faqs()
    user = get_current_user()
    return render_template("index.html", categories=categories, faqs=faqs, current_user=user)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()
    api_key = data.get("api_key", "").strip() or None

    if not message:
        return jsonify({
            "success": False,
            "error": "Message cannot be empty."
        }), 400

    response = bot_engine.process_message(message, api_key=api_key)
    return jsonify({
        "success": True,
        "query": message,
        "response": response
    })


@app.route("/api/gemini/status", methods=["GET"])
def gemini_status():
    env_configured = bool(bot_engine.knowledge_engine.default_gemini_key)
    return jsonify({
        "success": True,
        "env_configured": env_configured,
        "models": ["gemini-1.5-flash", "gemini-2.0-flash", "Built-in High-IQ Engine"]
    })


@app.route("/api/faqs", methods=["GET"])
def get_faqs():
    category = request.args.get("category")
    faqs = bot_engine.get_all_faqs()
    if category:
        faqs = [f for f in faqs if f["category"].lower() == category.lower()]
    return jsonify({"success": True, "count": len(faqs), "faqs": faqs})


@app.route("/api/suggest", methods=["GET"])
def suggest():
    q = request.args.get("q", "").strip()
    suggestions = bot_engine.get_suggestions(q, limit=5)
    return jsonify({"success": True, "query": q, "suggestions": suggestions})


@app.route("/api/telemetry", methods=["GET"])
def telemetry():
    return jsonify({
        "success": True,
        "engine": "TF-IDF + Cosine Vector Space (NLTK Tokenized)",
        "total_faqs": len(bot_engine.get_all_faqs()),
        "categories": bot_engine.get_categories(),
        "vector_dimensions": bot_engine.matcher.tfidf_matrix.shape[1] if bot_engine.matcher.tfidf_matrix is not None else 0,
        "corpus_patterns_indexed": len(bot_engine.matcher.corpus_entries)
    })



if __name__ == "__main__":
    print("=" * 60)
    print("Starting Task 2 FAQ Chatbot Web Server on http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
