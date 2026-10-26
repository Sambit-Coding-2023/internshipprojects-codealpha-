/**
 * Task 4: Intelligent Vision & Multi-Object Tracking UI Controller
 * Handles live telemetry polling, interactive parameter push, Web Audio alerts,
 * image inspection analysis, snapshot capture, and incident log audits.
 */

let statsInterval = null;
let lastInCount = 0;
let lastOutCount = 0;
let audioAlertsEnabled = true;
let currentTab = "live";

// UI Element References
const confSlider = document.getElementById("confSlider");
const confVal = document.getElementById("confVal");
const tripwireSlider = document.getElementById("tripwireSlider");
const tripwireVal = document.getElementById("tripwireVal");

const boxesToggle = document.getElementById("boxesToggle");
const trailsToggle = document.getElementById("trailsToggle");
const speedToggle = document.getElementById("speedToggle");
const tripwireToggle = document.getElementById("tripwireToggle");
const zoneToggle = document.getElementById("zoneToggle");
const heatmapToggle = document.getElementById("heatmapToggle");

// Telemetry Stats
const statFps = document.getElementById("statFps");
const statActive = document.getElementById("statActive");
const statTotal = document.getElementById("statTotal");
const statIn = document.getElementById("statIn");
const statOut = document.getElementById("statOut");
const statZone = document.getElementById("statZone");

const hudFps = document.getElementById("hudFps");
const hudActive = document.getElementById("hudActive");
const hudIn = document.getElementById("hudIn");
const hudOut = document.getElementById("hudOut");

const classChips = document.getElementById("classChips");
const streamTitle = document.getElementById("streamTitle");
const activeSourceBadge = document.getElementById("activeSourceBadge");
const eventStream = document.getElementById("eventStream");
const auditTableBody = document.getElementById("auditTableBody");

// Sources Buttons
const srcRealBtn = document.getElementById("srcRealBtn");
const srcSampleBtn = document.getElementById("srcSampleBtn");
const srcWebcamBtn = document.getElementById("srcWebcamBtn");
const srcUploadBtn = document.getElementById("srcUploadBtn");
const videoFileInput = document.getElementById("videoFileInput");

document.addEventListener("DOMContentLoaded", () => {
    // Slider listeners
    if (confSlider) {
        confSlider.addEventListener("input", () => {
            confVal.textContent = parseFloat(confSlider.value).toFixed(2);
        });
    }

    if (tripwireSlider) {
        tripwireSlider.addEventListener("input", () => {
            const pct = Math.round(parseFloat(tripwireSlider.value) * 100);
            tripwireVal.textContent = pct + "%";
        });
    }

    startStatsPolling();
});

/* ==========================================================================
   Tab Navigation
   ========================================================================== */
function switchTab(tabId) {
    currentTab = tabId;

    document.querySelectorAll(".mode-tab").forEach(tab => tab.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

    if (tabId === "live") {
        document.getElementById("tabLiveBtn").classList.add("active");
        document.getElementById("tabContentLive").classList.add("active");
    } else if (tabId === "image") {
        document.getElementById("tabImageBtn").classList.add("active");
        document.getElementById("tabContentImage").classList.add("active");
    } else if (tabId === "events") {
        document.getElementById("tabEventsBtn").classList.add("active");
        document.getElementById("tabContentEvents").classList.add("active");
    }
}

/* ==========================================================================
   Telemetry Polling
   ========================================================================== */
function startStatsPolling() {
    if (statsInterval) clearInterval(statsInterval);
    statsInterval = setInterval(fetchStats, 500);
}

async function fetchStats() {
    try {
        const response = await fetch("/api/stats");
        if (!response.ok) return;
        const data = await response.json();

        // Update counters
        statFps.textContent = data.fps.toFixed(1);
        statActive.textContent = data.active_count;
        statTotal.textContent = data.total_tracks;
        statIn.textContent = data.in_count;
        statOut.textContent = data.out_count;
        statZone.textContent = data.in_zone_count;

        hudFps.textContent = data.fps.toFixed(1);
        hudActive.textContent = data.active_count;
        hudIn.textContent = data.in_count;
        hudOut.textContent = data.out_count;

        // Check for line crossing audio alert trigger
        if (data.in_count > lastInCount || data.out_count > lastOutCount) {
            playAlertSound("crossing");
            lastInCount = data.in_count;
            lastOutCount = data.out_count;
        }

        // Render active class badges
        renderClassBadges(data.class_counts);

        // Render incident event stream
        if (data.recent_events) {
            renderEventStream(data.recent_events);
            if (currentTab === "events") {
                renderAuditTable(data.recent_events);
            }
        }
    } catch (err) {
        console.warn("Telemetry fetch error:", err);
    }
}

function renderClassBadges(counts) {
    if (!classChips) return;
    const keys = Object.keys(counts || {});
    if (keys.length === 0) {
        classChips.innerHTML = `<span class="empty-hint">Scanning frame for objects...</span>`;
        return;
    }

    classChips.innerHTML = keys.map(k => `
        <span class="class-badge">${k.toUpperCase()}: <strong>${counts[k]}</strong></span>
    `).join("");
}

function renderEventStream(events) {
    if (!eventStream) return;
    if (!events || events.length === 0) {
        eventStream.innerHTML = `<div class="empty-event-hint">Awaiting line crossing and intrusion events...</div>`;
        return;
    }

    eventStream.innerHTML = events.slice(0, 8).map(e => {
        let rowClass = "event-row";
        if (e.event_type === "LINE_CROSSING") {
            rowClass += e.details.includes("IN") ? " crossing-in" : " crossing-out";
        } else if (e.event_type === "ZONE_INTRUSION") {
            rowClass += " zone-intrusion";
        }

        return `
            <div class="${rowClass}">
                <span class="event-time">${e.timestamp}</span>
                <span class="event-desc">#${e.track_id} ${e.class_name.toUpperCase()} - ${e.details}</span>
                <span class="event-speed">${e.speed_kmh > 0 ? e.speed_kmh + ' km/h' : ''}</span>
            </div>
        `;
    }).join("");
}

function renderAuditTable(events) {
    if (!auditTableBody) return;
    if (!events || events.length === 0) {
        auditTableBody.innerHTML = `<tr><td colspan="6" class="table-empty">No events logged yet.</td></tr>`;
        return;
    }

    auditTableBody.innerHTML = events.map(e => `
        <tr>
            <td>${e.timestamp}</td>
            <td><strong>#${e.track_id}</strong></td>
            <td><span class="class-badge">${e.class_name.toUpperCase()}</span></td>
            <td>${e.event_type}</td>
            <td>${e.details}</td>
            <td>${e.speed_kmh} km/h</td>
        </tr>
    `).join("");
}

/* ==========================================================================
   Source Selection & Upload
   ========================================================================== */
async function setSource(sourceName) {
    [srcRealBtn, srcSampleBtn, srcWebcamBtn, srcUploadBtn].forEach(b => b && b.classList.remove("active"));

    if (sourceName === "real_traffic") {
        if (srcRealBtn) srcRealBtn.classList.add("active");
        streamTitle.textContent = "SURVEILLANCE VIDEO (YOLOV8 + KALMAN)";
        activeSourceBadge.textContent = "Real Traffic";
    } else if (sourceName === "sample") {
        if (srcSampleBtn) srcSampleBtn.classList.add("active");
        streamTitle.textContent = "SYNTHETIC TRAFFIC SIMULATION";
        activeSourceBadge.textContent = "Synthetic Sim";
    } else if (sourceName === "webcam") {
        if (srcWebcamBtn) srcWebcamBtn.classList.add("active");
        streamTitle.textContent = "LIVE WEBCAM STREAM (CAMERA 0)";
        activeSourceBadge.textContent = "Live Webcam";
    }

    try {
        const resp = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: sourceName })
        });
        const res = await resp.json();
        if (res.note && res.note.includes("Fallback")) {
            if (srcRealBtn) srcRealBtn.classList.add("active");
            if (srcWebcamBtn) srcWebcamBtn.classList.remove("active");
            streamTitle.textContent = "REAL TRAFFIC (WEBCAM UNAVAILABLE)";
            activeSourceBadge.textContent = "Real Traffic";
        }
    } catch (e) {
        console.warn("Error setting source:", e);
    }

    refreshVideoFeed();
}

function triggerVideoUpload() {
    if (videoFileInput) videoFileInput.click();
}

async function uploadVideoFile(inputEl) {
    if (!inputEl.files || inputEl.files.length === 0) return;
    const file = inputEl.files[0];

    const formData = new FormData();
    formData.append("video", file);

    streamTitle.textContent = `UPLOADING: ${file.name.toUpperCase()}...`;

    try {
        const resp = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            [srcRealBtn, srcSampleBtn, srcWebcamBtn].forEach(b => b && b.classList.remove("active"));
            if (srcUploadBtn) srcUploadBtn.classList.add("active");
            streamTitle.textContent = `CUSTOM: ${file.name.toUpperCase()}`;
            activeSourceBadge.textContent = "Custom Video";
            refreshVideoFeed();
        } else {
            alert("Upload failed: " + data.error);
            setSource("real_traffic");
        }
    } catch (err) {
        alert("Upload error: " + err.message);
        setSource("real_traffic");
    } finally {
        inputEl.value = "";
    }
}

function refreshVideoFeed() {
    const img = document.getElementById("videoFeed");
    if (img) {
        img.src = "/video_feed?t=" + new Date().getTime();
    }
}

/* ==========================================================================
   Parameters & Layer Toggles
   ========================================================================== */
async function updateSettings() {
    const conf = parseFloat(confSlider.value);
    const trails = trailsToggle.checked;
    const boxes = boxesToggle.checked;
    const speed = speedToggle.checked;
    const tripwire = tripwireToggle.checked;
    const zone = zoneToggle.checked;
    const heatmap = heatmapToggle.checked;

    await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            conf_threshold: conf,
            show_trails: trails,
            show_boxes: boxes,
            show_speed: speed,
            show_tripwire: tripwire,
            show_zone: zone,
            show_heatmap: heatmap
        })
    });
}

async function updateTripwirePosition(val) {
    await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tripwire_y: parseFloat(val) })
    });
}

async function setClassFilter(preset) {
    document.querySelectorAll(".filter-pills .pill").forEach(p => p.classList.remove("active"));
    event.target.classList.add("active");

    const filterList = (preset === "all") ? [] : [preset];
    await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ class_filter: filterList })
    });
}

async function resetTracker() {
    await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset: true })
    });
    lastInCount = 0;
    lastOutCount = 0;
}

async function clearEvents() {
    await fetch("/api/clear_events", { method: "POST" });
    if (eventStream) eventStream.innerHTML = `<div class="empty-event-hint">Event log cleared.</div>`;
    if (auditTableBody) auditTableBody.innerHTML = `<tr><td colspan="6" class="table-empty">Event log cleared.</td></tr>`;
}

/* ==========================================================================
   Snapshot & Fullscreen
   ========================================================================== */
function takeSnapshot() {
    const link = document.createElement("a");
    link.href = "/api/snapshot?t=" + new Date().getTime();
    link.download = `surveillance_snapshot_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function toggleFullScreen() {
    const elem = document.getElementById("videoWrapper");
    if (!document.fullscreenElement) {
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

/* ==========================================================================
   Web Audio Synthesizer Alerts
   ========================================================================== */
function toggleAudioAlerts() {
    audioAlertsEnabled = !audioAlertsEnabled;
    const btn = document.getElementById("audioToggleBtn");
    const icon = document.getElementById("audioIcon");
    const label = document.getElementById("audioLabel");

    if (audioAlertsEnabled) {
        icon.textContent = "🔔";
        label.textContent = "Alerts: ON";
        btn.classList.remove("muted");
    } else {
        icon.textContent = "🔕";
        label.textContent = "Alerts: OFF";
        btn.classList.add("muted");
    }
}

function playAlertSound(type = "crossing") {
    if (!audioAlertsEnabled) return;
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === "crossing") {
            // Futuristic pleasant chime
            osc.type = "sine";
            osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
            osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15); // A5
            gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.3);
        }
    } catch (e) {
        // AudioContext may be restricted by browser before user interaction
    }
}

/* ==========================================================================
   TAB 2: Static Image Inspector
   ========================================================================== */
const imageFileInput = document.getElementById("imageFileInput");
const imageViewBox = document.getElementById("imageViewBox");
const imageSummaryStrip = document.getElementById("imageSummaryStrip");
const imgTotalDets = document.getElementById("imgTotalDets");
const imgInferenceTime = document.getElementById("imgInferenceTime");
const imgDimensions = document.getElementById("imgDimensions");
const detectionsTableBody = document.getElementById("detectionsTableBody");
const downloadAnnotatedBtn = document.getElementById("downloadAnnotatedBtn");

function triggerImageUpload() {
    if (imageFileInput) imageFileInput.click();
}

async function processUploadedImage(inputEl) {
    if (!inputEl.files || inputEl.files.length === 0) return;
    const file = inputEl.files[0];

    const conf = document.getElementById("imgConfSlider").value;
    const formData = new FormData();
    formData.append("image", file);
    formData.append("conf", conf);

    imageViewBox.innerHTML = `<div class="table-empty">Running YOLOv8 Deep Neural Analysis...</div>`;

    try {
        const resp = await fetch("/api/detect_image", {
            method: "POST",
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            renderImageResults(data);
        } else {
            alert("Analysis failed: " + data.error);
        }
    } catch (err) {
        alert("Error analyzing image: " + err.message);
    } finally {
        inputEl.value = "";
    }
}

async function loadSampleImage() {
    const conf = document.getElementById("imgConfSlider").value;
    const formData = new FormData();
    formData.append("use_sample", "true");
    formData.append("conf", conf);

    imageViewBox.innerHTML = `<div class="table-empty">Loading & Analyzing Sample Street Scene...</div>`;

    try {
        const resp = await fetch("/api/detect_image", {
            method: "POST",
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            renderImageResults(data);
        } else {
            alert("Sample analysis failed: " + data.error);
        }
    } catch (err) {
        alert("Error analyzing sample: " + err.message);
    }
}

function renderImageResults(data) {
    // 1. Display Image
    imageViewBox.innerHTML = `<img src="${data.annotated_image}" alt="Annotated Detection Result">`;

    // 2. Summary stats
    imageSummaryStrip.style.display = "flex";
    imgTotalDets.textContent = data.total_detections;
    imgInferenceTime.textContent = `${data.inference_time_ms} ms`;
    imgDimensions.textContent = `${data.image_dimensions.width} × ${data.image_dimensions.height}`;

    // Download button handler
    downloadAnnotatedBtn.onclick = () => {
        const link = document.createElement("a");
        link.href = data.annotated_image;
        link.download = `yolov8_detection_result_${Date.now()}.jpg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // 3. Populate Detections Table
    if (data.detections.length === 0) {
        detectionsTableBody.innerHTML = `<tr><td colspan="4" class="table-empty">No objects detected above threshold.</td></tr>`;
        return;
    }

    detectionsTableBody.innerHTML = data.detections.map((d, i) => {
        const pct = Math.round(d.confidence * 100);
        const coords = d.box.map(v => Math.round(v)).join(", ");
        return `
            <tr>
                <td><strong>#${i + 1}</strong></td>
                <td><span class="class-badge">${d.class_name.toUpperCase()}</span></td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span>${pct}%</span>
                        <div style="width:60px; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;">
                            <div style="width:${pct}%; height:100%; background:var(--cyan);"></div>
                        </div>
                    </div>
                </td>
                <td style="color:var(--text-muted);">[${coords}]</td>
            </tr>
        `;
    }).join("");
}
