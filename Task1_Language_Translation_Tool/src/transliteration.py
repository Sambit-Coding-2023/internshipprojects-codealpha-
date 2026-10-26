"""
Phonetic Transliteration & Romanization Engine
Provides phonetic transliteration for non-Latin writing systems into Latin script:
- Devanagari (Hindi, Marathi, Sanskrit)
- Cyrillic (Russian, Ukrainian, Bulgarian)
- Greek
- Arabic (Buckwalter / phonetic Latin representation)
"""

import re
from typing import Optional

# Devanagari to Latin phonetics (Standard IAST / Common Indian English Romanization)
DEVANAGARI_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'अं': 'an', 'अः': 'ah'
}

DEVANAGARI_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ं': 'n', 'ँ': 'n', 'ः': 'h', '्': ''
}

DEVANAGARI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क्ष': 'ksh', 'त्र': 'tra', 'ज्ञ': 'gya'
}

# Cyrillic to Latin phonetics (GOST / ISO 9)
CYRILLIC_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

# Greek to Latin phonetics
GREEK_MAP = {
    'α': 'a', 'β': 'v', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'i',
    'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x',
    'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't', 'υ': 'y',
    'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
    'ά': 'a', 'έ': 'e', 'ή': 'i', 'ί': 'i', 'ό': 'o', 'ύ': 'y', 'ώ': 'o',
    'Α': 'A', 'Β': 'V', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'I',
    'Θ': 'Th', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X',
    'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F',
    'Χ': 'Ch', 'Ψ': 'Ps', 'Ω': 'O'
}

# Arabic basic phonetic mapping
ARABIC_MAP = {
    'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa', 'ب': 'b', 'ت': 't', 'ث': 'th',
    'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': "'",
    'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'h', 'ء': "'", 'ئ': "'", 'ؤ': "'",
    'َ': 'a', 'ُ': 'u', 'ِ': 'i', 'ً': 'an', 'ٌ': 'un', 'ٍ': 'in', 'ّ': '', 'ْ': ''
}


def transliterate_devanagari(text: str) -> str:
    """Converts Devanagari text to readable phonetic Latin script."""
    result = []
    i = 0
    n = len(text)
    consonants = set(DEVANAGARI_CONSONANTS.keys())
    matras = set(DEVANAGARI_MATRAS.keys())
    vowels = set(DEVANAGARI_VOWELS.keys())

    while i < n:
        ch = text[i]

        if ch in vowels:
            result.append(DEVANAGARI_VOWELS[ch])
            i += 1
        elif ch in consonants:
            base_cons = DEVANAGARI_CONSONANTS[ch]
            # Check next character for virama or matra
            if i + 1 < n and text[i + 1] in matras:
                next_ch = text[i + 1]
                matra_val = DEVANAGARI_MATRAS[next_ch]
                result.append(base_cons + matra_val)
                i += 2
            elif i + 1 < n and text[i + 1] == '्':  # Halant / Virama
                result.append(base_cons)
                i += 2
            else:
                # Inherent 'a' vowel unless followed by space or punctuation or at word end
                is_word_end = (i + 1 == n) or text[i + 1] in " ,.!?-\n\t"
                if is_word_end:
                    result.append(base_cons)
                else:
                    result.append(base_cons + 'a')
                i += 1
        elif ch in matras:
            result.append(DEVANAGARI_MATRAS[ch])
            i += 1
        else:
            result.append(ch)
            i += 1

    trans = "".join(result)
    # Clean double spaces or awkward joins
    trans = re.sub(r'([a-zA-Z])\s+([?.!,])', r'\1\2', trans)
    return trans.capitalize() if trans else ""


def transliterate_cyrillic(text: str) -> str:
    """Converts Russian/Cyrillic script to standard Latin phonetics."""
    res = []
    for char in text:
        res.append(CYRILLIC_MAP.get(char, char))
    return "".join(res)


def transliterate_greek(text: str) -> str:
    """Converts Greek script to standard Latin phonetics."""
    res = []
    for char in text:
        res.append(GREEK_MAP.get(char, char))
    return "".join(res)


def transliterate_arabic(text: str) -> str:
    """Converts Arabic script to standard Latin phonetics."""
    res = []
    for char in text:
        res.append(ARABIC_MAP.get(char, char))
    return "".join(res)


def get_transliteration(text: str, lang_code: str) -> Optional[str]:
    """
    Main entry point for transliteration.
    Returns Romanized phonetic transcription for non-Latin scripts, or None if not applicable.
    """
    if not text or not text.strip():
        return None

    lang = (lang_code or "").lower().split("-")[0]

    # Devanagari languages
    if lang in ("hi", "mr", "ne", "sa"):
        # Verify text contains Devanagari
        if re.search(r"[\u0900-\u097F]", text):
            return transliterate_devanagari(text)

    # Cyrillic languages
    elif lang in ("ru", "uk", "bg", "be", "mk", "sr"):
        if re.search(r"[\u0400-\u04FF]", text):
            return transliterate_cyrillic(text)

    # Greek
    elif lang in ("el",):
        if re.search(r"[\u0370-\u03FF]", text):
            return transliterate_greek(text)

    # Arabic
    elif lang in ("ar", "fa", "ur"):
        if re.search(r"[\u0600-\u06FF]", text):
            return transliterate_arabic(text)

    return None
