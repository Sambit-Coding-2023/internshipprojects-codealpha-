"""
Specialized Text Processing Engine:
1. Subtitle Translator (.SRT and .VTT): parses timestamps and dialogue blocks, translates
   only dialogue lines while preserving timestamps and cue numbers.
2. Code & Markdown Syntax Protector: isolates fenced code blocks, inline snippets, and URLs,
   protecting them from distortion during neural translation.
"""

import re
from typing import Any, Callable, Dict, List, Tuple


# =============================================================================
# Code & Markdown Syntax Protector
# =============================================================================

def protect_code_and_markdown(text: str) -> Tuple[str, List[str]]:
    """
    Extracts fenced code blocks (```...```) and inline backtick snippets (`...`)
    and replaces them with safe unique placeholder tokens like [[_CODE_0_]].
    Returns (masked_text, placeholders_list).
    """
    placeholders: List[str] = []

    def replacer(match: re.Match) -> str:
        idx = len(placeholders)
        placeholder = f"[[_CODE_{idx}_]]"
        placeholders.append(match.group(0))
        return placeholder

    # 1. First protect triple backtick code fences (multiline)
    masked = re.sub(r"```[\s\S]*?```", replacer, text)
    # 2. Protect single backticks inline
    masked = re.sub(r"`[^`\n]+`", replacer, masked)
    # 3. Protect standard URLs (http/https)
    masked = re.sub(r"https?://[^\s]+", replacer, masked)

    return masked, placeholders


def restore_code_and_markdown(translated_text: str, placeholders: List[str]) -> str:
    """Restores masked code blocks and URLs back to their original form."""
    restored = translated_text
    for idx, original in enumerate(placeholders):
        # Neural engines may insert spaces inside brackets or change casing:
        # e.g. [[ _CODE_0_ ]] or [[_code_0_]]
        pattern = re.compile(rf"\[\[\s*_[Cc][Oo][Dd][Ee]_{idx}_\s*\]\]", re.IGNORECASE)
        restored = pattern.sub(original, restored)
    return restored


# =============================================================================
# Subtitle (.SRT & .VTT) Parser & Translator
# =============================================================================

SRT_BLOCK_REGEX = re.compile(
    r"(?m)^(?P<index>\d+)\r?\n"
    r"(?P<timing>\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3})\r?\n"
    r"(?P<text>[\s\S]*?)(?=(?:\r?\n\r?\n\d+\r?\n)|\Z)"
)

VTT_BLOCK_REGEX = re.compile(
    r"(?m)(?:(?P<index>\d+)\r?\n)?"
    r"(?P<timing>\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3})\r?\n"
    r"(?P<text>[\s\S]*?)(?=(?:\r?\n\r?\n)|\Z)"
)


def is_subtitle_content(text: str) -> bool:
    """Determines if a text string is an SRT or VTT subtitle file."""
    if "WEBVTT" in text[:30]:
        return True
    if re.search(r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}", text):
        return True
    return False


def translate_subtitles(
    subtitle_content: str,
    translate_fn: Callable[[str], str]
) -> str:
    """
    Translates an SRT or VTT subtitle file:
    Parses each subtitle block, translates only the dialogue lines using translate_fn,
    and returns a formatted subtitle string with identical timecodes.
    """
    is_vtt = subtitle_content.strip().startswith("WEBVTT")

    # Match SRT blocks
    blocks = list(SRT_BLOCK_REGEX.finditer(subtitle_content))
    if not blocks and is_vtt:
        blocks = list(VTT_BLOCK_REGEX.finditer(subtitle_content))

    if not blocks:
        # Fallback if regex didn't catch non-standard blocks: simple line-based translation
        lines = subtitle_content.splitlines()
        translated_lines = []
        timing_pattern = re.compile(r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}")

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.isdigit() or timing_pattern.search(stripped) or stripped == "WEBVTT":
                translated_lines.append(line)
            else:
                try:
                    translated_lines.append(translate_fn(stripped))
                except Exception:
                    translated_lines.append(line)
        return "\n".join(translated_lines)

    output_blocks = []
    if is_vtt and not subtitle_content.startswith("WEBVTT"):
        output_blocks.append("WEBVTT\n")

    for match in blocks:
        idx = match.group("index") or ""
        timing = match.group("timing")
        raw_text = match.group("text").strip()

        if raw_text:
            try:
                translated_dialogue = translate_fn(raw_text)
            except Exception:
                translated_dialogue = raw_text
        else:
            translated_dialogue = ""

        if idx:
            block_str = f"{idx}\n{timing}\n{translated_dialogue}\n"
        else:
            block_str = f"{timing}\n{translated_dialogue}\n"

        output_blocks.append(block_str)

    return "\n".join(output_blocks).strip() + "\n"
