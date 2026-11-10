require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { generateTrack, GENRE_PROFILES } = require('./backend/musicEngine');
const store = require('./backend/store');
const auth = require('./backend/auth');
const neural = require('./backend/neuralClient');
const googleAuth = require('./backend/googleAuth');
const hf = require('./backend/hfSpaces');
const firebaseAuth = require('./backend/firebaseAuth');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/generated', express.static(path.join(__dirname, 'public', 'generated')));

store.ensure();

// ---------- Auth ----------
app.get('/api/auth/google/config', (req, res) => res.json(googleAuth.getGoogleConfig()));
app.post('/api/auth/google', async (req, res) => {
  try {
    const { idToken } = req.body || {};
    const result = await googleAuth.loginWithGoogle(idToken);
    res.json({ ok: true, ...result });
  } catch (e) { res.status(e.status || 500).json({ error: e.message }); }
});
app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password, displayName } = req.body || {};
    const { user, token } = await auth.register(email, password, displayName);
    res.json({ ok: true, user, token });
  } catch (e) { res.status(e.status || 400).json({ error: e.message }); }
});
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body || {};
    const { user, token } = await auth.login(email, password);
    res.json({ ok: true, user, token });
  } catch (e) { res.status(e.status || 401).json({ error: e.message }); }
});
app.get('/api/auth/me', auth.optionalAuth, async (req, res) => {
  if (!req.user) return res.status(401).json({ error: 'Not logged in' });
  res.json({ ok: true, user: req.user });
});
app.post('/api/auth/logout', (req, res) => res.json({ ok: true }));

app.get('/api/auth/firebase/config', (req, res) => res.json(firebaseAuth.getFirebaseConfig()));
app.post('/api/auth/firebase/google', async (req, res) => {
  try {
    const { idToken } = req.body || {};
    const result = await firebaseAuth.loginWithFirebase(idToken);
    res.json({ ok: true, ...result });
  } catch (e) { res.status(e.status || 500).json({ error: e.message }); }
});

// ---------- Health / Neural ----------
app.get('/api/health', (req, res) => res.json({ ok: true, service: 'auralis-ai', time: new Date().toISOString(), neural: neural.getNeuralStatus(), google: googleAuth.getGoogleConfig(), firebase: firebaseAuth.getFirebaseConfig(), hf: hf.getHFConfig() }));
app.get('/api/neural/status', (req, res) => res.json(neural.getNeuralStatus()));
app.get('/api/genres', (req, res) => res.json({ genres: Object.keys(GENRE_PROFILES), profiles: GENRE_PROFILES }));

app.get('/api/tracks', auth.optionalAuth, async (req, res) => {
  const q = (req.query.q || '').toLowerCase();
  const genre = req.query.genre || 'All';
  const sort = req.query.sort || 'recent';
  const mineOnly = req.query.mine === '1';
  const tracks = await store.readAll();
  let list = tracks;
  if (mineOnly && req.user) list = list.filter(t => t.userId === req.user.id || t.author === req.user.displayName);
  if (q) list = list.filter(t => (t.title + ' ' + t.prompt + ' ' + t.genre).toLowerCase().includes(q));
  if (genre !== 'All') list = list.filter(t => t.genre === genre);
  if (sort === 'popular') list = [...list].sort((a, b) => (b.plays || 0) - (a.plays || 0));
  else if (sort === 'liked') list = [...list].sort((a, b) => (b.likes || 0) - (a.likes || 0));
  else list = [...list].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  res.json({ tracks: list, total: list.length });
});

app.get('/api/tracks/:id', async (req, res) => {
  const tracks = await store.readAll();
  const t = tracks.find(x => x.id === req.params.id);
  if (!t) return res.status(404).json({ error: 'Track not found' });
  res.json({ track: t });
});

// ---------- Generate (procedural + optional neural) ----------
app.post('/api/generate', auth.optionalAuth, async (req, res) => {
  try {
    const body = req.body || {};
    const engine = body.engine || 'fast';
    const prompt = body.prompt || 'Beautiful AI melody';
    const duration = Math.min(90, Math.max(8, Number(body.duration) || 30));

    let track = null;
    if (engine === 'neural') {
      const nSec = Math.min(30, Math.max(5, Number(body.duration) || 10));
      const result = await neural.generateWithNeural({ prompt: prompt + ', ' + (body.genre || ''), duration: nSec, backend: body.backend });
      if (result.ok) {
        const preview = generateTrack({ prompt, genre: body.genre || 'Pop', bpm: body.bpm || null, root: body.root || 'C', scale: body.scale || 'C Major', duration: nSec, instruments: body.instruments || { melody: true, chords: true, bass: true, drums: true } });
        track = {
          ...preview,
          id: 'neural_' + Math.random().toString(36).slice(2, 9),
          title: prompt.length > 40 ? prompt.slice(0, 42) + '…' : prompt,
          audioUrl: result.url,
          engine: 'musicgen',
          model: result.model,
          via: result.via || 'local',
          duration: result.duration,
        };
      } else {
        const tr = generateTrack({ prompt, genre: body.genre || 'Pop', bpm: body.bpm ? Number(body.bpm) : null, mood: body.mood, root: body.root || 'C', scale: body.scale || 'C Major', duration, instruments: body.instruments });
        tr.fallbackReason = result.reason;
        tr.engine = 'fast-fallback';
        track = tr;
      }
    } else {
      track = generateTrack({
        prompt,
        genre: body.genre || 'Pop',
        bpm: body.bpm ? Number(body.bpm) : null,
        mood: body.mood || { energy: 0.5, brightness: 0.5, complexity: 0.5 },
        root: body.root || body.rootNote || 'C',
        scale: body.scale || 'C Major',
        duration: duration,
        instruments: body.instruments || { melody: true, chords: true, bass: true, drums: true },
      });
      track.engine = 'fast';
    }

    track.author = req.user ? req.user.displayName : (body.author || 'Guest');
    track.userId = req.user ? req.user.id : null;
    const all = await store.readAll();
    all.unshift(track);
    await store.writeAll(all.slice(0, 300));
    res.json({ ok: true, track });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Generation failed: ' + e.message });
  }
});

app.post('/api/neural/generate', auth.optionalAuth, async (req, res) => {
  try {
    const r = await neural.generateWithNeural({ prompt: req.body?.prompt || 'Piano melody', duration: req.body?.duration || 10, backend: req.body?.backend });
    if (!r.ok) return res.status(503).json({ ok: false, error: r.reason, status: neural.getNeuralStatus() });
    res.json({ ok: true, ...r });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/tracks/:id/like', async (req, res) => {
  const tracks = await store.readAll();
  const t = tracks.find(x => x.id === req.params.id);
  if (!t) return res.status(404).json({ error: 'Not found' });
  t.liked = !t.liked;
  t.likes = (t.likes || 0) + (t.liked ? 1 : -1);
  await store.writeAll(tracks);
  res.json({ ok: true, track: t });
});

app.post('/api/tracks/:id/play', async (req, res) => {
  const tracks = await store.readAll();
  const t = tracks.find(x => x.id === req.params.id);
  if (!t) return res.status(404).json({ error: 'Not found' });
  t.plays = (t.plays || 0) + 1;
  await store.writeAll(tracks);
  res.json({ ok: true, track: t });
});

app.post('/api/tracks/:id/remix', async (req, res) => {
  const tracks = await store.readAll();
  const orig = tracks.find(x => x.id === req.params.id);
  if (!orig) return res.status(404).json({ error: 'Not found' });
  const remix = generateTrack({
    prompt: orig.prompt + ' — remix variation',
    genre: req.body?.genre || orig.genre,
    bpm: req.body?.bpm || orig.bpm,
    mood: { energy: 0.5, brightness: 0.5, complexity: 0.6 },
    root: orig.root, scale: orig.scale, duration: orig.duration,
    instruments: { melody: true, chords: true, bass: true, drums: true },
  });
  remix.author = req.user ? req.user.displayName : 'Guest';
  remix.userId = req.user ? req.user.id : null;
  remix.remixOf = orig.id;
  tracks.unshift(remix);
  await store.writeAll(tracks);
  res.json({ ok: true, track: remix });
});

app.delete('/api/tracks/:id', async (req, res) => {
  const tracks = await store.readAll();
  const target = tracks.find(x => x.id === req.params.id);
  if (!target) return res.status(404).json({ error: 'Not found' });
  if (target.userId && req.user && target.userId !== req.user.id) return res.status(403).json({ error: 'Not your track' });
  if (target.userId && !req.user) return res.status(403).json({ error: 'Login required to delete' });
  const next = tracks.filter(x => x.id !== req.params.id);
  await store.writeAll(next);
  res.json({ ok: true });
});

app.post('/api/tracks/clear-mine', auth.optionalAuth, async (req, res) => {
  const tracks = await store.readAll();
  const keep = req.user ? t => t.userId !== req.user.id && !t.isSeed : t => t.isSeed;
  await store.writeAll(tracks.filter(keep));
  res.json({ ok: true });
});

app.get('/api/stats', auth.optionalAuth, async (req, res) => {
  const tracks = await store.readAll();
  const totalPlays = tracks.reduce((s, t) => s + (t.plays || 0), 0);
  const totalLikes = tracks.reduce((s, t) => s + (t.likes || 0), 0);
  const genres = [...new Set(tracks.map(t => t.genre))];
  const mine = req.user ? tracks.filter(t => t.userId === req.user.id).length : tracks.filter(t => t.author === 'Guest').length;
  res.json({
    totalTracks: tracks.length,
    totalPlays, totalLikes, mine, genresCount: genres.length,
    genres, avgDuration: tracks.length ? Math.round(tracks.reduce((s, t) => s + (t.duration || 0), 0) / tracks.length) : 0,
    artistCount: new Set(tracks.map(t => t.author)).size,
    neural: neural.getNeuralStatus(),
  });
});

app.get('/api/tracks/:id/export.json', async (req, res) => {
  const tracks = await store.readAll();
  const t = tracks.find(x => x.id === req.params.id);
  if (!t) return res.status(404).json({ error: 'Not found' });
  res.json(t);
});

app.get('*', (req, res) => {
  if (req.path.startsWith('/api/')) return res.status(404).json({ error: 'API route not found' });
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Vercel/Netlify serverless fallback for /api/generate
app.use('/api/generate', require('./api/generate'));

app.listen(PORT, () => {
  const n = neural.getNeuralStatus();
  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`🎵 Auralis AI — Music Generation Studio v2.1`);
  console.log(`🚀 Server running at http://localhost:${PORT}`);
  console.log(`🔐 Auth: email + Google (JWT)`);
  console.log(`🧠 Neural: ${n.enabledByEnv ? 'ON' : 'off'} | backend=${n.backendPreference} | backends=${n.backends.join(',')}`);
  console.log(`📁 Frontend: http://localhost:${PORT}/`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
});
