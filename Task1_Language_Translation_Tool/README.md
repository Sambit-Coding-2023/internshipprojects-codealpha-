
# 🌐 LingoStudio AI – Advanced Multi-Engine Translation & Speech Studio

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-black?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Tests-24%2F24%20Passing-brightgreen?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Accuracy](https://img.shields.io/badge/Benchmark%20Accuracy-100%25-success?style=flat)](evaluate.py)
[![Latency](https://img.shields.io/badge/Avg%20Latency-284ms-blue?style=flat)](evaluate.py)
[![Languages](https://img.shields.io/badge/Languages-100%2B%20Supported-purple?style=flat)](#supported-languages)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A state-of-the-art, production-grade AI language translation workstation and CLI studio powered by multi-engine neural routing, heuristic Unicode script auto-detection, Speech-to-Text microphone dictation, dual-tier Text-to-Speech (TTS) audio synthesis, and round-trip quality verification.

---

## 📑 Table of Contents
- [Project Overview](#-project-overview)
- [System Architecture](#-system-architecture)
- [Core Feature Highlights](#-core-feature-highlights)
  - [1. Multi-Engine Neural Routing & Fallback](#1-multi-engine-neural-routing--fault-tolerance)
  - [2. Three Distinct Studio Workspaces](#2-three-distinct-studio-workspaces)
  - [3. Formality & Stylistic Tone Adapter](#3-formality--stylistic-tone-adapter)
  - [4. Round-Trip Quality Verification (QA)](#4-round-trip-quality-verification-integrity-index)
  - [5. Operative History & Spaced-Repetition Deck](#5-operative-history--spaced-repetition-deck)
  - [6. Media & Subtitle (.SRT/.VTT) Translation](#6-media--subtitle-translator)
  - [7. Code & Markdown Syntax Preservation](#7-code--markdown-syntax-shield)
  - [8. Command Palette (Ctrl + K)](#8-command-palette-spotlight-launcher)
- [Project Structure](#-project-structure)
- [Installation & Quickstart](#-installation--quickstart)
- [CLI Reference](#-command-line-interface-cli)
- [Accuracy & Latency Benchmark](#-accuracy--latency-benchmark)
- [Automated Test Suite](#-automated-test-suite)
- [REST API Reference](#-rest-api-reference)
- [Keyboard Shortcuts Guide](#-keyboard-shortcuts)
- [License](#-license)

---

## 🌟 Project Overview

Most language translation projects are simplistic wrappers around a single API. **LingoStudio AI** was engineered from the ground up as a comprehensive translation ecosystem designed to solve real-world translation challenges:

1. **High Availability & Zero Lockout:** Graceful fallback across multiple neural translation engines (MyMemory, Google, LibreTranslate) and an offline phrasebook.
2. **Grammatical & Social Appropriateness:** Dynamic adaptation of translations to fit desired formality registers (*Formal*, *Casual*, *Academic*, *Simplified*).
3. **Conversational Fluency:** Real-time two-way voice communication with automatic language detection, speech recognition, and synthesized playback.
4. **Accuracy Auditing:** Objective back-translation scoring showing semantic preservation percentages before sending translations to clients or audiences.
5. **Developer & Subtitle Friendly:** Preserves timestamps in video subtitle files and shields programming code syntax from unwanted translation.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────────────────────────────────────┐
                       │          Client Input Layer (Browser Web App / CLI)     │
                       │   • Real-Time Text Input (Debounced 380ms)              │
                       │   • Web Speech API Microphone Voice Dictation           │
                       │   • Document & Subtitle Uploads (.srt, .vtt, .txt, .md) │
                       └────────────────────────────┬────────────────────────────┘
                                                    │
                                           [Unicode Heuristic]
                                        Script Auto-Detect Engine
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       Multi-Engine Translation Hub      │
                               └───────┬────────────┬───────────┬────────┘
                                       │            │           │
             ┌─────────────────────────┼────────────┼───────────┼─────────────────────────┐
             ▼                         ▼            ▼           ▼                         ▼
    [MyMemory Neural API]    [Google Translator]  [Libre]  [Offline Phrasebook]    [Tone Adapter]
    • Primary neural route   • 100+ Languages     • Mirror • Zero-network fallback • Formal/Casual
    • Fast response          • Deep vocabulary    • Open   • Instant response      • Academic
             │                         │            │           │                         │
             └─────────────────────────┴────────────┼───────────┴─────────────────────────┘
                                                    │
                                           [Response Packager]
                                    • Execution latency profiler (ms)
                                    • Detected language & confidence score
                                    • Phonetic transliteration / Romanization
                                    • CEFR text analytics & speaking metrics
                                                    │
                     ┌──────────────────────────────┴──────────────────────────────┐
                     ▼                                                             ▼
       [Interactive Web Studio (Port 5001)]                             [Command Line CLI]
       • Dual Studio, Polyglot 1-to-5, Walkie-Talkie                    • Terminal translation
       • Command Palette (Ctrl+K) & Shortcuts                           • Batch file processing
       • Operative History Drawer (Search, Restore, CSV)                • Speech synthesis (.mp3)
       • 3D Flippable Study Flashcard Deck (Anki-ready)                 • Benchmark evaluation
```

---

## 🚀 Core Feature Highlights

### 1. Multi-Engine Neural Routing & Fault Tolerance
- **Primary Route (MyMemory API):** High-speed translation routing with zero required API keys.
- **Secondary Route (Google Neural Translator):** Comprehensive dictionary vocabulary covering 100+ global languages via `deep-translator`.
- **Tertiary Route (LibreTranslate Mirrors):** Open-source API fallback for server resilience.
- **Offline Fallback Phrasebook:** Hardcoded, high-frequency phrase translations for essential travel, greetings, and emergency expressions when completely disconnected from the network.

### 2. Three Distinct Studio Workspaces
- **Dual Translation Studio:** Standard side-by-side workspace featuring live debounced translation, live character/word counters, CEFR reading difficulty index, speaking durations, dictionary definitions, and one-click audio players.
- **Polyglot 1-to-5 Broadcast Mode:** Input a single phrase and simultaneously broadcast translations to **5 target languages** (e.g., Spanish, French, German, Japanese, Hindi) with dedicated audio synthesis and individual copy buttons.
- **Two-Way Walkie-Talkie Conversation Mode:** Split-screen dual-microphone interface designed for real-world bilingual conversation. Person A speaks, the system transcribes and auto-translates, then speaks aloud to Person B in their native language.

### 3. Formality & Stylistic Tone Adapter
Dynamically transforms translated text between 5 stylistic registers:
- **Default:** Natural, balanced phrasing.
- **Formal:** Professional and polite address (converts informal pronouns to *usted*, *vous*, *Sie*, honorifics).
- **Casual:** Conversational, friendly phrasing (*tú*, *tu*, *du*, colloquial greetings).
- **Academic:** Elevated vocabulary, scholarly connectives, and precise phrasing.
- **Simplified:** Plain, learner-friendly language avoiding complex idioms (ideal for A1/A2 learners).

### 4. Round-Trip Quality Verification (Integrity Index)
Translates the target text back into the source language, evaluates token similarity, and computes a **Semantic Meaning Integrity Score** (e.g., `96% Meaning Integrity`) with an inspection card displaying the back-translation for confidence verification.

### 5. Operative History & Spaced-Repetition Deck
- **Instant Search & Filters:** Filter translation history in real time by search terms or toggle between "All" and "⭐ Starred".
- **One-Click Studio Restore:** Clicking any history card loads the source text into the studio, resets languages, triggers translation, and smooth-scrolls into the editor.
- **Card Action Controls:** Per-record **Restore**, **Copy**, **Listen (TTS)**, **Delete**, and **Star** buttons.
- **CSV Spreadsheet Export:** One-click download of your entire history with timestamped source and target pairs.
- **3D Flippable Study Deck:** Starred entries automatically sync to a study deck with 3D flippable flashcards and an **Anki-ready CSV export**.

### 6. Media & Subtitle (.SRT/.VTT) Translator
Upload video subtitle files (`.srt` or `.vtt`). The engine parses the subtitle format, translates dialogue lines, and preserves the exact start/end timecodes and subtitle sequence numbering.

### 7. Code & Markdown Syntax Shield
Translating technical documentation? The engine isolates inline code (`` `code` ``), code blocks (` ```python ... ``` `), HTML tags, and URLs, translating only natural prose while preserving programming syntax.

### 8. Command Palette (Spotlight Launcher)
Press <kbd>Ctrl + K</kbd> (or <kbd>Cmd + K</kbd>) anywhere in the app to open a spotlight launcher with **37+ instant actions**: quick-switch languages, toggle studio modes, change formality tones, format text, and run diagnostics.

---

## 📂 Project Structure

```
Task1_Language_Translation_Tool/
├── src/
│   ├── __init__.py
│   ├── languages.py             # 100+ global languages registry, native names, flags & locales
│   ├── translator.py            # Multi-engine orchestrator, heuristic auto-detector & cache
│   ├── tone_adapter.py          # Formality and stylistic tone transformer (5 registers)
│   ├── transliteration.py       # Phonetic Romanization (Devanagari, Cyrillic, Greek, Arabic)
│   ├── verifier.py              # Round-trip back-translation & semantic integrity scoring
│   ├── text_processor.py        # Subtitle (.srt/.vtt) parsing & code/markdown preservation
│   ├── tts_service.py           # Text-to-speech audio synthesis service (gTTS)
│   └── dictionary_service.py    # Definitions, phonetics, and synonyms lookup
├── static/
│   ├── css/
│   │   └── style.css            # Dark/light glassmorphic UI, animations, command palette
│   └── js/
│       └── app.js               # Debounced SPA controller, Web Speech, shortcuts, history
├── templates/
│   └── index.html               # Semantic HTML5 studio with modals, drawers & analytics
├── tests/
│   ├── test_translation.py      # Core translation, routing, and Flask endpoint tests
│   ├── test_tone_adapter.py     # Stylistic tone adaptation and API integration tests
│   └── test_new_features.py     # Standout feature tests (translit, verifier, srt, code)
├── app.py                       # Flask web server (Port 5001)
├── translate_cli.py             # Feature-rich Command Line Interface utility
├── cli.py                       # Interactive CLI entrypoint
├── evaluate.py                  # Multi-language accuracy & latency benchmark suite
├── requirements.txt             # Project Python dependencies
└── README.md                    # Comprehensive documentation
```

---

## 💻 Installation & Quickstart

### Prerequisites
- Python **3.10** or **3.11**
- An active internet connection (for live neural APIs)
- A modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Clone & Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-username/lingostudio-ai.git
cd lingostudio-ai

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Launch the Web Studio
```bash
python app.py
```
Open **`http://localhost:5001`** (or `http://127.0.0.1:5001`) in your browser to start translating!

---

## ⌨️ Command Line Interface (CLI)

The repository provides a full-featured CLI tool (`translate_cli.py`) for scripting and terminal workflows:

```bash
# 1. Quick translation
python translate_cli.py "Hello, welcome to our AI translation studio!" --target es

# 2. Specify source and target languages
python translate_cli.py "Bonjour tout le monde" --source fr --target en

# 3. Translate a whole document file
python translate_cli.py --file notes.txt --target de --output translated_de.txt

# 4. Generate and save spoken audio (TTS MP3)
python translate_cli.py "Thank you very much for your help" --target ja --tts

# 5. Detect language only
python translate_cli.py "Guten Morgen wie geht es Ihnen" --detect-only

# 6. Interactive terminal mode
python translate_cli.py
```

---

## 📊 Accuracy & Latency Benchmark

The project includes an automated multi-lingual evaluation suite (`evaluate.py`) that benchmarks accuracy and latency across international language pairs:

```bash
python evaluate.py
```

### Benchmark Results
```
================================================================================
        AI LANGUAGE TRANSLATION ACCURACY & LATENCY BENCHMARK        
================================================================================
Evaluating 8 multi-lingual test pairs...
--------------------------------------------------------------------------------
#   | LANG PAIR  | ENGINE               | LATENCY  | STATUS | TRANSLATION              
--------------------------------------------------------------------------------
1   | EN -> ES   | Google Neural Engine | 682.8 ms | PASS   | Hola, ¿cómo estás hoy?
2   | EN -> FR   | Google Neural Engine | 307.4 ms | PASS   | Bienvenue sur notre pl...
3   | EN -> DE   | Google Neural Engine | 255.7 ms | PASS   | Maschinelles Lernen un...
4   | EN -> JA   | Google Neural Engine | 164.0 ms | PASS   | 最寄りの駅までの道を教えていただけますか。
5   | EN -> HI   | Google Neural Engine | 287.0 ms | PASS   | अभ्यास परिपूर्ण बनाता ...
6   | EN -> ZH   | Google Neural Engine | 166.2 ms | PASS   | 非常感谢您的支持与合作。
7   | EN -> IT   | Google Neural Engine | 256.3 ms | PASS   | Il tempo oggi è solegg...
8   | EN -> RU   | Google Neural Engine | 153.1 ms | PASS   | Мы рады объявить о наш...
--------------------------------------------------------------------------------
Overall Accuracy:  8/8 (100.0%)
Average Latency:   284.1 ms
================================================================================
```

---

## 🧪 Automated Test Suite

The codebase is covered by **24 automated pytest unit and integration tests** validating endpoints, speech services, tone adaptation, subtitle handling, and translation fault tolerance:

```bash
python -m pytest tests/ -v
```

### Test Breakdown
- `tests/test_translation.py`: 8 tests covering auto-detection, engine routing, language catalogue, and API endpoints.
- `tests/test_tone_adapter.py`: 7 tests verifying formality rules across Spanish, French, and German.
- `tests/test_new_features.py`: 9 tests covering transliteration, subtitle parsing, code shielding, and back-translation QA.

```
tests/test_new_features.py .........                                     [ 37%]
tests/test_tone_adapter.py .......                                       [ 66%]
tests/test_translation.py ........                                       [100%]
============================= 24 passed in 8.47s ==============================
```

---

## 📡 REST API Reference

All backend capabilities are exposed via RESTful JSON endpoints:

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/` | `GET` | Web Studio graphical interface |
| `/api/languages` | `GET` | Returns all 100+ languages with ISO codes, flags, and native names |
| `/api/translate` | `POST` | Core translation endpoint (supports tone adaptation and analytics) |
| `/api/translate_multi` | `POST` | Translates text simultaneously into 5 languages (Polyglot mode) |
| `/api/detect` | `POST` | Detects language of input text with confidence score |
| `/api/verify` | `POST` | Performs round-trip back-translation and computes semantic integrity score |
| `/api/translate_subtitles` | `POST` | Translates `.srt` / `.vtt` subtitles while preserving exact timecodes |
| `/api/tts` | `POST` | Synthesizes speech into streaming `audio/mpeg` MP3 |
| `/api/dictionary` | `POST` | Retrieves phonetic transcriptions, definitions, and synonyms |
| `/api/health` | `GET` | Health status and uptime endpoint |

### Example Translation Request
```bash
curl -X POST http://localhost:5001/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, thank you for contacting our team.",
    "source_lang": "en",
    "target_lang": "es",
    "engine": "auto",
    "tone": "formal"
  }'
```

### Example Response
```json
{
  "success": true,
  "original_text": "Hello, thank you for contacting our team.",
  "translated_text": "Hola, gracias por comunicarse con nuestro equipo.",
  "source_lang": "en",
  "target_lang": "es",
  "detected_lang": "en",
  "engine_used": "Google Neural Engine",
  "tone": "formal",
  "latency_ms": 284,
  "analytics": {
    "char_count": 41,
    "word_count": 7,
    "reading_time_sec": 2,
    "speaking_time_sec": 3,
    "difficulty": "Intermediate (B1)"
  }
}
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|:---:|:---|
| <kbd>Ctrl + K</kbd> / <kbd>Cmd + K</kbd> | **Open Spotlight Command Palette (37+ Actions)** |
| <kbd>Ctrl + Shift + H</kbd> | **Toggle Translation History Drawer** |
| <kbd>Ctrl + Shift + F</kbd> | **Open Flashcard Study Deck (3D Flippable)** |
| <kbd>Ctrl + Enter</kbd> | **Translate text immediately** |
| <kbd>Ctrl + Shift + S</kbd> | **Swap source and target languages** |
| <kbd>Ctrl + Shift + C</kbd> | **Copy translation to clipboard** |
| <kbd>Ctrl + Shift + D</kbd> | **Toggle Voice Dictation Microphone** |
| <kbd>Ctrl + Shift + L</kbd> | **Listen to target speech (TTS Audio)** |
| <kbd>Ctrl + Shift + T</kbd> | **Toggle Dark / Light Theme** |
| <kbd>Esc</kbd> | **Dismiss open drawers, modals, and menus** |

---

## 📄 License

This project is licensed under the **MIT License** — you are free to modify, distribute, and use it in your personal and commercial portfolios.

---

*Engineered with precision for global communication. Built with Python, Flask, and Vanilla Web Technologies.*
