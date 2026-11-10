# 🎧 Auralis AI — Music Generation Platform v2.1

**Turn ideas into music.** Full-stack AI studio with **email + Google login**, **Fast procedural AI**, and **real neural MusicGen** (local GPU or HF Spaces cloud).

> Stack: **Node.js + Express** • **Vanilla JS + Web Audio** • **bcrypt + JWT + Google OAuth** • **Python MusicGen** (local GPU / HF Spaces)

---

## ✨ Features

- 💬 Prompt-to-song controls (genre, key, BPM, mood, layers)
- 🤖 **Two engines:** ⚡ Fast (instant, offline) + 🧠 Neural MusicGen (real WAV)
- ☁️ **Multi-backend neural:** HF Spaces T4 (free), HF Inference API, Local CUDA/CPU/MPS — auto + picker
- 🔐 **Auth:** Email/password (bcrypt+JWT) + **Continue with Google** (ID token verified server-side)
- ▶️ Dual playback (Web Audio synth + HTML5 WAV), visualizer, WAV export
- 📚 Library & Explore, plays/likes/remix/delete, Creator Studio

## 🚀 Quick Start

```bash
cd Task3_Music_Generation_AI
npm install
npm start
```
Open **http://localhost:5000** → Login → Generate.

### Scripts

| Command | Description |
|---|---|
| `npm start` | Fast + Auth (no neural) |
| `npm run dev` | Auto-reload |
| `npm run setup:neural` | Python deps (CPU) |
| `npm run setup:neural:gpu` | CUDA torch + deps |
| `npm run start:neural` | Neural local (GPU auto) |
| `npm run start:neural:cloud` | Neural via HF Spaces |
| `npm test` | Syntax check |

Set env vars in PowerShell: `$env:GOOGLE_CLIENT_ID="..."; $env:HF_SPACES_URL="..."; npm start`

---

## 🔐 Google Login (5 min)

1. **Google Cloud Console** → APIs & Services → Credentials → **Create Credentials → OAuth client ID → Web application**
2. **Authorized JavaScript origins:** `http://localhost:5000` (+ your domain in prod)
3. 🎯 Set env: `$env:GOOGLE_CLIENT_ID="1234-....apps.googleusercontent.com"`
4. Restart → **Continue with Google** button appears in the Login modal

Endpoints:
- `GET /api/auth/google/config` → `{configured, clientId}`
- `POST /api/auth/google` body `{idToken}` → `{user, token}` (creates/links account by email)

> Google users have `provider: "google"` and no password — password login for those emails returns *use Google login*.

## 🧠 Neural — three ways to run fast

**Priority `NEURAL_BACKEND=auto` (default): try cloud → local → Fast fallback**

### A) HF Spaces — free T4 GPU (~12s / 10s clip)
1. https://huggingface.co/new-space → SDK **Gradio**
2. Upload **`backend/space_app.py`** as `app.py`
3. Wait for GPU ready, copy URL: `https://your-space.hf.space`
4. In Auralis: `$env:HF_SPACES_URL="https://your-space.hf.space"; $env:USE_NEURAL_AI="true"; npm start`
   Or: `npm run start:neural:cloud`
5. In UI pick **☁️ HF Spaces** or *Auto*

### B) Local GPU — fastest if you have CUDA
```powershell
npm run setup:neural:gpu
npm run start:neural:gpu
```
Worker auto-detects `CUDA → MPS → CPU` and uses **fp16 on GPU** (~8–15s/10s).

### C) HF Inference API (no Space)
Get token: https://huggingface.co/settings/tokens → `$env:HF_TOKEN="hf_..."`

**Status:** `GET /api/neural/status` / `GET /api/health` shows `backends`, `hf`, `speedHints`.

**Generate:** `POST /api/generate` with `{engine:"neural", backend:"auto"|"local"|"hf-spaces"}`

## 🖥️ Structure

```
├─ server.js                  # auth (email+google) + generate routing
├─ backend/
│  ├─ musicEngine.js          # Fast AI
│  ├─ auth.js                 # bcrypt/JWT
│  ├─ googleAuth.js           # Google token verify
│  ├─ neuralClient.js         # auto router: cloud→local
│  ├─ hfSpaces.js             # Spaces + Inference API client
│  ├─ music_worker.py         # Local MusicGen (fp16 GPU)
│  └─ space_app.py            # HF Spaces Gradio app
└─ public/                    # + Google button + backend chips
```

## 🛠️ Roadmap
- [x] Email + Google auth
- [x] Neural local + Spaces + Inference API
- [ ] Postgres, email verify, OAuth refresh, comments, stems export

---
Made with ❤️ — Auralis AI

---

## 🔵 Firebase Google Authentication (added v2.2)

The login modal now uses **Firebase Auth** for Google sign-in:

1. Frontend loads Firebase SDK v13 (`firebase-app`, `firebase-analytics`, `firebase-auth`) via module script with the project's Firebase config.
2. Backend serves Firebase config via `GET /api/auth/firebase/config`.
3. User clicks **🔵 Continue with Google** → Firebase `signInWithPopup` → gets Firebase `idToken`.
4. Frontend exchanges token: `POST /api/auth/firebase/google {idToken}` → backend verifies via **firebase-admin** → upserts user → issues Auralis JWT.
5. Session saved (localStorage `auralis_token` / `auralis_user`).

### Server env for Firebase
```
FIREBASE_PROJECT_ID=auralis-ai-93b95
FIREBASE_CLIENT_EMAIL=<your-service-account-email>
FIREBASE_PRIVATE_KEY=<your-private-key-with-\n>
FIREBASE_WEB_API_KEY=AIzaSyAiTSBpOCsToeQ342LekWI9SCqcV9cexQg
FIREBASE_AUTH_DOMAIN=auralis-ai-93b95.firebaseapp.com
```

Get private key: Firebase Console → Project Settings → Service accounts → **Generate new private key** → copy to env.

### Frontend
- Module script: Firebase v13 with `firebaseConfig` (apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId, measurementId) + `getAuth`/`GoogleAuthProvider`; exposes `window.firebaseConfig`, `window.firebaseAuth`, `window.firebaseGoogleProvider`.
- Backend still serves `/api/auth/firebase/config` for status.

### Status
- When `FIREBASE_*` are set → `GET /api/auth/firebase/config` → `{enabled:true}` and button becomes active.
- When not set → button falls back gracefully (email login works).
