# 🚀 CodeAlpha Artificial Intelligence Internship Projects

[![Author](https://img.shields.io/badge/Author-Sambit%20Adhikary-blue?style=flat&logo=github)](https://github.com/Sambit-Coding-2023)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Frameworks](https://img.shields.io/badge/Frameworks-PyTorch%20%7C%20Flask%20%7C%20YOLOv8-FF6F00?style=flat)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A comprehensive suite of production-grade Artificial Intelligence, Natural Language Processing, Deep Learning, and Computer Vision solutions engineered during the **CodeAlpha Artificial Intelligence Internship**.

Each project is designed with modular Python architectures, interactive web interfaces (Flask + HTML5 Canvas / Web Audio / WebSocket/MJPEG streams), automated test suites, and thorough documentation.

---

## 📑 Portfolio Overview

| # | Project Name | Primary Technologies | Core Focus | Link |
|---|--------------|----------------------|------------|------|
| **Task 1** | **LingoStudio AI** | Hugging Face Transformers, MarianMT, Flask, TTS/STT | Multi-Engine Language Translation & Audio Synthesis | [Task 1 Directory](./Task1_Language_Translation_Tool) |
| **Task 2** | **AURA FAQ Chatbot** | NLTK, TF-IDF Vectorizer, Cosine Similarity, Flask | Semantic Intent Classification & Cyber HUD Assistant | [Task 2 Directory](./Task2_FAQ_Chatbot) |
| **Task 3** | **Music Generation AI** | PyTorch, Stacked LSTM, music21, Web Audio API | Deep Learning Symbolic Polyphonic Music Composer | [Task 3 Directory](./Task3_Music_Generation_AI) |
| **Task 4** | **Object Detection & Tracking** | YOLOv8n, SORT (Kalman Filter + Hungarian), OpenCV | Real-Time Multi-Object Tracking, Counting & Analytics | [Task 4 Directory](./Task4_Object_Detection_Tracking) |

---

## 🌟 Detailed Project Breakdown

### [Task 1: LingoStudio AI – Advanced Language Translation & Speech Studio](./Task1_Language_Translation_Tool)
* **Description**: A multi-engine neural machine translation workstation and CLI studio.
* **Key Features**:
  - Multi-engine neural routing with automatic fallback across Helsinki-NLP MarianMT models and lightweight online fallbacks.
  - Formality and stylistic tone adapters (Professional, Casual, Academic, Creative).
  - Round-trip quality verification (Back-Translation Integrity Score).
  - Speech-to-Text (STT) voice dictation & Dual-tier Text-to-Speech (TTS) audio synthesis.
  - Subtitle file translation (`.srt` and `.vtt`) and Markdown/Code syntax preservation shields.
* **Launch Command**:
  ```bash
  cd Task1_Language_Translation_Tool
  python app.py
  ```

---

### [Task 2: AURA – Futuristic AI FAQ Assistant](./Task2_FAQ_Chatbot)
* **Description**: An NLP-driven FAQ retrieval and customer support assistant with a Cyberpunk Glassmorphism interface.
* **Key Features**:
  - Tokenization, lemmatization (WordNet), and stopword elimination pipeline.
  - Vector space modeling with TF-IDF and hybrid cosine similarity with adjustable confidence thresholds.
  - Interactive HTML5 Synaptic Neural Canvas that dynamically pulses with AI cognitive states.
  - Bidirectional voice interactions (browser STT input and TTS speech synthesizer).
  - Zero-asset procedural Web Audio sound effect synthesizer.
* **Launch Command**:
  ```bash
  cd Task2_FAQ_Chatbot
  python app.py
  ```

---

### [Task 3: AI Music Generation with Deep Learning (LSTM & music21)](./Task3_Music_Generation_AI)
* **Description**: A symbolic music generator that learns harmonic and melodic structures from polyphonic MIDI compositions.
* **Key Features**:
  - Symbolic MIDI preprocessing, note and chord extraction, and pitch transposition data augmentation via `music21`.
  - Stacked 2-Layer LSTM neural network with Dropout and Embedding in PyTorch.
  - Temperature-controlled probabilistic sampling for creative vs. conservative melodies.
  - Interactive Digital Audio Workstation (DAW) web studio with a polyphonic Web Audio API piano synthesizer and HTML5 Canvas piano roll visualizer.
  - Direct `.mid` file generation and download.
* **Launch Command**:
  ```bash
  cd Task3_Music_Generation_AI
  python app.py
  ```

---

### [Task 4: Intelligent Real-Time Object Detection & Multi-Object Tracking Studio](./Task4_Object_Detection_Tracking)
* **Description**: An Intelligent Video Analytics (IVA) workstation for multi-object detection, trajectory tracking, and motion analytics.
* **Key Features**:
  - Deep neural object detection using Ultralytics YOLOv8n across 80 COCO classes.
  - SORT (Simple Online and Realtime Tracking) using 7-state Kalman Filtering and the Hungarian algorithm for IoU association.
  - Real-time velocity and 8-point compass heading vector calculation.
  - Bi-directional virtual tripwire (line crossing) with persistent IN/OUT counters.
  - Region of Interest (ROI) surveillance zone intrusion monitoring.
  - 2D Gaussian thermal motion density heatmap overlay.
  - Real-time web surveillance console with live video stream, parameter controls, image inspector, and CSV telemetry export.
* **Launch Command**:
  ```bash
  cd Task4_Object_Detection_Tracking
  python app.py
  ```

---

## 🛠️ Repository Structure

```
internshipprojects-codealpha-/
├── Task1_Language_Translation_Tool/
│   ├── src/                    # Translation engines, tone adapter, QA scorer
│   ├── static/                 # CSS styles and JavaScript client
│   ├── templates/              # HTML5 Web UI
│   ├── tests/                  # Pytest test suite (24 passing unit tests)
│   ├── app.py                  # Flask web studio
│   ├── cli.py                  # Command-line translation interface
│   ├── requirements.txt        # Task dependencies
│   └── README.md               # In-depth task documentation
│
├── Task2_FAQ_Chatbot/
│   ├── data/                   # FAQ knowledge base (faqs.json)
│   ├── src/                    # Preprocessing, TF-IDF vectorizer, matching engine
│   ├── static/                 # Glassmorphism cyber HUD styles & scripts
│   ├── templates/              # Interactive AI chat interface
│   ├── tests/                  # Pytest unit tests
│   ├── app.py                  # Flask web server
│   ├── cli.py                  # Interactive terminal chatbot
│   ├── evaluate.py             # Evaluation benchmark script
│   ├── requirements.txt        # Task dependencies
│   └── README.md               # In-depth task documentation
│
├── Task3_Music_Generation_AI/
│   ├── data/                   # Sample classical & jazz MIDI training data
│   ├── models/                 # Pretrained PyTorch LSTM weights (music_lstm.pth)
│   ├── outputs/                # Generated MIDI compositions
│   ├── src/                    # MIDI processor, LSTM model, trainer, generator
│   ├── static/                 # Interactive DAW styles, synth & piano roll
│   ├── templates/              # Web workstation UI
│   ├── tests/                  # Pytest unit tests
│   ├── app.py                  # Flask DAW studio
│   ├── requirements.txt        # Task dependencies
│   └── README.md               # In-depth task documentation
│
├── Task4_Object_Detection_Tracking/
│   ├── models/                 # Pretrained YOLOv8 weights (yolov8n.pt)
│   ├── sample_media/           # Sample traffic video & test images
│   ├── outputs/                # Rendered tracking videos & telemetry CSV logs
│   ├── src/                    # YOLO detector, SORT tracker, visualizer
│   ├── static/                 # Surveillance studio UI styles & scripts
│   ├── templates/              # Real-time web surveillance console
│   ├── tests/                  # Pytest tracking unit tests
│   ├── app.py                  # Flask live video surveillance server
│   ├── run_video.py            # Desktop OpenCV tracker with keyboard controls
│   ├── requirements.txt        # Task dependencies
│   └── README.md               # In-depth task documentation
│
├── static/
│   └── hub.css                 # Master design system styles
├── .gitignore                  # Git ignore rules for Python & caches
├── LICENSE                     # MIT License
└── README.md                   # Repository overview & index
```

---

## ⚡ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Sambit-Coding-2023/internshipprojects-codealpha-.git
cd internshipprojects-codealpha-
```

### 2. Environment Setup
Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install dependencies per task as needed:
```bash
# Task 1
pip install -r Task1_Language_Translation_Tool/requirements.txt

# Task 2
pip install -r Task2_FAQ_Chatbot/requirements.txt

# Task 3
pip install -r Task3_Music_Generation_AI/requirements.txt

# Task 4
pip install -r Task4_Object_Detection_Tracking/requirements.txt
```

---

## 👤 Author

* **Sambit Adhikary**
* **GitHub**: [@Sambit-Coding-2023](https://github.com/Sambit-Coding-2023)
* **Internship**: CodeAlpha Artificial Intelligence Internship

---

## 📄 License

This repository is licensed under the [MIT License](LICENSE).
