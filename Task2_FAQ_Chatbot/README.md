# ✅ TASK 2: Chatbot for FAQs

A complete, production-grade Natural Language Processing (NLP) FAQ Chatbot built for **CodeAlpha Task 2**. Implements text preprocessing with **NLTK**, semantic vector similarity with **TF-IDF & Cosine Similarity**, intent classification, and an interactive, modern web chat interface.

---

## 📋 Task 2 Requirements & Implementation

| # | Task Requirement (From Guidelines) | Project Implementation | Primary File(s) |
|---|---|---|---|
| **1** | **Collect FAQs related to a topic or product** (questions and their answers) | Curated structured e-commerce knowledgebase with 12 canonical questions, 60+ alternative training patterns, and category tags across Orders, Shipping, Returns, Payments, and Account Security. | [`data/faqs.json`](file:///d:/cdainternship/Task2_FAQ_Chatbot/data/faqs.json) |
| **2** | **Preprocess the text using NLP libraries like NLTK or SpaCy** (tokenize, clean, etc.) | Multi-stage NLTK text processing: Contraction expansion, punctuation stripping, tokenization (`word_tokenize`), stopword filtering (`stopwords.words('english')`), and dual-pass WordNet lemmatization with verb & noun POS tagging. | [`src/nlp_preprocessor.py`](file:///d:/cdainternship/Task2_FAQ_Chatbot/src/nlp_preprocessor.py) |
| **3** | **Match user questions with the most similar FAQ using techniques like cosine similarity or intent matching** | **TF-IDF Vectorizer** (unigram + bigram range) with **Cosine Similarity** matrix scoring. Enhanced with content-token gating and deterministic intent matching for conversational greetings, goodbyes, gratitude, and help. | [`src/matcher.py`](file:///d:/cdainternship/Task2_FAQ_Chatbot/src/matcher.py)<br>[`src/bot_engine.py`](file:///d:/cdainternship/Task2_FAQ_Chatbot/src/bot_engine.py) |
| **4** | **Display the best matching answer as a chatbot response** | Chatbot displays the top-ranked FAQ answer alongside match confidence percentage (`98% Match`), category tag (`[Orders]`), matched canonical question, and related alternative FAQ suggestions. | [`src/bot_engine.py`](file:///d:/cdainternship/Task2_FAQ_Chatbot/src/bot_engine.py)<br>[`static/js/chat.js`](file:///d:/cdainternship/Task2_FAQ_Chatbot/static/js/chat.js) |
| **5** | **Optional: Create a simple chat UI for user interaction** | Modern, responsive web chat interface built with vanilla HTML/CSS/JS and Flask. Features real-time typing indicators, predictive autocomplete, voice input (Speech-to-Text), dark/light mode toggle, and live FAQ search. | [`templates/index.html`](file:///d:/cdainternship/Task2_FAQ_Chatbot/templates/index.html)<br>[`static/css/style.css`](file:///d:/cdainternship/Task2_FAQ_Chatbot/static/css/style.css) |

---

## 🏆 Benchmark & Evaluation Results

An automated benchmark script ([`evaluate.py`](file:///d:/cdainternship/Task2_FAQ_Chatbot/evaluate.py)) evaluates 24 varied user queries against the FAQ corpus:

```
======================================================================
           FAQ CHATBOT ACCURACY & SIMILARITY BENCHMARK           
======================================================================
BENCHMARK SUMMARY RESULTS:
  * Total Test Queries:        24
  * Correctly Matched FAQs:    24/24 (100.0%)
  * High Confidence Matches:   24/24 (100.0%)
  * Average Confidence Score:  0.981
======================================================================
```

---

## 📁 Repository Structure

```
Task2_FAQ_Chatbot/
├── data/
│   ├── faqs.json               # Structured FAQ corpus with categories, questions, patterns, tags
│   └── users.db                # SQLite database for user accounts and active sessions
├── src/
│   ├── __init__.py
│   ├── auth.py                 # SQLite Auth manager with password hashing & session management
│   ├── creator_engine.py       # AI Image rendering, PowerPoint deck & PDF report generation
│   ├── knowledge_engine.py     # Universal DuckDuckGo & Wikipedia knowledge retrieval
│   ├── nlp_preprocessor.py     # NLTK tokenization, cleaning, stop words, WordNet lemmatization
│   ├── matcher.py              # TF-IDF + Cosine Similarity matching engine & predictive suggest
│   └── bot_engine.py           # Intent dispatch, FAQ matching, and action card formatting
├── static/
│   ├── css/style.css           # Modern, responsive styling with Dark & Light theme tokens
│   ├── js/app.js               # Main application controller, auth states, creation studio & UI
│   └── js/chat.js              # Web chat controller, Speech Recognition, and NLP inspector
├── templates/
│   └── index.html              # Clean modern Web UI with Auth modal, Task 2 Rubric & FAQ explorer
├── tests/
│   └── test_chatbot.py         # Pytest suite for preprocessing, matcher, and Flask endpoints
├── app.py                      # Flask HTTP Server, Auth endpoints & REST API routes
├── cli.py                      # Terminal-based interactive chatbot client
├── evaluate.py                 # Automated accuracy & similarity benchmark
├── requirements.txt            # Project Python dependencies
└── README.md                   # Project documentation
```

---

## 🔐 User Authentication & Account Management

The project includes a built-in user authentication and session management system:
- **Sign In & Sign Up Modal**: Toggle seamlessly between logging in and creating a new account.
- **Password Security**: Passwords are securely hashed using `werkzeug.security` (`generate_password_hash` / `check_password_hash`).
- **Database Persistence**: Backed by a local SQLite database (`data/users.db`) tracking user details, registration dates, roles, and active sessions.
- **REST Endpoints**:
  - `POST /api/auth/register` (Username, Email, Full Name, Password)
  - `POST /api/auth/login` (Username or Email, Password)
  - `POST /api/auth/logout` (Invalidates session cookie)
  - `GET /api/auth/me` (Current user profile state)
- **Pre-Seeded Demo Account**: Instant 1-click testing via the **"🚀 Quick Demo Login"** button:
  - **Username**: `demo_user`
  - **Password**: `demo123`
- **User Profile UI**:
  - Top navigation bar profile pill with dynamic avatar initial.
  - Interactive dropdown popover with quick profile details and logout action.
  - Full-screen glassmorphism **Account Profile Modal** showing member status, join date, email, and role.
  - Interactive sidebar user profile footer badge.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Accuracy Benchmark
```bash
python evaluate.py
```

### 3. Run the Automated Pytest Suite
```bash
python -m pytest tests/test_chatbot.py
```

### 4. Run the Terminal CLI Chatbot
```bash
python cli.py
```

### 5. Launch the Web Chatbot Application
```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:5000`**
