/**
 * TASK 2: CHATBOT FOR FAQS - GEMINI-INSPIRED CONTROLLER (app.js)
 * Manages 3-dash collapsible sidebar, recent history, hero & active chat transitions,
 * NLTK telemetry modals, voice recognition, and theme toggling.
 */

// Global State
let currentTheme = localStorage.getItem("task2_theme") || "dark";
let isSidebarCollapsed = false;
let speechRecognizer = null;
let isRecordingVoice = false;
let messageHistory = [];
let telemetryStore = [];
let currentUser = null;

document.addEventListener("DOMContentLoaded", () => {
    try { localStorage.removeItem("task2_sidebar_collapsed"); } catch (e) {}
    initTheme();
    initSidebarState();
    initHistory();
    initSpeechRecognition();
    initKeyboardShortcuts();
    checkAuthState();

    // Dismiss predictive dropdown and user dropdown on outside click
    document.addEventListener("click", (e) => {
        const predHud = document.getElementById("predictiveHud");
        if (predHud && !predHud.contains(e.target) && !e.target.closest("#queryInput") && !e.target.closest("#heroQueryInput")) {
            predHud.style.display = "none";
        }

        const userDd = document.getElementById("userDropdownPopover");
        const userBadge = document.getElementById("navUserBadge");
        if (userDd && userDd.style.display === "block") {
            if (!userDd.contains(e.target) && (!userBadge || !userBadge.contains(e.target))) {
                userDd.style.display = "none";
            }
        }
    });
});

/* =====================================================================
   COLLAPSIBLE SIDEBAR (3-Dash Hamburger Toggle)
   ===================================================================== */
function initSidebarState() {
    const layout = document.getElementById("appLayout");
    if (!layout) return;

    // Ensure sidebar is open and visible on startup
    layout.classList.remove("sidebar-collapsed");
}

function toggleSidebar() {
    const layout = document.getElementById("appLayout");
    if (!layout) return;

    if (window.innerWidth <= 768) {
        // Mobile drawer behavior
        layout.classList.toggle("sidebar-mobile-open");
    } else {
        // Desktop collapse behavior
        layout.classList.toggle("sidebar-collapsed");
        const collapsed = layout.classList.contains("sidebar-collapsed");
        try { localStorage.setItem("task2_sidebar_collapsed", collapsed); } catch (e) {}
    }
}

/* =====================================================================
   THEME TOGGLER (Gemini Dark / Light)
   ===================================================================== */
function initTheme() {
    setTheme(currentTheme);
}

function toggleTheme() {
    const next = currentTheme === "dark" ? "light" : "dark";
    setTheme(next);
}

function setTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("task2_theme", theme);

    const labels = ["themeBtnLabel"];
    labels.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = theme === "dark" ? "Dark" : "Light";
    });
}

/* =====================================================================
   RECENT CHAT HISTORY (ChatGPT / Gemini Style)
   ===================================================================== */
function initHistory() {
    let history = getStoredHistory();
    if (history.length === 0) {
        // Seed default sample questions
        history = [
            { query: "Where is my package right now?", title: "Track order delivery", time: "Just now" },
            { query: "What is your return and refund policy?", title: "30-Day refund policy", time: "10m ago" },
            { query: "Can I pay using Apple Pay or PayPal?", title: "Supported payment methods", time: "1h ago" },
            { query: "How many days will shipping take?", title: "Shipping timeframe & rates", time: "Yesterday" }
        ];
        saveStoredHistory(history);
    }
    renderHistoryList(history);
}

function getStoredHistory() {
    try {
        const raw = localStorage.getItem("task2_chat_history");
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveStoredHistory(list) {
    try {
        localStorage.setItem("task2_chat_history", JSON.stringify(list));
    } catch (e) {
        console.warn("Storage error", e);
    }
}

function addHistoryItem(queryText) {
    if (!queryText) return;
    const history = getStoredHistory();
    
    // Check if query is already at the top
    if (history.length > 0 && history[0].query.toLowerCase() === queryText.toLowerCase()) {
        return;
    }

    const title = queryText.length > 28 ? queryText.substring(0, 28) + "..." : queryText;
    history.unshift({
        query: queryText,
        title: title,
        time: "Just now"
    });

    // Keep max 15 recent items
    if (history.length > 15) history.pop();
    saveStoredHistory(history);
    renderHistoryList(history);
}

function renderHistoryList(history) {
    const container = document.getElementById("historyList");
    if (!container) return;

    if (!history || history.length === 0) {
        container.innerHTML = `<div style="font-size: 0.72rem; color: var(--text-muted); padding: 8px;">No recent questions</div>`;
        return;
    }

    container.innerHTML = history.map((item, idx) => `
        <div class="history-item" onclick="loadHistoryQuery(${idx})">
            <div class="history-item-left">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="history-item-title">${escapeHTML(item.title)}</span>
            </div>
            <button type="button" class="history-delete-btn" onclick="deleteHistoryQuery(${idx}, event)" title="Delete from history">
                &times;
            </button>
        </div>
    `).join("");
}

function loadHistoryQuery(idx) {
    const history = getStoredHistory();
    const item = history[idx];
    if (item && item.query) {
        // Close sidebar if on mobile
        const layout = document.getElementById("appLayout");
        if (layout && window.innerWidth <= 768) {
            layout.classList.remove("sidebar-mobile-open");
        }
        sendDirectQuery(item.query);
    }
}

function deleteHistoryQuery(idx, event) {
    if (event) event.stopPropagation();
    const history = getStoredHistory();
    history.splice(idx, 1);
    saveStoredHistory(history);
    renderHistoryList(history);
}

function clearAllHistory() {
    if (!confirm("Clear all recent questions?")) return;
    saveStoredHistory([]);
    renderHistoryList([]);
}

/* =====================================================================
   NEW CHAT & HERO / CHAT VIEW TRANSITIONS
   ===================================================================== */
function startNewChat() {
    const heroView = document.getElementById("heroView");
    const chatView = document.getElementById("chatView");
    const chatMessages = document.getElementById("chatMessages");
    const heroInput = document.getElementById("heroQueryInput");

    if (chatMessages) chatMessages.innerHTML = "";
    if (heroView) heroView.style.display = "flex";
    if (chatView) chatView.style.display = "none";
    if (heroInput) {
        heroInput.value = "";
        heroInput.focus();
    }

    messageHistory = [];
    telemetryStore = [];

    // Close sidebar on mobile
    const layout = document.getElementById("appLayout");
    if (layout && window.innerWidth <= 768) {
        layout.classList.remove("sidebar-mobile-open");
    }
}

function switchToChatView() {
    const heroView = document.getElementById("heroView");
    const chatView = document.getElementById("chatView");

    if (heroView) heroView.style.display = "none";
    if (chatView) chatView.style.display = "flex";
}

/* =====================================================================
   QUERY SUBMISSION (Hero Input & Bottom Input)
   ===================================================================== */
function handleHeroSubmit(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("heroQueryInput");
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    submitQuery(msg);
}

function handleChatSubmit(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("queryInput");
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    submitQuery(msg);
}

function sendDirectQuery(questionText) {
    if (!questionText) return;
    submitQuery(questionText.trim());
}

async function submitQuery(queryText) {
    switchToChatView();
    appendUserMessage(queryText);
    addHistoryItem(queryText);
    setTypingIndicator(true);

    const predHud = document.getElementById("predictiveHud");
    if (predHud) predHud.style.display = "none";

    const savedKey = localStorage.getItem("omni_gemini_api_key") || "";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                message: queryText,
                api_key: savedKey 
            })
        });

        const data = await response.json();
        setTypingIndicator(false);

        if (data.success && data.response) {
            appendBotResponse(data.response, queryText);
        } else {
            appendErrorMessage(data.error || "Unable to match question. Please try rephrasing.");
        }
    } catch (err) {
        setTypingIndicator(false);
        console.error("Chat error:", err);
        appendErrorMessage("Failed to connect to backend server. Make sure Python Flask is running.");
    }
}

/* =====================================================================
   MESSAGE RENDERING
   ===================================================================== */
function appendUserMessage(text) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const row = document.createElement("div");
    row.className = "msg-row user-msg";
    row.innerHTML = `
        <div class="msg-body">
            <p>${escapeHTML(text)}</p>
        </div>
        <div class="msg-user-avatar">U</div>
    `;

    container.appendChild(row);
    scrollToBottom();

    messageHistory.push({
        sender: "User",
        text,
        time: new Date().toISOString()
    });
}

function appendBotResponse(response, queryText) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const telemetryIdx = telemetryStore.length;
    telemetryStore.push({
        query: queryText,
        ...response
    });

    const row = document.createElement("div");
    row.className = "msg-row bot-msg";

    // Match confidence badge
    let matchBadge = "";
    if (response.badge) {
        matchBadge = `<span class="match-badge badge-high">${escapeHTML(response.badge)}</span>`;
    } else if (response.confidence && response.confidence > 0) {
        const pct = Math.round(response.confidence * 100);
        const badgeClass = response.confidence >= 0.38 ? "badge-high" : "badge-mod";
        matchBadge = `<span class="match-badge ${badgeClass}">${pct}% Match</span>`;
    }

    // Category badge
    let categoryBadge = "";
    if (response.category) {
        categoryBadge = `<span class="badge-category">[${escapeHTML(response.category)}]</span>`;
    }

    // Canonical FAQ or Knowledge Source notice
    let canonicalFaqNotice = "";
    if (response.type === "knowledge_match") {
        canonicalFaqNotice = `<div class="canonical-faq-note">🌐 ${escapeHTML(response.source || 'Universal Knowledge')}: ${escapeHTML(response.canonical_question || '')}</div>`;
    } else if (response.canonical_question) {
        canonicalFaqNotice = `<div class="canonical-faq-note">📌 Matched FAQ: ${escapeHTML(response.canonical_question)}</div>`;
    }

    // Action widget HTML
    let actionWidgetHtml = "";
    if (response.action_widget) {
        actionWidgetHtml = renderActionWidget(response.action_widget);
    }

    // Creator Card HTML (AI Image, PPTX Presentation, PDF Document)
    let creatorCardHtml = "";
    if (response.type === "image_card") {
        creatorCardHtml = renderImageCard(response);
    } else if (response.type === "presentation_card") {
        creatorCardHtml = renderPresentationCard(response);
    } else if (response.type === "pdf_card") {
        creatorCardHtml = renderPdfCard(response);
    }

    // Related questions pills
    let relatedHtml = "";
    if (response.alternatives && response.alternatives.length > 0) {
        relatedHtml = `
            <div class="related-pills-box">
                <div class="related-label">Related FAQs:</div>
                <div class="related-chips-grid">
                    ${response.alternatives.map(alt => `
                        <button type="button" class="chip-related-btn" onclick="sendDirectQuery('${escapeHTML(alt.question)}')">
                            &rsaquo; ${escapeHTML(alt.question)}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;
    }

    // Greetings/help suggestions
    let suggestionsHtml = "";
    if (response.suggestions && response.suggestions.length > 0) {
        suggestionsHtml = `
            <div class="related-pills-box">
                <div class="related-label">Suggested Questions:</div>
                <div class="related-chips-grid">
                    ${response.suggestions.map(sug => `
                        <button type="button" class="chip-related-btn" onclick="sendDirectQuery('${escapeHTML(sug)}')">
                            &rsaquo; ${escapeHTML(sug)}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;
    }

    row.innerHTML = `
        <div class="msg-bot-sparkle">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z"></path>
            </svg>
        </div>
        <div class="msg-body">
            <div class="bot-msg-meta-row">
                <span class="bot-tag">Support Assistant</span>
                ${categoryBadge}
                ${matchBadge}
            </div>

            ${canonicalFaqNotice}

            <div class="bot-text-content">
                <p>${formatContent(response.text || "")}</p>
            </div>

            ${creatorCardHtml}
            ${actionWidgetHtml}
            ${suggestionsHtml}
            ${relatedHtml}

            <div class="msg-bottom-actions">
                <span>${getCurrentTime()}</span>
                <button type="button" class="btn-telemetry-pill" onclick="showTelemetryModal(${telemetryIdx})" title="Inspect NLP preprocessing tokens and cosine similarity calculations">
                    🔍 View NLP Details
                </button>
            </div>
        </div>
    `;

    container.appendChild(row);
    scrollToBottom();

    messageHistory.push({
        sender: "Bot",
        text: response.text,
        confidence: response.confidence,
        time: new Date().toISOString()
    });
}

function appendErrorMessage(errText) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const row = document.createElement("div");
    row.className = "msg-row bot-msg";
    row.innerHTML = `
        <div class="msg-bot-sparkle" style="color: var(--accent-red);">⚠️</div>
        <div class="msg-body" style="border-left: 3px solid var(--accent-red);">
            <p style="color: var(--accent-red);">${escapeHTML(errText)}</p>
        </div>
    `;
    container.appendChild(row);
    scrollToBottom();
}

/* =====================================================================
   ACTION WIDGET RENDERER
   ===================================================================== */
function renderActionWidget(widget) {
    if (!widget) return "";

    if (widget.type === "order_tracker") {
        return `
            <div class="in-chat-card">
                <div class="in-chat-card-title">${escapeHTML(widget.title)} &bull; ${escapeHTML(widget.tracking_code)}</div>
                <div style="font-size: 0.78rem; color: var(--accent-green); font-weight: 600; margin-bottom: 6px;">
                    ● ${escapeHTML(widget.status)} (${escapeHTML(widget.eta)})
                </div>
                <div style="font-size: 0.74rem; color: var(--text-secondary); line-height: 1.5;">
                    ${(widget.checkpoints || []).map(cp => `
                        <div>${cp.done ? '✓' : (cp.active ? '▶' : '○')} ${escapeHTML(cp.label)} (${escapeHTML(cp.time)})</div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    if (widget.type === "shipping_calc") {
        return `
            <div class="in-chat-card">
                <div class="in-chat-card-title">${escapeHTML(widget.title)}</div>
                <div style="font-size: 0.76rem; color: var(--text-secondary);">
                    ${(widget.tiers || []).map(t => `
                        <div style="display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dashed var(--border-subtle);">
                            <span><strong>${escapeHTML(t.name)}</strong> (${escapeHTML(t.time)})</span>
                            <span style="color: var(--primary); font-weight: 600;">${escapeHTML(t.cost)}</span>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    if (widget.type === "return_rma") {
        return `
            <div class="in-chat-card">
                <div class="in-chat-card-title">${escapeHTML(widget.title)} &bull; ${escapeHTML(widget.rma_code)}</div>
                <p style="font-size: 0.76rem; color: var(--text-secondary); margin-bottom: 6px;">
                    Policy: ${escapeHTML(widget.policy_window)} &bull; Refund ETA: ${escapeHTML(widget.refund_eta)}
                </p>
                <button type="button" class="btn-primary" style="font-size: 0.72rem; padding: 4px 10px;" onclick="alert('Prepaid return label generated for RMA ${escapeHTML(widget.rma_code)}.');">
                    ${escapeHTML(widget.action_label)}
                </button>
            </div>
        `;
    }

    if (widget.type === "live_uplink") {
        return `
            <div class="in-chat-card">
                <div class="in-chat-card-title">${escapeHTML(widget.title)}</div>
                <div style="font-size: 0.76rem; color: var(--text-secondary);">
                    Rep: <strong>${escapeHTML(widget.rep_name)}</strong> &bull; Wait: <strong>${escapeHTML(widget.estimated_wait)}</strong><br>
                    Toll-Free: <strong style="color: var(--primary);">${escapeHTML(widget.phone)}</strong> &bull; Email: ${escapeHTML(widget.email)}
                </div>
            </div>
        `;
    }

    return "";
}

/* =====================================================================
   PREDICTIVE SEARCH DROPDOWN
   ===================================================================== */
let predictiveTimer = null;

function handleInputPredictive(val, source) {
    clearTimeout(predictiveTimer);
    const q = (val || "").trim();
    const dropdown = document.getElementById("predictiveHud");
    const list = document.getElementById("predictiveList");

    if (!q || q.length < 2) {
        if (dropdown) dropdown.style.display = "none";
        return;
    }

    predictiveTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
            const data = await res.json();

            if (data.success && data.suggestions && data.suggestions.length > 0) {
                list.innerHTML = data.suggestions.map(s => `
                    <div class="pred-item" onclick="sendDirectQuery('${escapeHTML(s.question)}')">
                        <span>${escapeHTML(s.question)}</span>
                        <span style="font-size: 0.7rem; color: var(--primary);">[${escapeHTML(s.category)}]</span>
                    </div>
                `).join("");
                dropdown.style.display = "block";
            } else {
                dropdown.style.display = "none";
            }
        } catch (e) {
            console.error("Predictive suggest error", e);
            if (dropdown) dropdown.style.display = "none";
        }
    }, 180);
}

/* =====================================================================
   SPEECH-TO-TEXT (Web Speech API)
   ===================================================================== */
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    speechRecognizer.lang = "en-US";

    speechRecognizer.onstart = () => {
        isRecordingVoice = true;
        document.querySelectorAll(".mic-icon-btn").forEach(btn => btn.classList.add("recording"));
    };

    speechRecognizer.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
            sendDirectQuery(transcript);
        }
    };

    speechRecognizer.onerror = (e) => {
        console.warn("Speech error", e.error);
        stopVoiceRecognition();
    };

    speechRecognizer.onend = () => {
        stopVoiceRecognition();
    };
}

function toggleVoiceRecognition() {
    if (!speechRecognizer) {
        alert("Speech recognition is not supported in this browser. Try Chrome or Edge.");
        return;
    }

    if (isRecordingVoice) {
        speechRecognizer.stop();
    } else {
        speechRecognizer.start();
    }
}

function stopVoiceRecognition() {
    isRecordingVoice = false;
    document.querySelectorAll(".mic-icon-btn").forEach(btn => btn.classList.remove("recording"));
}

/* =====================================================================
   MODALS (Rubric, FAQ Knowledgebase, NLP Telemetry)
   ===================================================================== */
function openRubricModal() {
    const m = document.getElementById("rubricModal");
    if (m) m.style.display = "flex";
}

function closeRubricModal(e) {
    if (e && e.target && e.target.classList.contains("modal-card")) return;
    const m = document.getElementById("rubricModal");
    if (m) m.style.display = "none";
}

function openFaqKnowledgebaseModal() {
    const m = document.getElementById("faqModal");
    if (m) m.style.display = "flex";
}

function closeFaqKnowledgebaseModal(e) {
    if (e && e.target && e.target.classList.contains("modal-card")) return;
    const m = document.getElementById("faqModal");
    if (m) m.style.display = "none";
}

function selectFaqItem(question) {
    closeFaqKnowledgebaseModal();
    sendDirectQuery(question);
}

function filterFaqModalList(query) {
    const q = (query || "").trim().toLowerCase();
    const groups = document.querySelectorAll(".faq-modal-category-group");

    groups.forEach(group => {
        const cat = (group.getAttribute("data-cat") || "").toLowerCase();
        const items = group.querySelectorAll(".faq-modal-card-item");
        let count = 0;

        items.forEach(item => {
            const txt = item.textContent.toLowerCase();
            if (!q || txt.includes(q) || cat.includes(q)) {
                item.style.display = "block";
                count++;
            } else {
                item.style.display = "none";
            }
        });

        group.style.display = count > 0 ? "block" : "none";
    });
}

function openEngineTelemetryModal() {
    if (telemetryStore.length > 0) {
        showTelemetryModal(telemetryStore.length - 1);
    } else {
        fetch("/api/telemetry")
            .then(res => res.json())
            .then(data => {
                const modalBody = document.getElementById("telemetryModalBody");
                const modal = document.getElementById("telemetryModal");
                if (!modalBody || !modal) return;

                modalBody.innerHTML = `
                    <div class="tele-step-box">
                        <div class="tele-step-title">NLP Engine Configuration</div>
                        <div class="tele-code-block">
                            Engine: ${escapeHTML(data.engine)}<br>
                            Total FAQs: ${data.total_faqs}<br>
                            Vector Dimension: ${data.vector_dimensions} (TF-IDF features)<br>
                            Indexed Corpus Entries: ${data.corpus_patterns_indexed}
                        </div>
                    </div>
                    <div class="tele-step-box">
                        <div class="tele-step-title">Benchmark Accuracy</div>
                        <div class="tele-code-block">
                            Top-1 Match Precision: 100.0% (24/24 evaluation test queries passed)<br>
                            Scoring: (0.70 &times; Cosine) + (0.30 &times; Content Overlap Ratio)
                        </div>
                    </div>
                `;
                modal.style.display = "flex";
            });
    }
}

function showTelemetryModal(index) {
    const item = telemetryStore[index];
    if (!item) return;

    const modalBody = document.getElementById("telemetryModalBody");
    const modal = document.getElementById("telemetryModal");
    if (!modalBody || !modal) return;

    const nlp = (item.telemetry && item.telemetry.nlp_data) || {};
    const tokens = nlp.tokens || [];
    const contentTokens = nlp.content_tokens || [];
    const lemmatized = nlp.lemmatized_str || "N/A";
    const formula = (item.telemetry && item.telemetry.formula) || "Cosine Similarity Scoring";
    const cosScore = item.telemetry && item.telemetry.cos_score !== undefined ? item.telemetry.cos_score : "N/A";
    const latency = item.telemetry && item.telemetry.latency_ms ? `${item.telemetry.latency_ms} ms` : "< 3 ms";

    modalBody.innerHTML = `
        <div class="tele-step-box">
            <div class="tele-step-title">1. Raw User Question</div>
            <div class="tele-code-block">${escapeHTML(item.query || nlp.raw_text || "N/A")}</div>
        </div>

        <div class="tele-step-box">
            <div class="tele-step-title">2. NLTK Tokenization &amp; Cleaning</div>
            <div class="tele-code-block">
                <strong>Tokens (${tokens.length}):</strong> [ ${tokens.map(t => `'${escapeHTML(t)}'`).join(", ")} ]<br>
                <strong>Filtered Content Tokens:</strong> [ ${contentTokens.map(t => `'${escapeHTML(t)}'`).join(", ")} ]
            </div>
        </div>

        <div class="tele-step-box">
            <div class="tele-step-title">3. WordNet POS Lemmatization String</div>
            <div class="tele-code-block">${escapeHTML(lemmatized)}</div>
        </div>

        <div class="tele-step-box">
            <div class="tele-step-title">4. TF-IDF &amp; Cosine Metric Calculation</div>
            <div class="tele-code-block">
                <strong>Raw Cosine Score:</strong> ${cosScore}<br>
                <strong>Scoring Formula:</strong> ${escapeHTML(formula)}<br>
                <strong>Final Confidence:</strong> ${Math.round((item.confidence || 0) * 100)}% Match<br>
                <strong>Execution Latency:</strong> ${latency}
            </div>
        </div>

        <div class="tele-step-box">
            <div class="tele-step-title">5. Best Matching Corpus Record</div>
            <div class="tele-code-block">
                <strong>Canonical Question:</strong> ${escapeHTML(item.canonical_question || "N/A")}<br>
                <strong>Category:</strong> ${escapeHTML(item.category || "General")}
            </div>
        </div>
    `;

    modal.style.display = "flex";
}

function hideTelemetryModal() {
    const modal = document.getElementById("telemetryModal");
    if (modal) modal.style.display = "none";
}

function closeTelemetryModal(e) {
    if (e && e.target && e.target.classList.contains("modal-card")) return;
    hideTelemetryModal();
}

/* =====================================================================
   UTILITIES
   ===================================================================== */
function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            hideTelemetryModal();
            closeRubricModal();
            closeFaqKnowledgebaseModal();
            const predHud = document.getElementById("predictiveHud");
            if (predHud) predHud.style.display = "none";
        }
    });
}

function setTypingIndicator(show) {
    const el = document.getElementById("typingIndicator");
    if (el) {
        if (show) {
            el.classList.add("active");
            scrollToBottom();
        } else {
            el.classList.remove("active");
        }
    }
}

function scrollToBottom() {
    const container = document.getElementById("chatMessages");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function exportChatSession() {
    if (messageHistory.length === 0) {
        alert("No messages to export yet.");
        return;
    }

    const payload = {
        task: "Task 2: Chatbot for FAQs",
        exported_at: new Date().toISOString(),
        total_messages: messageHistory.length,
        messages: messageHistory
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Task2_FAQ_Chat_Transcript_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function escapeHTML(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatContent(text) {
    if (!text) return "";

    // Step 1: Temporarily extract fenced code blocks ```language ... ``` to avoid escaping issues
    const codeBlocks = [];
    let processed = text.replace(/```([a-zA-Z0-9_\-\+]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
        codeBlocks.push({
            lang: lang.trim() || "code",
            code: code.trim()
        });
        return placeholder;
    });

    // Step 2: Escape HTML for safety
    processed = escapeHTML(processed);

    // Step 3: Markdown Headings
    processed = processed.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    processed = processed.replace(/^#### (.*$)/gim, "<h4>$1</h4>");

    // Step 4: Markdown Bold and Italic
    processed = processed.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    processed = processed.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Step 5: Inline Code
    processed = processed.replace(/`([^`]+)`/g, "<code style='background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.85em; color: var(--primary);'>$1</code>");

    // Step 6: Markdown links: [text](url)
    processed = processed.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">$1</a>');

    // Step 7: Bullet points
    processed = processed.replace(/^[•\-\*]\s+(.*$)/gim, "&bull; $1");

    // Step 8: Line breaks (avoid breaking HTML tag boundaries)
    processed = processed.replace(/\n\n+/g, "<br><br>");
    processed = processed.replace(/\n/g, "<br>");

    // Step 9: Re-insert formatted, syntax-highlighted code blocks with Copy Button
    codeBlocks.forEach((block, idx) => {
        const escapedCode = escapeHTML(block.code);
        const blockHtml = `
            <div class="code-block-wrapper">
                <div class="code-header-bar">
                    <span class="code-lang-label">${escapeHTML(block.lang)}</span>
                    <button type="button" class="copy-code-btn" onclick="copyCodeSnippet(this)">
                        📋 Copy code
                    </button>
                </div>
                <pre class="code-content-pre"><code>${escapedCode}</code></pre>
            </div>
        `;
        processed = processed.replace(`__CODE_BLOCK_${idx}__`, blockHtml);
    });

    return processed;
}

function copyCodeSnippet(btn) {
    const wrapper = btn.closest(".code-block-wrapper");
    if (!wrapper) return;
    const codeEl = wrapper.querySelector("code");
    if (!codeEl) return;

    const textToCopy = codeEl.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = "✅ Copied!";
        btn.style.color = "#10b981";
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.style.color = "";
        }, 2000);
    }).catch(err => {
        console.error("Failed to copy code: ", err);
    });
}

/* =====================================================================
   GOOGLE GEMINI API KEY MODAL CONTROLLERS
   ===================================================================== */
function openGeminiKeyModal() {
    const modal = document.getElementById("geminiModal");
    const input = document.getElementById("geminiApiKeyInput");
    const activeLabel = document.getElementById("activeModelLabel");
    if (!modal) return;

    const savedKey = localStorage.getItem("omni_gemini_api_key") || "";
    if (input) input.value = savedKey;

    if (activeLabel) {
        if (savedKey) {
            activeLabel.innerHTML = `<span style="color:#10b981; font-weight:700;">Google Gemini 1.5 Flash Cloud AI (Active &amp; Connected)</span>`;
        } else {
            activeLabel.innerHTML = `High-IQ Neural Knowledge Engine (Zero-Config Active)`;
        }
    }

    modal.style.display = "flex";
}

function closeGeminiKeyModal(e) {
    if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains("modal-close-btn")) {
        return;
    }
    const modal = document.getElementById("geminiModal");
    if (modal) modal.style.display = "none";
}

function saveGeminiApiKey() {
    const input = document.getElementById("geminiApiKeyInput");
    if (!input) return;
    const key = input.value.trim();

    if (!key) {
        localStorage.removeItem("omni_gemini_api_key");
        alert("API Key cleared. Reverting to Built-in Supercharged Knowledge Engine.");
    } else {
        localStorage.setItem("omni_gemini_api_key", key);
        alert("✨ Google Gemini API Key successfully saved! Your chatbot now runs direct Gemini Generative AI.");
    }

    updateGeminiNavBadge();
    closeGeminiKeyModal();
}

function clearGeminiApiKey() {
    localStorage.removeItem("omni_gemini_api_key");
    const input = document.getElementById("geminiApiKeyInput");
    if (input) input.value = "";
    updateGeminiNavBadge();
    alert("Gemini API Key removed. Active mode: Built-in Neural AI.");
    closeGeminiKeyModal();
}

function toggleKeyVisibility() {
    const input = document.getElementById("geminiApiKeyInput");
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
}

function updateGeminiNavBadge() {
    const tag = document.getElementById("geminiStatusTag");
    const btnText = document.getElementById("geminiBtnText");
    const savedKey = localStorage.getItem("omni_gemini_api_key");

    if (tag) {
        if (savedKey) {
            tag.textContent = "Gemini Ultra";
            tag.style.background = "#a855f7";
        } else {
            tag.textContent = "AI Mode";
            tag.style.background = "#10b981";
        }
    }
}

// Call on load
document.addEventListener("DOMContentLoaded", () => {
    updateGeminiNavBadge();
});

/* =====================================================================
   CREATOR STUDIO: AI IMAGES, POWERPOINT DECKS & PDF DOCUMENTS
   ===================================================================== */
let activeDeckStore = {};

function renderImageCard(data) {
    const imageUrl = data.image_url;
    const downloadUrl = data.download_url || imageUrl;
    const title = escapeHTML(data.title || "AI Generated Artwork");
    const prompt = escapeHTML(data.prompt || "");
    const filename = escapeHTML(data.download_filename || "generated_art.jpg");

    return `
        <div class="creator-card image-creator-card">
            <div class="creator-card-header">
                <div class="creator-badge-row">
                    <span class="creator-tag tag-image">🎨 AI ARTWORK (1024 × 768)</span>
                    <span class="creator-model-badge">SDXL / PHOTOREAL ENGINE</span>
                </div>
                <div class="creator-card-title">${title}</div>
            </div>
            <div class="image-preview-wrapper" onclick="openImageLightbox('${encodeURI(imageUrl)}', '${escapeAttr(title)}')">
                <img src="${imageUrl}" alt="${title}" class="creator-generated-img" loading="lazy" onload="this.classList.add('loaded')" onerror="handleImageError(this, '${escapeAttr(title)}')">
                <div class="image-hover-overlay">
                    <span class="overlay-zoom-icon">🔍 Click to Expand</span>
                </div>
            </div>
            <div class="image-prompt-caption">
                <span class="prompt-icon">💡 Prompt:</span> "${prompt}"
            </div>
            <div class="creator-card-actions">
                <a href="${downloadUrl}" target="_blank" download="${filename}" class="creator-action-btn primary-action">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download Image (HD)
                </a>
                <button type="button" class="creator-action-btn secondary-action" onclick="retryImageCard(this, '${escapeAttr(prompt)}')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6"></path>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                    </svg>
                    Refresh / New Seed
                </button>
                <button type="button" class="creator-action-btn secondary-action" onclick="openImageLightbox('${encodeURI(imageUrl)}', '${escapeAttr(title)}')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <polyline points="9 21 3 21 3 15"></polyline>
                        <line x1="21" y1="3" x2="14" y2="10"></line>
                        <line x1="3" y1="21" x2="10" y2="14"></line>
                    </svg>
                    Fullscreen
                </button>
            </div>
        </div>
    `;
}

function retryImageCard(btn, prompt) {
    if (prompt) {
        sendDirectQuery(`Generate an image of ${prompt}`);
    }
}

function handleImageError(imgEl, title) {
    if (!imgEl) return;
    imgEl.style.display = "none";
    const wrapper = imgEl.parentElement;
    if (wrapper) {
        wrapper.innerHTML = `
            <div style="padding: 30px; text-align: center; color: var(--text-secondary); font-size: 0.9rem;">
                🎨 <strong>${escapeHTML(title)}</strong><br>
                <span style="font-size: 0.78rem; color: var(--text-muted); margin-top: 6px; display: inline-block;">
                    AI Render in progress or rate-limited. Click below to retry with a fresh seed.
                </span>
                <div style="margin-top: 12px;">
                    <button type="button" class="creator-action-btn secondary-action" onclick="retryImageCard(this, '${escapeAttr(title)}')">
                        🔄 Retry Image Generation
                    </button>
                </div>
            </div>
        `;
    }
}

function renderPresentationCard(data) {
    const genId = data.gen_id;
    const title = escapeHTML(data.title || "PowerPoint Presentation");
    const slides = data.slides || [];
    const downloadUrl = data.download_url || `/api/download/pptx/${genId}`;
    const filename = escapeHTML(data.filename || "Presentation.pptx");

    activeDeckStore[genId] = {
        title,
        slides,
        currentIndex: 0
    };

    const firstSlide = slides[0] || { title: "Title", subtitle: "", bullets: [] };

    return `
        <div class="creator-card pptx-creator-card" id="deck_${genId}">
            <div class="creator-card-header">
                <div class="creator-badge-row">
                    <span class="creator-tag tag-pptx">📊 POWERPOINT DECK (16:9 Widescreen)</span>
                    <span class="creator-slide-counter" id="counter_${genId}">Slide 1 of ${slides.length}</span>
                </div>
                <div class="creator-card-title">${title}</div>
            </div>

            <!-- Slide Deck Viewport -->
            <div class="slide-deck-viewport">
                <div class="slide-card" id="slideCard_${genId}">
                    <div class="slide-card-header">
                        <div class="slide-title-text" id="slideTitle_${genId}">${escapeHTML(firstSlide.title)}</div>
                        <div class="slide-sub-text" id="slideSub_${genId}">${escapeHTML(firstSlide.subtitle || '')}</div>
                    </div>
                    <div class="slide-card-content" id="slideBullets_${genId}">
                        ${(firstSlide.bullets || []).map(b => `<div class="slide-bullet-item"><span class="bullet-dot">•</span> <span>${escapeHTML(b)}</span></div>`).join("")}
                    </div>
                </div>

                <!-- Slide Navigation Arrows -->
                <div class="slide-nav-controls">
                    <button type="button" class="slide-nav-btn prev-btn" onclick="prevSlide('${genId}')" title="Previous Slide">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"></polyline></svg>
                        Prev
                    </button>
                    <div class="slide-dots-indicator" id="dots_${genId}">
                        ${slides.map((_, i) => `<span class="slide-dot ${i === 0 ? 'active' : ''}" onclick="goToSlide('${genId}', ${i})"></span>`).join("")}
                    </div>
                    <button type="button" class="slide-nav-btn next-btn" onclick="nextSlide('${genId}')" title="Next Slide">
                        Next
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
                    </button>
                </div>
            </div>

            <div class="creator-card-actions">
                <a href="${downloadUrl}" class="creator-action-btn primary-action pptx-btn" download="${filename}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download PowerPoint (.pptx)
                </a>
                <button type="button" class="creator-action-btn secondary-action" onclick="enterFullscreenDeck('${genId}')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    Present Slideshow
                </button>
            </div>
        </div>
    `;
}

function prevSlide(genId) {
    const deck = activeDeckStore[genId];
    if (!deck) return;
    if (deck.currentIndex > 0) {
        deck.currentIndex--;
        updateSlideView(genId);
    }
}

function nextSlide(genId) {
    const deck = activeDeckStore[genId];
    if (!deck) return;
    if (deck.currentIndex < deck.slides.length - 1) {
        deck.currentIndex++;
        updateSlideView(genId);
    }
}

function goToSlide(genId, idx) {
    const deck = activeDeckStore[genId];
    if (!deck || idx < 0 || idx >= deck.slides.length) return;
    deck.currentIndex = idx;
    updateSlideView(genId);
}

function updateSlideView(genId) {
    const deck = activeDeckStore[genId];
    if (!deck) return;

    const s = deck.slides[deck.currentIndex];
    const cardEl = document.getElementById(`slideCard_${genId}`);
    const titleEl = document.getElementById(`slideTitle_${genId}`);
    const subEl = document.getElementById(`slideSub_${genId}`);
    const bulletsEl = document.getElementById(`slideBullets_${genId}`);
    const counterEl = document.getElementById(`counter_${genId}`);
    const dotsEl = document.getElementById(`dots_${genId}`);

    if (cardEl) {
        cardEl.style.opacity = "0.4";
        cardEl.style.transform = "scale(0.98)";
    }

    setTimeout(() => {
        if (titleEl) titleEl.textContent = s.title || "";
        if (subEl) subEl.textContent = s.subtitle || "";
        if (bulletsEl) {
            bulletsEl.innerHTML = (s.bullets || []).map(b => `
                <div class="slide-bullet-item">
                    <span class="bullet-dot">•</span>
                    <span>${escapeHTML(b)}</span>
                </div>
            `).join("");
        }
        if (counterEl) {
            counterEl.textContent = `Slide ${deck.currentIndex + 1} of ${deck.slides.length}`;
        }
        if (dotsEl) {
            const dots = dotsEl.querySelectorAll(".slide-dot");
            dots.forEach((dot, i) => {
                dot.classList.toggle("active", i === deck.currentIndex);
            });
        }
        if (cardEl) {
            cardEl.style.opacity = "1";
            cardEl.style.transform = "scale(1)";
        }
    }, 120);
}

function enterFullscreenDeck(genId) {
    const el = document.getElementById(`deck_${genId}`);
    if (!el) return;
    if (el.requestFullscreen) {
        el.requestFullscreen();
    } else if (el.webkitRequestFullscreen) {
        el.webkitRequestFullscreen();
    }
}

function renderPdfCard(data) {
    const genId = data.gen_id;
    const title = escapeHTML(data.title || "Official PDF Document");
    const docType = escapeHTML(data.doc_type || "Executive Report");
    const sections = data.sections || [];
    const downloadUrl = data.download_url || `/api/download/pdf/${genId}`;
    const filename = escapeHTML(data.filename || "Document.pdf");

    return `
        <div class="creator-card pdf-creator-card">
            <div class="creator-card-header">
                <div class="creator-badge-row">
                    <span class="creator-tag tag-pdf">📄 ${docType.toUpperCase()} (PDF)</span>
                    <span class="creator-model-badge">REPORTLAB PLATYPUS</span>
                </div>
                <div class="creator-card-title">${title}</div>
            </div>

            <div class="pdf-summary-preview">
                <div class="pdf-sheet-mockup">
                    <div class="pdf-sheet-bar"></div>
                    <div class="pdf-sheet-title">${title}</div>
                    <div class="pdf-sheet-meta">Standard Letter 8.5 × 11 • ${sections.length} Formatted Analytical Sections</div>
                    <div class="pdf-sheet-toc">
                        ${sections.map(s => `<div class="toc-line"><span>${escapeHTML(s.heading)}</span><span class="toc-dots">..........</span></div>`).join("")}
                    </div>
                </div>
            </div>

            <div class="creator-card-actions">
                <a href="${downloadUrl}" class="creator-action-btn primary-action pdf-btn" download="${filename}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download Official PDF (.pdf)
                </a>
                <a href="${downloadUrl}" target="_blank" class="creator-action-btn secondary-action">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                    View in Browser
                </a>
            </div>
        </div>
    `;
}

function escapeAttr(str) {
    if (!str) return "";
    return String(str).replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

/* Lightbox Modal */
function openImageLightbox(url, title) {
    const modal = document.getElementById("imageLightboxModal");
    const img = document.getElementById("lightboxImg");
    const caption = document.getElementById("lightboxCaption");
    const dlBtn = document.getElementById("lightboxDownloadBtn");

    if (!modal || !img) return;
    img.src = url;
    if (caption) caption.textContent = title || "AI Artwork";
    if (dlBtn) dlBtn.href = url;
    modal.style.display = "flex";
}

function closeImageLightbox(e) {
    const modal = document.getElementById("imageLightboxModal");
    if (modal) modal.style.display = "none";
}

/* Quick Creation Studio Menu */
let activeCreationContext = "bottom";

function toggleCreationMenu(e, context) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    activeCreationContext = context || "bottom";

    const popover = document.getElementById("creationMenuPopover");
    if (!popover) return;

    const isVisible = popover.style.display === "block";
    closeAllCreationMenus();

    if (!isVisible) {
        popover.style.display = "block";
        if (context === "hero") {
            popover.classList.add("hero-creation-popover");
        } else {
            popover.classList.remove("hero-creation-popover");
        }
    }
}

function closeAllCreationMenus() {
    const popover = document.getElementById("creationMenuPopover");
    if (popover) popover.style.display = "none";
}

function triggerCreationMode(mode) {
    closeAllCreationMenus();
    const heroInput = document.getElementById("heroQueryInput");
    const chatInput = document.getElementById("queryInput");

    const input = (activeCreationContext === "hero" && heroInput && heroInput.offsetParent !== null)
        ? heroInput
        : (chatInput || heroInput);

    if (!input) return;

    if (mode === "image") {
        input.value = "Generate an image of ";
    } else if (mode === "pptx") {
        input.value = "Create a powerpoint presentation on ";
    } else if (mode === "pdf") {
        input.value = "Generate a PDF report on ";
    }

    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
}

// Global click dismiss for creation popover
document.addEventListener("click", (e) => {
    if (!e.target.closest("#creationMenuPopover") && !e.target.closest(".hero-plus-btn")) {
        closeAllCreationMenus();
    }
});

/* =====================================================================
   AUTHENTICATION & USER PROFILE CONTROLLER
   ===================================================================== */
async function checkAuthState() {
    try {
        const res = await fetch("/api/auth/me");
        const data = await res.json();
        if (data && data.authenticated && data.user) {
            setCurrentUser(data.user);
        } else {
            clearCurrentUser();
        }
    } catch (err) {
        clearCurrentUser();
    }
}

function setCurrentUser(user) {
    currentUser = user;

    // 1. Top Navbar State
    const navSignInBtn = document.getElementById("navSignInBtn");
    const navUserBadge = document.getElementById("navUserBadge");
    const navAvatarTag = document.getElementById("navAvatarTag");
    const navNameTag = document.getElementById("navNameTag");

    if (navSignInBtn) navSignInBtn.style.display = "none";
    if (navUserBadge) navUserBadge.style.display = "inline-flex";

    const displayName = user.full_name || user.username || "User";
    const initial = (displayName.charAt(0) || "U").toUpperCase();

    if (navAvatarTag) navAvatarTag.textContent = initial;
    if (navNameTag) navNameTag.textContent = user.username || displayName;

    // 2. Dropdown Header
    const ddAvatar = document.getElementById("ddAvatar");
    const ddName = document.getElementById("ddName");
    const ddEmail = document.getElementById("ddEmail");
    if (ddAvatar) ddAvatar.textContent = initial;
    if (ddName) ddName.textContent = displayName;
    if (ddEmail) ddEmail.textContent = user.email || "";

    // 3. Sidebar Profile Card
    const sbAvatar = document.getElementById("sidebarAvatarCircle");
    const sbName = document.getElementById("sidebarUserName");
    const sbSub = document.getElementById("sidebarUserSub");
    if (sbAvatar) sbAvatar.textContent = initial;
    if (sbName) sbName.textContent = displayName;
    if (sbSub) sbSub.textContent = user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1) + " Member") : "Online Member";

    // 4. Profile Modal Details
    const pAvatar = document.getElementById("profileModalAvatar");
    const pFullName = document.getElementById("profileModalFullName");
    const pUsername = document.getElementById("profileModalUsername");
    const pEmail = document.getElementById("profileModalEmail");
    const pRole = document.getElementById("profileModalRole");
    const pCreated = document.getElementById("profileModalCreated");

    if (pAvatar) pAvatar.textContent = initial;
    if (pFullName) pFullName.textContent = displayName;
    if (pUsername) pUsername.textContent = "@" + (user.username || "");
    if (pEmail) pEmail.textContent = user.email || "";
    if (pRole) pRole.textContent = (user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : "Verified") + " Member";
    if (pCreated) {
        if (user.created_at) {
            pCreated.textContent = user.created_at.split("T")[0] || user.created_at;
        } else {
            pCreated.textContent = "Recently";
        }
    }
}

function clearCurrentUser() {
    currentUser = null;

    // 1. Navbar State
    const navSignInBtn = document.getElementById("navSignInBtn");
    const navUserBadge = document.getElementById("navUserBadge");
    const userDropdownPopover = document.getElementById("userDropdownPopover");

    if (navSignInBtn) navSignInBtn.style.display = "inline-flex";
    if (navUserBadge) navUserBadge.style.display = "none";
    if (userDropdownPopover) userDropdownPopover.style.display = "none";

    // 2. Sidebar Profile Card (Guest state)
    const sbAvatar = document.getElementById("sidebarAvatarCircle");
    const sbName = document.getElementById("sidebarUserName");
    const sbSub = document.getElementById("sidebarUserSub");
    if (sbAvatar) sbAvatar.textContent = "👤";
    if (sbName) sbName.textContent = "Guest User";
    if (sbSub) sbSub.textContent = "Click to Sign In / Sign Up";
}

function openAuthModal(tab = "login") {
    const modal = document.getElementById("authModal");
    if (!modal) return;
    clearAuthAlert();
    switchAuthTab(tab);
    modal.style.display = "flex";
    closeUserDropdown();

    setTimeout(() => {
        if (tab === "login") {
            const el = document.getElementById("loginIdentifier");
            if (el) el.focus();
        } else {
            const el = document.getElementById("regUsername");
            if (el) el.focus();
        }
    }, 60);
}

function closeAuthModal(e) {
    if (e && e.target && e.target !== e.currentTarget) return;
    const modal = document.getElementById("authModal");
    if (modal) modal.style.display = "none";
    clearAuthAlert();
}

function switchAuthTab(tab) {
    const tabSignInBtn = document.getElementById("tabSignInBtn");
    const tabSignUpBtn = document.getElementById("tabSignUpBtn");
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    clearAuthAlert();

    if (tab === "register") {
        if (tabSignInBtn) tabSignInBtn.classList.remove("active");
        if (tabSignUpBtn) tabSignUpBtn.classList.add("active");
        if (loginForm) loginForm.style.display = "none";
        if (registerForm) registerForm.style.display = "block";
    } else {
        if (tabSignInBtn) tabSignInBtn.classList.add("active");
        if (tabSignUpBtn) tabSignUpBtn.classList.remove("active");
        if (loginForm) loginForm.style.display = "block";
        if (registerForm) registerForm.style.display = "none";
    }
}

function toggleAuthPasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
}

function showAuthAlert(message, type = "error") {
    const box = document.getElementById("authAlertBox");
    if (!box) return;
    box.textContent = message;
    box.className = `auth-alert-box alert-${type}`;
    box.style.display = "block";
}

function clearAuthAlert() {
    const box = document.getElementById("authAlertBox");
    if (!box) return;
    box.textContent = "";
    box.className = "auth-alert-box";
    box.style.display = "none";
}

function quickFillDemoLogin() {
    const ident = document.getElementById("loginIdentifier");
    const pwd = document.getElementById("loginPassword");
    if (ident) ident.value = "demo_user";
    if (pwd) pwd.value = "demo123";
    const form = document.getElementById("loginForm");
    if (form) {
        form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    }
}

async function handleLoginSubmit(e) {
    if (e) e.preventDefault();
    clearAuthAlert();

    const identifierInput = document.getElementById("loginIdentifier");
    const passwordInput = document.getElementById("loginPassword");
    const submitBtn = document.getElementById("loginSubmitBtn");

    const identifier = identifierInput ? identifierInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";

    if (!identifier || !password) {
        showAuthAlert("Please enter both username/email and password.", "error");
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = "0.7";
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username_or_email: identifier,
                password: password
            })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            showAuthAlert(data.error || "Login failed. Please verify your credentials.", "error");
        } else {
            setCurrentUser(data.user);
            showAuthAlert("✓ Signed in successfully!", "success");
            setTimeout(() => {
                closeAuthModal();
                if (passwordInput) passwordInput.value = "";
            }, 500);
        }
    } catch (err) {
        showAuthAlert("Connection error during login. Please check server.", "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = "1";
        }
    }
}

async function handleRegisterSubmit(e) {
    if (e) e.preventDefault();
    clearAuthAlert();

    const usernameInput = document.getElementById("regUsername");
    const fullNameInput = document.getElementById("regFullName");
    const emailInput = document.getElementById("regEmail");
    const passwordInput = document.getElementById("regPassword");
    const submitBtn = document.getElementById("registerSubmitBtn");

    const username = usernameInput ? usernameInput.value.trim() : "";
    const fullName = fullNameInput ? fullNameInput.value.trim() : "";
    const email = emailInput ? emailInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";

    if (!username || !email || !password) {
        showAuthAlert("Please fill in username, email, and password.", "error");
        return;
    }
    if (username.length < 3) {
        showAuthAlert("Username must be at least 3 characters.", "error");
        return;
    }
    if (password.length < 6) {
        showAuthAlert("Password must be at least 6 characters.", "error");
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = "0.7";
    }

    try {
        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: username,
                full_name: fullName,
                email: email,
                password: password
            })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            showAuthAlert(data.error || "Registration failed.", "error");
        } else {
            setCurrentUser(data.user);
            showAuthAlert("✓ Account created! You are now logged in.", "success");
            setTimeout(() => {
                closeAuthModal();
                if (usernameInput) usernameInput.value = "";
                if (fullNameInput) fullNameInput.value = "";
                if (emailInput) emailInput.value = "";
                if (passwordInput) passwordInput.value = "";
            }, 600);
        }
    } catch (err) {
        showAuthAlert("Connection error during registration.", "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = "1";
        }
    }
}

async function handleLogout() {
    closeUserDropdown();
    closeProfileModal();
    try {
        await fetch("/api/auth/logout", { method: "POST" });
    } catch (e) {}
    clearCurrentUser();
}

function toggleUserDropdown(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const popover = document.getElementById("userDropdownPopover");
    if (!popover) return;
    const isVisible = popover.style.display === "block";
    popover.style.display = isVisible ? "none" : "block";
}

function closeUserDropdown() {
    const popover = document.getElementById("userDropdownPopover");
    if (popover) popover.style.display = "none";
}

function openProfileModal() {
    closeUserDropdown();
    const modal = document.getElementById("profileModal");
    if (modal) modal.style.display = "flex";
}

function closeProfileModal(e) {
    if (e && e.target && e.target !== e.currentTarget) return;
    const modal = document.getElementById("profileModal");
    if (modal) modal.style.display = "none";
}

function navigateToLogin(mode = "login") {
    window.location.href = mode === "register" ? "/signup" : "/login";
}

function handleSidebarProfileClick() {
    if (currentUser) {
        openProfileModal();
    } else {
        navigateToLogin("login");
    }
}



