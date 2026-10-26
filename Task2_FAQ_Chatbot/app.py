"""
Flask Web Application for Task 2: FAQ Chatbot
Provides REST API endpoints and an interactive web chat UI.
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, render_template, request
from src.bot_engine import FAQBotEngine

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Initialize Bot Engine
bot_engine = FAQBotEngine()


@app.route("/")
def index():
    categories = bot_engine.get_categories()
    faqs = bot_engine.get_all_faqs()
    return render_template("index.html", categories=categories, faqs=faqs)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "success": False,
            "error": "Message cannot be empty."
        }), 400

    response = bot_engine.process_message(message)
    return jsonify({
        "success": True,
        "query": message,
        "response": response
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
