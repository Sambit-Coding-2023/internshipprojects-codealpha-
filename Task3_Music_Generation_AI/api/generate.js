// Auralis AI — Music Generation Platform
// Fast procedural AI + optional Neural (MusicGen) + auth (email + Google)

module.exports = async function handler(req, res) {
  // Static hosting fallback (e.g. Vercel/Netlify) — for local run use `npm start` (Express server.js)
  try {
    const { generateTrack } = require('./backend/musicEngine');
    if (req.method === 'POST' && req.url === '/api/generate') {
      const body = req.body || {};
      const track = generateTrack({
        prompt: body.prompt || 'Beautiful AI melody',
        genre: body.genre || 'Pop',
        bpm: body.bpm ? Number(body.bpm) : null,
        mood: body.mood || { energy: 0.5, brightness: 0.5, complexity: 0.5 },
        root: body.root || 'C',
        scale: body.scale || 'C Major',
        duration: Math.min(90, Math.max(8, Number(body.duration) || 30)),
        instruments: body.instruments || { melody: true, chords: true, bass: true, drums: true },
      });
      track.author = body.author || 'You';
      return res.status(200).json({ ok: true, track });
    }
  } catch (e) {}
  return res.status(200).json({ ok: true, note: 'Vercel static fallback — run Express server for full API', tracks: [] });
};
