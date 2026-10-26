/**
 * AI Music Composer Studio Controller
 * Built with Web Audio API for in-browser polyphonic synthesis and HTML5 Canvas Piano Roll.
 */

// Audio Synthesis Engine
let audioCtx = null;
let currentEvents = [];
let isPlaying = false;
let isPaused = false;
let playbackStartTime = 0;
let pauseOffset = 0;
let totalDurationSeconds = 0;
let playbackTimer = null;
let animationFrameId = null;

// Sliders and Badges
const tempSlider = document.getElementById("tempSlider");
const tempVal = document.getElementById("tempVal");
const lengthSlider = document.getElementById("lengthSlider");
const lengthVal = document.getElementById("lengthVal");
const tempoSlider = document.getElementById("tempoSlider");
const tempoVal = document.getElementById("tempoVal");

// Canvas
const canvas = document.getElementById("pianoRollCanvas");
const ctx = canvas.getContext("2d");

// Transport elements
const playBtn = document.getElementById("playBtn");
const pauseBtn = document.getElementById("pauseBtn");
const stopBtn = document.getElementById("stopBtn");
const generateBtn = document.getElementById("generateBtn");
const downloadBtn = document.getElementById("downloadMidiBtn");
const timeCounter = document.getElementById("timeCounter");
const totalDurationEl = document.getElementById("totalDuration");
const activeNoteLabel = document.getElementById("activeNoteLabel");
const canvasStatus = document.getElementById("canvasStatus");
const noteChipsContainer = document.getElementById("noteChips");

document.addEventListener("DOMContentLoaded", () => {
    initSliders();
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    drawEmptyGrid();
});

function initSliders() {
    tempSlider.addEventListener("input", () => {
        tempVal.textContent = parseFloat(tempSlider.value).toFixed(2);
    });
    lengthSlider.addEventListener("input", () => {
        lengthVal.textContent = lengthSlider.value;
    });
    tempoSlider.addEventListener("input", () => {
        tempoVal.textContent = `${tempoSlider.value} BPM`;
    });
}

function applyPreset(temp, length, tempo) {
    tempSlider.value = temp;
    tempVal.textContent = parseFloat(temp).toFixed(2);
    lengthSlider.value = length;
    lengthVal.textContent = length;
    tempoSlider.value = tempo;
    tempoVal.textContent = `${tempo} BPM`;
    generateMusic();
}

function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    if (currentEvents.length > 0) {
        drawPianoRoll(getCurrentPlaybackTime());
    } else {
        drawEmptyGrid();
    }
}

// Convert MIDI number to frequency (Hz)
function midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
}

// Web Audio API Polyphonic Synthesizer
function getAudioContext() {
    if (!audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContextClass();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

function playSynthesizerNote(midi, startTime, duration) {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    // Warm Rhodes / Soft Synth tone
    osc.type = "triangle";
    osc.frequency.setValueAtTime(midiToFreq(midi), startTime);

    // ADSR Envelope
    const attack = 0.02;
    const decay = 0.15;
    const sustain = 0.6;
    const release = 0.2;

    gain.gain.setValueAtTime(0, startTime);
    gain.gain.linearRampToValueAtTime(0.3, startTime + attack);
    gain.gain.linearRampToValueAtTime(0.3 * sustain, startTime + attack + decay);
    gain.gain.setValueAtTime(0.3 * sustain, startTime + duration);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration + release);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(startTime);
    osc.stop(startTime + duration + release);
}

// Generate API Call
async function generateMusic() {
    generateBtn.disabled = true;
    generateBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <line x1="12" y1="2" x2="12" y2="6"></line>
            <line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line>
            <line x1="18" y1="12" x2="22" y2="12"></line>
        </svg>
        <span>Composing Sequence...</span>
    `;
    canvasStatus.textContent = "AI generating musical tokens...";
    stopMusic();

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                length: parseInt(lengthSlider.value),
                temperature: parseFloat(tempSlider.value),
                tempo: parseInt(tempoSlider.value)
            })
        });

        const data = await response.json();
        generateBtn.disabled = false;
        generateBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            <span>Generate New Melody</span>
        `;

        if (data.success) {
            currentEvents = data.audio_events || [];
            totalDurationSeconds = currentEvents.reduce((max, ev) => Math.max(max, ev.time + ev.duration), 0);

            // Enable transport & download
            playBtn.disabled = false;
            stopBtn.disabled = false;
            downloadBtn.classList.remove("disabled");
            downloadBtn.href = data.download_url;
            downloadBtn.setAttribute("download", data.filename);

            totalDurationEl.textContent = formatTime(totalDurationSeconds);
            canvasStatus.textContent = `Generated ${data.total_notes} notes | Tempo: ${data.tempo_bpm} BPM`;

            renderNoteChips(data.notes);
            drawPianoRoll(0);

            // Auto-play the newly generated composition!
            playMusic();
        } else {
            alert("Generation failed: " + data.error);
        }
    } catch (err) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = `<span>Generate New Melody</span>`;
        alert("Failed to communicate with music engine: " + err.message);
    }
}

function renderNoteChips(notes) {
    noteChipsContainer.innerHTML = "";
    notes.forEach((n, idx) => {
        const chip = document.createElement("span");
        chip.className = "note-chip";
        chip.id = `chip-${idx}`;
        chip.textContent = n;
        noteChipsContainer.appendChild(chip);
    });
}

function drawEmptyGrid() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#121624";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;

    // Draw horizontal grid lines
    const rows = 20;
    const rowH = canvas.height / rows;
    for (let i = 0; i <= rows; i++) {
        ctx.beginPath();
        ctx.moveTo(0, i * rowH);
        ctx.lineTo(canvas.width, i * rowH);
        ctx.stroke();
    }

    // Draw vertical beat lines
    const cols = 32;
    const colW = canvas.width / cols;
    for (let j = 0; j <= cols; j++) {
        ctx.beginPath();
        ctx.moveTo(j * colW, 0);
        ctx.lineTo(j * colW, canvas.height);
        ctx.stroke();
    }
}

function drawPianoRoll(currentTime) {
    if (currentEvents.length === 0) {
        drawEmptyGrid();
        return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background
    ctx.fillStyle = "#121624";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Find MIDI pitch range
    const midiPitches = currentEvents.map(e => e.midi);
    const minMidi = Math.min(...midiPitches) - 2;
    const maxMidi = Math.max(...midiPitches) + 2;
    const pitchRange = Math.max(12, maxMidi - minMidi + 1);

    const timeSpan = Math.max(totalDurationSeconds, 1);
    const scaleX = (canvas.width - 60) / timeSpan;
    const scaleY = canvas.height / pitchRange;
    const leftMargin = 50;

    // Draw horizontal pitch rows
    for (let m = minMidi; m <= maxMidi; m++) {
        const y = canvas.height - (m - minMidi + 1) * scaleY;
        const isBlackKey = [1, 3, 6, 8, 10].includes(m % 12);

        ctx.fillStyle = isBlackKey ? "rgba(0, 0, 0, 0.25)" : "rgba(255, 255, 255, 0.02)";
        ctx.fillRect(leftMargin, y, canvas.width - leftMargin, scaleY);

        ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        ctx.strokeRect(leftMargin, y, canvas.width - leftMargin, scaleY);

        // Pitch labels on the left margin
        if (m % 12 === 0) { // C note
            ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
            ctx.font = "10px JetBrains Mono";
            ctx.fillText(`C${Math.floor(m / 12) - 1}`, 10, y + scaleY - 4);
        }
    }

    // Draw Notes
    currentEvents.forEach(ev => {
        const x = leftMargin + ev.time * scaleX;
        const y = canvas.height - (ev.midi - minMidi + 1) * scaleY;
        const w = Math.max(8, ev.duration * scaleX - 2);
        const h = scaleY - 2;

        const isCurrent = currentTime >= ev.time && currentTime < (ev.time + ev.duration);

        if (isCurrent) {
            ctx.fillStyle = "#34d399";
            ctx.shadowColor = "rgba(52, 211, 153, 0.8)";
            ctx.shadowBlur = 12;
            activeNoteLabel.textContent = ev.note;
        } else {
            ctx.fillStyle = "rgba(168, 85, 247, 0.75)";
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
        }

        ctx.beginPath();
        ctx.roundRect(x, y, w, h, 3);
        ctx.fill();

        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;
    });

    // Draw Playback Tracker Line
    const trackerX = leftMargin + currentTime * scaleX;
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2;
    ctx.shadowColor = "#38bdf8";
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.moveTo(trackerX, 0);
    ctx.lineTo(trackerX, canvas.height);
    ctx.stroke();
    ctx.shadowBlur = 0;
}

// Playback Transport Functions
function playMusic() {
    if (currentEvents.length === 0) return;

    const ctx = getAudioContext();
    isPlaying = true;
    isPaused = false;
    playBtn.disabled = true;
    pauseBtn.disabled = false;

    playbackStartTime = ctx.currentTime - pauseOffset;

    // Schedule all notes with WebAudio
    currentEvents.forEach(ev => {
        if (ev.time >= pauseOffset) {
            const noteStartTime = playbackStartTime + ev.time;
            playSynthesizerNote(ev.midi, noteStartTime, ev.duration);
        }
    });

    // Start UI update animation loop
    animatePlayback();
}

function pauseMusic() {
    if (!isPlaying) return;
    const ctx = getAudioContext();
    pauseOffset = ctx.currentTime - playbackStartTime;
    isPlaying = false;
    isPaused = true;

    playBtn.disabled = false;
    pauseBtn.disabled = true;

    // Suspend audio context to halt sound immediately
    if (audioCtx) audioCtx.suspend();
    cancelAnimationFrame(animationFrameId);
}

function stopMusic() {
    isPlaying = false;
    isPaused = false;
    pauseOffset = 0;

    playBtn.disabled = currentEvents.length === 0;
    pauseBtn.disabled = true;
    timeCounter.textContent = "00:00";
    activeNoteLabel.textContent = "--";

    if (audioCtx) {
        audioCtx.close();
        audioCtx = null;
    }
    cancelAnimationFrame(animationFrameId);
    drawPianoRoll(0);
}

function getCurrentPlaybackTime() {
    if (!isPlaying) return pauseOffset;
    const ctx = getAudioContext();
    return Math.max(0, ctx.currentTime - playbackStartTime);
}

function animatePlayback() {
    if (!isPlaying) return;

    const curTime = getCurrentPlaybackTime();
    timeCounter.textContent = formatTime(curTime);
    drawPianoRoll(curTime);

    if (curTime >= totalDurationSeconds) {
        stopMusic();
        return;
    }

    animationFrameId = requestAnimationFrame(animatePlayback);
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}
