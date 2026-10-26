/**
 * AURA // Futuristic AI HUD Controller
 * Manages Quantum Neural Canvas, Web Audio Procedural SFX,
 * Bidirectional Voice (STT & TTS), In-Chat Action Widgets,
 * Predictive Autocomplete, and Neural Telemetry Explainability.
 */

// Global State
let audioCtx = null;
let sfxEnabled = true;
let ttsEnabled = false;
let speechRecognizer = null;
let isRecordingVoice = false;
let activeUtterance = null;
let currentTheme = localStorage.getItem("aura_theme") || "cyberpunk";
let messageHistory = [];
let telemetryStore = [];

/* =====================================================================
   INITIALIZATION & EVENT LISTENERS
   ===================================================================== */
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initCyberClock();
    initNeuralCanvas();
    initSpeechRecognition();
    initKeyboardShortcuts();
    
    // Set welcome time
    const welcomeTime = document.getElementById("welcomeTime");
    if (welcomeTime) {
        welcomeTime.textContent = getCurrentCyberTime();
    }

    // Audio SFX state from storage
    const storedSFX = localStorage.getItem("aura_sfx");
    if (storedSFX !== null) {
        sfxEnabled = (storedSFX === "true");
        updateSFXButton();
    }

    // TTS state from storage
    const storedTTS = localStorage.getItem("aura_tts");
    if (storedTTS !== null) {
        ttsEnabled = (storedTTS === "true");
        updateTTSButton();
    }

    // Close predictive HUD and theme menu on outside click
    document.addEventListener("click", (e) => {
        const predHud = document.getElementById("predictiveHud");
        if (predHud && !predHud.contains(e.target) && e.target.id !== "queryInput") {
            predHud.style.display = "none";
        }
        const themeMenu = document.getElementById("themeMenu");
        if (themeMenu && !themeMenu.contains(e.target) && !e.target.closest("#themeBtn")) {
            themeMenu.classList.remove("active");
        }
    });

    // Delegated click handler for all suggested question pills and quick query buttons
    document.addEventListener("click", (e) => {
        const trigger = e.target.closest(".quick-btn, .sugg-pill, .starter-pill, .pred-item, [data-query]");
        if (trigger) {
            if (trigger.tagName === "BUTTON" || trigger.tagName === "A") {
                e.preventDefault();
            }
            sendQuickQuery(trigger);
        }
    });
});

/* =====================================================================
   REAL-TIME CYBER CLOCK
   ===================================================================== */
function initCyberClock() {
    const clockEl = document.getElementById("cyberClock");
    if (!clockEl) return;
    
    function updateClock() {
        const now = new Date();
        const h = String(now.getUTCHours()).padStart(2, '0');
        const m = String(now.getUTCMinutes()).padStart(2, '0');
        const s = String(now.getUTCSeconds()).padStart(2, '0');
        const ms = Math.floor(now.getUTCMilliseconds() / 100);
        clockEl.textContent = `${h}:${m}:${s}.${ms}`;
    }
    updateClock();
    setInterval(updateClock, 100);
}

function getCurrentCyberTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/* =====================================================================
   PROCEDURAL WEB AUDIO SYNTHESIZER (No external mp3 assets)
   ===================================================================== */
function getAudioContext() {
    if (!audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            audioCtx = new AudioContextClass();
        }
    }
    if (audioCtx && audioCtx.state === "suspended") {
        audioCtx.resume();
    }
    return audioCtx;
}

function playCyberChirp() {
    if (!sfxEnabled) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.08);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.12);
    } catch (e) {
        // AudioContext restricted or unsupported
    }
}

function playDecryptionChime() {
    if (!sfxEnabled) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;
        [523.25, 659.25, 1046.50].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + i * 0.06);
            gain.gain.setValueAtTime(0.06, now + i * 0.06);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.06 + 0.25);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + i * 0.06);
            osc.stop(now + i * 0.06 + 0.25);
        });
    } catch (e) {}
}

function playSonarPing() {
    if (!sfxEnabled) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1400, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.25);
    } catch (e) {}
}

function playTactileClick() {
    if (!sfxEnabled) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        gain.gain.setValueAtTime(0.03, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.03);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.03);
    } catch (e) {}
}

function toggleSFX() {
    sfxEnabled = !sfxEnabled;
    localStorage.setItem("aura_sfx", sfxEnabled);
    updateSFXButton();
    if (sfxEnabled) playCyberChirp();
}

function updateSFXButton() {
    const btn = document.getElementById("sfxBtnText");
    if (btn) btn.textContent = sfxEnabled ? "SFX: ON" : "SFX: OFF";
}

/* =====================================================================
   TEXT-TO-SPEECH (NEURAL VOICE SYNTHESIS)
   ===================================================================== */
function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    localStorage.setItem("aura_tts", ttsEnabled);
    updateTTSButton();
    if (ttsEnabled) {
        speakText("Neural voice vocalizer activated.");
    } else {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }
}

function updateTTSButton() {
    const btn = document.getElementById("ttsBtnText");
    if (btn) btn.textContent = ttsEnabled ? "Voice: ON" : "Voice: OFF";
}

function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    
    // Clean markdown/html for speech
    const clean = text.replace(/<[^>]*>?/gm, '')
                      .replace(/[*_#`◈⚡🛡️💳🎟️📡&bull;]/g, '')
                      .trim();
    
    if (!clean) return;

    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.05;
    utterance.pitch = 1.02;

    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Samantha") || v.name.includes("Jenny")));
    if (naturalVoice) {
        utterance.voice = naturalVoice;
    }

    activeUtterance = utterance;
    window.speechSynthesis.speak(utterance);
}

/* =====================================================================
   SPEECH-TO-TEXT (VOICE INPUT)
   ===================================================================== */
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech Recognition API not supported in this browser.");
        return;
    }

    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = true;
    speechRecognizer.lang = "en-US";

    speechRecognizer.onstart = () => {
        isRecordingVoice = true;
        playSonarPing();
        document.getElementById("micBtn").classList.add("recording");
        document.getElementById("voiceWaveformOverlay").style.display = "flex";
        document.getElementById("voiceStatusText").textContent = "LISTENING TO VOICE SYNAPSE...";
    };

    speechRecognizer.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        const input = document.getElementById("queryInput");
        if (input) input.value = transcript;
    };

    speechRecognizer.onerror = (event) => {
        stopVoiceRecognition();
    };

    speechRecognizer.onend = () => {
        stopVoiceRecognition();
        const input = document.getElementById("queryInput");
        if (input && input.value.trim().length > 1) {
            document.getElementById("chatForm").dispatchEvent(new Event("submit"));
        }
    };
}

function toggleVoiceRecognition() {
    if (!speechRecognizer) {
        alert("Speech Recognition is not supported by your browser. Please use Chrome, Edge, or Safari.");
        return;
    }
    if (isRecordingVoice) {
        speechRecognizer.stop();
        stopVoiceRecognition();
    } else {
        try {
            speechRecognizer.start();
        } catch (e) {
            stopVoiceRecognition();
        }
    }
}

function stopVoiceRecognition() {
    isRecordingVoice = false;
    const micBtn = document.getElementById("micBtn");
    if (micBtn) micBtn.classList.remove("recording");
    const overlay = document.getElementById("voiceWaveformOverlay");
    if (overlay) overlay.style.display = "none";
}

/* =====================================================================
   QUANTUM NEURAL CANVAS BACKGROUND
   ===================================================================== */
function initNeuralCanvas() {
    const canvas = document.getElementById("neuralCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener("resize", () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = Math.min(Math.floor((width * height) / 18000), 75);

    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.7,
            vy: (Math.random() - 0.5) * 0.7,
            radius: Math.random() * 2 + 1.2,
            pulse: Math.random() * Math.PI
        });
    }

    let mouse = { x: -1000, y: -1000 };
    window.addEventListener("mousemove", (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    function getThemeColors() {
        if (currentTheme === "matrix") return { p: "rgba(0, 255, 102,", l: "rgba(0, 255, 102," };
        if (currentTheme === "solar") return { p: "rgba(255, 136, 0,", l: "rgba(255, 80, 0," };
        if (currentTheme === "quantum") return { p: "rgba(99, 102, 241,", l: "rgba(139, 92, 246," };
        return { p: "rgba(0, 240, 255,", l: "rgba(168, 85, 247," };
    }

    function animateCanvas() {
        ctx.clearRect(0, 0, width, height);
        const colors = getThemeColors();

        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;

            p.pulse += 0.03;
            const r = p.radius + Math.sin(p.pulse) * 0.6;

            ctx.beginPath();
            ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
            ctx.fillStyle = `${colors.p} 0.7)`;
            ctx.shadowBlur = 8;
            ctx.shadowColor = `${colors.p} 0.5)`;
            ctx.fill();

            // Connect nearby nodes
            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 125) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    const alpha = (1 - dist / 125) * 0.25;
                    ctx.strokeStyle = `${colors.l} ${alpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.shadowBlur = 0;
                    ctx.stroke();
                }
            }

            // Connect to mouse pointer
            const mdx = p.x - mouse.x;
            const mdy = p.y - mouse.y;
            const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
            if (mdist < 140) {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(mouse.x, mouse.y);
                const mAlpha = (1 - mdist / 140) * 0.5;
                ctx.strokeStyle = `${colors.p} ${mAlpha})`;
                ctx.lineWidth = 1.2;
                ctx.stroke();
            }
        }
        requestAnimationFrame(animateCanvas);
    }
    animateCanvas();
}

/* =====================================================================
   THEME MANAGER
   ===================================================================== */
function initTheme() {
    setTheme(currentTheme);
}

function toggleThemeMenu() {
    playTactileClick();
    const menu = document.getElementById("themeMenu");
    if (menu) menu.classList.toggle("active");
}

function setTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("aura_theme", theme);

    const labels = {
        cyberpunk: "Cyber Neon",
        matrix: "Matrix Green",
        solar: "Solar Plasma",
        quantum: "Quantum Void"
    };

    const labelEl = document.getElementById("currentThemeLabel");
    if (labelEl) labelEl.textContent = labels[theme] || "Cyber Neon";

    const menu = document.getElementById("themeMenu");
    if (menu) menu.classList.remove("active");
    playTactileClick();
}

/* =====================================================================
   PREDICTIVE AUTOCOMPLETE HUD
   ===================================================================== */
let predDebounceTimer = null;
async function handleInputPredictive(val) {
    clearTimeout(predDebounceTimer);
    const hud = document.getElementById("predictiveHud");
    const list = document.getElementById("predictiveList");
    const clean = val.trim();

    if (!clean || clean.length < 2) {
        hud.style.display = "none";
        return;
    }

    predDebounceTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/api/suggest?q=${encodeURIComponent(clean)}`);
            const data = await res.json();

            if (data.success && data.suggestions && data.suggestions.length > 0) {
                list.innerHTML = data.suggestions.map(s => `
                    <div class="pred-item" data-query="${escapeHTML(s.question)}" onclick="sendQuickQuery(this)">
                        <span class="pred-q font-mono">◈ ${escapeHTML(s.question)}</span>
                        <div class="pred-meta">
                            <span class="pred-badge">${escapeHTML(s.category)}</span>
                            <span class="conf-pill conf-high">${Math.round(s.score * 100)}%</span>
                        </div>
                    </div>
                `).join("");
                hud.style.display = "block";
            } else {
                hud.style.display = "none";
            }
        } catch (e) {
            hud.style.display = "none";
        }
    }, 180);
}

/* =====================================================================
   CHAT MESSAGING & RENDERING ENGINE
   ===================================================================== */
function scrollToBottom() {
    const container = document.getElementById("chatMessages");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function appendUserMessage(text) {
    const container = document.getElementById("chatMessages");
    const row = document.createElement("div");
    row.className = "message-row user-row";
    row.innerHTML = `
        <div class="msg-avatar font-orbitron">ME</div>
        <div class="msg-bubble">
            <div class="bubble-header-hud">
                <span class="hud-tag">USER TRANSMISSION</span>
                <span class="hud-status">AUTHENTICATED</span>
            </div>
            <p>${escapeHTML(text)}</p>
            <div class="msg-meta">
                <span class="msg-time">${getCurrentCyberTime()}</span>
            </div>
        </div>
    `;
    container.appendChild(row);
    scrollToBottom();
    playCyberChirp();

    messageHistory.push({
        sender: "USER",
        text: text,
        time: new Date().toISOString()
    });
}

function appendBotResponse(response) {
    const container = document.getElementById("chatMessages");
    const row = document.createElement("div");
    row.className = "message-row bot-row";

    // Store telemetry
    const telemetryIdx = telemetryStore.length;
    // Store telemetry and answer text safely without inline quote issues
    const rawAnswer = response.text || "";
    telemetryStore.push({
        ...(response.telemetry || {}),
        answerText: rawAnswer
    });

    // Confidence badge
    let confBadge = "";
    if (response.confidence && response.confidence > 0) {
        const confPct = Math.round(response.confidence * 100);
        const confClass = response.confidence >= 0.38 ? "conf-high" : (response.confidence >= 0.20 ? "conf-mod" : "conf-low");
        confBadge = `<span class="conf-pill ${confClass}">${confPct}% Match</span>`;
    }

    // Category badge
    let categoryBadge = "";
    if (response.category) {
        categoryBadge = `<span style="color: var(--primary); font-weight: 600;">[${escapeHTML(response.category)}]</span>`;
    }

    // Latency badge
    let latencyBadge = "";
    if (response.telemetry && response.telemetry.latency_ms) {
        latencyBadge = `<span class="font-mono text-neon-cyan">⚡ ${response.telemetry.latency_ms} ms</span>`;
        const sidebarLatency = document.getElementById("sidebarLatency");
        if (sidebarLatency) sidebarLatency.textContent = `${response.telemetry.latency_ms} ms`;
    }

    // Sentiment badge
    let sentimentBadge = "";
    if (response.sentiment) {
        sentimentBadge = `<span title="${escapeHTML(response.sentiment.label)}" style="cursor:help;">${response.sentiment.icon} ${escapeHTML(response.sentiment.label)}</span>`;
    }

    // Interactive Action Widget
    let actionWidgetHtml = "";
    if (response.action_widget) {
        actionWidgetHtml = renderActionWidget(response.action_widget);
    }

    // Alternatives
    let alternativesHtml = "";
    if (response.alternatives && response.alternatives.length > 0) {
        alternativesHtml = `
            <div class="quick-suggestions-box">
                <span class="sugg-label font-mono">◈ RELATED NEURAL PATTERNS:</span>
                <div class="sugg-pills">
                    ${response.alternatives.map(alt => `
                        <button type="button" class="sugg-pill" data-query="${escapeHTML(alt.question)}" onclick="sendQuickQuery(this)">
                            <span class="pill-spark">&rsaquo;</span> ${escapeHTML(alt.question)}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;
    }

    // Suggestions
    let suggestionsHtml = "";
    if (response.suggestions && response.suggestions.length > 0) {
        suggestionsHtml = `
            <div class="quick-suggestions-box">
                <span class="sugg-label font-mono">◈ RECOMMENDED TRANSMISSIONS:</span>
                <div class="sugg-pills">
                    ${response.suggestions.map(sug => `
                        <button type="button" class="sugg-pill" data-query="${escapeHTML(sug)}" onclick="sendQuickQuery(this)">
                            <span class="pill-spark">⚡</span> ${escapeHTML(sug)}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;
    }

    row.innerHTML = `
        <div class="msg-avatar font-orbitron">AI</div>
        <div class="msg-bubble">
            <div class="bubble-header-hud">
                <span class="hud-tag">AURA // SYNAPSE ANSWER</span>
                <span class="hud-status font-mono">MATCH STATUS: ${escapeHTML(response.status || "PROCESSED")}</span>
            </div>
            <div class="bot-text-content" id="botText-${telemetryIdx}"></div>
            ${actionWidgetHtml}
            ${suggestionsHtml}
            ${alternativesHtml}
            <div class="msg-meta">
                <span class="msg-time">${getCurrentCyberTime()}</span>
                ${categoryBadge}
                ${confBadge}
                ${latencyBadge}
                ${sentimentBadge}
                <button class="vocalize-btn" onclick="vocalizeMessage(${telemetryIdx})" title="Read Aloud with AI Voice">
                    🔊 Vocalize
                </button>
                <button class="telemetry-chip-btn" onclick="showTelemetryModal(${telemetryIdx})" title="Inspect Vector Math & NLP Telemetry">
                    ◈ Neural Math
                </button>
            </div>
        </div>
    `;

    container.appendChild(row);
    scrollToBottom();

    // Typewriter Decryption Stream Animation
    streamTypewriterText(`botText-${telemetryIdx}`, rawAnswer, () => {
        playDecryptionChime();
        if (ttsEnabled) {
            speakText(rawAnswer);
        }
    });

    messageHistory.push({
        sender: "AI",
        text: rawAnswer,
        confidence: response.confidence,
        time: new Date().toISOString(),
        telemetry: response.telemetry
    });
}

/* =====================================================================
   HIGH-SPEED TYPEWRITER DECRYPTION STREAM
   ===================================================================== */
function streamTypewriterText(elementId, fullText, onComplete) {
    const el = document.getElementById(elementId);
    if (!el) return;

    let index = 0;
    const formatted = formatMessageContent(fullText);
    const speed = 14; // ms per char for crisp futuristic stream

    el.innerHTML = '<span class="typing-cursor"></span>';

    function typeNext() {
        if (index < fullText.length) {
            index++;
            el.innerHTML = formatMessageContent(fullText.substring(0, index)) + '<span class="typing-cursor"></span>';
            scrollToBottom();
            setTimeout(typeNext, speed);
        } else {
            el.innerHTML = formatted;
            if (onComplete) onComplete();
        }
    }
    typeNext();
}

function formatMessageContent(text) {
    if (!text) return "";
    return escapeHTML(text).replace(/\n/g, "<br>");
}

function escapeHTML(str) {
    if (!str) return "";
    return String(str).replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

/* =====================================================================
   INTERACTIVE HOLOGRAPHIC ACTION WIDGETS
   ===================================================================== */
function renderActionWidget(widget) {
    if (!widget) return "";

    // 1. Order Tracking Radar Widget
    if (widget.type === "order_tracker") {
        return `
            <div class="action-widget-card">
                <div class="widget-header">
                    <span class="widget-title">🛰️ ${escapeHTML(widget.title)}</span>
                    <span class="font-mono text-neon-cyan">${escapeHTML(widget.status)}</span>
                </div>
                <div class="tracking-timeline">
                    ${widget.checkpoints.map(cp => `
                        <div class="timeline-node ${cp.done ? 'done' : (cp.active ? 'active' : '')}">
                            <span class="node-bullet"></span>
                            <span class="node-title">${escapeHTML(cp.label)}</span>
                            <span class="node-time">${escapeHTML(cp.time)}</span>
                        </div>
                    `).join("")}
                </div>
                <div class="tracking-info-bar">
                    <span>TRACKING ID: <strong>${escapeHTML(widget.tracking_code)}</strong></span>
                    <span>CARRIER: <strong>${escapeHTML(widget.carrier)}</strong></span>
                    <span>ETA: <strong class="text-neon-green">${escapeHTML(widget.eta)}</strong></span>
                </div>
            </div>
        `;
    }

    // 2. Instant Return RMA Card
    if (widget.type === "return_rma") {
        return `
            <div class="action-widget-card">
                <div class="widget-header">
                    <span class="widget-title">📦 ${escapeHTML(widget.title)}</span>
                    <span class="conf-pill conf-high">${escapeHTML(widget.policy_window)}</span>
                </div>
                <div class="rma-box">
                    <div style="font-size:0.7rem; color:var(--text-muted); margin-bottom:4px;">DIGITAL RETURN RMA BARCODE</div>
                    <div class="rma-barcode">||| | |||| | ||||| | ||</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#fff; margin-top:6px;">RMA #${escapeHTML(widget.rma_code)}</div>
                </div>
                <button class="rma-btn" onclick="alert('Digital Return Label Generated & Sent to Your Registered Email!'); playCyberChirp();">
                    ◈ ${escapeHTML(widget.action_label)}
                </button>
            </div>
        `;
    }

    // 3. Cyber Discount Promo Vault
    if (widget.type === "promo_code") {
        return `
            <div class="action-widget-card">
                <div class="widget-header">
                    <span class="widget-title">🎟️ ${escapeHTML(widget.title)}</span>
                    <span class="font-mono text-neon-green">ACTIVE COUPONS</span>
                </div>
                <div class="promo-grid">
                    ${widget.codes.map(c => `
                        <div class="promo-card" onclick="copyPromoCode('${escapeHTML(c.code)}')">
                            <span class="promo-code-txt">${escapeHTML(c.code)}</span>
                            <span style="font-size:0.75rem; color:var(--success); font-weight:700;">${escapeHTML(c.discount)}</span>
                            <span class="promo-desc">${escapeHTML(c.description)}</span>
                            <span style="font-size:0.62rem; color:var(--primary); margin-top:4px;">[CLICK TO COPY]</span>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    // 4. Quantum Security Shield
    if (widget.type === "security_shield") {
        return `
            <div class="action-widget-card">
                <div class="widget-header">
                    <span class="widget-title">🛡️ ${escapeHTML(widget.title)}</span>
                    <span class="conf-pill conf-high">VERIFIED SECURE</span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; font-size:0.74rem;">
                    <div style="background:rgba(0,0,0,0.4); padding:8px; border-radius:6px;">
                        <span style="color:var(--text-muted); font-size:0.65rem;">CIPHER</span>
                        <div style="color:var(--primary); font-weight:700;">${escapeHTML(widget.encryption)}</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.4); padding:8px; border-radius:6px;">
                        <span style="color:var(--text-muted); font-size:0.65rem;">AUDIT CERT</span>
                        <div style="color:var(--success); font-weight:700;">${escapeHTML(widget.pci_dss)}</div>
                    </div>
                </div>
            </div>
        `;
    }

    // 5. Live Human Support Uplink
    if (widget.type === "live_uplink") {
        return `
            <div class="action-widget-card">
                <div class="widget-header">
                    <span class="widget-title">📡 ${escapeHTML(widget.title)}</span>
                    <span class="conf-pill conf-high">CHANNEL OPEN</span>
                </div>
                <div class="radar-wrap">
                    <div class="radar-sweep"></div>
                    <div>
                        <div style="font-weight:700; color:#fff; font-size:0.82rem;">${escapeHTML(widget.rep_name)}</div>
                        <div style="font-size:0.72rem; color:var(--text-secondary);">Direct Bridge: ${escapeHTML(widget.phone)} &bull; ${escapeHTML(widget.email)}</div>
                        <div style="font-size:0.68rem; color:var(--success); margin-top:3px;">QUEUE POSITION: #${widget.queue_position} &bull; EST. WAIT: ${escapeHTML(widget.estimated_wait)}</div>
                    </div>
                </div>
            </div>
        `;
    }

    return "";
}

function copyPromoCode(code) {
    navigator.clipboard.writeText(code);
    playCyberChirp();
    alert(`Promo Code '${code}' copied to clipboard!`);
}

/* =====================================================================
   NEURAL TELEMETRY EXPLAINABILITY MODAL
   ===================================================================== */
function showTelemetryModal(teleIdx) {
    playTactileClick();
    const telemetry = telemetryStore[teleIdx] || {};
    const modal = document.getElementById("telemetryModal");
    const body = document.getElementById("telemetryModalBody");
    if (!modal || !body) return;

    const nlp = telemetry.nlp_data || {};
    const terms = telemetry.top_terms || [];

    body.innerHTML = `
        <!-- Latency & Model Overview -->
        <div class="telemetry-section-box">
            <div class="box-heading">◈ COGNITIVE EXECUTION METRICS</div>
            <div class="telemetry-grid">
                <div class="telemetry-card">
                    <span class="tele-label">PROCESSING LATENCY</span>
                    <span class="tele-val text-neon-cyan">${telemetry.latency_ms || "3.2"} ms</span>
                </div>
                <div class="telemetry-card">
                    <span class="tele-label">COSINE SIMILARITY</span>
                    <span class="tele-val text-neon-green">${telemetry.cos_score || "1.000"}</span>
                </div>
                <div class="telemetry-card">
                    <span class="tele-label">CONTENT TOKEN OVERLAP</span>
                    <span class="tele-val text-neon-purple">${Math.round((telemetry.overlap_ratio || 1.0) * 100)}% Overlap</span>
                </div>
                <div class="telemetry-card">
                    <span class="tele-label">VECTOR SPACE DIMENSIONS</span>
                    <span class="tele-val">${telemetry.vector_dimension || 384} Features</span>
                </div>
            </div>
        </div>

        <!-- Formula Breakdown -->
        <div class="telemetry-section-box">
            <div class="box-heading">◈ HYBRID SCORING FORMULA</div>
            <div class="formula-highlight">
                ${escapeHTML(telemetry.formula || "0.70 × CosineSim + 0.30 × OverlapRatio = FinalConfidence")}
            </div>
        </div>

        <!-- NLP Preprocessing Pipeline Breakdown -->
        <div class="telemetry-section-box">
            <div class="box-heading">◈ NLTK PREPROCESSING PIPELINE BREAKDOWN</div>
            <div style="display:flex; flex-direction:column; gap:8px; font-size:0.75rem; font-family:'JetBrains Mono', monospace;">
                <div><span style="color:var(--text-muted)">1. RAW USER INPUT:</span> <span style="color:#fff;">"${escapeHTML(nlp.raw_text || '')}"</span></div>
                <div><span style="color:var(--text-muted)">2. CONTRACTIONS EXPANDED:</span> <span style="color:var(--primary);">${escapeHTML(nlp.expanded_text || '')}</span></div>
                <div><span style="color:var(--text-muted)">3. LEMMATIZED TOKENS:</span> <span style="color:var(--accent);">${escapeHTML(nlp.lemmatized_str || '')}</span></div>
                <div><span style="color:var(--text-muted)">4. CONTENT KEYWORDS GATED:</span> <span style="color:var(--success); font-weight:700;">[${(nlp.content_tokens || []).join(", ")}]</span></div>
            </div>
        </div>

        <!-- Top TF-IDF Terms Bar Chart -->
        ${terms.length > 0 ? `
            <div class="telemetry-section-box">
                <div class="box-heading">◈ TOP TF-IDF FEATURE WEIGHTS</div>
                <div style="margin-top: 10px;">
                    ${terms.map(t => `
                        <div class="term-bar-row">
                            <span class="term-name font-mono">${escapeHTML(t.term)}</span>
                            <div class="term-bar-track">
                                <div class="term-bar-fill" style="width: ${Math.min(t.weight * 100, 100)}%;"></div>
                            </div>
                            <span class="term-weight">${t.weight.toFixed(3)}</span>
                        </div>
                    `).join("")}
                </div>
            </div>
        ` : ''}
    `;

    modal.style.display = "flex";
}

function hideTelemetryModal() {
    playTactileClick();
    const modal = document.getElementById("telemetryModal");
    if (modal) modal.style.display = "none";
}

function closeTelemetryModal(e) {
    if (e.target.id === "telemetryModal") {
        hideTelemetryModal();
    }
}

/* =====================================================================
   TYPING INDICATOR
   ===================================================================== */
function showTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.style.display = "flex";
    scrollToBottom();
}

function hideTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.style.display = "none";
}

/* =====================================================================
   FORM SUBMISSION & MESSAGE DISPATCH
   ===================================================================== */
async function handleChatSubmit(event) {
    if (event) event.preventDefault();
    const input = document.getElementById("queryInput");
    const query = input ? input.value.trim() : "";
    if (!query) return;
    submitMessage(query);
}

let lastSubmittedQuery = "";
let lastSubmittedTime = 0;

function sendQuickQuery(inputOrText) {
    playTactileClick();
    let query = "";
    if (typeof inputOrText === "string") {
        query = inputOrText;
    } else if (inputOrText && typeof inputOrText === "object") {
        let el = inputOrText;
        if (inputOrText.target) {
            el = inputOrText.currentTarget || (inputOrText.target.closest ? inputOrText.target.closest("button, [data-query]") : inputOrText.target);
        }
        if (el && el.getAttribute && el.getAttribute("data-query")) {
            query = el.getAttribute("data-query");
        } else if (el && el.dataset && el.dataset.query) {
            query = el.dataset.query;
        } else if (el && el.querySelector && el.querySelector(".btn-txt")) {
            query = el.querySelector(".btn-txt").textContent.trim();
        } else if (el && el.innerText) {
            query = el.innerText.replace(/^[◈⚡›\s]+/, "").trim();
        }
    }

    query = (query || "").trim();
    if (!query) return;

    // Deduplication guard (prevents rapid double-fires from inline onclick + document listener)
    const now = Date.now();
    if (query === lastSubmittedQuery && (now - lastSubmittedTime) < 400) {
        return;
    }
    lastSubmittedQuery = query;
    lastSubmittedTime = now;

    const input = document.getElementById("queryInput");
    if (input) input.value = query;

    submitMessage(query);
}

function sendQuickQueryFromBtn(btn) {
    sendQuickQuery(btn);
}

function vocalizeMessage(telemetryIdx) {
    playTactileClick();
    const item = telemetryStore[telemetryIdx];
    if (item && item.answerText) {
        speakText(item.answerText);
    }
}

async function submitMessage(query) {
    const cleanQuery = (query || "").trim();
    if (!cleanQuery) return;

    if (isRecordingVoice) {
        stopVoiceRecognition();
    }

    const input = document.getElementById("queryInput");
    if (input) input.value = "";

    const predHud = document.getElementById("predictiveHud");
    if (predHud) predHud.style.display = "none";

    appendUserMessage(cleanQuery);
    showTypingIndicator();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: cleanQuery })
        });
        const data = await response.json();
        hideTypingIndicator();

        if (data.success && data.response) {
            appendBotResponse(data.response);
        } else {
            appendBotResponse({
                text: "Sorry, I encountered an issue processing your question in the neural network.",
                confidence: 0
            });
        }
    } catch (err) {
        hideTypingIndicator();
        appendBotResponse({
            text: "Connection error: Unable to connect to neural API server.",
            confidence: 0
        });
    }
}

function clearChat() {
    playTactileClick();
    const container = document.getElementById("chatMessages");
    container.innerHTML = `
        <div class="message-row bot-row">
            <div class="msg-avatar font-orbitron">AI</div>
            <div class="msg-bubble">
                <div class="bubble-header-hud">
                    <span class="hud-tag">BUFFER PURGED & RESET</span>
                    <span class="hud-status font-mono">READY</span>
                </div>
                <p>Neural conversational memory cleared. How may I assist your inquiries now?</p>
                <div class="msg-meta">
                    <span class="msg-time">${getCurrentCyberTime()}</span>
                </div>
            </div>
        </div>
    `;
    messageHistory = [];
}

/* =====================================================================
   SIDEBAR TOPIC FILTERING
   ===================================================================== */
function filterSidebarTopics(query) {
    const q = query.toLowerCase().trim();
    const groups = document.querySelectorAll(".category-group");

    groups.forEach(group => {
        const cat = group.getAttribute("data-cat") || "";
        const buttons = group.querySelectorAll(".quick-btn");
        let hasMatch = cat.includes(q);

        buttons.forEach(btn => {
            const txt = btn.textContent.toLowerCase();
            if (txt.includes(q)) {
                btn.style.display = "flex";
                hasMatch = true;
            } else {
                btn.style.display = q ? "none" : "flex";
            }
        });

        group.style.display = hasMatch ? "block" : "none";
    });
}

/* =====================================================================
   SESSION EXPORTER
   ===================================================================== */
function exportSessionLog() {
    playTactileClick();
    const audit = {
        session_id: "AURA-" + Math.random().toString(36).substring(2, 10).toUpperCase(),
        timestamp: new Date().toISOString(),
        security_protocol: "TLS 1.3 / Quantum SHA-256",
        engine: "NLTK TF-IDF + Cosine Vector Engine",
        messages: messageHistory
    };

    const blob = new Blob([JSON.stringify(audit, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aura_cyber_audit_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/* =====================================================================
   KEYBOARD SHORTCUTS
   ===================================================================== */
function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        // Ctrl+M: Toggle Voice Recording
        if (e.ctrlKey && (e.key === "m" || e.key === "M")) {
            e.preventDefault();
            toggleVoiceRecognition();
        }
        // Ctrl+K or /: Focus query input
        if ((e.ctrlKey && (e.key === "k" || e.key === "K")) || (e.key === "/" && document.activeElement.tagName !== "INPUT")) {
            e.preventDefault();
            const input = document.getElementById("queryInput");
            if (input) input.focus();
        }
        // Escape: Close predictive HUD & modals
        if (e.key === "Escape") {
            const predHud = document.getElementById("predictiveHud");
            if (predHud) predHud.style.display = "none";
            hideTelemetryModal();
            stopVoiceRecognition();
        }
    });
}
