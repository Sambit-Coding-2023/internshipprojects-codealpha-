"""
Translation Verification & Quality Evaluation Engine
Performs round-trip back-translation (Source -> Target -> Source) to compute
semantic integrity score, lexical alignment, and translation fidelity ratings.
"""

import difflib
import re
import time
from typing import Any, Dict, List, Set


def _tokenize(text: str) -> List[str]:
    """Extracts normalized alphanumeric word tokens."""
    return [w.lower() for w in re.findall(r"\b\w+\b", text)]


def _calculate_token_jaccard(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Computes Jaccard similarity index between token sets."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union)


def _calculate_sequence_ratio(text_a: str, text_b: str) -> float:
    """Computes Ratcliff-Obershelp sequence similarity ratio."""
    matcher = difflib.SequenceMatcher(None, text_a.lower().strip(), text_b.lower().strip())
    return matcher.ratio()


def verify_translation_quality(
    translation_service,
    source_text: str,
    target_text: str,
    source_lang: str,
    target_lang: str
) -> Dict[str, Any]:
    """
    Performs round-trip verification:
    1. Back-translates target_text to original source language.
    2. Compares source_text with back_translated text.
    3. Calculates confidence percentage and quality status.
    """
    start_time = time.time()
    source_text_clean = source_text.strip()
    target_text_clean = target_text.strip()

    if not source_text_clean or not target_text_clean:
        return {
            "success": False,
            "error": "Source or target text empty"
        }

    # If source and target are identical
    if source_lang == target_lang:
        return {
            "success": True,
            "back_translation": target_text_clean,
            "integrity_score": 100,
            "rating": "Identical Match",
            "rating_color": "green",
            "matched_keywords": _tokenize(source_text_clean)[:5],
            "latency_ms": 0
        }

    # Execute back-translation: target_lang -> source_lang
    try:
        back_res = translation_service.translate(
            text=target_text_clean,
            source_lang=target_lang,
            target_lang=source_lang
        )
        back_text = back_res.get("translated_text", "").strip()
    except Exception as e:
        return {
            "success": False,
            "error": f"Back-translation failed: {str(e)}"
        }

    tokens_orig = _tokenize(source_text_clean)
    tokens_back = _tokenize(back_text)

    jaccard = _calculate_token_jaccard(tokens_orig, tokens_back)
    seq_ratio = _calculate_sequence_ratio(source_text_clean, back_text)

    # Weighted composite score: 60% token overlap + 40% sequence alignment
    composite = (jaccard * 0.60) + (seq_ratio * 0.40)

    # Boost score slightly for short phrases where minor word variance doesn't hurt meaning
    if len(tokens_orig) <= 4 and jaccard > 0:
        composite = min(1.0, composite + 0.15)

    integrity_pct = max(10, min(100, int(round(composite * 100))))

    # Determine Rating
    if integrity_pct >= 85:
        rating = "Excellent Fidelity"
        color = "green"
    elif integrity_pct >= 70:
        rating = "Good Semantic Match"
        color = "blue"
    elif integrity_pct >= 50:
        rating = "Moderate Match (Review)"
        color = "orange"
    else:
        rating = "Potential Meaning Shift"
        color = "red"

    matched_keywords = list(set(tokens_orig).intersection(set(tokens_back)))[:6]

    elapsed_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "success": True,
        "back_translation": back_text,
        "integrity_score": integrity_pct,
        "rating": rating,
        "rating_color": color,
        "matched_keywords": matched_keywords,
        "latency_ms": elapsed_ms
    }
