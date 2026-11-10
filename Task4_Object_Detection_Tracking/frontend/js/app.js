/* TrafficGuard AI — SPA logic (vanilla JS, no build step) */
"use strict";

/* ---------------------------------------------------------------- helpers */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

const state = {
  token: localStorage.getItem("tg_token") || null,
  user: null,
  view: "dashboard",
  source: { kind: null, file: null, name: null, url: null }, // kind: 'upload' | 'demo'
  zones: { stop: null, dir: null, tool: "stop" },
  mode: "auto", // 'auto' | 'manual'
  currentJobId: null,
  pollTimer: null,
  charts: {},
};

function toast(msg, kind = "ok") {
  const t = document.createElement("div");
  t.className = `toast ${kind === "ok" ? "" : kind}`;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 350); }, 4500);
}

async function api(path, { method = "GET", body, form, raw = false } = {}) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let payload;
  if (form) payload = form;
  else if (body) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(path, { method, headers, body: payload });
  const data = raw ? res : await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function chart(id, cfg) {
  const el = document.getElementById(id);
  if (!el || typeof Chart === "undefined") return;
  if (state.charts[id]) state.charts[id].destroy();
  state.charts[id] = new Chart(el, cfg);
}

const TYPE_LABELS = { overspeed: "Overspeeding", red_light: "Red-light jumping", wrong_way: "Wrong-way", helmet: "No helmet" };
const chartColors = ["#f87171", "#f5b518", "#22d3ee", "#34d399", "#a78bfa", "#fb923c"];

function doughnutChart(id, counts) {
  const labels = Object.keys(counts || {});
  chart(id, {
    type: "doughnut",
    data: {
      labels: labels.map((k) => TYPE_LABELS[k] || k),
      datasets: [{ data: labels.map((k) => counts[k]), backgroundColor: chartColors, borderColor: "#0b111c", borderWidth: 3 }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: "#e7edf6" } } } },
  });
}

function barChart(id, counts) {
  const labels = Object.keys(counts || {});
  chart(id, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: labels.map((k) => counts[k]), backgroundColor: "#f5b518", borderRadius: 6 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { x: { ticks: { color: "#e7edf6" } }, y: { ticks: { color: "#e7edf6", precision: 0 } } },
      plugins: { legend: { display: false } },
    },
  });
}

function fmtWhen(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/* ---------------------------------------------------------------- auth */
function showAuth() { $("#auth-view").hidden = false; $("#app-view").hidden = true; }
function showApp() {
  $("#auth-view").hidden = true; $("#app-view").hidden = false;
  const name = state.user?.name || "User";
  $("#user-name").textContent = name;
  $("#user-email").textContent = state.user?.email || "";
  $("#user-initials").textContent = name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  switchView("dashboard");
}

let authMode = "login";
function bindAuth() {
  $("#tab-login").onclick = () => { authMode = "login"; $("#tab-login").classList.add("active"); $("#tab-register").classList.remove("active"); $("#name-field").style.display = "none"; $("#auth-submit").textContent = "Sign in"; $("#auth-error").hidden = true; };
  $("#tab-register").onclick = () => { authMode = "register"; $("#tab-register").classList.add("active"); $("#tab-login").classList.remove("active"); $("#name-field").style.display = "block"; $("#auth-submit").textContent = "Create account"; $("#auth-error").hidden = true; };

  $("#auth-form").onsubmit = async (e) => {
    e.preventDefault();
    const email = $("#auth-email").value.trim();
    const password = $("#auth-password").value;
    const name = $("#auth-name").value.trim();
    $("#auth-error").hidden = true;
    const btn = $("#auth-submit");
    btn.disabled = true; btn.textContent = "Please wait…";
    try {
      const res = await api(authMode === "login" ? "/api/auth/login" : "/api/auth/register", {
        method: "POST",
        body: authMode === "login" ? { email, password } : { name, email, password },
      });
      state.token = res.token; state.user = res.user;
      localStorage.setItem("tg_token", state.token);
      toast(`Welcome${authMode === "register" ? " aboard" : " back"}, ${res.user.name}!`);
      showApp();
    } catch (err) {
      const box = $("#auth-error");
      box.textContent = err.message; box.hidden = false;
    } finally {
      btn.disabled = false; btn.textContent = authMode === "login" ? "Sign in" : "Create account";
    }
  };

  $("#logout-btn").onclick = () => {
    state.token = null; state.user = null;
    localStorage.removeItem("tg_token");
    stopPolling();
    showAuth();
    toast("Signed out. See you soon!", "info");
  };
}

/* ---------------------------------------------------------------- nav */
function bindNav() {
  $$(".nav-btn").forEach((b) => (b.onclick = () => switchView(b.dataset.view)));
  $("#dash-goto-analyze").onclick = () => switchView("analyze");
}
function switchView(v) {
  state.view = v;
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  ["dashboard", "analyze", "history", "guide"].forEach((name) => {
    $("#view-" + name).hidden = name !== v;
  });
  if (v === "dashboard") loadDashboard();
  if (v === "history") loadHistory();
}

/* ---------------------------------------------------------------- dashboard */
async function loadDashboard() {
  try {
    const s = await api("/api/stats");
    $("#kpi-jobs").textContent = s.total_jobs;
    $("#kpi-vehicles").textContent = s.total_vehicles;
    $("#kpi-violating").textContent = s.total_violating_vehicles;
    $("#kpi-violations").textContent = s.total_violations;
    $("#kpi-done").textContent = s.completed_jobs;
    doughnutChart("chart-violations", s.violating_vehicles_by_type);
    barChart("chart-classes", s.vehicles_by_class);
    const list = $("#recent-list");
    if (!s.recent.length) {
      list.innerHTML = '<p class="muted">No analyses yet. Head to <b>Analyze video</b> to run your first detection.</p>';
      return;
    }
    list.innerHTML = "";
    for (const j of s.recent) {
      const row = document.createElement("div");
      row.className = "recent-item";
      row.innerHTML = `<span>🎬 <strong>${escapeHtml(j.filename)}</strong> <span class="muted">· ${fmtWhen(j.created_at)}</span></span>
        <span><span class="pill ${j.status}">${j.status}</span> ${j.summary ? `· 🚗 ${j.summary.total_vehicles} · ⚠️ ${j.summary.total_violating_vehicles} breaking rules` : ""}</span>`;
      list.appendChild(row);
    }
  } catch (err) { toast(err.message, "error"); }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------------------------------------------------------- history */
async function loadHistory() {
  const body = $("#history-body");
  try {
    const { jobs } = await api("/api/jobs");
    if (!jobs.length) { body.innerHTML = '<tr><td colspan="7" class="muted">No analyses yet.</td></tr>'; return; }
    body.innerHTML = "";
    for (const j of jobs) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>🎬 ${escapeHtml(j.filename)}</td>
        <td><span class="pill ${j.status}">${j.status}${j.status === "processing" || j.status === "queued" ? ` ${j.progress}%` : ""}</span></td>
        <td>${j.summary ? j.summary.total_vehicles : "—"}</td>
        <td>${j.summary ? j.summary.total_violating_vehicles : "—"}</td>
        <td>${j.summary ? j.summary.total_violations : "—"}</td>
        <td>${fmtWhen(j.created_at)}</td>
        <td>${j.status === "done" ? `<button class="btn btn-small" data-view="analyze" data-job="${j.id}">View results</button>` : ""}</td>`;
      tr.querySelector("button")?.addEventListener("click", () => { viewJob(j.id); });
      body.appendChild(tr);
    }
  } catch (err) { toast(err.message, "error"); }
}

async function viewJob(jobId) {
  try {
    const { job } = await api(`/api/jobs/${jobId}`);
    if (job.status !== "done") { toast("That analysis is still processing.", "info"); return; }
    switchView("analyze");
    renderResults(job);
  } catch (err) { toast(err.message, "error"); }
}

$("#refresh-history").onclick = loadHistory;

/* ---------------------------------------------------------------- analyze: source */
function bindAnalyze() {
  const dz = $("#dropzone"), input = $("#file-input");
  dz.onclick = () => input.click();
  dz.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") input.click(); };
  input.onchange = () => { if (input.files[0]) setSource({ kind: "upload", file: input.files[0], name: input.files[0].name, url: URL.createObjectURL(input.files[0]) }); };
  ["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
  dz.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files[0];
    if (f) setSource({ kind: "upload", file: f, name: f.name, url: URL.createObjectURL(f) });
  });

  $("#demo-btn").onclick = async () => {
    const btn = $("#demo-btn");
    btn.disabled = true; btn.textContent = "⏳ Preparing demo…";
    try {
      const info = await api("/api/demo/generate", { method: "POST" });
      applyPreset(info.recommended_config);
      setSource({ kind: "demo", file: null, name: "Built-in demo clip (real road photo + simulated camera pan)", url: `/api/demo/file?token=${encodeURIComponent(state.token)}` });
      toast("Demo clip ready — demo settings applied. Just draw nothing, hit Run AI detection.", "info");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn.disabled = false; btn.textContent = "▶ Get built-in demo clip";
    }
  };

  $("#run-btn").onclick = runAnalysis;

  /* config sliders */
  const slider = (id, out, fmt) => {
    const el = $(id);
    const sync = () => { $(out).textContent = fmt(parseFloat(el.value)); };
    el.oninput = sync; sync();
  };
  slider("#cfg-limit", "#o-limit", (v) => `${v} km/h`);
  slider("#cfg-ppm", "#o-ppm", (v) => v.toFixed(1));
  slider("#cfg-conf", "#o-conf", (v) => v.toFixed(2));

  $("#preset-defaults").onclick = () => applyPreset({ auto_mode: true, speed_limit_kmh: 50, pixels_per_meter: 1.0, conf: 0.4, light: { red: 7, green: 7, initial: "red" } });
  $("#preset-highway").onclick = () => applyPreset({ auto_mode: true, speed_limit_kmh: 100, pixels_per_meter: 1.5, conf: 0.4, light: { red: 7, green: 7, initial: "red" } });
  $("#preset-demo").onclick = () => applyPreset({ auto_mode: false, speed_limit_kmh: 50, pixels_per_meter: 0.5, conf: 0.35, light: { red: 7, green: 7, initial: "red" } });

  $("#mode-auto").onclick = () => setMode("auto");
  $("#mode-manual").onclick = () => setMode("manual");
  setMode("auto");

  /* export buttons */
  $("#export-csv").onclick = () => download(`/api/jobs/${state.currentJobId}/export.csv`, `violations_${state.currentJobId}.csv`);
  $("#export-pdf").onclick = () => download(`/api/jobs/${state.currentJobId}/export.pdf`, `report_${state.currentJobId}.pdf`);

  $("#modal-close").onclick = closeModal;
  $("#modal-backdrop").onclick = closeModal;
}

function download(url, name) {
  const a = document.createElement("a");
  a.href = `${url}?token=${encodeURIComponent(state.token)}`;
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
}

function applyPreset(p) {
  if (typeof p.auto_mode === "boolean") setMode(p.auto_mode ? "auto" : "manual");
  $("#cfg-limit").value = p.speed_limit_kmh;
  $("#cfg-ppm").value = p.pixels_per_meter;
  $("#cfg-conf").value = p.conf;
  if (p.light) { $("#cfg-red-s").value = p.light.red; $("#cfg-green-s").value = p.light.green; $("#cfg-initial").value = p.light.initial; }
  ["#cfg-limit", "#cfg-ppm", "#cfg-conf"].forEach((sel) => $(sel).dispatchEvent(new Event("input")));
}

function collectConfig() {
  const zones = state.zones;
  const auto = state.mode === "auto";
  const digit = (sel, dflt) => Math.max(2, parseInt($(sel).value, 10) || dflt);
  return {
    auto_mode: auto,
    ppm_mode: auto ? "auto" : "manual",
    speed_limit_kmh: parseInt($("#cfg-limit").value, 10),
    pixels_per_meter: parseFloat($("#cfg-ppm").value),
    conf: parseFloat($("#cfg-conf").value),
    violations: {
      overspeed: $("#cfg-overspeed").checked,
      red_light: $("#cfg-redlight").checked && (auto || !!zones.stop),
      wrong_way: $("#cfg-wrongway").checked && (auto || !!zones.dir),
      helmet: $("#cfg-helmet").checked,
    },
    stop_line: auto ? null : zones.stop,
    allowed_direction: !auto && zones.dir ? { dx: zones.dir.x2 - zones.dir.x1, dy: zones.dir.y2 - zones.dir.y1 } : null,
    light_cycle: auto ? null : {
      red_seconds: digit("#cfg-red-s", 7),
      green_seconds: digit("#cfg-green-s", 7),
      initial: $("#cfg-initial").value,
    },
  };
}

function setMode(m) {
  state.mode = m;
  $("#mode-auto").classList.toggle("active", m === "auto");
  $("#mode-manual").classList.toggle("active", m === "manual");
  $("#ppm-field").hidden = m !== "manual";
  $("#cycle-field").hidden = m !== "manual";
  $("#zone-tools").hidden = m !== "manual" || state.source.kind === null;
  $("#zone-hint").hidden = state.source.kind === null;
  $("#zone-hint").textContent = m === "auto"
    ? "Automatic mode: the AI reads the traffic light, auto-places the stop line, and learns the flow direction. Review the annotated video for what it saw."
    : "Manual mode: drag on the video to draw the stop line, then switch tools to set the allowed direction.";
}

/* ---------------------------------------------------------------- analyze: staging + zones */
const stage = { poster: null, drawing: false, start: null, preview: null };

function setSource({ kind, file, name, url }) {
  state.source = { kind, file, name, url };
  state.zones.stop = null; state.zones.dir = null;
  $("#source-info").textContent = `Selected: ${name}`;
  const vid = $("#source-video");
  vid.src = url;
  $("#stage").hidden = false; $("#zone-hint").hidden = false;
  $("#zone-tools").hidden = state.mode !== "manual";
  $("#run-btn").disabled = false;
  vid.onloadedmetadata = () => {
    vid.currentTime = Math.min(0.25, (vid.duration || 1) * 0.05);
  };
  vid.onseeked = () => { snapshotPoster(); };
  bindZoneCanvas();
  snapshotPoster();
}

function snapshotPoster() {
  const vid = $("#source-video"), cv = $("#zone-canvas");
  if (!vid.videoWidth) return;
  const rect = cv.getBoundingClientRect();
  cv.width = Math.max(1, Math.round(rect.width));
  cv.height = Math.max(1, Math.round(rect.height));
  stage.poster = document.createElement("canvas");
  stage.poster.width = cv.width; stage.poster.height = cv.height;
  const ctx = stage.poster.getContext("2d");
  ctx.drawImage(vid, 0, 0, cv.width, cv.height);
  drawZones();
}

function drawZones() {
  const cv = $("#zone-canvas");
  if (!stage.poster) return;
  const ctx = cv.getContext("2d");
  ctx.drawImage(stage.poster, 0, 0);
  const W = cv.width, H = cv.height;
  const line = state.zones.stop || (state.tool === "stop" ? stage.preview : null);
  if (line && state.tool === "stop") {
    ctx.strokeStyle = "#ffcc33"; ctx.lineWidth = Math.max(3, W * 0.004);
    ctx.beginPath(); ctx.moveTo(line.x1 * W, line.y1 * H); ctx.lineTo(line.x2 * W, line.y2 * H); ctx.stroke();
    ctx.fillStyle = "#ffcc33"; ctx.font = `bold ${Math.max(13, W * 0.016)}px Inter`;
    ctx.fillText("STOP LINE", (line.x1 + line.x2) / 2 * W - 40, (line.y1 + line.y2) / 2 * H - 10);
  } else if (state.zones.stop) {
    ctx.strokeStyle = "#ffcc33"; ctx.lineWidth = Math.max(3, W * 0.004);
    ctx.beginPath(); ctx.moveTo(state.zones.stop.x1 * W, state.zones.stop.y1 * H);
    ctx.lineTo(state.zones.stop.x2 * W, state.zones.stop.y2 * H); ctx.stroke();
  }
  const arrow = state.zones.dir || (state.tool === "dir" ? stage.preview : null);
  if (arrow && state.tool === "dir") {
    drawArrow(ctx, arrow, W, H);
  } else if (state.zones.dir) {
    drawArrow(ctx, state.zones.dir, W, H);
  }
}

function drawArrow(ctx, a, W, H) {
  const x1 = a.x1 * W, y1 = a.y1 * H, x2 = a.x2 * W, y2 = a.y2 * H;
  ctx.strokeStyle = "#34d399"; ctx.fillStyle = "#34d399"; ctx.lineWidth = Math.max(3, W * 0.004);
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const hs = Math.max(14, W * 0.02);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - hs * Math.cos(ang - 0.45), y2 - hs * Math.sin(ang - 0.45));
  ctx.lineTo(x2 - hs * Math.cos(ang + 0.45), y2 - hs * Math.sin(ang + 0.45));
  ctx.closePath(); ctx.fill();
  ctx.font = `bold ${Math.max(13, W * 0.016)}px Inter`;
  ctx.fillText("ALLOWED", x1 - 30, y1 + 24);
}

function bindZoneCanvas() {
  const cv = $("#zone-canvas");
  if (cv.dataset.bound) return;
  cv.dataset.bound = "1";
  const pos = (e) => {
    const r = cv.getBoundingClientRect();
    return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
  };
  cv.onpointerdown = (e) => { stage.drawing = true; stage.start = pos(e); stage.preview = { x1: stage.start.x, y1: stage.start.y, x2: stage.start.x, y2: stage.start.y }; cv.setPointerCapture(e.pointerId); };
  cv.onpointermove = (e) => {
    if (!stage.drawing) return;
    const p = pos(e);
    stage.preview = { x1: stage.start.x, y1: stage.start.y, x2: p.x, y2: p.y };
    drawZones();
  };
  cv.onpointerup = () => {
    if (!stage.drawing) return;
    stage.drawing = false;
    if (stage.preview) {
      const len = Math.hypot(stage.preview.x2 - stage.preview.x1, stage.preview.y2 - stage.preview.y1);
      if (len > 0.03) {
        if (state.zones.tool === "stop") { state.zones.stop = { ...stage.preview }; toast("Stop line set. Switch to the direction tool to set allowed flow."); }
        else { state.zones.dir = { ...stage.preview }; toast("Allowed direction set."); }
      }
    }
    stage.preview = null;
    drawZones();
  };
  cv.onpointercancel = () => { stage.drawing = false; stage.preview = null; drawZones(); };

  $("#tool-stop").onclick = () => { state.zones.tool = "stop"; $("#tool-stop").classList.add("active"); $("#tool-dir").classList.remove("active"); drawZones(); };
  $("#tool-dir").onclick = () => { state.zones.tool = "dir"; $("#tool-dir").classList.add("active"); $("#tool-stop").classList.remove("active"); drawZones(); };
  $("#tool-clear").onclick = () => { state.zones.stop = null; state.zones.dir = null; stage.preview = null; drawZones(); toast("Zones cleared.", "info"); };
}

/* ---------------------------------------------------------------- run + poll */
async function runAnalysis() {
  if (!state.source.kind) { toast("Select a video or the demo clip first.", "error"); return; }
  const cfg = collectConfig();
  const btn = $("#run-btn");
  btn.disabled = true;
  $("#results").hidden = true;
  $("#progress-wrap").hidden = false;
  $("#progress-fill").style.width = "2%";
  $("#progress-text").textContent = "Uploading & queueing…";

  try {
    const form = new FormData();
    form.append("config", JSON.stringify(cfg));
    if (state.source.kind === "demo") form.append("source", "demo");
    else form.append("video", state.source.file, state.source.name);
    const { job_id } = await api("/api/analyze", { method: "POST", form });
    state.currentJobId = job_id;
    $("#progress-text").textContent = "AI engine started — detecting & tracking vehicles…";
    pollJob(job_id);
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    $("#progress-wrap").hidden = true;
  }
}

function stopPolling() { if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; } }

function pollJob(jobId) {
  stopPolling();
  state.pollTimer = setInterval(async () => {
    try {
      const { job } = await api(`/api/jobs/${jobId}`);
      $("#progress-fill").style.width = `${job.progress || 0}%`;
      if (job.status === "processing") $("#progress-text").textContent = `Processing frame by frame… ${job.progress}% (YOLOv8 + ByteTrack)`;
      if (job.status === "done") {
        stopPolling();
        $("#progress-text").textContent = "Done! Rendering results…";
        renderResults(job);
        $("#run-btn").disabled = false;
        toast("Analysis complete!");
      } else if (job.status === "error") {
        stopPolling();
        $("#progress-text").textContent = `Failed: ${job.error}`;
        $("#run-btn").disabled = false;
        toast(job.error || "Analysis failed.", "error");
      }
    } catch (err) { /* keep polling quietly */ }
  }, 1500);
}

/* ---------------------------------------------------------------- results */
function renderResults(job) {
  const r = job.result;
  $("#results").hidden = false;
  $("#results-meta").textContent = `${job.filename} · analyzed ${fmtWhen(job.finished_at)}`;
  $("#r-violating").textContent = r.total_violating_vehicles;
  $("#r-vehicles").textContent = r.total_vehicles;
  $("#r-violations").textContent = r.total_violations;
  $("#r-compliant").textContent = r.compliant_vehicles;

  const out = $("#output-video");
  out.src = `/api/jobs/${job.id}/video?token=${encodeURIComponent(state.token)}`;

  doughnutChart("chart-result-types", r.violating_vehicles_by_type);
  barChart("chart-result-classes", r.vehicle_counts);

  const body = $("#viol-body");
  const violations = r.violations || [];
  $("#viol-count").textContent = violations.length ? `(${violations.length} events)` : "";
  if (!violations.length) {
    body.innerHTML = '<tr><td colspan="8" class="muted">No violations detected 🎉</td></tr>';
  } else {
    body.innerHTML = "";
    for (const v of [...violations].sort((a, b) => a.timestamp_s - b.timestamp_s)) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td class="mono">${v.id}</td>
        <td><span class="vtag ${v.type}">${v.label}</span></td>
        <td>${escapeHtml(v.vehicle)}</td>
        <td class="mono">#${v.track_id}</td>
        <td class="mono">${v.timestamp_s}s</td>
        <td class="mono">${v.speed_kmh} km/h</td>
        <td><img class="ev-thumb" src="/api/jobs/${job.id}/evidence/${encodeURIComponent(v.evidence)}?token=${encodeURIComponent(state.token)}" alt="evidence" loading="lazy" /></td>
        <td>${escapeHtml(v.detail)}</td>`;
      tr.querySelector("img").onclick = () => openModal(
        `/api/jobs/${job.id}/evidence/${encodeURIComponent(v.evidence)}?token=${encodeURIComponent(state.token)}`,
        `${v.label} — ${v.vehicle} #${v.track_id} at ${v.timestamp_s}s (${v.speed_kmh} km/h). ${v.detail}`);
      body.appendChild(tr);
    }
  }

  const grid = $("#evidence-grid");
  if (!violations.length) grid.innerHTML = '<p class="muted">No evidence frames — no violations were recorded.</p>';
  else {
    grid.innerHTML = "";
    for (const v of violations) {
      const div = document.createElement("div");
      div.className = "ev-item";
      div.innerHTML = `<img src="/api/jobs/${job.id}/evidence/${encodeURIComponent(v.evidence)}?token=${encodeURIComponent(state.token)}" alt="evidence" loading="lazy" />
        <p>${v.label} · ${v.vehicle} · ${v.timestamp_s}s</p>`;
      div.onclick = () => openModal(
        `/api/jobs/${job.id}/evidence/${encodeURIComponent(v.evidence)}?token=${encodeURIComponent(state.token)}`,
        `${v.label} — ${v.vehicle} #${v.track_id} at ${v.timestamp_s}s (${v.speed_kmh} km/h). ${v.detail}`);
      grid.appendChild(div);
    }
  }
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function openModal(src, caption) {
  $("#modal-img").src = src;
  $("#modal-caption").textContent = caption;
  $("#modal").hidden = false;
}
function closeModal() { $("#modal").hidden = true; }

/* ---------------------------------------------------------------- boot */
document.addEventListener("DOMContentLoaded", async () => {
  bindAuth(); bindNav(); bindAnalyze();
  if (state.token) {
    try {
      const { user } = await api("/api/auth/me");
      state.user = user;
      showApp();
      return;
    } catch { state.token = null; localStorage.removeItem("tg_token"); }
  }
  showAuth();
});
