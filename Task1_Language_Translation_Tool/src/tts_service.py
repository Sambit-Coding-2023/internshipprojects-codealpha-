"""
Text-to-Speech (TTS) Service using gTTS
Synthesizes speech audio streams and MP3 downloads from translated text across languages.
"""

import io
from pathlib import Path
from typing import Optional
# pyrefly: ignore[missing-import]
from gtts import gTTS

# Mapping language codes to supported gTTS language tags
GTTS_SUPPORTED_LANGS = {
    "en": "en", "es": "es", "fr": "fr", "de": "de", "hi": "hi",
    "zh": "zh-CN", "ja": "ja", "ko": "ko", "ar": "ar", "ru": "ru",
    "pt": "pt", "it": "it", "nl": "nl", "tr": "tr", "pl": "pl",
    "sv": "sv", "id": "id", "vi": "vi", "th": "th", "el": "el",
    "cs": "cs", "da": "da", "fi": "fi", "no": "no", "hu": "hu",
    "ro": "ro", "uk": "uk", "he": "iw", "bn": "bn", "te": "te",
    "ta": "ta", "mr": "mr", "gu": "gu", "kn": "kn", "ml": "ml",
    "ur": "ur", "af": "af", "sq": "sq", "bg": "bg", "hr": "hr",
    "sk": "sk", "sl": "sl", "sw": "sw", "cy": "cy"
}


class TTSService:
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path(__file__).parent.parent / "outputs" / "audio"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_speech_stream(self, text: str, lang_code: str = "en", slow: bool = False) -> io.BytesIO:
        """
        Generates in-memory MP3 audio bytes using gTTS.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot synthesize empty text.")

        gtts_lang = GTTS_SUPPORTED_LANGS.get(lang_code.lower(), "en")

        tts = gTTS(text=clean_text, lang=gtts_lang, slow=slow)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp

    def save_speech_file(self, text: str, lang_code: str, filename: str) -> Path:
        """Saves generated speech to audio file on disk."""
        target_path = self.cache_dir / filename
        gtts_lang = GTTS_SUPPORTED_LANGS.get(lang_code.lower(), "en")
        tts = gTTS(text=text, lang=gtts_lang)
        tts.save(str(target_path))
        return target_path
