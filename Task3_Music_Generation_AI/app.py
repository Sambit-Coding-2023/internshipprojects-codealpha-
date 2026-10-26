"""
Flask Web Application for Task 3: AI Music Generation Studio
Serves interactive DAW-style UI with in-browser WebAudio synthesizer and MIDI exports.
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, render_template, request, send_from_directory
from src.generator import MusicGenerator
from src.midi_processor import MidiProcessor

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Initialize Generator
generator = MusicGenerator()
processor = MidiProcessor()


@app.route("/")
def index():
    vocab_size = generator.vocab_size
    return render_template("index.html", vocab_size=vocab_size)


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True, silent=True) or {}
    length = int(data.get("length", 48))
    temperature = float(data.get("temperature", 0.8))
    tempo = int(data.get("tempo", 110))

    # Clamp parameters
    length = max(16, min(length, 128))
    temperature = max(0.2, min(temperature, 1.8))
    tempo = max(60, min(tempo, 200))

    try:
        result = generator.generate(
            length=length,
            temperature=temperature,
            tempo_bpm=tempo
        )
        return jsonify({
            "success": True,
            "filename": result["filename"],
            "download_url": f"/api/download/{result['filename']}",
            "total_notes": result["total_notes"],
            "notes": result["notes"],
            "temperature": result["temperature"],
            "tempo_bpm": result["tempo_bpm"],
            "audio_events": result["audio_events"]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/download/<path:filename>", methods=["GET"])
def download_midi(filename):
    outputs_dir = Path(__file__).parent / "outputs"
    return send_from_directory(
        directory=str(outputs_dir),
        path=filename,
        as_attachment=True,
        download_name=filename,
        mimetype="audio/midi"
    )


@app.route("/api/vocab", methods=["GET"])
def get_vocab():
    return jsonify({
        "success": True,
        "vocab_size": generator.vocab_size,
        "notes": list(generator.note_to_int.keys())[:30]
    })


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Task 3 AI Music Studio on http://localhost:5002")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5002, debug=False)
