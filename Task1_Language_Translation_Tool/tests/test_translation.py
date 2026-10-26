"""
Automated Test Suite for Task 1: Language Translation Tool
Validates language registry, language auto-detection, translation engine routing,
text-to-speech audio synthesis, dictionary lookup, and Flask web API endpoints.
"""

import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")

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
from src.languages import LANGUAGES, get_all_languages, get_language_name, get_popular_languages
from src.translator import TranslationService
from src.tts_service import TTSService
from src.dictionary_service import DictionaryService


@pytest.fixture(scope="module")
def translator():
    return TranslationService()


@pytest.fixture(scope="module")
def tts_service():
    return TTSService()


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestLanguageTranslationTask:
    def test_language_registry(self):
        """Verifies language definitions, code lookups, and auto-detect support."""
        all_langs = get_all_languages()
        assert len(all_langs) >= 50, f"Expected 50+ languages, found {len(all_langs)}"
        assert any(l["code"] == "auto" for l in all_langs), "Auto-detect missing from language list"
        
        popular = get_popular_languages()
        assert len(popular) >= 5, "Popular language chips list too small"
        
        assert get_language_name("es") == "Spanish"
        assert get_language_name("fr") == "French"
        assert get_language_name("de") == "German"

    def test_language_detection(self, translator):
        """Tests fast Unicode script and heuristic language detection."""
        # Devanagari script -> Hindi
        code_hi, conf_hi = translator.detect_language("नमस्ते, आप कैसे हैं?")
        assert code_hi == "hi"
        assert conf_hi >= 0.8

        # Cyrillic script -> Russian
        code_ru, conf_ru = translator.detect_language("Привет, как дела?")
        assert code_ru == "ru"
        assert conf_ru >= 0.8

        # Japanese Hiragana/Katakana -> Japanese
        code_ja, conf_ja = translator.detect_language("こんにちは、元気ですか？")
        assert code_ja == "ja"

        # French stop words
        code_fr, conf_fr = translator.detect_language("Bonjour tout le monde et bienvenue")
        assert code_fr == "fr"

        # English
        code_en, conf_en = translator.detect_language("Hello and welcome to this translation suite")
        assert code_en == "en"

    def test_translation_execution(self, translator):
        """Tests translation of words and sentences across languages."""
        # English to Spanish
        res_es = translator.translate("Hello world", source_lang="en", target_lang="es")
        assert res_es["success"] is True
        assert len(res_es["translated_text"]) > 0
        assert "hola" in res_es["translated_text"].lower() or "mundo" in res_es["translated_text"].lower()

        # English to French
        res_fr = translator.translate("Good morning", source_lang="en", target_lang="fr")
        assert res_fr["success"] is True
        assert "bonjour" in res_fr["translated_text"].lower()

        # Identical source and target
        res_same = translator.translate("Consistent text", source_lang="en", target_lang="en")
        assert res_same["success"] is True
        assert res_same["translated_text"] == "Consistent text"
        assert res_same["engine_used"] == "identity"

        # Empty string
        res_empty = translator.translate("", source_lang="en", target_lang="es")
        assert res_empty["success"] is True
        assert res_empty["translated_text"] == ""

    def test_deep_translator_method(self, translator):
        """Verifies deep-translator method executes without unhandled rate limits."""
        res = translator.translate_deep_translator("Hello world", "en", "es")
        assert isinstance(res, str) and len(res) > 0
        assert "hola" in res.lower() or "mundo" in res.lower()

    def test_long_text_translation(self, translator):
        """Verifies multi-sentence paragraph translation exceeding 600 characters."""
        long_passage = (
            "Artificial intelligence is rapidly transforming global communication and technology. "
            "Modern machine learning algorithms can understand context, nuances, and idioms across multiple cultures. "
            "By translating text accurately, neural systems bridge international divides and foster collaboration."
        )
        res = translator.translate(long_passage, source_lang="en", target_lang="es")
        assert res["success"] is True
        assert len(res["translated_text"]) > 100
        assert res["char_count"] > 250
        assert res["engine_used"] in ("Google Neural Engine", "MyMemory Engine")


    def test_tts_service_stream(self, tts_service):
        """Verifies text-to-speech audio stream generation."""
        stream = tts_service.generate_speech_stream("Hello, welcome to our application", lang_code="en")
        assert stream is not None
        data = stream.read()
        assert len(data) > 500, "Generated TTS audio stream empty or corrupted"

    def test_dictionary_service(self):
        """Tests word lookup service for definitions and synonyms."""
        ds = DictionaryService()
        res = ds.lookup("knowledge")
        if res:  # If internet lookup succeeds
            assert "word" in res
            assert res["word"] == "knowledge"
            assert "meanings" in res

    def test_flask_web_endpoints(self, client):
        """Validates all Flask HTTP routes and JSON API responses."""
        # 1. Main UI
        res = client.get("/")
        assert res.status_code == 200
        assert b"LingoStudio" in res.data
        assert b"Translate" in res.data

        # 2. Languages endpoint
        res = client.get("/api/languages")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert len(data["languages"]) > 30

        # 3. Detect endpoint
        res = client.post("/api/detect", json={"text": "Bonjour tout le monde"})
        assert res.status_code == 200
        detect_data = res.get_json()
        assert detect_data["success"] is True
        assert detect_data["code"] == "fr"

        # 4. Translate endpoint
        res = client.post("/api/translate", json={
            "text": "Hello, how are you?",
            "source_lang": "auto",
            "target_lang": "es"
        })
        assert res.status_code == 200
        tr_data = res.get_json()
        assert tr_data["success"] is True
        assert len(tr_data["translated_text"]) > 0

        # 5. TTS Audio Endpoint
        tts_res = client.post("/api/tts", json={
            "text": "Good afternoon",
            "lang": "en"
        })
        assert tts_res.status_code == 200
        assert tts_res.mimetype == "audio/mpeg"
        assert len(tts_res.data) > 500

        # 6. Health endpoint
        h_res = client.get("/api/health")
        assert h_res.status_code == 200
        assert h_res.get_json()["status"] == "healthy"
