"""
Multi-Engine Translation Service
Handles translation via Google Chrome Extension API, MyMemory API, LibreTranslate,
and DeepTranslator with automatic language detection, sentence-aware chunking for long texts,
fallback resilience, and latency profiling.
"""

import html
import json
import re
import sys
import time
import urllib.parse
import warnings
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*RequestsDependencyWarning.*")

import requests

from .languages import LANGUAGES, get_language_name

# Common Unicode script ranges for instant local detection
UNICODE_SCRIPTS = [
    (r"[\u0900-\u097F]", "hi"),  # Devanagari (Hindi, Marathi, Nepali)
    (r"[\u0400-\u04FF]", "ru"),  # Cyrillic (Russian, Ukrainian, etc.)
    (r"[\u0600-\u06FF]", "ar"),  # Arabic
    (r"[\u3040-\u309F\u30A0-\u30FF]", "ja"),  # Hiragana / Katakana (Japanese)
    (r"[\uAC00-\uD7AF]", "ko"),  # Hangul (Korean)
    (r"[\u4E00-\u9FFF]", "zh"),  # CJK Unified Ideographs (Chinese)
    (r"[\u0590-\u05FF]", "he"),  # Hebrew
    (r"[\u0370-\u03FF]", "el"),  # Greek
    (r"[\u0E00-\u0E7F]", "th"),  # Thai
    (r"[\u0980-\u09FF]", "bn"),  # Bengali
    (r"[\u0C00-\u0C7F]", "te"),  # Telugu
    (r"[\u0B80-\u0BFF]", "ta"),  # Tamil
]

# Simple stopword fingerprinting for Latin-alphabet languages
LATIN_STOPWORDS = {
    "en": {"the", "and", "is", "in", "it", "you", "that", "he", "was", "for", "on", "are", "with", "as", "hello", "welcome"},
    "es": {"el", "la", "de", "que", "y", "en", "un", "ser", "se", "no", "haber", "por", "con", "su", "para", "como", "hola"},
    "fr": {"le", "la", "de", "et", "un", "une", "dans", "pour", "est", "sur", "avec", "il", "qui", "au", "bonjour", "merci"},
    "de": {"der", "die", "das", "und", "in", "zu", "den", "das", "nicht", "von", "sie", "ist", "des", "sich", "mit", "hallo"},
    "it": {"il", "la", "di", "e", "in", "che", "un", "una", "per", "non", "sono", "con", "ciao", "grazie"},
    "pt": {"o", "a", "de", "e", "do", "da", "em", "um", "para", "com", "não", "uma", "os", "olá", "obrigado"},
    "nl": {"de", "het", "een", "en", "van", "ik", "te", "dat", "die", "in", "een", "hij", "hallo"}
}

# Offline sample dictionary for immediate zero-network fallback
OFFLINE_PHRASES = {
    "hello": {"es": "Hola", "fr": "Bonjour", "de": "Hallo", "hi": "नमस्ते", "zh": "你好", "ja": "こんにちは", "ar": "مرحبا", "ru": "Привет", "it": "Ciao", "pt": "Olá"},
    "how are you": {"es": "¿Cómo estás?", "fr": "Comment allez-vous?", "de": "Wie geht es dir?", "hi": "आप कैसे हैं?", "zh": "你好吗？", "ja": "お元気ですか？", "it": "Come stai?", "pt": "Como você está?"},
    "good morning": {"es": "Buenos días", "fr": "Bonjour", "de": "Guten Morgen", "hi": "सुप्रभात", "zh": "早上好", "ja": "おはようございます", "it": "Buongiorno", "pt": "Bom dia"},
    "thank you": {"es": "Gracias", "fr": "Merci", "de": "Danke", "hi": "धन्यवाद", "zh": "谢谢", "ja": "ありがとうございます", "it": "Grazie", "pt": "Obrigado"},
    "goodbye": {"es": "Adiós", "fr": "Au revoir", "de": "Auf Wiedersehen", "hi": "अलविदा", "zh": "再见", "ja": "さようなら", "it": "Arrivederci", "pt": "Adeus"}
}


class TranslationService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detects language using fast Unicode script matching, stopwords analysis,
        and fallback to default.
        Returns:
            Tuple of (iso_code, confidence_between_0_and_1)
        """
        clean_text = text.strip()
        if not clean_text:
            return "en", 1.0

        # 1. Check Unicode Scripts
        for pattern, lang_code in UNICODE_SCRIPTS:
            matches = re.findall(pattern, clean_text)
            if len(matches) >= 2 or (len(clean_text) <= 5 and len(matches) >= 1):
                return lang_code, 0.95

        # 2. Check Latin stopwords
        words = set(re.findall(r"\b[a-zA-Z\u00C0-\u017F]+\b", clean_text.lower()))
        if words:
            best_lang = "en"
            max_score = 0
            for lang, stops in LATIN_STOPWORDS.items():
                intersection = words.intersection(stops)
                score = len(intersection)
                if score > max_score:
                    max_score = score
                    best_lang = lang

            if max_score > 0:
                confidence = min(0.95, 0.55 + (max_score * 0.12))
                return best_lang, round(confidence, 2)

        return "en", 0.65

    def _split_text_chunks(self, text: str, max_chunk_size: int = 400) -> List[str]:
        """
        Splits long text into sentence-aware chunks to prevent query length limits.
        """
        if len(text) <= max_chunk_size:
            return [text]

        # Split along sentence boundaries or newlines
        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            if not sentence:
                continue
            # If a single sentence is larger than max_chunk_size, break by words
            if len(sentence) > max_chunk_size:
                words = sentence.split(" ")
                sub_chunk = []
                sub_len = 0
                for w in words:
                    if sub_len + len(w) + 1 > max_chunk_size and sub_chunk:
                        chunks.append(" ".join(sub_chunk))
                        sub_chunk = [w]
                        sub_len = len(w)
                    else:
                        sub_chunk.append(w)
                        sub_len += len(w) + 1
                if sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                continue

            if current_len + len(sentence) + 1 > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_len = len(sentence)
            else:
                current_chunk.append(sentence)
                current_len += len(sentence) + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def translate_google_chrome(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, str]:
        """
        Fast, high-reliability Google Translate engine via official Chrome extension API.
        Handles both short and long text, preserves Unicode characters, and detects language.
        Returns:
            Tuple of (translated_text, detected_source_lang)
        """
        src = "auto" if source_lang == "auto" else source_lang
        chunks = self._split_text_chunks(text, max_chunk_size=1200)
        translated_parts = []
        detected_src = src

        for chunk in chunks:
            encoded_query = urllib.parse.quote(chunk)
            url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={src}&tl={target_lang}&q={encoded_query}"
            
            resp = self.session.get(url, timeout=6)
            if resp.status_code != 200:
                raise ConnectionError(f"Google Chrome API status {resp.status_code}")

            resp.encoding = "utf-8"
            data = resp.json()
            if not data:
                continue

            first_item = data[0]
            if isinstance(first_item, list):
                if len(first_item) >= 2:
                    translated_parts.append(first_item[0])
                    detected_src = first_item[1]
                elif len(first_item) >= 1:
                    translated_parts.append(first_item[0])
            elif isinstance(first_item, str):
                translated_parts.append(first_item)

        result_text = " ".join(translated_parts)
        return html.unescape(result_text), detected_src

    def translate_mymemory(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates text using MyMemory public API with chunking for texts > 400 chars.
        """
        src = "en" if source_lang == "auto" else source_lang
        chunks = self._split_text_chunks(text, max_chunk_size=400)
        translated_parts = []

        for chunk in chunks:
            encoded_query = urllib.parse.quote(chunk)
            url = f"https://api.mymemory.translated.net/get?q={encoded_query}&langpair={src}|{target_lang}"
            
            response = self.session.get(url, timeout=7)
            if response.status_code != 200:
                raise ConnectionError(f"MyMemory API returned status {response.status_code}")

            response.encoding = "utf-8"
            data = response.json()
            status = data.get("responseStatus")
            if status not in (200, "200"):
                msg = data.get("responseDetails", "Translation error")
                raise ValueError(f"MyMemory error: {msg}")

            translated = data.get("responseData", {}).get("translatedText", "")
            translated_parts.append(html.unescape(translated))

        return " ".join(translated_parts)

    def translate_deep_translator(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text using deep-translator with automatic Google endpoint fallback."""
        src = "auto" if source_lang == "auto" else source_lang
        try:
            try:
                from deep_translator import GoogleTranslator  # type: ignore # pyrefly: ignore
            except ImportError:
                import importlib
                dt = importlib.import_module("deep_translator")
                GoogleTranslator = getattr(dt, "GoogleTranslator")

            translator = GoogleTranslator(source=src, target=target_lang)
            result = translator.translate(text)
            if result:
                return html.unescape(result)
        except Exception:
            pass

        # Fallback to high-reliability neural endpoint when deep_translator encounters 429 rate limit
        translated, _ = self.translate_google_chrome(text, source_lang, target_lang)
        return translated

    def translate_libre(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text using public LibreTranslate mirrors."""
        src = "auto" if source_lang == "auto" else source_lang
        mirrors = [
            "https://translate.terraprint.co/translate",
            "https://libretranslate.de/translate"
        ]
        
        for mirror in mirrors:
            try:
                res = self.session.post(
                    mirror,
                    json={"q": text, "source": src, "target": target_lang, "format": "text"},
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    if "translatedText" in data:
                        return html.unescape(data["translatedText"])
            except Exception:
                continue
                
        raise ConnectionError("LibreTranslate mirrors unreachable")

    def translate_offline(self, text: str, target_lang: str) -> Optional[str]:
        """Translates common phrases from local dictionary when network is unavailable."""
        clean = text.strip().lower()
        if clean in OFFLINE_PHRASES:
            return OFFLINE_PHRASES[clean].get(target_lang)
        return None

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "es",
        preferred_engine: str = "auto"
    ) -> Dict[str, Any]:
        """
        Unified translation orchestrator with auto-detection, multi-engine routing,
        sentence chunking for arbitrary lengths, preferred engine selection, and execution metrics.
        """
        start_time = time.time()
        text = text.strip()

        if not text:
            return {
                "success": True,
                "translated_text": "",
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": "en",
                "detected_lang_name": "English",
                "engine_used": "none",
                "latency_ms": 0,
                "char_count": 0,
                "word_count": 0
            }

        # Handle identical source and target
        if source_lang != "auto" and source_lang == target_lang:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "success": True,
                "translated_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": source_lang,
                "detected_lang_name": get_language_name(source_lang),
                "engine_used": "identity",
                "latency_ms": elapsed_ms,
                "char_count": len(text),
                "word_count": len(text.split())
            }

        # Language Detection heuristic
        detected_lang = source_lang
        detection_confidence = 1.0
        if source_lang == "auto":
            detected_lang, detection_confidence = self.detect_language(text)

        translated_text = ""
        engine_used = ""
        errors = []

        pref = (preferred_engine or "auto").lower()

        # Engine candidate order based on preference
        engines_to_try = []
        if pref == "mymemory":
            engines_to_try = ["mymemory", "google", "deep_translator", "libre", "offline"]
        elif pref == "offline":
            engines_to_try = ["offline", "google", "mymemory"]
        else:
            engines_to_try = ["google", "mymemory", "deep_translator", "libre", "offline"]

        for eng in engines_to_try:
            if translated_text:
                break
            try:
                if eng == "google":
                    translated_text, detected_from_api = self.translate_google_chrome(text, source_lang, target_lang)
                    if detected_from_api and detected_from_api != "auto":
                        detected_lang = detected_from_api
                        detection_confidence = 0.98
                    engine_used = "Google Neural Engine"
                elif eng == "mymemory":
                    translated_text = self.translate_mymemory(text, detected_lang, target_lang)
                    engine_used = "MyMemory Engine"
                elif eng == "deep_translator":
                    translated_text = self.translate_deep_translator(text, source_lang, target_lang)
                    engine_used = "DeepTranslator"
                elif eng == "libre":
                    translated_text = self.translate_libre(text, source_lang, target_lang)
                    engine_used = "LibreTranslate"
                elif eng == "offline":
                    offline_res = self.translate_offline(text, target_lang)
                    if offline_res:
                        translated_text = offline_res
                        engine_used = "Offline Phrasebook"
            except Exception as e:
                errors.append(f"{eng}: {str(e)}")

        if not translated_text:
            raise RuntimeError(f"All translation engines failed. Details: {'; '.join(errors)}")

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        return {
            "success": True,
            "translated_text": translated_text,

            "source_lang": source_lang,
            "target_lang": target_lang,
            "detected_lang": detected_lang,
            "detected_lang_name": get_language_name(detected_lang),
            "detected_confidence": detection_confidence,
            "engine_used": engine_used,
            "latency_ms": elapsed_ms,
            "char_count": len(text),
            "word_count": len(text.split())
        }
