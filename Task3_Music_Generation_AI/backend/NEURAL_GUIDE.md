# 🧠 Auralis AI — Neural Music Guide (final)

## Status: implemented & tested
- `backend/musicEngine.js` — Fast procedural AI (default) ✅ tested
- `backend/auth.js` — bcrypt + JWT auth ✅ tested
- `backend/googleAuth.js` — Google OAuth (idToken verify) ✅ wired ✅ tested (config endpoint + fake-token rejection)
- `backend/neuralClient.js` — multi-backend router ✅
- `backend/hfSpaces.js` — HF Spaces + Inference API ✅
- `backend/music_worker.py` — MusicGen local (CUDA/MPS/CPU + fp16) ✅
- `backend/space_app.py` — HF Gradio Space app ✅
- `api/generate.js` — Vercel serverless fallback ✅
- Server smoke tests ✅ (health, register, generate, stats all pass)

## How to run now

```powershell
cd D:\cdainternship\Task3_Music_Generation_AI
npm install
npm start
```

Open: http://localhost:5000

## AI Engines

1) **Fast (instant)** — default in UI chip.
2) **Neural** — choose `🎧 Neural MusicGen`:
   - Backend: `Auto (Cloud → Local)` / `Local GPU/CPU` / `HF Spaces`
   - First time may take 20–60s (model download ~1GB).
   - Falls back to Fast if unavailable.

## Auth

- Email: signup/login with bcrypt + JWT.
- Google: needs `GOOGLE_CLIENT_ID` env + OAuth consent enabled.
- After login → your generations are tied to you.

## Speed notes
- Backend store now async (Promise fs) — no sync I/O blocking event loop.
- Visualizer redraw throttled to ~30fps.

## Troubleshooting
- Slow → check backend async fixes, visualizer throttle.
- Neural slow → install GPU torch / set HF_SPACES_URL.
- Google login fails → set GOOGLE_CLIENT_ID.

---
Made with ❤️ — Auralis AI
