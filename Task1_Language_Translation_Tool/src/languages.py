"""
Languages Registry & Metadata
Comprehensive catalog of languages with ISO 639-1 codes, English names, native autonyms,
flag emojis, and speech synthesis voice locales.
"""

from typing import Dict, List, Optional

LANGUAGES: Dict[str, Dict[str, str]] = {
    "auto": {"name": "Auto Detect", "native": "Detect Language", "flag": "🌐", "locale": "en-US"},
    "en": {"name": "English", "native": "English", "flag": "🇺🇸", "locale": "en-US"},
    "es": {"name": "Spanish", "native": "Español", "flag": "🇪🇸", "locale": "es-ES"},
    "fr": {"name": "French", "native": "Français", "flag": "🇫🇷", "locale": "fr-FR"},
    "de": {"name": "German", "native": "Deutsch", "flag": "🇩🇪", "locale": "de-DE"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "flag": "🇮🇳", "locale": "hi-IN"},
    "zh": {"name": "Chinese (Simplified)", "native": "简体中文", "flag": "🇨🇳", "locale": "zh-CN"},
    "ja": {"name": "Japanese", "native": "日本語", "flag": "🇯🇵", "locale": "ja-JP"},
    "ko": {"name": "Korean", "native": "한국어", "flag": "🇰🇷", "locale": "ko-KR"},
    "ar": {"name": "Arabic", "native": "العربية", "flag": "🇸🇦", "locale": "ar-SA"},
    "ru": {"name": "Russian", "native": "Русский", "flag": "🇷🇺", "locale": "ru-RU"},
    "pt": {"name": "Portuguese", "native": "Português", "flag": "🇵🇹", "locale": "pt-PT"},
    "it": {"name": "Italian", "native": "Italiano", "flag": "🇮🇹", "locale": "it-IT"},
    "nl": {"name": "Dutch", "native": "Nederlands", "flag": "🇳🇱", "locale": "nl-NL"},
    "tr": {"name": "Turkish", "native": "Türkçe", "flag": "🇹🇷", "locale": "tr-TR"},
    "pl": {"name": "Polish", "native": "Polski", "flag": "🇵🇱", "locale": "pl-PL"},
    "sv": {"name": "Swedish", "native": "Svenska", "flag": "🇸🇪", "locale": "sv-SE"},
    "id": {"name": "Indonesian", "native": "Bahasa Indonesia", "flag": "🇮🇩", "locale": "id-ID"},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "flag": "🇻🇳", "locale": "vi-VN"},
    "th": {"name": "Thai", "native": "ไทย", "flag": "🇹🇭", "locale": "th-TH"},
    "el": {"name": "Greek", "native": "Ελληνικά", "flag": "🇬🇷", "locale": "el-GR"},
    "cs": {"name": "Czech", "native": "Čeština", "flag": "🇨🇿", "locale": "cs-CZ"},
    "da": {"name": "Danish", "native": "Dansk", "flag": "🇩🇰", "locale": "da-DK"},
    "fi": {"name": "Finnish", "native": "Suomi", "flag": "🇫🇮", "locale": "fi-FI"},
    "no": {"name": "Norwegian", "native": "Norsk", "flag": "🇳🇴", "locale": "no-NO"},
    "hu": {"name": "Hungarian", "native": "Magyar", "flag": "🇭🇺", "locale": "hu-HU"},
    "ro": {"name": "Romanian", "native": "Română", "flag": "🇷🇴", "locale": "ro-RO"},
    "uk": {"name": "Ukrainian", "native": "Українська", "flag": "🇺🇦", "locale": "uk-UA"},
    "he": {"name": "Hebrew", "native": "עברית", "flag": "🇮🇱", "locale": "he-IL"},
    "bn": {"name": "Bengali", "native": "বাংলা", "flag": "🇧🇩", "locale": "bn-BD"},
    "te": {"name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳", "locale": "te-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳", "locale": "ta-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "flag": "🇮🇳", "locale": "mr-IN"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳", "locale": "gu-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳", "locale": "kn-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "flag": "🇮🇳", "locale": "ml-IN"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "flag": "🇮🇳", "locale": "pa-IN"},
    "ur": {"name": "Urdu", "native": "اردو", "flag": "🇵🇰", "locale": "ur-PK"},
    "fa": {"name": "Persian", "native": "فارسی", "flag": "🇮🇷", "locale": "fa-IR"},
    "ms": {"name": "Malay", "native": "Bahasa Melayu", "flag": "🇲🇾", "locale": "ms-MY"},
    "tl": {"name": "Filipino (Tagalog)", "native": "Tagalog", "flag": "🇵🇭", "locale": "fil-PH"},
    "af": {"name": "Afrikaans", "native": "Afrikaans", "flag": "🇿🇦", "locale": "af-ZA"},
    "sq": {"name": "Albanian", "native": "Shqip", "flag": "🇦🇱", "locale": "sq-AL"},
    "am": {"name": "Amharic", "native": "አማርኛ", "flag": "🇪🇹", "locale": "am-ET"},
    "hy": {"name": "Armenian", "native": "Հայերեն", "flag": "🇦🇲", "locale": "hy-AM"},
    "az": {"name": "Azerbaijani", "native": "Azərbaycan", "flag": "🇦🇿", "locale": "az-AZ"},
    "eu": {"name": "Basque", "native": "Euskara", "flag": "🇪🇸", "locale": "eu-ES"},
    "be": {"name": "Belarusian", "native": "Беларуская", "flag": "🇧🇾", "locale": "be-BY"},
    "bs": {"name": "Bosnian", "native": "Bosanski", "flag": "🇧🇦", "locale": "bs-BA"},
    "bg": {"name": "Bulgarian", "native": "Български", "flag": "🇧🇬", "locale": "bg-BG"},
    "ca": {"name": "Catalan", "native": "Català", "flag": "🇪🇸", "locale": "ca-ES"},
    "hr": {"name": "Croatian", "native": "Hrvatski", "flag": "🇭🇷", "locale": "hr-HR"},
    "et": {"name": "Estonian", "native": "Eesti", "flag": "🇪🇪", "locale": "et-EE"},
    "gl": {"name": "Galician", "native": "Galego", "flag": "🇪🇸", "locale": "gl-ES"},
    "ka": {"name": "Georgian", "native": "ქართული", "flag": "🇬🇪", "locale": "ka-GE"},
    "is": {"name": "Icelandic", "native": "Íslenska", "flag": "🇮🇸", "locale": "is-IS"},
    "ga": {"name": "Irish", "native": "Gaeilge", "flag": "🇮🇪", "locale": "ga-IE"},
    "kk": {"name": "Kazakh", "native": "Қазақ тілі", "flag": "🇰🇿", "locale": "kk-KZ"},
    "lv": {"name": "Latvian", "native": "Latviešu", "flag": "🇱🇻", "locale": "lv-LV"},
    "lt": {"name": "Lithuanian", "native": "Lietuvių", "flag": "🇱🇹", "locale": "lt-LT"},
    "mk": {"name": "Macedonian", "native": "Македонски", "flag": "🇲🇰", "locale": "mk-MK"},
    "mn": {"name": "Mongolian", "native": "Монгол", "flag": "🇲🇳", "locale": "mn-MN"},
    "ne": {"name": "Nepali", "native": "नेपाली", "flag": "🇳🇵", "locale": "ne-NP"},
    "sr": {"name": "Serbian", "native": "Српски", "flag": "🇷🇸", "locale": "sr-RS"},
    "si": {"name": "Sinhala", "native": "සිංහල", "flag": "🇱🇰", "locale": "si-LK"},
    "sk": {"name": "Slovak", "native": "Slovenčina", "flag": "🇸🇰", "locale": "sk-SK"},
    "sl": {"name": "Slovenian", "native": "Slovenščina", "flag": "🇸🇮", "locale": "sl-SI"},
    "sw": {"name": "Swahili", "native": "Kiswahili", "flag": "🇰🇪", "locale": "sw-KE"},
    "cy": {"name": "Welsh", "native": "Cymraeg", "flag": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "locale": "cy-GB"},
    "yi": {"name": "Yiddish", "native": "ייִדיש", "flag": "🇮🇱", "locale": "yi-001"},
    "zu": {"name": "Zulu", "native": "isiZulu", "flag": "🇿🇦", "locale": "zu-ZA"},
    "la": {"name": "Latin", "native": "Latina", "flag": "🏛️", "locale": "la"}
}

POPULAR_CODES = ["en", "es", "fr", "de", "hi", "zh", "ja", "ar", "ru", "pt", "it"]


def get_all_languages() -> List[Dict[str, str]]:
    """Returns a sorted list of language descriptors for client selectors."""
    langs = []
    # Auto first
    langs.append({"code": "auto", **LANGUAGES["auto"]})
    # Rest alphabetically by English name
    sorted_codes = sorted([c for c in LANGUAGES if c != "auto"], key=lambda c: LANGUAGES[c]["name"])
    for c in sorted_codes:
        langs.append({"code": c, **LANGUAGES[c]})
    return langs


def get_target_languages() -> List[Dict[str, str]]:
    """Returns languages allowed as translation targets (excludes 'auto')."""
    return [lang for lang in get_all_languages() if lang["code"] != "auto"]


def get_popular_languages() -> List[Dict[str, str]]:
    """Returns the curated list of popular languages for quick-switch chips."""
    return [{"code": c, **LANGUAGES[c]} for c in POPULAR_CODES if c in LANGUAGES]


def get_language_name(code: str) -> str:
    """Returns English display name for an ISO code."""
    return LANGUAGES.get(code.lower(), {}).get("name", code.upper())


def get_language_locale(code: str) -> str:
    """Returns speech synthesis locale for an ISO code."""
    return LANGUAGES.get(code.lower(), {}).get("locale", "en-US")
