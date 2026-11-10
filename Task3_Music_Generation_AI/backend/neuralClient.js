// Auralis Neural Client v2 — multi-backend: local (GPU/CPU) + HF Spaces + HF Inference API
// Backends (NEURAL_BACKEND env): local | hf-spaces | auto (try cloud, fallback local)
// USE_NEURAL_AI=true enables neural generation. Falls back to procedural Fast if all fail.
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const hf = require('./hfSpaces');

const WORKER = path.join(__dirname, 'music_worker.py');
const OUT_DIR = path.join(__dirname, '..', 'public', 'generated');
const PYTHON = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

function ensureOut() { if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true }); }
function neuralEnabled() { return process.env.USE_NEURAL_AI === 'true' || process.env.USE_NEURAL_AI === '1'; }
function backendPref() { return (process.env.NEURAL_BACKEND || 'auto').toLowerCase(); }

function probePython() {
  try {
    const r = spawnSync(PYTHON, ['--version'], { encoding: 'utf8', timeout: 3000 });
    return { available: !r.error, version: (r.stdout || r.stderr || '').trim() };
  } catch (e) { return { available: false, version: '', error: e.message }; }
}

function getNeuralStatus() {
  const py = probePython();
  const hfCfg = hf.getHFConfig();
  const backends = [];
  if (hfCfg.spacesUrl) backends.push('hf-spaces');
  if (hfCfg.tokenConfigured) backends.push('hf-inference-api');
  backends.push('local-musicgen');

  const gpuHint = {
    cpu: 'CPU: 40–60s per 10s clip',
    cuda: 'CUDA GPU: ~8–15s per 10s clip (fast!)',
    mps: 'Apple MPS GPU: ~15–30s per 10s clip',
  };

  const checks = {
    enabledByEnv: neuralEnabled(),
    backendPreference: backendPref(),
    workerExists: fs.existsSync(WORKER),
    python: PYTHON,
    pythonAvailable: py.available,
    pythonVersion: py.version,
    outDir: OUT_DIR,
    model: process.env.MUSICGEN_MODEL || 'facebook/musicgen-small',
    backends,
    hf: hfCfg,
    speedHints: gpuHint,
    ready: neuralEnabled() && backends.length > 0,
    hint: neuralEnabled()
      ? (backendPref() === 'local'
          ? 'Local MusicGen ready — run npm run setup:neural:gpu for faster CUDA. First run downloads model (~1GB).'
          : 'Neural ready (cloud + local). Set HF_SPACES_URL for free T4 GPU. First local run downloads model (~1GB).')
      : 'Neural off. Run: npm run setup:neural → npm run start:neural  (or npm run start:neural:cloud for Spaces).',
  };
  return checks;
}

function generateLocal({ prompt, duration = 10, guidance = 3.0 }) {
  return new Promise((resolve) => {
    if (!neuralEnabled()) return resolve({ ok: false, reason: 'Neural not enabled (USE_NEURAL_AI != true)' });
    if (!fs.existsSync(WORKER)) return resolve({ ok: false, reason: 'music_worker.py missing' });
    ensureOut();
    const id = 'neural_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
    const outFile = path.join(OUT_DIR, id + '.wav');
    const input = {
      prompt: String(prompt || 'Beautiful melody').slice(0, 500),
      output_path: outFile,
      duration: Math.max(5, Math.min(30, Number(duration) || 10)),
      guidance: Number(guidance) || 3.0,
      model: process.env.MUSICGEN_MODEL || 'facebook/musicgen-small',
    };
    const inputFile = path.join(os.tmpdir(), id + '.json');
    fs.writeFileSync(inputFile, JSON.stringify(input, null, 2));
    const child = spawn(PYTHON, [WORKER, inputFile], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 180000 });
    let out = '', err = '';
    child.stdout.on('data', d => { out += d; });
    child.stderr.on('data', d => { err += d; });
    child.on('error', (e) => resolve({ ok: false, reason: 'Python spawn failed: ' + e.message, out, err }));
    child.on('close', (code) => {
      try { fs.unlinkSync(inputFile); } catch {}
      if (code !== 0) return resolve({ ok: false, reason: `MusicGen worker exit ${code}: ${(err || out).slice(-1200)}`, out, err });
      if (!fs.existsSync(outFile)) return resolve({ ok: false, reason: 'No WAV produced', out, err });
      const stats = fs.statSync(outFile);
      if (stats.size < 1000) return resolve({ ok: false, reason: 'WAV too small (model error)' });
      resolve({ ok: true, file: outFile, url: `/generated/${path.basename(outFile)}`, duration: input.duration, prompt: input.prompt, model: input.model, size: stats.size, via: 'local' });
    });
  });
}

/**
 * Smart generate: respects NEURAL_BACKEND + per-request backend override.
 * @param backendOverride: 'auto' | 'local' | 'hf-spaces' | 'hf-api'
 */
async function generateWithNeural({ prompt, duration = 10, guidance = 3.0, backend: backendOverride }) {
  if (!neuralEnabled()) return { ok: false, reason: 'Neural not enabled (USE_NEURAL_AI != true)' };
  const pref = (backendOverride || backendPref()).toLowerCase();
  const tried = [];

  if (pref === 'hf-spaces' || pref === 'hf-api' || pref === 'cloud') {
    const r = await hf.generateCloud({ prompt, duration });
    if (r.ok) return r;
    tried.push('cloud:' + r.reason);
  }
  if (pref === 'auto' || pref === 'local' || pref === 'hf-spaces' || pref === 'hf-api') {
    // auto: try local after cloud (or before if no cloud configured)
    const r = await generateLocal({ prompt, duration, guidance });
    if (r.ok) return r;
    tried.push('local:' + r.reason);
  }
  return { ok: false, reason: 'All neural backends failed → ' + tried.join(' | ').slice(0, 1200) };
}

module.exports = { neuralEnabled, getNeuralStatus, generateWithNeural, generateLocal, PYTHON, WORKER, backendPref };
