"""
Test Suite for Tone and Formality Adaptation
Verifies tone adaptations for Spanish, French, German, English,
as well as the Flask API /api/translate tone parameter and analytics.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from app import app
from src.tone_adapter import adapt_tone


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestToneAdapter:
    def test_default_tone_unchanged(self):
        """Verifies default tone does not modify the text."""
        raw = "¿Cómo estás tú?"
        assert adapt_tone(raw, "es", "default") == raw
        assert adapt_tone(raw, "es", "") == raw

    def test_spanish_formal_adaptation(self):
        """Verifies Spanish formal adaptation converts tú to usted."""
        raw = "Hola, ¿cómo estás tú? ¿Puedes ayudarme con tu tarea?"
        formal = adapt_tone(raw, "es", "formal")
        assert "usted" in formal
        assert "su" in formal
        assert "tú" not in formal

    def test_spanish_casual_adaptation(self):
        """Verifies Spanish casual adaptation converts usted to tú."""
        raw = "Buenos días, ¿cómo está usted? ¿Puede decirme su nombre?"
        casual = adapt_tone(raw, "es", "casual")
        assert "tú" in casual
        assert "tu" in casual
        assert "usted" not in casual

    def test_french_formal_adaptation(self):
        """Verifies French formal adaptation converts tu to vous."""
        raw = "Salut, comment vas-tu? Tu peux venir."
        formal = adapt_tone(raw, "fr", "formal")
        assert "vous" in formal or "Vous" in formal
        assert "tu" not in formal.lower().split()

    def test_german_formal_adaptation(self):
        """Verifies German formal adaptation converts du to Sie."""
        raw = "Hallo, wie geht es dir? Hast du Zeit?"
        formal = adapt_tone(raw, "de", "formal")
        assert "Ihnen" in formal or "Sie" in formal

    def test_english_academic_adaptation(self):
        """Verifies English academic adaptation elevates vocabulary."""
        raw = "This study shows good results and examines big changes."
        academic = adapt_tone(raw, "en", "academic")
        assert "demonstrates" in academic
        assert "substantial" in academic

    def test_api_translate_with_tone_and_analytics(self, client):
        """Tests that /api/translate returns tone and text analytics."""
        res = client.post("/api/translate", json={
            "text": "Hello, how are you? I would like to buy a new laptop.",
            "source_lang": "en",
            "target_lang": "es",
            "tone": "formal"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data.get("tone") == "formal"
        assert "analytics" in data
        assert "reading_time_sec" in data["analytics"]
        assert "speaking_time_sec" in data["analytics"]
        assert "cefr_level" in data["analytics"]
