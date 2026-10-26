import sys
import warnings

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import time

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")

from pathlib import Path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, render_template, request, send_file

from src.languages import get_all_languages, get_language_name, get_popular_languages, get_target_languages
from src.translator import TranslationService
from src.tts_service import TTSService
from src.dictionary_service import DictionaryService
from src.transliteration import get_transliteration
from src.verifier import verify_translation_quality
from src.text_processor import protect_code_and_markdown, restore_code_and_markdown, translate_subtitles, is_subtitle_content
from src.tone_adapter import adapt_tone

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.context_processor
def inject_version():
    return {"version": int(time.time())}

@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

translator = TranslationService()
tts_service = TTSService()
dict_service = DictionaryService()


@app.route("/")
def index():
    """Renders the main translation studio interface."""
    all_langs = get_all_languages()
    target_langs = get_target_languages()
    popular_langs = get_popular_languages()
    return render_template(
        "index.html",
        all_langs=all_langs,
        target_langs=target_langs,
        popular_langs=popular_langs
    )


@app.route("/api/languages", methods=["GET"])
def api_languages():
    """Returns available language options."""
    return jsonify({
        "success": True,
        "languages": get_all_languages(),
        "popular": get_popular_languages()
    })


@app.route("/api/translate", methods=["POST"])
def api_translate():
    """Translates incoming text with auto-detection, multi-engine routing, optional code-protection, tone adaptation, and transliteration."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    source_lang = data.get("source_lang", "auto").strip().lower()
    target_lang = data.get("target_lang", "es").strip().lower()
    engine = data.get("engine", "auto").strip().lower()
    protect_code = data.get("protect_code", False)
    tone = data.get("tone", "default").strip().lower()

    if not text:
        return jsonify({
            "success": True,
            "translated_text": "",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "char_count": 0,
            "word_count": 0,
            "tone": tone
        })

    try:
        placeholders = []
        text_to_translate = text
        if protect_code:
            text_to_translate, placeholders = protect_code_and_markdown(text)

        result = translator.translate(
            text=text_to_translate,
            source_lang=source_lang,
            target_lang=target_lang,
            preferred_engine=engine
        )

        if placeholders and result.get("translated_text"):
            result["translated_text"] = restore_code_and_markdown(result["translated_text"], placeholders)

        # Apply tone and formality adaptation if requested
        if tone and tone != "default" and result.get("translated_text"):
            result["translated_text"] = adapt_tone(result["translated_text"], target_lang, tone)
        result["tone"] = tone

        # Attach phonetic transliteration for non-Latin writing systems
        translit = get_transliteration(result.get("translated_text", ""), target_lang)
        result["transliteration"] = translit

        # Compute readability and speaking metrics
        words = len(text.split())
        chars = len(text)
        reading_sec = max(1, round(words / 3.3)) if words > 0 else 0
        speaking_sec = max(1, round(words / 2.3)) if words > 0 else 0

        if words <= 5:
            cefr = "A1 (Beginner)"
        elif words <= 15:
            cefr = "A2 (Elementary)"
        elif words <= 35:
            cefr = "B1 (Intermediate)"
        elif words <= 70:
            cefr = "B2 (Upper Intermediate)"
        else:
            cefr = "C1 (Advanced)"

        result["analytics"] = {
            "reading_time_sec": reading_sec,
            "speaking_time_sec": speaking_sec,
            "cefr_level": cefr,
            "word_count": words,
            "char_count": chars
        }

        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/translate_multi", methods=["POST"])
def api_translate_multi():
    """Translates source text into multiple target languages simultaneously with tone adaptation and transliteration."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    source_lang = data.get("source_lang", "auto").strip().lower()
    targets = data.get("targets", ["es", "fr", "de", "ja", "hi"])
    tone = data.get("tone", "default").strip().lower()

    if not text:
        return jsonify({"success": True, "results": {}})

    results = {}
    for tgt in targets:
        try:
            res = translator.translate(text, source_lang=source_lang, target_lang=tgt)
            if tone and tone != "default" and res.get("translated_text"):
                res["translated_text"] = adapt_tone(res["translated_text"], tgt, tone)
            res["transliteration"] = get_transliteration(res.get("translated_text", ""), tgt)
            results[tgt] = res
        except Exception as e:
            results[tgt] = {"success": False, "error": str(e)}

    return jsonify({"success": True, "results": results})


@app.route("/api/verify", methods=["POST"])
def api_verify():
    """Verifies translation quality through round-trip back-translation and semantic integrity scoring."""
    data = request.get_json(force=True, silent=True) or {}
    source_text = data.get("source_text", "").strip()
    target_text = data.get("target_text", "").strip()
    source_lang = data.get("source_lang", "en").strip().lower()
    target_lang = data.get("target_lang", "es").strip().lower()

    if not source_text or not target_text:
        return jsonify({"success": False, "error": "Missing source or target text"}), 400

    result = verify_translation_quality(
        translation_service=translator,
        source_text=source_text,
        target_text=target_text,
        source_lang=source_lang,
        target_lang=target_lang
    )
    return jsonify(result)


@app.route("/api/transliterate", methods=["POST"])
def api_transliterate():
    """Returns Romanized phonetic reading for non-Latin script text."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "").strip().lower()
    romanized = get_transliteration(text, lang)
    return jsonify({
        "success": True,
        "original": text,
        "transliteration": romanized
    })


@app.route("/api/translate_subtitles", methods=["POST"])
def api_translate_subtitles():
    """Translates SRT/VTT subtitle files while preserving timestamps."""
    data = request.get_json(force=True, silent=True) or {}
    content = data.get("content", "").strip()
    source_lang = data.get("source_lang", "auto").strip().lower()
    target_lang = data.get("target_lang", "es").strip().lower()

    if not content:
        return jsonify({"success": False, "error": "No subtitle content provided"}), 400

    def tr_fn(line_text):
        res = translator.translate(line_text, source_lang=source_lang, target_lang=target_lang)
        return res.get("translated_text", line_text)

    try:
        translated_subs = translate_subtitles(content, tr_fn)
        return jsonify({
            "success": True,
            "translated_content": translated_subs
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/api/detect", methods=["POST"])
def api_detect():
    """Performs instant language detection on a text snippet."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "No text provided"}), 400

    lang_code, confidence = translator.detect_language(text)
    return jsonify({
        "success": True,
        "code": lang_code,
        "name": get_language_name(lang_code),
        "confidence": confidence
    })


@app.route("/api/tts", methods=["POST"])
def api_tts():
    """Synthesizes text into high-quality MP3 audio and streams it."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "en").strip().lower()

    if not text:
        return jsonify({"success": False, "error": "No text provided for speech"}), 400

    try:
        # Limit to 500 characters for instant speech generation
        truncated_text = text[:500]
        audio_stream = tts_service.generate_speech_stream(truncated_text, lang_code=lang)
        return send_file(
            audio_stream,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="speech.mp3"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dictionary", methods=["POST"])
def api_dictionary():
    """Looks up definitions, phonetics, and synonyms for terms."""
    data = request.get_json(force=True, silent=True) or {}
    word = data.get("word", "").strip()
    result = dict_service.lookup(word)
    return jsonify({
        "success": bool(result),
        "data": result
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "AI Language Translation Studio",
        "version": "1.0.0"
    })


if __name__ == "__main__":
    print("=" * 65)
    print("Starting Task 1 AI Language Translation Studio on http://localhost:5001")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5001, debug=True)
