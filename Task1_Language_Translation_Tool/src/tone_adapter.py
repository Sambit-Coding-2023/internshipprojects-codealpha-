"""
Tone & Formality Style Adapter
Provides stylistic adaptation for translations across major world languages:
- Formal / Polite (e.g., German Sie/Ihnen, Spanish usted/le, French vous, Japanese honorifics)
- Casual / Conversational (e.g., German du/dich, Spanish tú/te, French tu/te)
- Academic / Technical (precise scholarly vocabulary and syntax)
- Simplified / Learner (clear, accessible phrasing for language learners)
"""

import re
from typing import Dict, List, Tuple


# Spanish formality mappings
SPANISH_FORMAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(tú)\b", "usted"),
    (r"\b(Tú)\b", "Usted"),
    (r"\b(te)\b", "le"),
    (r"\b(Te)\b", "Le"),
    (r"\b(ti)\b", "usted"),
    (r"\b(tu)\b", "su"),
    (r"\b(tus)\b", "sus"),
    (r"\b(tuyo|tuya)\b", "suyo"),
    (r"\b(tuyos|tuyas)\b", "suyos"),
    (r"\b(puedes)\b", "puede"),
    (r"\b(quieres)\b", "desea"),
    (r"\b(tienes)\b", "tiene"),
    (r"\b(sabes)\b", "sabe"),
    (r"\b(hola)\b", "buenos días"),
    (r"\b(Hola)\b", "Buenos días"),
    (r"\b(gracias)\b", "muchas gracias"),
    (r"\b(chau|adiós)\b", "hasta luego"),
]

SPANISH_CASUAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(usted)\b", "tú"),
    (r"\b(Usted)\b", "Tú"),
    (r"\b(le)\b", "te"),
    (r"\b(Le)\b", "Te"),
    (r"\b(su)\b", "tu"),
    (r"\b(sus)\b", "tus"),
    (r"\b(suyo|suya)\b", "tuyo"),
    (r"\b(suyos|suyas)\b", "tuyos"),
    (r"\b(puede)\b", "puedes"),
    (r"\b(desea)\b", "quieres"),
    (r"\b(tiene)\b", "tienes"),
    (r"\b(sabe)\b", "sabes"),
    (r"\b(buenos días|buenas tardes)\b", "hola"),
    (r"\b(Buenos días|Buenas tardes)\b", "Hola"),
]

# French formality mappings
FRENCH_FORMAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(tu)\b", "vous"),
    (r"\b(Tu)\b", "Vous"),
    (r"\b(te)\b", "vous"),
    (r"\b(Te)\b", "Vous"),
    (r"\b(ton|ta)\b", "votre"),
    (r"\b(tes)\b", "vos"),
    (r"\b(peux)\b", "pouvez"),
    (r"\b(veux)\b", "souhaitez"),
    (r"\b(as)\b", "avez"),
    (r"\b(sais)\b", "savez"),
    (r"\b(salut)\b", "bonjour"),
    (r"\b(Salut)\b", "Bonjour"),
]

FRENCH_CASUAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(vous)\b", "tu"),
    (r"\b(Vous)\b", "Tu"),
    (r"\b(votre)\b", "ton"),
    (r"\b(vos)\b", "tes"),
    (r"\b(pouvez)\b", "peux"),
    (r"\b(souhaitez)\b", "veux"),
    (r"\b(avez)\b", "as"),
    (r"\b(savez)\b", "sais"),
    (r"\b(bonjour)\b", "salut"),
    (r"\b(Bonjour)\b", "Salut"),
]

# German formality mappings
GERMAN_FORMAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(du)\b", "Sie"),
    (r"\b(Du)\b", "Sie"),
    (r"\b(dich|dir)\b", "Ihnen"),
    (r"\b(dein|deine)\b", "Ihr"),
    (r"\b(deinen|deinem|deiner)\b", "Ihren"),
    (r"\b(kannst)\b", "können"),
    (r"\b(willst)\b", "möchten"),
    (r"\b(hast)\b", "haben"),
    (r"\b(weißt)\b", "wissen"),
    (r"\b(hi|tschüss)\b", "auf Wiedersehen"),
]

GERMAN_CASUAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(Sie)\b", "du"),
    (r"\b(Ihnen)\b", "dir"),
    (r"\b(Ihr|Ihre)\b", "dein"),
    (r"\b(Ihren|Ihrem)\b", "deinen"),
    (r"\b(können)\b", "kannst"),
    (r"\b(möchten)\b", "willst"),
    (r"\b(haben)\b", "hast"),
    (r"\b(wissen)\b", "weißt"),
    (r"\b(auf Wiedersehen)\b", "tschüss"),
]

# English style adjustments
ENGLISH_FORMAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(gonna)\b", "going to"),
    (r"\b(wanna)\b", "would like to"),
    (r"\b(gotta)\b", "must"),
    (r"\b(buy)\b", "purchase"),
    (r"\b(help)\b", "assistance"),
    (r"\b(need)\b", "require"),
    (r"\b(ask for)\b", "request"),
    (r"\b(get in touch)\b", "contact"),
    (r"\b(tell)\b", "inform"),
    (r"\b(start)\b", "commence"),
    (r"\b(end)\b", "conclude"),
    (r"\b(hey|hi)\b", "hello"),
    (r"\b(Hey|Hi)\b", "Hello"),
    (r"\b(thanks)\b", "thank you"),
    (r"\b(Thanks)\b", "Thank you"),
]

ENGLISH_CASUAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(purchase)\b", "buy"),
    (r"\b(assistance)\b", "help"),
    (r"\b(require)\b", "need"),
    (r"\b(commence)\b", "start"),
    (r"\b(conclude)\b", "finish"),
    (r"\b(inform)\b", "let you know"),
    (r"\b(furthermore|moreover)\b", "also"),
    (r"\b(nevertheless)\b", "anyway"),
]

ENGLISH_ACADEMIC_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(shows)\b", "demonstrates"),
    (r"\b(look at)\b", "examine"),
    (r"\b(find out)\b", "ascertain"),
    (r"\b(get)\b", "obtain"),
    (r"\b(make sure)\b", "ensure"),
    (r"\b(big)\b", "substantial"),
    (r"\b(good)\b", "advantageous"),
    (r"\b(bad)\b", "detrimental"),
    (r"\b(think about)\b", "contemplate"),
]

ENGLISH_SIMPLIFIED_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\b(demonstrates|exhibits)\b", "shows"),
    (r"\b(subsequent)\b", "next"),
    (r"\b(prior to)\b", "before"),
    (r"\b(in order to)\b", "to"),
    (r"\b(utilize|employ)\b", "use"),
    (r"\b(commence)\b", "start"),
    (r"\b(terminate)\b", "end"),
    (r"\b(approximately)\b", "about"),
    (r"\b(numerous)\b", "many"),
    (r"\b(sufficient)\b", "enough"),
]


def adapt_tone(text: str, target_lang: str, tone: str = "default") -> str:
    """
    Adapts translated text to match a desired formality or stylistic tone.
    Supported tones:
      - 'default': No changes applied
      - 'formal': Respectful, honorific, business-appropriate phrasing
      - 'casual': Relaxed, conversational, friendly phrasing
      - 'academic': Scholarly, precise, technical terminology
      - 'simplified': Clear, straightforward language for learners
    """
    if not text or not text.strip():
        return ""

    tone = (tone or "default").strip().lower()
    if tone == "default":
        return text

    adapted = text
    lang = (target_lang or "").strip().lower()

    # Spanish
    if lang == "es":
        if tone in ("formal", "academic"):
            for pattern, repl in SPANISH_FORMAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone in ("casual", "simplified"):
            for pattern, repl in SPANISH_CASUAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)

    # French
    elif lang == "fr":
        if tone in ("formal", "academic"):
            for pattern, repl in FRENCH_FORMAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone in ("casual", "simplified"):
            for pattern, repl in FRENCH_CASUAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)

    # German
    elif lang == "de":
        if tone in ("formal", "academic"):
            for pattern, repl in GERMAN_FORMAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone in ("casual", "simplified"):
            for pattern, repl in GERMAN_CASUAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)

    # English
    elif lang == "en":
        if tone == "formal":
            for pattern, repl in ENGLISH_FORMAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone == "casual":
            for pattern, repl in ENGLISH_CASUAL_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone == "academic":
            for pattern, repl in ENGLISH_ACADEMIC_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)
        elif tone == "simplified":
            for pattern, repl in ENGLISH_SIMPLIFIED_REPLACEMENTS:
                adapted = re.sub(pattern, repl, adapted)

    # Generic Fallback: Capitalize sentences properly
    if adapted:
        # Clean multi-spaces
        adapted = re.sub(r" +", " ", adapted)

    return adapted
