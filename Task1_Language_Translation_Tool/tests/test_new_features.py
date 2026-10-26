"""
Test Suite for Extended Standout Features:
- Phonetic Transliteration (Devanagari, Cyrillic, Greek, Arabic)
- Round-Trip Verification & Semantic Integrity Scoring
- Code & Markdown Preservation
- Subtitle (.SRT/.VTT) Translation
- New Flask API Endpoints (/api/verify, /api/transliterate, /api/translate_subtitles)
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from app import app
from src.transliteration import get_transliteration, transliterate_devanagari, transliterate_cyrillic
from src.verifier import verify_translation_quality
from src.text_processor import (
    protect_code_and_markdown,
    restore_code_and_markdown,
    translate_subtitles,
    is_subtitle_content
)
from src.translator import TranslationService


@pytest.fixture(scope="module")
def translator():
    return TranslationService()


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestStandoutFeatures:
    def test_transliteration_devanagari(self):
        """Verifies Hindi/Devanagari phonetic transliteration."""
        hindi_phrase = "नमस्ते"
        res = transliterate_devanagari(hindi_phrase)
        assert res is not None
        assert "namaste" in res.lower()

    def test_transliteration_cyrillic(self):
        """Verifies Russian/Cyrillic phonetic transliteration."""
        cyrillic_phrase = "Привет мир"
        res = transliterate_cyrillic(cyrillic_phrase)
        assert "privet" in res.lower()
        assert "mir" in res.lower()

    def test_transliteration_wrapper(self):
        """Tests general get_transliteration for various languages."""
        assert get_transliteration("नमस्ते", "hi") is not None
        assert get_transliteration("Привет", "ru") is not None
        assert get_transliteration("Hello", "en") is None  # English doesn't need transliteration

    def test_code_markdown_protection(self):
        """Ensures fenced and inline code blocks are preserved intact."""
        raw_text = "Here is the code: ```python\nx = 42\nprint(x)\n``` and variable `user_id`."
        masked, placeholders = protect_code_and_markdown(raw_text)
        assert len(placeholders) == 2
        assert "[[_CODE_0_]]" in masked
        assert "[[_CODE_1_]]" in masked

        # Simulate translation where surrounding words change
        simulated_translation = "Aquí está el código: [[_CODE_0_]] y la variable [[_CODE_1_]]."
        restored = restore_code_and_markdown(simulated_translation, placeholders)
        assert "```python\nx = 42\nprint(x)\n```" in restored
        assert "`user_id`" in restored

    def test_subtitle_parsing_and_translation(self):
        """Tests .SRT subtitle block detection and timing preservation."""
        sample_srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello world\n\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "Good morning\n"
        )
        assert is_subtitle_content(sample_srt) is True

        def dummy_tr(text):
            if "Hello" in text:
                return "Hola mundo"
            return "Buenos días"

        translated_srt = translate_subtitles(sample_srt, dummy_tr)
        assert "00:00:01,000 --> 00:00:04,000" in translated_srt
        assert "Hola mundo" in translated_srt
        assert "00:00:05,000 --> 00:00:08,000" in translated_srt
        assert "Buenos días" in translated_srt

    def test_quality_verifier(self, translator):
        """Verifies round-trip verification returns integrity score and back-translation."""
        res = verify_translation_quality(
            translation_service=translator,
            source_text="Hello world",
            target_text="Hola mundo",
            source_lang="en",
            target_lang="es"
        )
        assert res["success"] is True
        assert "back_translation" in res
        assert res["integrity_score"] >= 50
        assert "rating" in res

    def test_api_verify_endpoint(self, client):
        """Validates /api/verify endpoint."""
        res = client.post("/api/verify", json={
            "source_text": "Good morning my friend",
            "target_text": "Buenos días mi amigo",
            "source_lang": "en",
            "target_lang": "es"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["integrity_score"] > 0
        assert len(data["back_translation"]) > 0

    def test_api_transliterate_endpoint(self, client):
        """Validates /api/transliterate endpoint."""
        res = client.post("/api/transliterate", json={
            "text": "नमस्ते",
            "lang": "hi"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "namaste" in data["transliteration"].lower()

    def test_api_translate_subtitles_endpoint(self, client):
        """Validates /api/translate_subtitles endpoint."""
        sample_srt = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Hello\n"
        )
        res = client.post("/api/translate_subtitles", json={
            "content": sample_srt,
            "source_lang": "en",
            "target_lang": "es"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "00:00:01,000 --> 00:00:03,000" in data["translated_content"]
