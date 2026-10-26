/**
 * LingoStudio AI — Interactive Translation Studio Controller
 * Production-ready real-time translation orchestrator with multi-engine routing,
 * Web Speech API dictation, dual-tier TTS audio synthesis, history persistence,
 * document imports, and keyboard shortcuts.
 */

(function (window, document) {
    'use strict';

    // =========================================================================
    // Application State
    // =========================================================================
    const state = {
        sourceLang: 'auto',
        targetLang: 'es',
        engine: 'auto',
        realtime: true,
        theme: 'dark',
        tone: 'default',
        cmdSelectedIndex: 0,
        cmdFilteredList: [],
        history: [],
        historySearchQuery: '',
        historyActiveFilter: 'all',
        deck: [],
        currentDeckIndex: 0,
        currentMode: 'dual',
        isRecording: false,
        recognition: null,
        activeRecognition: null,
        speechPrefix: '',
        hasCapturedSpeech: false,
        debounceTimer: null,
        currentAudio: null,
        lastTranslatedText: '',
        lastSourceText: '',
        lastTransliteration: '',
        lastSubtitleContent: null,
        detectedLangCode: null
    };

    // Safe localStorage loading
    try {
        state.theme = localStorage.getItem('lingostudio_theme') || 'dark';
        const rawHistory = localStorage.getItem('lingostudio_history');
        if (rawHistory) {
            state.history = JSON.parse(rawHistory);
            if (!Array.isArray(state.history)) state.history = [];
        }
        if (!state.history || state.history.length === 0) {
            state.history = [
                {
                    id: 'seed-1',
                    source: 'Hello, welcome to LingoStudio AI translation studio!',
                    target: '¡Hola, bienvenido al estudio de traducción LingoStudio AI!',
                    sourceLang: 'en',
                    targetLang: 'es',
                    engine: 'Google Neural Engine',
                    starred: true,
                    date: '10:00 AM'
                },
                {
                    id: 'seed-2',
                    source: 'Artificial intelligence enables seamless real-time multilingual communication.',
                    target: "L'intelligence artificielle permet une communication multilingue transparente en temps réel.",
                    sourceLang: 'en',
                    targetLang: 'fr',
                    engine: 'MyMemory Neural',
                    starred: false,
                    date: '10:15 AM'
                },
                {
                    id: 'seed-3',
                    source: 'Practice makes perfect in language mastery.',
                    target: 'Übung macht den Meister beim Sprachenlernen.',
                    sourceLang: 'en',
                    targetLang: 'de',
                    engine: 'Google Neural Engine',
                    starred: true,
                    date: '10:30 AM'
                }
            ];
            try { localStorage.setItem('lingostudio_history', JSON.stringify(state.history)); } catch (e) {}
        }
        const rawDeck = localStorage.getItem('lingostudio_deck');
        if (rawDeck) {
            state.deck = JSON.parse(rawDeck);
            if (!Array.isArray(state.deck)) state.deck = [];
        }
    } catch (e) {
        console.warn('Storage read warning:', e);
    }

    // Helper to get element by ID safely
    function el(id) {
        return document.getElementById(id);
    }

    // =========================================================================
    // Theme Management
    // =========================================================================
    function applyTheme(theme) {
        state.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem('lingostudio_theme', theme);
        } catch (e) {}
    }

    function toggleTheme() {
        const next = state.theme === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        showToast(`Switched to ${next} theme`, 'info');
    }

    // =========================================================================
    // Language Toolbar Sync & Management
    // =========================================================================
    function setupLanguageSelectors() {
        const srcSelect = el('sourceLangSelect');
        const tgtSelect = el('targetLangSelect');
        if (srcSelect && srcSelect.value) state.sourceLang = srcSelect.value;
        if (tgtSelect && tgtSelect.value) state.targetLang = tgtSelect.value;
        syncChipsWithSelects();
    }

    function syncChipsWithSelects() {
        const srcChips = el('sourceChips');
        if (srcChips) {
            srcChips.querySelectorAll('.chip').forEach(chip => {
                if (chip.getAttribute('data-lang') === state.sourceLang) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
        }

        const tgtChips = el('targetChips');
        if (tgtChips) {
            tgtChips.querySelectorAll('.chip').forEach(chip => {
                if (chip.getAttribute('data-lang') === state.targetLang) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
        }
    }

    function setSourceLanguage(code) {
        state.sourceLang = code;
        const select = el('sourceLangSelect');
        if (select) select.value = code;
        syncChipsWithSelects();
        triggerTranslationDebounced();
    }

    function setTargetLanguage(code) {
        state.targetLang = code;
        const select = el('targetLangSelect');
        if (select) select.value = code;
        syncChipsWithSelects();
        triggerTranslationDebounced();
    }

    function swapLanguages() {
        let newSource = state.targetLang;
        let newTarget = state.sourceLang === 'auto' ? (state.detectedLangCode || 'en') : state.sourceLang;
        if (newTarget === 'auto') newTarget = 'en';

        const outputArea = el('translationOutput');
        const inputArea = el('sourceTextInput');

        if (outputArea && inputArea) {
            const currentTranslation = outputArea.innerText.trim();
            const hasPlaceholder = outputArea.querySelector('.placeholder-text');
            if (currentTranslation && !hasPlaceholder) {
                inputArea.value = currentTranslation;
                updateCharCount();
            }
        }

        state.sourceLang = newSource;
        state.targetLang = newTarget;

        const srcSelect = el('sourceLangSelect');
        const tgtSelect = el('targetLangSelect');
        if (srcSelect) srcSelect.value = newSource;
        if (tgtSelect) tgtSelect.value = newTarget;

        syncChipsWithSelects();
        showToast(`Swapped: ${newSource.toUpperCase()} ⇄ ${newTarget.toUpperCase()}`, 'info');
        performTranslation(true);
    }

    // =========================================================================
    // Translation Execution & API
    // =========================================================================
    function triggerTranslationDebounced() {
        if (!state.realtime) return;
        clearTimeout(state.debounceTimer);
        state.debounceTimer = setTimeout(() => {
            performTranslation(false);
        }, 380);
    }

    async function performTranslation(isManual = false) {
        const textarea = el('sourceTextInput');
        const translateBtn = el('manualTranslateBtn');
        const text = textarea ? textarea.value.trim() : '';

        // If manual click on empty text: alert user
        if (!text) {
            if (isManual) {
                showToast('Please enter or dictate some text to translate first', 'info');
                if (textarea) textarea.focus();
            }
            clearOutput();
            return;
        }

        // Always read the live selected languages from DOM
        const srcSelect = el('sourceLangSelect');
        const tgtSelect = el('targetLangSelect');
        const engSelect = el('engineSelect');

        if (srcSelect) state.sourceLang = srcSelect.value;
        if (tgtSelect) state.targetLang = tgtSelect.value;
        if (engSelect) state.engine = engSelect.value;

        // Visual feedback on button
        if (translateBtn) {
            translateBtn.disabled = true;
            translateBtn.innerHTML = `
                <svg class="spin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                    <path d="M12 2a10 10 0 0 1 10 10"></path>
                </svg>
                <span>Translating...</span>
            `;
        }

        setLoading(true);

        const protectCode = el('protectCodeToggle') ? el('protectCodeToggle').checked : false;

        try {
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    source_lang: state.sourceLang,
                    target_lang: state.targetLang,
                    engine: state.engine,
                    protect_code: protectCode,
                    tone: state.tone || 'default'
                })
            });

            if (!response.ok) {
                throw new Error(`Server returned status ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                renderTranslationResult(data, text);

                if (translateBtn) {
                    translateBtn.innerHTML = `
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span>Translated!</span>
                    `;
                    setTimeout(() => {
                        restoreTranslateButton();
                    }, 1000);
                }

                if (isManual) {
                    showToast('Translation completed successfully!', 'success');
                }
            } else {
                showToast(data.error || 'Translation failed', 'error');
                restoreTranslateButton();
            }
        } catch (err) {
            console.error('Translation request error:', err);
            showToast('Unable to reach translation server. Please try again.', 'error');
            restoreTranslateButton();
        } finally {
            setLoading(false);
        }
    }

    function restoreTranslateButton() {
        const translateBtn = el('manualTranslateBtn');
        if (translateBtn) {
            translateBtn.disabled = false;
            translateBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
                <span>Translate Now</span>
                <span class="kbd-hint">Ctrl + Enter</span>
            `;
        }
    }

    function renderTranslationResult(data, sourceText) {
        state.lastTranslatedText = data.translated_text || '';
        state.lastSourceText = sourceText || '';

        const output = el('translationOutput');
        if (output) {
            if (data.translated_text) {
                output.textContent = data.translated_text;
            } else {
                output.innerHTML = '<span class="placeholder-text">Translation will appear here in real-time...</span>';
            }
        }

        // Render phonetic transliteration reading (if language has non-Latin script)
        const translitBar = el('translitBar');
        const translitText = el('translitText');
        if (translitBar && translitText) {
            if (data.transliteration) {
                translitText.textContent = data.transliteration;
                translitBar.style.display = 'flex';
                state.lastTransliteration = data.transliteration;
            } else {
                translitBar.style.display = 'none';
                state.lastTransliteration = '';
            }
        }

        // Reset verification card on fresh translation
        const verCard = el('verificationCard');
        if (verCard) verCard.style.display = 'none';

        // Render detected language badge
        const badge = el('detectedBadge');
        const badgeText = el('detectedLangText');
        if (data.detected_lang && (state.sourceLang === 'auto' || data.source_lang === 'auto')) {
            state.detectedLangCode = data.detected_lang;
            const conf = data.detected_confidence ? Math.round(data.detected_confidence * 100) : 95;
            if (badge && badgeText) {
                badgeText.textContent = `Detected: ${data.detected_lang_name || data.detected_lang.toUpperCase()} (${conf}%)`;
                badge.style.display = 'inline-flex';
            }
        } else if (badge) {
            badge.style.display = 'none';
        }

        // Render engine badge
        const engBadge = el('engineUsedBadge');
        const engText = el('engineBadgeText');
        if (engBadge && engText) {
            engText.textContent = data.engine_used || 'Neural Engine';
            engBadge.style.display = 'inline-flex';
        }

        // Render latency tag
        const latencyTag = el('translationLatencyTag');
        if (latencyTag) {
            const ms = Math.round(data.latency_ms || 45);
            latencyTag.textContent = `${ms}ms`;
        }

        // Auto-save to history
        recordHistoryItem({
            source: sourceText,
            target: data.translated_text,
            sourceLang: data.detected_lang || state.sourceLang,
            targetLang: state.targetLang,
            engine: data.engine_used || state.engine
        });

        // Live text analytics
        if (data.analytics) {
            renderAnalytics(data.analytics);
        }

        // Dictionary lookup for single words
        checkDictionaryLookup(sourceText);
    }

    function clearOutput() {
        const output = el('translationOutput');
        if (output) {
            output.innerHTML = '<span class="placeholder-text">Translation will appear here in real-time...</span>';
        }
        const badge = el('detectedBadge');
        if (badge) badge.style.display = 'none';
        const engBadge = el('engineUsedBadge');
        if (engBadge) engBadge.style.display = 'none';
        const latency = el('translationLatencyTag');
        if (latency) latency.textContent = 'Ready';
        const dict = el('dictionaryCard');
        if (dict) dict.style.display = 'none';
        const translit = el('translitBar');
        if (translit) translit.style.display = 'none';
        const verCard = el('verificationCard');
        if (verCard) verCard.style.display = 'none';
        state.lastTranslatedText = '';

        const wordsEl = el('analyticsWords');
        if (wordsEl) wordsEl.textContent = '0 words';
        const readTimeEl = el('analyticsReadTime');
        if (readTimeEl) readTimeEl.textContent = '0s read';
        const speakTimeEl = el('analyticsSpeakTime');
        if (speakTimeEl) speakTimeEl.textContent = '0s speak';
        const cefrEl = el('analyticsCefr');
        if (cefrEl) cefrEl.textContent = 'CEFR A1';
    }

    function clearSourceInput() {
        if (state.isRecording) {
            stopRecording(false);
        }
        const textarea = el('sourceTextInput');
        if (textarea) {
            textarea.value = '';
            textarea.focus();
        }
        updateCharCount();
        clearOutput();
    }

    function setLoading(isLoading) {
        const overlay = el('loadingOverlay');
        if (overlay) {
            if (isLoading) {
                overlay.classList.add('active');
            } else {
                overlay.classList.remove('active');
            }
        }
    }

    function updateCharCount() {
        const textarea = el('sourceTextInput');
        const counter = el('sourceCharCount');
        const text = textarea ? textarea.value : '';
        const len = text.length;
        if (counter) {
            counter.textContent = `${len.toLocaleString()} / 5,000`;
        }

        // Live heuristics for analytics strip
        const trimmed = text.trim();
        const words = trimmed ? trimmed.split(/\s+/).filter(Boolean).length : 0;
        const readTimeSec = Math.max(1, Math.round(words / (200 / 60))); // ~200 WPM
        const speakTimeSec = Math.max(1, Math.round(words / (140 / 60))); // ~140 WPM

        const wordsEl = el('analyticsWords');
        const readTimeEl = el('analyticsReadTime');
        const speakTimeEl = el('analyticsSpeakTime');
        const cefrEl = el('analyticsCefr');

        if (wordsEl) wordsEl.textContent = `${words.toLocaleString()} words`;
        if (readTimeEl) readTimeEl.textContent = words > 0 ? (readTimeSec < 60 ? `${readTimeSec}s read` : `${Math.ceil(readTimeSec / 60)}m read`) : '0s read';
        if (speakTimeEl) speakTimeEl.textContent = words > 0 ? (speakTimeSec < 60 ? `${speakTimeSec}s speak` : `${Math.ceil(speakTimeSec / 60)}m speak`) : '0s speak';
        if (cefrEl && !trimmed) cefrEl.textContent = 'CEFR A1';
    }

    function renderAnalytics(analytics) {
        if (!analytics) return;
        const wordsEl = el('analyticsWords');
        const readTimeEl = el('analyticsReadTime');
        const speakTimeEl = el('analyticsSpeakTime');
        const cefrEl = el('analyticsCefr');

        if (wordsEl && analytics.words !== undefined) wordsEl.textContent = `${analytics.words.toLocaleString()} words`;
        if (readTimeEl && analytics.reading_time_sec !== undefined) {
            const sec = analytics.reading_time_sec;
            readTimeEl.textContent = sec < 60 ? `${sec}s read` : `${Math.ceil(sec / 60)}m read`;
        }
        if (speakTimeEl && analytics.speaking_time_sec !== undefined) {
            const sec = analytics.speaking_time_sec;
            speakTimeEl.textContent = sec < 60 ? `${sec}s speak` : `${Math.ceil(sec / 60)}m speak`;
        }
        if (cefrEl && analytics.cefr_level) {
            cefrEl.textContent = `CEFR ${analytics.cefr_level}`;
        }
    }

    // =========================================================================
    // Dictionary & Synonyms
    // =========================================================================
    async function checkDictionaryLookup(text) {
        const clean = text.trim();
        const words = clean.split(/\s+/);
        const card = el('dictionaryCard');

        if (words.length !== 1 || clean.length < 2 || clean.length > 30) {
            if (card) card.style.display = 'none';
            return;
        }

        try {
            const res = await fetch('/api/dictionary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ word: clean })
            });
            const result = await res.json();
            if (result.success && result.data) {
                renderDictionaryCard(result.data);
            } else if (card) {
                card.style.display = 'none';
            }
        } catch (e) {
            if (card) card.style.display = 'none';
        }
    }

    function renderDictionaryCard(data) {
        const card = el('dictionaryCard');
        const wordEl = el('dictWord');
        const phonEl = el('dictPhonetic');
        const contentEl = el('dictContent');

        if (!card || !contentEl) return;

        if (wordEl) wordEl.textContent = data.word;
        if (phonEl) phonEl.textContent = data.phonetic || '';

        let html = '';
        if (data.meanings && data.meanings.length > 0) {
            data.meanings.forEach(m => {
                html += `<div class="dict-part">${escapeHtml(m.partOfSpeech || 'definition')}</div>`;
                if (m.definitions && m.definitions.length > 0) {
                    m.definitions.forEach(d => {
                        html += `<div class="dict-def">• ${escapeHtml(d)}</div>`;
                    });
                }
                if (m.synonyms && m.synonyms.length > 0) {
                    html += `<div class="dict-synonyms">`;
                    m.synonyms.forEach(s => {
                        html += `<span class="synonym-pill">${escapeHtml(s)}</span>`;
                    });
                    html += `</div>`;
                }
            });
        }

        contentEl.innerHTML = html;
        card.style.display = 'block';
    }

    // =========================================================================
    // Speech Recognition (Speech-to-Text Voice Dictation)
    // =========================================================================
    const SPEECH_LOCALE_MAP = {
        'auto': 'en-US',
        'en': 'en-US',
        'es': 'es-ES',
        'fr': 'fr-FR',
        'de': 'de-DE',
        'hi': 'hi-IN',
        'zh': 'zh-CN',
        'zh-CN': 'zh-CN',
        'zh-TW': 'zh-TW',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'ar': 'ar-SA',
        'ru': 'ru-RU',
        'pt': 'pt-PT',
        'it': 'it-IT',
        'nl': 'nl-NL',
        'tr': 'tr-TR',
        'pl': 'pl-PL',
        'sv': 'sv-SE',
        'id': 'id-ID',
        'vi': 'vi-VN',
        'th': 'th-TH',
        'el': 'el-GR',
        'cs': 'cs-CZ',
        'da': 'da-DK',
        'fi': 'fi-FI',
        'no': 'no-NO',
        'hu': 'hu-HU',
        'ro': 'ro-RO',
        'uk': 'uk-UA',
        'he': 'he-IL',
        'bn': 'bn-BD',
        'te': 'te-IN',
        'ta': 'ta-IN',
        'mr': 'mr-IN',
        'gu': 'gu-IN',
        'kn': 'kn-IN',
        'ml': 'ml-IN',
        'pa': 'pa-IN',
        'ur': 'ur-PK',
        'fa': 'fa-IR',
        'ms': 'ms-MY',
        'tl': 'fil-PH',
        'af': 'af-ZA',
        'sq': 'sq-AL',
        'am': 'am-ET',
        'hy': 'hy-AM',
        'az': 'az-AZ',
        'eu': 'eu-ES',
        'be': 'be-BY',
        'bs': 'bs-BA',
        'bg': 'bg-BG',
        'ca': 'ca-ES',
        'hr': 'hr-HR',
        'et': 'et-EE',
        'gl': 'gl-ES',
        'ka': 'ka-GE',
        'is': 'is-IS',
        'ga': 'ga-IE',
        'kk': 'kk-KZ',
        'lv': 'lv-LV',
        'lt': 'lt-LT',
        'mk': 'mk-MK',
        'mn': 'mn-MN',
        'ne': 'ne-NP',
        'sr': 'sr-RS',
        'si': 'si-LK',
        'sk': 'sk-SK',
        'sl': 'sl-SI',
        'sw': 'sw-KE',
        'cy': 'cy-GB',
        'yi': 'yi-001',
        'zu': 'zu-ZA',
        'la': 'la'
    };

    function getSpeechLocale(langCode) {
        if (!langCode || langCode === 'auto') {
            return navigator.language || 'en-US';
        }
        const cleaned = langCode.trim();
        if (SPEECH_LOCALE_MAP[cleaned]) {
            return SPEECH_LOCALE_MAP[cleaned];
        }
        if (cleaned.includes('-')) {
            return cleaned;
        }
        return `${cleaned}-${cleaned.toUpperCase()}`;
    }

    function checkSpeechRecognitionSupport() {
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    }

    function setupSpeechRecognition() {
        const supported = checkSpeechRecognitionSupport();
        const mic = el('micBtn');
        if (mic) {
            if (!supported) {
                mic.title = "Voice dictation not supported in this browser (Works in Chrome, Edge, and Safari)";
            } else {
                mic.title = "Voice Dictation (Ctrl+Shift+D) — Click to speak";
            }
        }
    }

    let lastDictateToggleTime = 0;

    function toggleRecording(e) {
        if (e && typeof e.preventDefault === 'function') {
            e.preventDefault();
        }

        // Debounce rapid double-fires (e.g. from multiple event triggers)
        const now = Date.now();
        if (now - lastDictateToggleTime < 350) {
            return;
        }
        lastDictateToggleTime = now;

        if (state.isRecording) {
            stopRecording(true);
        } else {
            startRecording();
        }
    }

    function startRecording() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            showToast('Voice dictation is supported in Google Chrome, Microsoft Edge, and Safari.', 'error');
            return;
        }

        // Microphone access warning for non-secure HTTP origins
        if (window.isSecureContext === false && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            showToast('Microphone access requires HTTPS or localhost.', 'error');
            return;
        }

        // Stop any currently running recognition cleanly
        if (state.activeRecognition) {
            try { state.activeRecognition.abort(); } catch (e) {}
            state.activeRecognition = null;
        }

        try {
            const recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;

            const chosenLang = state.sourceLang === 'auto'
                ? (state.detectedLangCode || 'en')
                : state.sourceLang;
            recognition.lang = getSpeechLocale(chosenLang);

            const input = el('sourceTextInput');
            const initialText = input ? input.value : '';
            state.speechPrefix = initialText ? initialText.trimEnd() + ' ' : '';
            state.hasCapturedSpeech = false;

            recognition.onstart = () => {
                state.isRecording = true;
                state.activeRecognition = recognition;
                const mic = el('micBtn');
                const micTxt = el('micBtnText');
                if (mic) {
                    mic.classList.add('recording');
                    const eq = mic.querySelector('.audio-equalizer');
                    if (eq) eq.style.display = 'inline-flex';
                }
                if (micTxt) micTxt.textContent = 'Listening...';
                showToast(`Microphone active (${recognition.lang}) — speak now`, 'info');
            };

            recognition.onresult = (event) => {
                let sessionFinal = '';
                let sessionInterim = '';

                for (let i = 0; i < event.results.length; ++i) {
                    const res = event.results[i];
                    if (res.isFinal) {
                        sessionFinal += res[0].transcript + ' ';
                    } else {
                        sessionInterim += res[0].transcript;
                    }
                }

                if (sessionFinal || sessionInterim) {
                    state.hasCapturedSpeech = true;
                }

                if (input) {
                    const fullText = (state.speechPrefix + sessionFinal + sessionInterim).trimStart();
                    input.value = fullText;
                    updateCharCount();
                }
            };

            recognition.onerror = (event) => {
                console.warn('Speech recognition error event:', event.error);
                if (event.error === 'no-speech') {
                    // Normal pause in speaking, do not abort
                    return;
                }

                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    showToast('Microphone blocked. Please allow microphone permission in your browser address bar.', 'error');
                } else if (event.error === 'network') {
                    showToast('Speech service network issue. Please check your internet connection.', 'error');
                } else if (event.error === 'audio-capture') {
                    showToast('No microphone detected. Please plug in or enable an audio input device.', 'error');
                } else if (event.error === 'language-not-supported') {
                    showToast(`Language ${recognition.lang} not supported for voice dictation. Defaulting to English.`, 'info');
                    try {
                        recognition.lang = 'en-US';
                        recognition.start();
                        return;
                    } catch (e) {}
                } else if (event.error !== 'aborted') {
                    showToast(`Voice error: ${event.error}`, 'error');
                }

                stopRecording(false);
            };

            recognition.onend = () => {
                const hadSession = state.isRecording;
                stopRecording(false);

                if (hadSession && state.hasCapturedSpeech) {
                    showToast('Dictation captured! Translating...', 'success');
                    performTranslation(true);
                }
            };

            recognition.start();
        } catch (err) {
            console.error('Failed to start speech recognition:', err);
            showToast('Unable to start microphone dictation. Please try again.', 'error');
            stopRecording(false);
        }
    }

    function stopRecording(userInitiated = false) {
        state.isRecording = false;

        if (state.activeRecognition) {
            const rec = state.activeRecognition;
            state.activeRecognition = null;
            try {
                if (userInitiated) {
                    rec.stop();
                } else {
                    rec.abort();
                }
            } catch (e) {}
        }

        const mic = el('micBtn');
        const micTxt = el('micBtnText');
        if (mic) {
            mic.classList.remove('recording');
            const eq = mic.querySelector('.audio-equalizer');
            if (eq) eq.style.display = 'none';
        }
        if (micTxt) micTxt.textContent = 'Dictate';
    }

    // =========================================================================
    // Speech Synthesis (Text-to-Speech)
    // =========================================================================
    function listenSource() {
        const textarea = el('sourceTextInput');
        const text = textarea ? textarea.value.trim() : '';
        const lang = state.detectedLangCode || (state.sourceLang === 'auto' ? 'en' : state.sourceLang);
        playSpeech(text, lang, el('sourceTtsBtn'), null, '');
    }

    function listenTarget() {
        const output = el('translationOutput');
        const text = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        playSpeech(text, state.targetLang, el('targetTtsBtn'), el('targetTtsBtnText'), 'Listen');
    }

    async function playSpeech(text, langCode, buttonElement, buttonTextElement, defaultLabel) {
        if (!text || !text.trim()) {
            showToast('No text available for speech synthesis', 'info');
            return;
        }

        const eq = buttonElement ? buttonElement.querySelector('.audio-equalizer') : null;

        if (state.currentAudio && !state.currentAudio.paused) {
            state.currentAudio.pause();
            state.currentAudio = null;
            if (buttonTextElement) buttonTextElement.textContent = defaultLabel;
            if (eq) eq.style.display = 'none';
            return;
        }

        // Hide any previously active equalizers
        document.querySelectorAll('.card-footer .audio-equalizer').forEach(el => el.style.display = 'none');

        if (buttonTextElement) buttonTextElement.textContent = 'Playing...';
        if (eq) eq.style.display = 'inline-flex';

        try {
            // Primary: High-fidelity MP3 synthesis from server
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, lang: langCode })
            });

            if (response.ok) {
                const blob = await response.blob();
                const audioUrl = URL.createObjectURL(blob);
                const audio = new Audio(audioUrl);
                state.currentAudio = audio;

                audio.onended = () => {
                    if (buttonTextElement) buttonTextElement.textContent = defaultLabel;
                    if (eq) eq.style.display = 'none';
                    state.currentAudio = null;
                    URL.revokeObjectURL(audioUrl);
                };

                audio.onerror = () => {
                    if (eq) eq.style.display = 'none';
                    fallbackClientSpeech(text, langCode, buttonElement, buttonTextElement, defaultLabel);
                };

                await audio.play();
                return;
            }
        } catch (e) {
            console.warn('Server TTS unavailable, using native speech:', e);
        }

        fallbackClientSpeech(text, langCode, buttonElement, buttonTextElement, defaultLabel);
    }

    function fallbackClientSpeech(text, langCode, buttonElement, buttonTextElement, defaultLabel) {
        const eq = buttonElement ? buttonElement.querySelector('.audio-equalizer') : null;
        if (eq) eq.style.display = 'inline-flex';

        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = langCode || 'en';
            utterance.onend = () => {
                if (buttonTextElement) buttonTextElement.textContent = defaultLabel;
                if (eq) eq.style.display = 'none';
            };
            utterance.onerror = () => {
                if (buttonTextElement) buttonTextElement.textContent = defaultLabel;
                if (eq) eq.style.display = 'none';
            };
            window.speechSynthesis.speak(utterance);
        } else {
            showToast('Audio playback not supported in this browser', 'error');
            if (buttonTextElement) buttonTextElement.textContent = defaultLabel;
            if (eq) eq.style.display = 'none';
        }
    }

    // =========================================================================
    // Copy, Bookmark & Export Features
    // =========================================================================
    async function copyTranslation() {
        const output = el('translationOutput');
        const text = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        if (!text || (output && output.querySelector('.placeholder-text'))) {
            showToast('No translation to copy', 'info');
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
            const copyTxt = el('copyBtnText');
            if (copyTxt) copyTxt.textContent = 'Copied!';
            showToast('Translation copied to clipboard!', 'success');
            setTimeout(() => {
                if (copyTxt) copyTxt.textContent = 'Copy';
            }, 2000);
        } catch (err) {
            showToast('Failed to copy to clipboard', 'error');
        }
    }

    function bookmarkCurrentTranslation() {
        const output = el('translationOutput');
        const text = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        if (!text || (output && output.querySelector('.placeholder-text'))) {
            showToast('Translate something first to save it', 'info');
            return;
        }

        const input = el('sourceTextInput');
        const source = input ? input.value.trim() : '';

        recordHistoryItem({
            source: source,
            target: text,
            sourceLang: state.detectedLangCode || state.sourceLang,
            targetLang: state.targetLang,
            engine: state.engine,
            starred: true
        });

        showToast('Saved to your translation history!', 'success');
    }

    function downloadFile(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function exportAsText() {
        const output = el('translationOutput');
        const target = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        const input = el('sourceTextInput');
        const source = input ? input.value.trim() : '';
        if (!target) return showToast('No translation to export', 'info');

        const content = `LingoStudio AI Translation Export\n` +
            `Timestamp: ${new Date().toISOString()}\n` +
            `Pair: ${state.sourceLang.toUpperCase()} -> ${state.targetLang.toUpperCase()}\n\n` +
            `[Source Text]:\n${source}\n\n` +
            `[Translation]:\n${target}\n`;

        downloadFile(content, `translation_${state.targetLang}.txt`, 'text/plain;charset=utf-8');
        showToast('Exported text file', 'success');
    }

    function exportAsJson() {
        const output = el('translationOutput');
        const target = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        const input = el('sourceTextInput');
        const source = input ? input.value.trim() : '';
        if (!target) return showToast('No translation to export', 'info');

        const payload = {
            app: 'LingoStudio AI',
            timestamp: new Date().toISOString(),
            source_language: state.sourceLang,
            target_language: state.targetLang,
            source_text: source,
            translated_text: target,
            engine: state.engine
        };

        downloadFile(JSON.stringify(payload, null, 2), `translation_${state.targetLang}.json`, 'application/json');
        showToast('Exported JSON package', 'success');
    }

    async function exportAsMp3() {
        const output = el('translationOutput');
        const text = state.lastTranslatedText || (output ? output.innerText.trim() : '');
        if (!text) return showToast('No translation to export as audio', 'info');

        showToast('Synthesizing high-quality MP3 audio...', 'info');
        try {
            const res = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, lang: state.targetLang })
            });

            if (!res.ok) throw new Error('Audio generation failed');

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `speech_${state.targetLang}.mp3`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('Downloaded audio MP3', 'success');
        } catch (err) {
            showToast('Failed to download speech MP3', 'error');
        }
    }

    // =========================================================================
    // History Persistence & Operative Drawer
    // =========================================================================
    function recordHistoryItem(item) {
        if (!item.source || !item.target) return;

        if (state.history.length > 0) {
            const last = state.history[0];
            if (last.source === item.source && last.target === item.target && last.targetLang === item.targetLang) {
                return;
            }
        }

        const entry = {
            id: Date.now().toString(),
            source: item.source,
            target: item.target,
            sourceLang: item.sourceLang || 'auto',
            targetLang: item.targetLang,
            engine: item.engine || 'Neural',
            starred: !!item.starred,
            date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        state.history.unshift(entry);
        if (state.history.length > 60) state.history.pop();
        try {
            localStorage.setItem('lingostudio_history', JSON.stringify(state.history));
        } catch (e) {}

        updateHistoryBadge();
        updateHistorySubtitle();
        renderHistoryList();
    }

    function updateHistoryBadge() {
        const badge = el('historyBadge');
        if (badge) {
            badge.textContent = state.history.length;
        }
    }

    function updateHistorySubtitle() {
        const sub = el('historySubtitle');
        if (sub) {
            const total = state.history.length;
            const starred = state.history.filter(h => h.starred).length;
            sub.textContent = `${total} translation${total === 1 ? '' : 's'} recorded (${starred} starred)`;
        }
    }

    function getFilteredHistory() {
        const q = (state.historySearchQuery || '').toLowerCase().trim();
        return state.history.filter(item => {
            if (state.historyActiveFilter === 'starred' && !item.starred) {
                return false;
            }
            if (!q) return true;
            return (item.source && item.source.toLowerCase().includes(q)) ||
                   (item.target && item.target.toLowerCase().includes(q)) ||
                   (item.sourceLang && item.sourceLang.toLowerCase().includes(q)) ||
                   (item.targetLang && item.targetLang.toLowerCase().includes(q)) ||
                   (item.engine && item.engine.toLowerCase().includes(q));
        });
    }

    function renderHistoryList() {
        const list = el('historyList');
        if (!list) return;

        const filtered = getFilteredHistory();

        if (state.history.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px;opacity:0.4;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <div><strong>No translation history yet</strong></div>
                    <div style="font-size:0.8rem;margin-top:4px;">Translations you perform in the studio are automatically recorded here.</div>
                </div>`;
            return;
        }

        if (filtered.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div>No results found for "${escapeHtml(state.historySearchQuery)}"</div>
                    <div style="font-size:0.8rem;margin-top:4px;">Try searching for a different keyword or language code.</div>
                </div>`;
            return;
        }

        let html = '';
        filtered.forEach(item => {
            html += `
            <div class="history-card" data-id="${item.id}" role="button" tabindex="0" title="Click to restore this translation in studio">
                <div class="history-card-header">
                    <div class="history-pair-badge">
                        <span class="history-lang-src">${escapeHtml((item.sourceLang || 'auto').toUpperCase())}</span>
                        <span class="history-arrow">→</span>
                        <span class="history-lang-tgt">${escapeHtml((item.targetLang || 'es').toUpperCase())}</span>
                        ${item.engine ? `<span class="history-engine-tag">${escapeHtml(item.engine)}</span>` : ''}
                    </div>
                    <div class="history-meta-right">
                        <span class="history-time">${escapeHtml(item.date)}</span>
                        <button type="button" class="hist-star-btn ${item.starred ? 'active' : ''}" data-star-id="${item.id}" title="${item.starred ? 'Remove Star' : 'Star & Add to Study Deck'}">
                            ★
                        </button>
                    </div>
                </div>
                <div class="history-text-group">
                    <div class="history-source-row">
                        <span class="hist-label">SRC</span>
                        <div class="history-source-text">${escapeHtml(item.source)}</div>
                    </div>
                    <div class="history-target-row">
                        <span class="hist-label">TGT</span>
                        <div class="history-target-text">${escapeHtml(item.target)}</div>
                    </div>
                </div>
                <div class="history-card-footer">
                    <button type="button" class="hist-action-btn restore-btn" data-restore-id="${item.id}" title="Load in Studio & Translate">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>
                        <span>Restore</span>
                    </button>
                    <button type="button" class="hist-action-btn copy-btn" data-copy-id="${item.id}" title="Copy Translation">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        <span>Copy</span>
                    </button>
                    <button type="button" class="hist-action-btn listen-btn" data-listen-id="${item.id}" title="Listen to Translation">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
                        <span>Listen</span>
                    </button>
                    <button type="button" class="hist-action-btn delete-btn" data-delete-id="${item.id}" title="Delete Record">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>`;
        });

        list.innerHTML = html;

        // Attach action handlers
        list.querySelectorAll('.history-card').forEach(card => {
            const id = card.getAttribute('data-id');
            card.addEventListener('click', (e) => {
                if (e.target.closest('button')) return;
                restoreHistoryItem(id);
            });
        });

        list.querySelectorAll('[data-restore-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                restoreHistoryItem(btn.getAttribute('data-restore-id'));
            });
        });

        list.querySelectorAll('[data-copy-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                copyHistoryItem(btn.getAttribute('data-copy-id'));
            });
        });

        list.querySelectorAll('[data-listen-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                listenHistoryItem(btn.getAttribute('data-listen-id'));
            });
        });

        list.querySelectorAll('[data-delete-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteHistoryItem(btn.getAttribute('data-delete-id'));
            });
        });

        list.querySelectorAll('[data-star-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleHistoryStar(btn.getAttribute('data-star-id'));
            });
        });
    }

    function restoreHistoryItem(id) {
        const found = state.history.find(h => h.id === id);
        if (!found) return;

        const input = el('sourceTextInput');
        if (input) {
            input.value = found.source;
            updateCharCount();
        }

        if (found.sourceLang && found.sourceLang !== 'auto') {
            setSourceLanguage(found.sourceLang);
        }
        if (found.targetLang) {
            setTargetLanguage(found.targetLang);
        }

        closeHistoryDrawer();
        performTranslation(true);

        // Smooth scroll to studio input
        if (input) {
            input.focus();
            input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        showToast(`Restored "${found.source.substring(0, 28)}..." to studio! 🚀`, 'success');
    }

    function copyHistoryItem(id) {
        const found = state.history.find(h => h.id === id);
        if (!found || !found.target) return;
        navigator.clipboard.writeText(found.target).then(() => {
            showToast('Copied translation to clipboard!', 'success');
        }).catch(() => {
            showToast('Unable to copy translation', 'error');
        });
    }

    function listenHistoryItem(id) {
        const found = state.history.find(h => h.id === id);
        if (!found || !found.target) return;
        playSpeech(found.target, found.targetLang, null, null, '');
    }

    function deleteHistoryItem(id) {
        const idx = state.history.findIndex(h => h.id === id);
        if (idx !== -1) {
            state.history.splice(idx, 1);
            try {
                localStorage.setItem('lingostudio_history', JSON.stringify(state.history));
            } catch (e) {}
            updateHistoryBadge();
            updateHistorySubtitle();
            renderHistoryList();
            showToast('Item deleted from history', 'info');
        }
    }

    function toggleHistoryStar(id) {
        const item = state.history.find(h => h.id === id);
        if (!item) return;

        item.starred = !item.starred;
        try {
            localStorage.setItem('lingostudio_history', JSON.stringify(state.history));
        } catch (e) {}

        // Sync with flashcard deck
        if (item.starred) {
            const exists = state.deck.some(d => d.source === item.source && d.target === item.target);
            if (!exists) {
                state.deck.unshift({
                    id: Date.now().toString(),
                    source: item.source,
                    target: item.target,
                    sourceLang: item.sourceLang,
                    targetLang: item.targetLang,
                    transliteration: '',
                    dateAdded: new Date().toLocaleDateString()
                });
                saveDeckToStorage();
                updateDeckBadge();
                showToast('Starred and saved to Flashcard Study Deck! ⭐', 'success');
            } else {
                showToast('Starred item in history! ⭐', 'success');
            }
        } else {
            showToast('Removed star from history item', 'info');
        }

        updateHistorySubtitle();
        renderHistoryList();
    }

    function exportHistoryCsv() {
        if (!state.history || state.history.length === 0) {
            showToast('No history records to export', 'info');
            return;
        }

        let csv = 'Source Text,Translated Text,Source Language,Target Language,Engine,Date\n';
        state.history.forEach(item => {
            const src = `"${(item.source || '').replace(/"/g, '""')}"`;
            const tgt = `"${(item.target || '').replace(/"/g, '""')}"`;
            csv += `${src},${tgt},${item.sourceLang},${item.targetLang},${item.engine || 'Neural'},${item.date}\n`;
        });

        downloadFile(csv, `lingostudio_history_${Date.now()}.csv`, 'text/csv;charset=utf-8');
        showToast('Exported history as CSV file!', 'success');
    }

    let lastHistoryToggleTime = 0;
    function toggleHistoryDrawer(e) {
        if (e && typeof e.preventDefault === 'function') {
            e.preventDefault();
        }
        const now = Date.now();
        if (now - lastHistoryToggleTime < 250) {
            return;
        }
        lastHistoryToggleTime = now;

        const drawer = el('historyDrawer');
        if (drawer && drawer.classList.contains('open')) {
            closeHistoryDrawer();
        } else {
            openHistoryDrawer();
        }
    }

    function openHistoryDrawer() {
        renderHistoryList();
        updateHistorySubtitle();
        const drawer = el('historyDrawer');
        const backdrop = el('historyDrawerBackdrop');
        if (drawer) {
            drawer.classList.add('open');
            drawer.setAttribute('aria-hidden', 'false');
        }
        if (backdrop) {
            backdrop.classList.add('active');
        }

        const searchInput = el('historySearchInput');
        if (searchInput) {
            searchInput.value = state.historySearchQuery || '';
            setTimeout(() => searchInput.focus(), 150);
        }
    }

    function closeHistoryDrawer() {
        const drawer = el('historyDrawer');
        const backdrop = el('historyDrawerBackdrop');
        if (drawer) {
            drawer.classList.remove('open');
            drawer.setAttribute('aria-hidden', 'true');
        }
        if (backdrop) {
            backdrop.classList.remove('active');
        }
    }

    function clearAllHistory() {
        if (state.history.length === 0) {
            showToast('History is already empty', 'info');
            return;
        }
        if (confirm('Are you sure you want to clear all translation history?')) {
            state.history = [];
            try {
                localStorage.removeItem('lingostudio_history');
            } catch (e) {}
            updateHistoryBadge();
            updateHistorySubtitle();
            renderHistoryList();
            showToast('All translation history cleared', 'info');
        }
    }

    function setupHistoryControls() {
        const searchInput = el('historySearchInput');
        const searchClear = el('historySearchClear');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                state.historySearchQuery = e.target.value;
                if (searchClear) {
                    searchClear.style.display = e.target.value ? 'block' : 'none';
                }
                renderHistoryList();
            });
        }

        if (searchClear) {
            searchClear.addEventListener('click', () => {
                state.historySearchQuery = '';
                if (searchInput) searchInput.value = '';
                searchClear.style.display = 'none';
                renderHistoryList();
                if (searchInput) searchInput.focus();
            });
        }

        const filterChips = el('historyFilterChips');
        if (filterChips) {
            filterChips.querySelectorAll('.history-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    const filter = chip.getAttribute('data-filter') || 'all';
                    state.historyActiveFilter = filter;
                    filterChips.querySelectorAll('.history-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    renderHistoryList();
                });
            });
        }

        const exportBtn = el('exportHistoryBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportHistoryCsv);
        }

        const backdrop = el('historyDrawerBackdrop');
        if (backdrop) {
            backdrop.addEventListener('click', closeHistoryDrawer);
        }
    }

    // =========================================================================
    // Fullscreen Presentation Mode
    // =========================================================================
    function openFullscreen() {
        const input = el('sourceTextInput');
        const output = el('translationOutput');
        const source = input ? input.value.trim() : '';
        const target = state.lastTranslatedText || (output ? output.innerText.trim() : '');

        if (!target || (output && output.querySelector('.placeholder-text'))) {
            showToast('No translation to display in fullscreen', 'info');
            return;
        }

        const fsSource = el('fsSourceText');
        const fsTarget = el('fsTargetText');
        if (fsSource) fsSource.textContent = source;
        if (fsTarget) fsTarget.textContent = target;

        const view = el('fullscreenView');
        if (view) {
            view.classList.add('open');
            view.setAttribute('aria-hidden', 'false');
        }
    }

    function closeFullscreen() {
        const view = el('fullscreenView');
        if (view) {
            view.classList.remove('open');
            view.setAttribute('aria-hidden', 'true');
        }
    }

    // =========================================================================
    // Shortcuts Modal
    // =========================================================================
    function openShortcutsModal() {
        const modal = el('shortcutsModal');
        if (modal) {
            modal.classList.add('open');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    function closeShortcutsModal() {
        const modal = el('shortcutsModal');
        if (modal) {
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    // =========================================================================
    // Toast Notifications
    // =========================================================================
    function showToast(message, type = 'info') {
        const container = el('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icon = type === 'success' ? '✓' : (type === 'error' ? '⚠️' : 'ℹ️');
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 300);
        }, 3200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // =========================================================================
    // Event Listeners Setup
    // =========================================================================
    function setupEventListeners() {
        // Theme toggle
        const themeBtn = el('themeToggleBtn');
        if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

        // Engine selector
        const engSelect = el('engineSelect');
        if (engSelect) {
            engSelect.addEventListener('change', (e) => {
                state.engine = e.target.value;
                showToast(`Routing set to ${engSelect.options[engSelect.selectedIndex].text}`, 'info');
                performTranslation(true);
            });
        }

        // Textarea input
        const textarea = el('sourceTextInput');
        if (textarea) {
            textarea.addEventListener('input', () => {
                updateCharCount();
                triggerTranslationDebounced();
            });
        }

        // Clear input button
        const clearBtn = el('clearInputBtn');
        if (clearBtn) clearBtn.addEventListener('click', clearSourceInput);

        // Language Select dropdowns
        const srcSelect = el('sourceLangSelect');
        if (srcSelect) {
            srcSelect.addEventListener('change', (e) => setSourceLanguage(e.target.value));
        }

        const tgtSelect = el('targetLangSelect');
        if (tgtSelect) {
            tgtSelect.addEventListener('change', (e) => setTargetLanguage(e.target.value));
        }

        // Quick Chips
        const srcChips = el('sourceChips');
        if (srcChips) {
            srcChips.addEventListener('click', (e) => {
                const chip = e.target.closest('.chip');
                if (chip) setSourceLanguage(chip.getAttribute('data-lang'));
            });
        }

        const tgtChips = el('targetChips');
        if (tgtChips) {
            tgtChips.addEventListener('click', (e) => {
                const chip = e.target.closest('.chip');
                if (chip) setTargetLanguage(chip.getAttribute('data-lang'));
            });
        }

        // Swap button
        const swapBtn = el('swapLangBtn');
        if (swapBtn) swapBtn.addEventListener('click', swapLanguages);

        // Dictate button
        const micBtn = el('micBtn');
        if (micBtn) micBtn.addEventListener('click', toggleRecording);

        // Audio TTS buttons
        const srcTts = el('sourceTtsBtn');
        if (srcTts) srcTts.addEventListener('click', listenSource);

        const tgtTts = el('targetTtsBtn');
        if (tgtTts) tgtTts.addEventListener('click', listenTarget);

        // Copy button
        const copyBtn = el('copyBtn');
        if (copyBtn) copyBtn.addEventListener('click', copyTranslation);

        // Bookmark button
        const bmBtn = el('bookmarkBtn');
        if (bmBtn) bmBtn.addEventListener('click', bookmarkCurrentTranslation);

        // Share button
        const shareBtn = el('shareLinkBtn');
        if (shareBtn) shareBtn.addEventListener('click', shareCurrentTranslation);

        // Fullscreen view
        const fsBtn = el('fullscreenBtn');
        if (fsBtn) fsBtn.addEventListener('click', openFullscreen);

        const closeFsBtn = el('closeFullscreenBtn');
        if (closeFsBtn) closeFsBtn.addEventListener('click', closeFullscreen);

        // Translate Now manual button
        const translateBtn = el('manualTranslateBtn');
        if (translateBtn) {
            translateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                performTranslation(true);
            });
        }

        // Realtime toggle
        const rtToggle = el('realtimeToggle');
        if (rtToggle) {
            rtToggle.addEventListener('change', (e) => {
                state.realtime = e.target.checked;
                showToast(`Real-time translation ${state.realtime ? 'enabled' : 'disabled'}`, 'info');
            });
        }

        // Preset sample phrases
        const presetBtn = el('presetBtn');
        const presetMenu = el('presetMenu');
        if (presetBtn && presetMenu) {
            presetBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                presetMenu.classList.toggle('show');
            });

            presetMenu.addEventListener('click', (e) => {
                const item = e.target.closest('.preset-item');
                if (item) {
                    const phrase = item.getAttribute('data-phrase');
                    if (phrase && textarea) {
                        textarea.value = phrase;
                        updateCharCount();
                        performTranslation(true);
                    }
                    presetMenu.classList.remove('show');
                }
            });
        }

        // Document and Subtitle file upload
        const fileUpload = el('fileUploadInput');
        if (fileUpload) {
            fileUpload.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const isSubtitle = file.name.endsWith('.srt') || file.name.endsWith('.vtt');
                const reader = new FileReader();
                reader.onload = async (event) => {
                    const content = event.target.result;
                    if (isSubtitle) {
                        const subBadge = el('subAlertBadge');
                        if (subBadge) subBadge.style.display = 'inline-block';
                        const srtBtn = el('exportSrtBtn');
                        if (srtBtn) srtBtn.style.display = 'block';

                        if (textarea) {
                            textarea.value = content;
                            updateCharCount();
                        }

                        showToast(`Subtitle file ${file.name} loaded. Translating dialogue while preserving timecodes...`, 'info');
                        setLoading(true);
                        try {
                            const res = await fetch('/api/translate_subtitles', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    content: content,
                                    source_lang: state.sourceLang,
                                    target_lang: state.targetLang
                                })
                            });
                            const d = await res.json();
                            if (d.success) {
                                state.lastSubtitleContent = d.translated_content;
                                const out = el('translationOutput');
                                if (out) out.textContent = d.translated_content;
                                showToast('Subtitle translation complete! You can download it from Export menu.', 'success');
                            } else {
                                showToast(d.error || 'Subtitle translation failed', 'error');
                            }
                        } catch (err) {
                            showToast('Subtitle translation error', 'error');
                        } finally {
                            setLoading(false);
                        }
                    } else {
                        const subBadge = el('subAlertBadge');
                        if (subBadge) subBadge.style.display = 'none';
                        const srtBtn = el('exportSrtBtn');
                        if (srtBtn) srtBtn.style.display = 'none';
                        state.lastSubtitleContent = null;

                        if (textarea) {
                            textarea.value = content;
                            updateCharCount();
                            performTranslation(true);
                            showToast(`Uploaded ${file.name} successfully`, 'success');
                        }
                    }
                };
                reader.onerror = () => showToast('Failed to read file', 'error');
                reader.readAsText(file);
            });
        }

        // Export dropdown
        const exportBtn = el('exportBtn');
        const exportMenu = el('exportMenu');
        if (exportBtn && exportMenu) {
            exportBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                exportMenu.classList.toggle('show');
            });

            const txtBtn = el('exportTxtBtn');
            if (txtBtn) txtBtn.addEventListener('click', exportAsText);

            const jsonBtn = el('exportJsonBtn');
            if (jsonBtn) jsonBtn.addEventListener('click', exportAsJson);

            const mp3Btn = el('exportMp3Btn');
            if (mp3Btn) mp3Btn.addEventListener('click', exportAsMp3);

            const srtBtn = el('exportSrtBtn');
            if (srtBtn) {
                srtBtn.addEventListener('click', () => {
                    const textToSave = state.lastSubtitleContent || state.lastTranslatedText;
                    if (!textToSave) {
                        showToast('No translated subtitle content to export', 'error');
                        return;
                    }
                    const blob = new Blob([textToSave], { type: 'text/plain;charset=utf-8' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `translation_${state.targetLang}.srt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('Subtitle .srt file downloaded!', 'success');
                });
            }
        }

        // Close dropdowns on outside click
        document.addEventListener('click', () => {
            if (presetMenu) presetMenu.classList.remove('show');
            if (exportMenu) exportMenu.classList.remove('show');
        });

        // Close dictionary card
        const closeDict = el('closeDictBtn');
        if (closeDict) {
            closeDict.addEventListener('click', () => {
                const card = el('dictionaryCard');
                if (card) card.style.display = 'none';
            });
        }

        // History Drawer
        const histBtn = el('historyToggleBtn');
        if (histBtn) histBtn.addEventListener('click', toggleHistoryDrawer);

        const closeHist = el('closeDrawerBtn');
        if (closeHist) closeHist.addEventListener('click', closeHistoryDrawer);

        const clearHist = el('clearHistoryBtn');
        if (clearHist) clearHist.addEventListener('click', clearAllHistory);

        // Shortcuts Modal
        const scBtn = el('shortcutsBtn');
        if (scBtn) scBtn.addEventListener('click', openShortcutsModal);

        const closeSc = el('closeShortcutsModal');
        if (closeSc) closeSc.addEventListener('click', closeShortcutsModal);

        const scModal = el('shortcutsModal');
        if (scModal) {
            scModal.addEventListener('click', (e) => {
                if (e.target === scModal) closeShortcutsModal();
            });
        }

        // Global Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeHistoryDrawer();
                closeFullscreen();
                closeShortcutsModal();
                closeCommandPalette();
                const menu = el('formatMenu');
                if (menu) menu.classList.remove('show');
                return;
            }

            // Ctrl + K or Cmd + K: Toggle Command Palette
            if ((e.ctrlKey || e.metaKey) && (e.key === 'K' || e.key === 'k')) {
                e.preventDefault();
                const modal = el('cmdPaletteModal');
                if (modal && modal.classList.contains('open')) {
                    closeCommandPalette();
                } else {
                    openCommandPalette();
                }
                return;
            }

            // Ctrl + Enter: Translate immediately
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                performTranslation(true);
                return;
            }

            // Ctrl + Shift + S: Swap languages
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'S' || e.key === 's')) {
                e.preventDefault();
                swapLanguages();
                return;
            }

            // Ctrl + Shift + C: Copy translation
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c')) {
                e.preventDefault();
                copyTranslation();
                return;
            }

            // Ctrl + Shift + D: Toggle voice dictation
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
                e.preventDefault();
                toggleRecording();
                return;
            }

            // Ctrl + Shift + L: Listen to translation
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'L' || e.key === 'l')) {
                e.preventDefault();
                listenTarget();
                return;
            }

            // Ctrl + Shift + H: Toggle History Drawer
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'H' || e.key === 'h')) {
                e.preventDefault();
                toggleHistoryDrawer();
                return;
            }

            // Ctrl + Shift + F: Open Study Deck
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'F' || e.key === 'f')) {
                e.preventDefault();
                openDeckModal();
                return;
            }

            // Ctrl + Shift + T: Toggle Theme
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'T' || e.key === 't')) {
                e.preventDefault();
                toggleTheme();
                return;
            }
        });
    }

    // =========================================================================
    // Extended Standout Features: Transliteration & Copy
    // =========================================================================
    function copyTransliteration() {
        const text = state.lastTransliteration;
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            showToast('Phonetic pronunciation copied!', 'success');
        }).catch(() => {
            showToast('Unable to copy pronunciation', 'error');
        });
    }

    // =========================================================================
    // Extended Standout Features: Round-Trip Quality Verification
    // =========================================================================
    async function verifyAccuracy() {
        const sourceText = state.lastSourceText || (el('sourceTextInput') ? el('sourceTextInput').value : '');
        const targetText = state.lastTranslatedText;

        if (!sourceText || !targetText) {
            showToast('Please translate text first before verifying accuracy.', 'info');
            return;
        }

        const verifyBtn = el('verifyAccuracyBtn');
        const verifyBtnText = el('verifyBtnText');
        if (verifyBtnText) verifyBtnText.textContent = 'Verifying...';
        if (verifyBtn) verifyBtn.disabled = true;

        try {
            const res = await fetch('/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_text: sourceText,
                    target_text: targetText,
                    source_lang: state.detectedLangCode || state.sourceLang,
                    target_lang: state.targetLang
                })
            });
            const data = await res.json();
            if (data.success) {
                const card = el('verificationCard');
                const badge = el('verifyScoreBadge');
                const rating = el('verifyRatingText');
                const backText = el('verifyBackText');

                if (badge) badge.textContent = `🛡️ ${data.integrity_score}% Meaning Integrity`;
                if (rating) rating.textContent = data.rating;
                if (backText) backText.textContent = `"${data.back_translation}"`;
                if (card) card.style.display = 'block';

                showToast(`Integrity Score: ${data.integrity_score}% (${data.rating})`, 'success');
            } else {
                showToast(data.error || 'Verification failed', 'error');
            }
        } catch (e) {
            showToast('Verification request failed', 'error');
        } finally {
            if (verifyBtnText) verifyBtnText.textContent = 'Verify';
            if (verifyBtn) verifyBtn.disabled = false;
        }
    }

    function closeVerificationCard() {
        const card = el('verificationCard');
        if (card) card.style.display = 'none';
    }

    // =========================================================================
    // Extended Standout Features: Studio Mode Switcher
    // =========================================================================
    function switchStudioMode(mode) {
        state.currentMode = mode;

        const dualSection = el('dualStudioSection');
        const polySection = el('polyglotSection');
        const convoSection = el('convoSection');

        const dualBtn = el('modeDualBtn');
        const polyBtn = el('modePolyglotBtn');
        const convoBtn = el('modeConvoBtn');

        [dualBtn, polyBtn, convoBtn].forEach(b => {
            if (b) b.classList.remove('active');
        });

        if (mode === 'dual') {
            if (dualSection) dualSection.style.display = 'block';
            if (polySection) polySection.style.display = 'none';
            if (convoSection) convoSection.style.display = 'none';
            if (dualBtn) dualBtn.classList.add('active');
            showToast('Switched to Dual Translation Studio', 'info');
        } else if (mode === 'polyglot') {
            if (dualSection) dualSection.style.display = 'none';
            if (polySection) polySection.style.display = 'flex';
            if (convoSection) convoSection.style.display = 'none';
            if (polyBtn) polyBtn.classList.add('active');

            // Sync current input from dual mode if polyglot input is empty
            const srcInput = el('sourceTextInput');
            const polyInput = el('polyglotInput');
            if (srcInput && polyInput && srcInput.value && !polyInput.value) {
                polyInput.value = srcInput.value;
                performPolyglotTranslation();
            }
            showToast('Polyglot Broadcast Mode active (1-to-5 Concurrency)', 'info');
        } else if (mode === 'convo') {
            if (dualSection) dualSection.style.display = 'none';
            if (polySection) polySection.style.display = 'none';
            if (convoSection) convoSection.style.display = 'flex';
            if (convoBtn) convoBtn.classList.add('active');
            showToast('Two-Way Walkie-Talkie Conversation Mode active', 'info');
        }
    }

    // =========================================================================
    // Extended Standout Features: Polyglot Broadcast Mode (1-to-5)
    // =========================================================================
    async function performPolyglotTranslation() {
        const polyInput = el('polyglotInput');
        const text = polyInput ? polyInput.value.trim() : '';
        if (!text) {
            showToast('Please enter text to broadcast', 'info');
            return;
        }

        const statusTag = el('polyglotStatusTag');
        if (statusTag) statusTag.textContent = '⚡ Broadcasting across neural clusters...';

        try {
            const targets = ['es', 'fr', 'de', 'ja', 'hi'];
            const res = await fetch('/api/translate_multi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    source_lang: 'auto',
                    targets: targets,
                    tone: state.tone || 'default'
                })
            });
            const data = await res.json();
            if (data.success && data.results) {
                targets.forEach(tgt => {
                    const result = data.results[tgt];
                    const out = el(`polyOutput_${tgt}`);
                    if (out && result && result.translated_text) {
                        out.textContent = result.translated_text;
                    }
                    if (tgt === 'hi' && result && result.transliteration) {
                        const tr = el('polyTranslit_hi');
                        if (tr) {
                            tr.textContent = `🗣️ Pronunciation: ${result.transliteration}`;
                            tr.style.display = 'block';
                        }
                    }
                });
                if (statusTag) statusTag.textContent = 'Broadcast completed across 5 languages';
                showToast('Polyglot broadcast translated to 5 languages!', 'success');
            }
        } catch (e) {
            if (statusTag) statusTag.textContent = 'Broadcast encountered an error';
            showToast('Polyglot broadcast failed', 'error');
        }
    }

    function clearPolyglotInput() {
        const input = el('polyglotInput');
        if (input) input.value = '';
        ['es', 'fr', 'de', 'ja', 'hi'].forEach(tgt => {
            const out = el(`polyOutput_${tgt}`);
            if (out) out.textContent = 'Translation will appear here...';
        });
        const tr = el('polyTranslit_hi');
        if (tr) tr.style.display = 'none';
        const status = el('polyglotStatusTag');
        if (status) status.textContent = 'Ready to broadcast';
    }

    function copyPolyglot(lang) {
        const out = el(`polyOutput_${lang}`);
        if (!out || !out.textContent || out.textContent.includes('will appear here')) return;
        navigator.clipboard.writeText(out.textContent).then(() => {
            showToast(`Copied ${lang.toUpperCase()} translation!`, 'success');
        });
    }

    function listenPolyglot(lang) {
        const out = el(`polyOutput_${lang}`);
        if (!out || !out.textContent || out.textContent.includes('will appear here')) return;
        playAudio(out.textContent, lang);
    }

    // =========================================================================
    // Extended Standout Features: Two-Way Conversation Walkie-Talkie
    // =========================================================================
    function startConvoSpeech(speaker) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            showToast('Speech recognition not supported in this browser.', 'error');
            return;
        }

        const langASelect = el('convoLangA');
        const langBSelect = el('convoLangB');
        const langA = langASelect ? langASelect.value : 'en';
        const langB = langBSelect ? langBSelect.value : 'es';

        const sourceLang = speaker === 'A' ? langA : langB;
        const targetLang = speaker === 'A' ? langB : langA;

        const micBtn = el(speaker === 'A' ? 'convoMicBtnA' : 'convoMicBtnB');
        const micTxt = el(speaker === 'A' ? 'convoMicTextA' : 'convoMicTextB');

        const rec = new SpeechRec();
        rec.continuous = false;
        rec.interimResults = false;
        rec.lang = getSpeechLocale(sourceLang);

        if (micBtn) micBtn.classList.add('recording');
        if (micTxt) micTxt.textContent = 'Listening... Speak now';

        rec.onresult = async (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript) {
                appendConvoBubble(speaker, transcript, '...', sourceLang, targetLang);
                try {
                    const res = await fetch('/api/translate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: transcript,
                            source_lang: sourceLang,
                            target_lang: targetLang
                        })
                    });
                    const d = await res.json();
                    if (d.success) {
                        updateLastConvoBubble(d.translated_text);
                        // Speak aloud to other person
                        playAudio(d.translated_text, targetLang);
                    }
                } catch (err) {
                    updateLastConvoBubble('(Translation error)');
                }
            }
        };

        rec.onerror = () => {
            showToast('Microphone error or permission denied', 'error');
            resetConvoMic(speaker);
        };

        rec.onend = () => {
            resetConvoMic(speaker);
        };

        try {
            rec.start();
        } catch (e) {
            resetConvoMic(speaker);
        }
    }

    function resetConvoMic(speaker) {
        const micBtn = el(speaker === 'A' ? 'convoMicBtnA' : 'convoMicBtnB');
        const micTxt = el(speaker === 'A' ? 'convoMicTextA' : 'convoMicTextB');
        if (micBtn) micBtn.classList.remove('recording');
        if (micTxt) {
            micTxt.textContent = speaker === 'A' ? 'Person A Speak' : 'Person B Speak';
        }
    }

    function appendConvoBubble(speaker, original, translated, srcLang, tgtLang) {
        const stream = el('convoChatStream');
        if (!stream) return;

        // Remove welcome banner on first message
        const welcome = stream.querySelector('.convo-welcome');
        if (welcome) welcome.remove();

        const bubble = document.createElement('div');
        bubble.className = `convo-bubble ${speaker === 'A' ? 'speaker-a' : 'speaker-b'}`;
        bubble.innerHTML = `
            <div class="bubble-meta">
                <span><strong>Person ${speaker}</strong> (${srcLang.toUpperCase()} ➔ ${tgtLang.toUpperCase()})</span>
                <span>Just now</span>
            </div>
            <div class="bubble-original">"${escapeHtml(original)}"</div>
            <div class="bubble-translated">${escapeHtml(translated)}</div>
        `;
        stream.appendChild(bubble);
        stream.scrollTop = stream.scrollHeight;
    }

    function updateLastConvoBubble(translated) {
        const stream = el('convoChatStream');
        if (!stream) return;
        const lastBubble = stream.querySelector('.convo-bubble:last-child .bubble-translated');
        if (lastBubble) {
            lastBubble.textContent = translated;
        }
        stream.scrollTop = stream.scrollHeight;
    }

    function clearConvoChat() {
        const stream = el('convoChatStream');
        if (stream) {
            stream.innerHTML = `
                <div class="convo-welcome">
                    <div class="welcome-icon">🎙️</div>
                    <h3>Two-Way Voice Walkie-Talkie</h3>
                    <p>Click Person A or Person B's microphone below to speak. Speech is instantly recognized, translated, and read aloud in real-time!</p>
                </div>
            `;
        }
        showToast('Conversation chat cleared', 'info');
    }

    // =========================================================================
    // Extended Standout Features: Flashcard Vocabulary Study Deck
    // =========================================================================
    function updateDeckBadge() {
        const badge = el('deckBadge');
        const count = state.deck.length;
        if (badge) {
            badge.textContent = count.toString();
            badge.style.display = count > 0 ? 'inline-flex' : 'none';
        }
        const modalCount = el('deckCountBadge');
        if (modalCount) modalCount.textContent = `${count} cards`;
    }

    function saveDeckToStorage() {
        try {
            localStorage.setItem('lingostudio_deck', JSON.stringify(state.deck));
        } catch (e) {}
        updateDeckBadge();
    }

    function addCurrentToDeck() {
        const source = state.lastSourceText || (el('sourceTextInput') ? el('sourceTextInput').value.trim() : '');
        const target = state.lastTranslatedText;

        if (!source || !target) {
            showToast('Translate a phrase first before adding to your deck', 'info');
            return;
        }

        // Avoid exact duplicate
        const exists = state.deck.some(c => c.source.toLowerCase() === source.toLowerCase() && c.targetLang === state.targetLang);
        if (exists) {
            showToast('Card already in your Study Deck!', 'info');
            return;
        }

        const newCard = {
            id: Date.now(),
            source: source,
            target: target,
            sourceLang: state.detectedLangCode || state.sourceLang,
            targetLang: state.targetLang,
            transliteration: state.lastTransliteration || '',
            dateAdded: new Date().toLocaleDateString()
        };

        state.deck.unshift(newCard);
        saveDeckToStorage();
        showToast('Saved to Flashcard Study Deck! ⭐', 'success');
    }

    function openDeckModal() {
        const modal = el('studyDeckModal');
        if (modal) {
            modal.classList.add('open');
            modal.setAttribute('aria-hidden', 'false');
            state.currentDeckIndex = 0;
            renderActiveDeckCard();
        }
    }

    function closeDeckModal() {
        const modal = el('studyDeckModal');
        if (modal) {
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    function renderActiveDeckCard() {
        const emptyState = el('deckEmptyState');
        const viewer = el('deckCardViewer');
        const card = el('activeFlashcard');

        if (card) card.classList.remove('flipped');

        if (!state.deck || state.deck.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            if (viewer) viewer.style.display = 'none';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        if (viewer) viewer.style.display = 'flex';

        if (state.currentDeckIndex >= state.deck.length) {
            state.currentDeckIndex = state.deck.length - 1;
        }
        if (state.currentDeckIndex < 0) {
            state.currentDeckIndex = 0;
        }

        const item = state.deck[state.currentDeckIndex];
        const frontLang = el('cardFrontLang');
        const frontText = el('cardFrontText');
        const backLang = el('cardBackLang');
        const backText = el('cardBackText');
        const translit = el('cardTranslitText');
        const indicator = el('deckPositionIndicator');

        if (frontLang) frontLang.textContent = (item.sourceLang || 'SOURCE').toUpperCase();
        if (frontText) frontText.textContent = item.source;
        if (backLang) backLang.textContent = (item.targetLang || 'TARGET').toUpperCase();
        if (backText) backText.textContent = item.target;
        if (translit) {
            if (item.transliteration) {
                translit.textContent = `🗣️ ${item.transliteration}`;
                translit.style.display = 'block';
            } else {
                translit.style.display = 'none';
            }
        }
        if (indicator) {
            indicator.textContent = `${state.currentDeckIndex + 1} / ${state.deck.length}`;
        }
    }

    function flipFlashcard() {
        const card = el('activeFlashcard');
        if (card) card.classList.toggle('flipped');
    }

    function prevDeckCard() {
        if (state.deck.length <= 1) return;
        state.currentDeckIndex = (state.currentDeckIndex - 1 + state.deck.length) % state.deck.length;
        renderActiveDeckCard();
    }

    function nextDeckCard() {
        if (state.deck.length <= 1) return;
        state.currentDeckIndex = (state.currentDeckIndex + 1) % state.deck.length;
        renderActiveDeckCard();
    }

    function deleteCurrentDeckCard() {
        if (state.deck.length === 0) return;
        state.deck.splice(state.currentDeckIndex, 1);
        saveDeckToStorage();
        showToast('Card removed from deck', 'info');
        renderActiveDeckCard();
    }

    function listenDeckCard(face) {
        if (state.deck.length === 0) return;
        const item = state.deck[state.currentDeckIndex];
        if (face === 'front') {
            playAudio(item.source, item.sourceLang);
        } else {
            playAudio(item.target, item.targetLang);
        }
    }

    function exportDeckCsv() {
        if (state.deck.length === 0) {
            showToast('No cards in study deck to export', 'error');
            return;
        }

        let csv = 'Source Text,Translated Text,Pronunciation,Source Language,Target Language,Date Added\n';
        state.deck.forEach(c => {
            const cleanSrc = `"${c.source.replace(/"/g, '""')}"`;
            const cleanTgt = `"${c.target.replace(/"/g, '""')}"`;
            const cleanTr = `"${(c.transliteration || '').replace(/"/g, '""')}"`;
            csv += `${cleanSrc},${cleanTgt},${cleanTr},${c.sourceLang},${c.targetLang},${c.dateAdded}\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `lingostudio_anki_deck_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Exported deck as Anki-ready CSV file!', 'success');
    }

    // =========================================================================
    // Tone & Formality Selector
    // =========================================================================
    function setupToneSelector() {
        const toneContainer = el('toneChips');
        if (!toneContainer) return;
        toneContainer.querySelectorAll('.tone-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const tone = chip.getAttribute('data-tone') || 'default';
                setTone(tone);
            });
        });
    }

    function setTone(toneName) {
        state.tone = toneName || 'default';
        const toneContainer = el('toneChips');
        if (toneContainer) {
            toneContainer.querySelectorAll('.tone-chip').forEach(c => {
                if (c.getAttribute('data-tone') === state.tone) {
                    c.classList.add('active');
                } else {
                    c.classList.remove('active');
                }
            });
        }
        showToast(`Formality tone set to ${state.tone.toUpperCase()}`, 'info');
        performTranslation(false);
    }

    // =========================================================================
    // Text Formatting Tools & Clipboard
    // =========================================================================
    function setupFormatDropdown() {
        const btn = el('formatMenuBtn');
        const menu = el('formatMenu');
        if (!btn || !menu) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!menu.contains(e.target) && e.target !== btn) {
                menu.classList.remove('show');
            }
        });

        menu.querySelectorAll('.format-item').forEach(item => {
            item.addEventListener('click', () => {
                const format = item.getAttribute('data-format');
                menu.classList.remove('show');
                if (format === 'paste') {
                    pasteFromClipboard();
                } else if (format) {
                    formatSourceText(format);
                }
            });
        });
    }

    function formatSourceText(type) {
        const textarea = el('sourceTextInput');
        if (!textarea || !textarea.value) {
            showToast('Enter some text first to apply formatting', 'info');
            return;
        }
        let val = textarea.value;

        switch (type) {
            case 'sentence':
                val = val.toLowerCase().replace(/(^\s*|\.\s*|\?\s*|!\s*)([a-z\u00C0-\u017F])/g, (m, p1, p2) => p1 + p2.toUpperCase());
                break;
            case 'title':
                val = val.replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
                break;
            case 'upper':
                val = val.toUpperCase();
                break;
            case 'lower':
                val = val.toLowerCase();
                break;
            case 'clean':
                val = val.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
                break;
        }

        textarea.value = val;
        updateCharCount();
        triggerTranslationDebounced();
        showToast(`Applied format: ${type}`, 'info');
    }

    async function pasteFromClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                const textarea = el('sourceTextInput');
                if (textarea) {
                    textarea.value = text;
                    updateCharCount();
                    showToast('Pasted from clipboard!', 'success');
                    performTranslation(true);
                }
            } else {
                showToast('Clipboard is empty', 'info');
            }
        } catch (e) {
            showToast('Unable to read clipboard. Please paste using Ctrl+V', 'error');
        }
    }

    // =========================================================================
    // Share Link & URL Query Sync
    // =========================================================================
    function shareCurrentTranslation() {
        const textarea = el('sourceTextInput');
        const text = state.lastSourceText || (textarea ? textarea.value.trim() : '');
        if (!text) {
            showToast('Enter text first to generate a shareable link', 'info');
            return;
        }

        const url = new URL(window.location.origin + window.location.pathname);
        url.searchParams.set('src', state.sourceLang);
        url.searchParams.set('tgt', state.targetLang);
        if (state.tone && state.tone !== 'default') {
            url.searchParams.set('tone', state.tone);
        }
        url.searchParams.set('q', text);

        if (navigator.clipboard) {
            navigator.clipboard.writeText(url.href).then(() => {
                showToast('Shareable translation link copied to clipboard! 🔗', 'success');
            }).catch(() => {
                prompt('Copy this shareable translation link:', url.href);
            });
        } else {
            prompt('Copy this shareable translation link:', url.href);
        }
    }

    function setupURLQuerySync() {
        try {
            const params = new URLSearchParams(window.location.search);
            const q = params.get('q');
            const src = params.get('src');
            const tgt = params.get('tgt');
            const tone = params.get('tone');

            let hasParams = false;

            if (src) {
                state.sourceLang = src;
                const select = el('sourceLangSelect');
                if (select) select.value = src;
                hasParams = true;
            }
            if (tgt) {
                state.targetLang = tgt;
                const select = el('targetLangSelect');
                if (select) select.value = tgt;
                hasParams = true;
            }
            syncChipsWithSelects();

            if (tone) {
                state.tone = tone;
                const toneContainer = el('toneChips');
                if (toneContainer) {
                    toneContainer.querySelectorAll('.tone-chip').forEach(c => {
                        if (c.getAttribute('data-tone') === tone) {
                            c.classList.add('active');
                        } else {
                            c.classList.remove('active');
                        }
                    });
                }
                hasParams = true;
            }

            if (q) {
                const textarea = el('sourceTextInput');
                if (textarea) {
                    textarea.value = q;
                    updateCharCount();
                    hasParams = true;
                }
            }

            if (hasParams && q) {
                performTranslation(false);
            }
        } catch (e) {
            console.warn('URL query sync error:', e);
        }
    }

    // =========================================================================
    // Command Palette (Ctrl + K / Cmd + K)
    // =========================================================================
    const COMMAND_ITEMS = [
        { id: 'trans_es', title: 'Translate to Spanish (Español)', category: 'Languages', badge: 'ES', action: () => setTargetLanguage('es') },
        { id: 'trans_fr', title: 'Translate to French (Français)', category: 'Languages', badge: 'FR', action: () => setTargetLanguage('fr') },
        { id: 'trans_de', title: 'Translate to German (Deutsch)', category: 'Languages', badge: 'DE', action: () => setTargetLanguage('de') },
        { id: 'trans_ja', title: 'Translate to Japanese (日本語)', category: 'Languages', badge: 'JA', action: () => setTargetLanguage('ja') },
        { id: 'trans_hi', title: 'Translate to Hindi (हिन्दी)', category: 'Languages', badge: 'HI', action: () => setTargetLanguage('hi') },
        { id: 'trans_zh', title: 'Translate to Chinese (中文)', category: 'Languages', badge: 'ZH', action: () => setTargetLanguage('zh') },
        { id: 'trans_ar', title: 'Translate to Arabic (العربية)', category: 'Languages', badge: 'AR', action: () => setTargetLanguage('ar') },
        { id: 'trans_it', title: 'Translate to Italian (Italiano)', category: 'Languages', badge: 'IT', action: () => setTargetLanguage('it') },
        { id: 'trans_pt', title: 'Translate to Portuguese (Português)', category: 'Languages', badge: 'PT', action: () => setTargetLanguage('pt') },
        { id: 'trans_ru', title: 'Translate to Russian (Русский)', category: 'Languages', badge: 'RU', action: () => setTargetLanguage('ru') },
        { id: 'swap_lang', title: 'Swap Source & Target Languages', category: 'Actions', badge: 'Ctrl+Shift+S', action: () => swapLanguages() },
        { id: 'dictate', title: 'Toggle Voice Dictation Microphone', category: 'Audio', badge: 'Ctrl+Shift+D', action: () => toggleRecording() },
        { id: 'listen_tgt', title: 'Listen to Translated Audio (TTS)', category: 'Audio', badge: 'Ctrl+Shift+L', action: () => listenTarget() },
        { id: 'listen_src', title: 'Listen to Source Text Audio', category: 'Audio', badge: 'Audio', action: () => listenSource() },
        { id: 'verify_acc', title: 'Verify Translation Quality & Back-Translation', category: 'Actions', badge: 'QA', action: () => verifyAccuracy() },
        { id: 'copy_tgt', title: 'Copy Translated Text to Clipboard', category: 'Actions', badge: 'Ctrl+Shift+C', action: () => copyTranslation() },
        { id: 'share_link', title: 'Share Translation Link', category: 'Actions', badge: 'Share', action: () => shareCurrentTranslation() },
        { id: 'bookmark_deck', title: 'Save to Flashcard Study Deck', category: 'Flashcards', badge: 'Star', action: () => bookmarkCurrentTranslation() },
        { id: 'open_deck', title: 'Open Flashcard Study Deck Modal', category: 'Flashcards', badge: 'Study', action: () => openDeckModal() },
        { id: 'open_history', title: 'Open History Drawer', category: 'History', badge: 'Drawer', action: () => openHistoryDrawer() },
        { id: 'mode_dual', title: 'Switch Mode: Dual Translation Studio', category: 'Modes', badge: 'Studio', action: () => switchStudioMode('dual') },
        { id: 'mode_polyglot', title: 'Switch Mode: Polyglot 1-to-5 Broadcast', category: 'Modes', badge: 'Broadcast', action: () => switchStudioMode('polyglot') },
        { id: 'mode_convo', title: 'Switch Mode: Two-Way Walkie-Talkie', category: 'Modes', badge: 'Live', action: () => switchStudioMode('convo') },
        { id: 'tone_default', title: 'Tone: Default (Balanced)', category: 'Tone', badge: 'Tone', action: () => setTone('default') },
        { id: 'tone_formal', title: 'Tone: Formal (Professional & Polite)', category: 'Tone', badge: 'Tone', action: () => setTone('formal') },
        { id: 'tone_casual', title: 'Tone: Casual (Conversational)', category: 'Tone', badge: 'Tone', action: () => setTone('casual') },
        { id: 'tone_academic', title: 'Tone: Academic (Scholarly & Precise)', category: 'Tone', badge: 'Tone', action: () => setTone('academic') },
        { id: 'tone_simplified', title: 'Tone: Simplified (Learner-Friendly)', category: 'Tone', badge: 'Tone', action: () => setTone('simplified') },
        { id: 'format_clean', title: 'Format: Clean Extra Spaces & Blank Lines', category: 'Formatting', badge: 'Clean', action: () => formatSourceText('clean') },
        { id: 'format_sentence', title: 'Format: Convert to Sentence case', category: 'Formatting', badge: 'Aa', action: () => formatSourceText('sentence') },
        { id: 'format_title', title: 'Format: Convert to Title Case', category: 'Formatting', badge: 'Aa', action: () => formatSourceText('title') },
        { id: 'format_upper', title: 'Format: Convert to UPPERCASE', category: 'Formatting', badge: 'AA', action: () => formatSourceText('upper') },
        { id: 'format_lower', title: 'Format: Convert to lowercase', category: 'Formatting', badge: 'aa', action: () => formatSourceText('lower') },
        { id: 'paste_clip', title: 'Paste Text from Clipboard', category: 'Formatting', badge: 'Paste', action: () => pasteFromClipboard() },
        { id: 'clear_input', title: 'Clear Source Text Input', category: 'Actions', badge: 'Clear', action: () => clearSourceInput() },
        { id: 'theme_toggle', title: 'Toggle Dark / Light Theme', category: 'Appearance', badge: 'Ctrl+Shift+T', action: () => toggleTheme() },
        { id: 'open_shortcuts', title: 'Open Keyboard Shortcuts Guide', category: 'Help', badge: '?', action: () => openShortcutsModal() }
    ];

    function setupCommandPalette() {
        const cmdModal = el('cmdPaletteModal');
        const cmdInput = el('cmdPaletteInput');
        const cmdBtn = el('cmdPaletteBtn');
        const closeBtn = el('closeCmdPaletteBtn');

        if (cmdBtn) {
            cmdBtn.addEventListener('click', (e) => {
                e.preventDefault();
                openCommandPalette();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', closeCommandPalette);
        }

        if (cmdModal) {
            cmdModal.addEventListener('click', (e) => {
                if (e.target === cmdModal) closeCommandPalette();
            });
        }

        if (cmdInput) {
            cmdInput.addEventListener('input', (e) => {
                filterCommandPalette(e.target.value);
            });

            cmdInput.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    navigateCommandPalette(1);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    navigateCommandPalette(-1);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    executeCurrentCommand();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    closeCommandPalette();
                }
            });
        }
    }

    function openCommandPalette() {
        const modal = el('cmdPaletteModal');
        const input = el('cmdPaletteInput');
        if (!modal) return;
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');
        if (input) {
            input.value = '';
            setTimeout(() => input.focus(), 50);
        }
        filterCommandPalette('');
    }

    function closeCommandPalette() {
        const modal = el('cmdPaletteModal');
        if (modal) {
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    function filterCommandPalette(query) {
        const q = (query || '').toLowerCase().trim();
        if (!q) {
            state.cmdFilteredList = COMMAND_ITEMS;
        } else {
            state.cmdFilteredList = COMMAND_ITEMS.filter(item => {
                return item.title.toLowerCase().includes(q) ||
                       item.category.toLowerCase().includes(q) ||
                       item.badge.toLowerCase().includes(q);
            });
        }
        state.cmdSelectedIndex = 0;
        renderCommandList();
    }

    function renderCommandList() {
        const listEl = el('cmdResultsList');
        if (!listEl) return;

        if (state.cmdFilteredList.length === 0) {
            listEl.innerHTML = `<div class="cmd-empty">No matching commands found.</div>`;
            return;
        }

        let html = '';
        state.cmdFilteredList.forEach((cmd, idx) => {
            const isSelected = idx === state.cmdSelectedIndex;
            html += `
                <div class="cmd-item ${isSelected ? 'selected' : ''}" data-cmd-index="${idx}" role="option" aria-selected="${isSelected}">
                    <div class="cmd-item-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                        </svg>
                    </div>
                    <div class="cmd-item-text">
                        <span class="cmd-item-title">${escapeHtml(cmd.title)}</span>
                        <span class="cmd-item-cat">${escapeHtml(cmd.category)}</span>
                    </div>
                    <span class="cmd-item-kbd">${escapeHtml(cmd.badge)}</span>
                </div>
            `;
        });

        listEl.innerHTML = html;

        listEl.querySelectorAll('.cmd-item').forEach(itemEl => {
            itemEl.addEventListener('click', () => {
                const idx = parseInt(itemEl.getAttribute('data-cmd-index'), 10);
                state.cmdSelectedIndex = idx;
                executeCurrentCommand();
            });
        });

        const selectedEl = listEl.querySelector('.cmd-item.selected');
        if (selectedEl) {
            selectedEl.scrollIntoView({ block: 'nearest' });
        }
    }

    function navigateCommandPalette(direction) {
        if (!state.cmdFilteredList || state.cmdFilteredList.length === 0) return;
        state.cmdSelectedIndex = (state.cmdSelectedIndex + direction + state.cmdFilteredList.length) % state.cmdFilteredList.length;
        renderCommandList();
    }

    function executeCurrentCommand() {
        if (!state.cmdFilteredList || state.cmdFilteredList.length === 0) return;
        const cmd = state.cmdFilteredList[state.cmdSelectedIndex];
        if (cmd && typeof cmd.action === 'function') {
            closeCommandPalette();
            cmd.action();
        }
    }

    // =========================================================================
    // Initialization
    // =========================================================================
    function init() {
        applyTheme(state.theme);
        updateHistoryBadge();
        updateHistorySubtitle();
        updateDeckBadge();
        setupLanguageSelectors();
        setupToneSelector();
        setupFormatDropdown();
        setupCommandPalette();
        setupHistoryControls();
        setupEventListeners();
        setupSpeechRecognition();
        setupURLQuerySync();

        // Sample initial phrase if user opens with empty field (only if no query params present)
        const params = new URLSearchParams(window.location.search);
        const textarea = el('sourceTextInput');
        if (textarea && !textarea.value.trim() && !params.get('q')) {
            textarea.value = "Hello, welcome to LingoStudio AI translation studio!";
            updateCharCount();
            performTranslation(false);
        }
    }

    // Expose global functions on window for inline handlers and devtools
    window.performTranslation = performTranslation;
    window.swapLanguages = swapLanguages;
    window.clearSourceInput = clearSourceInput;
    window.listenSource = listenSource;
    window.listenTarget = listenTarget;
    window.copyTranslation = copyTranslation;
    window.bookmarkCurrentTranslation = bookmarkCurrentTranslation;
    window.toggleTheme = toggleTheme;
    window.toggleHistoryDrawer = toggleHistoryDrawer;
    window.openHistoryDrawer = openHistoryDrawer;
    window.closeHistoryDrawer = closeHistoryDrawer;
    window.clearAllHistory = clearAllHistory;
    window.restoreHistoryItem = restoreHistoryItem;
    window.copyHistoryItem = copyHistoryItem;
    window.listenHistoryItem = listenHistoryItem;
    window.deleteHistoryItem = deleteHistoryItem;
    window.toggleHistoryStar = toggleHistoryStar;
    window.exportHistoryCsv = exportHistoryCsv;
    window.openShortcutsModal = openShortcutsModal;
    window.closeShortcutsModal = closeShortcutsModal;
    window.openFullscreen = openFullscreen;
    window.closeFullscreen = closeFullscreen;
    window.toggleRecording = toggleRecording;
    window.setSourceLanguage = setSourceLanguage;
    window.setTargetLanguage = setTargetLanguage;

    // Extended Feature Window Exports
    window.copyTransliteration = copyTransliteration;
    window.verifyAccuracy = verifyAccuracy;
    window.closeVerificationCard = closeVerificationCard;
    window.switchStudioMode = switchStudioMode;
    window.performPolyglotTranslation = performPolyglotTranslation;
    window.clearPolyglotInput = clearPolyglotInput;
    window.copyPolyglot = copyPolyglot;
    window.listenPolyglot = listenPolyglot;
    window.startConvoSpeech = startConvoSpeech;
    window.clearConvoChat = clearConvoChat;
    window.openDeckModal = openDeckModal;
    window.closeDeckModal = closeDeckModal;
    window.addCurrentToDeck = addCurrentToDeck;
    window.flipFlashcard = flipFlashcard;
    window.prevDeckCard = prevDeckCard;
    window.nextDeckCard = nextDeckCard;
    window.deleteCurrentDeckCard = deleteCurrentDeckCard;
    window.listenDeckCard = listenDeckCard;
    window.exportDeckCsv = exportDeckCsv;

    // New Enhancement Exports
    window.openCommandPalette = openCommandPalette;
    window.closeCommandPalette = closeCommandPalette;
    window.setTone = setTone;
    window.formatSourceText = formatSourceText;
    window.pasteFromClipboard = pasteFromClipboard;
    window.shareCurrentTranslation = shareCurrentTranslation;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window, document);
