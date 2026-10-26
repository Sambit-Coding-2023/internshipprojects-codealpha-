"""
Comprehensive Unit & Integration Test Suite for Task 2: FAQ Chatbot
Validates text normalization, TF-IDF vector matching, confidence thresholds,
and Flask web API endpoints.
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src.") or mod == "app":
        del sys.modules[mod]
while str(project_root) in sys.path:
    sys.path.remove(str(project_root))
sys.path.insert(0, str(project_root))

import pytest
from app import app
from src.bot_engine import FAQBotEngine
from src.matcher import FAQMatcher
from src.nlp_preprocessor import TextPreprocessor


@pytest.fixture(scope="module")
def bot_engine():
    return FAQBotEngine()


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestFAQChatbotTask:
    def test_preprocessor(self):
        """Verifies text normalization, punctuation removal, and stop words."""
        tp = TextPreprocessor()
        clean = tp.clean_text("Where is MY Order #12345?!")
        assert "where" in clean
        assert "#" not in clean
        assert "!" not in clean

    def test_matcher_exact_and_fuzzy(self, bot_engine):
        """Verifies semantic similarity matching for customer queries."""
        # Tracking query
        res1 = bot_engine.process_message("Where is my package right now?")
        assert res1["status"] in ("high_confidence", "exact_match")
        assert "track" in res1["text"].lower() or "order" in res1["text"].lower()

        # Cancellation query
        res2 = bot_engine.process_message("Can I cancel my recent order?")
        assert res2["status"] in ("high_confidence", "exact_match")
        assert "cancel" in res2["text"].lower()

        # Refund query
        res3 = bot_engine.process_message("What is your refund policy?")
        assert res3["status"] in ("high_confidence", "exact_match")
        assert "return" in res3["text"].lower() or "refund" in res3["text"].lower()

    def test_unknown_query_fallback(self, bot_engine):
        """Verifies bot provides graceful fallback with suggestions for unknown queries."""
        res = bot_engine.process_message("Supercalifragilisticexpialidocious quantum physics gibberish")
        assert res["status"] in ("low_confidence", "unmatched")
        assert "alternatives" in res

    def test_flask_web_endpoints(self, client):
        """Validates all Task 2 Flask HTTP routes and JSON API responses."""
        # 1. Main UI
        res = client.get("/")
        assert res.status_code == 200
        assert b"FAQ" in res.data or b"Chatbot" in res.data or b"Support" in res.data

        # 2. FAQs list
        res_faqs = client.get("/api/faqs")
        assert res_faqs.status_code == 200
        data_faqs = res_faqs.get_json()
        assert data_faqs["success"] is True
        assert data_faqs["count"] >= 10

        # 3. Chat API
        chat_res = client.post("/api/chat", json={"message": "How do I track my order?"})
        assert chat_res.status_code == 200
        chat_data = chat_res.get_json()
        assert chat_data["success"] is True
        assert "response" in chat_data

        # 4. Suggest API
        sug_res = client.get("/api/suggest?q=refund")
        assert sug_res.status_code == 200
        sug_data = sug_res.get_json()
        assert sug_data["success"] is True
        assert len(sug_data["suggestions"]) > 0

        # 5. Telemetry API
        tel_res = client.get("/api/telemetry")
        assert tel_res.status_code == 200
        tel_data = tel_res.get_json()
        assert tel_data["success"] is True
        assert tel_data["total_faqs"] >= 10
