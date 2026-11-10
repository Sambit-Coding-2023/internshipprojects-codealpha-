// Auralis AI — Track store (async fs promises, non-blocking)
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const FILE = path.join(DATA_DIR, 'tracks.json');

function ensure() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(FILE)) fs.writeFileSync(FILE, JSON.stringify(seedTracks(), null, 2));
}

function readAll() {
  ensure();
  return new Promise((resolve) => {
    try { resolve(JSON.parse(fs.readFileSync(FILE, 'utf8'))); } catch { resolve([]); }
  });
}
function writeAll(tracks) {
  ensure();
  return new Promise((resolve, reject) => {
    fs.writeFileSync(FILE, JSON.stringify(tracks, null, 2), 'utf8', (e) => (e ? reject(e) : resolve(true)));
  });
}

function seedTracks() {
  const { generateTrack } = require('./musicEngine');
  const seeds = [
    { prompt: 'Midnight city cruise — synthwave ', genre: 'Synthwave', bpm: 102, root: 'A', scale: 'A Minor', duration: 24, mood: { energy: 0.7, brightness: 0.8, complexity: 0.5 } },
    { prompt: 'Rainy evening lo-fi study beats', genre: 'Lo-Fi', bpm: 76, root: 'C', scale: 'C Major', duration: 24, mood: { energy: 0.3, brightness: 0.35, complexity: 0.4 } },
    { prompt: 'Epic orchestral sunrise', genre: 'Classical', bpm: 72, root: 'G', scale: 'G Major', duration: 24, mood: { energy: 0.5, brightness: 0.55, complexity: 0.8 } },
    { prompt: 'Neon club anthem EDM', genre: 'EDM', bpm: 128, root: 'D', scale: 'D Major', duration: 24, mood: { energy: 0.9, brightness: 0.9, complexity: 0.4 } },
    { prompt: 'Dreamy ambient clouds', genre: 'Ambient', bpm: 60, root: 'E', scale: 'E Minor', duration: 24, mood: { energy: 0.2, brightness: 0.3, complexity: 0.3 } },
    { prompt: 'Jazz café night piano', genre: 'Jazz', bpm: 98, root: 'F', scale: 'F Major', duration: 24, mood: { energy: 0.4, brightness: 0.5, complexity: 0.7 } },
  ];
  return seeds.map((s, i) => {
    const t = generateTrack({ ...s, instruments: { melody: true, chords: true, bass: true, drums: true } });
    t.plays = 120 + i * 47;
    t.likes = 18 + i * 9;
    t.author = ['Nova', 'Kai', 'Luna', 'Atlas', 'Mira', 'Juno'][i];
    t.isSeed = true;
    t.palette = [
      ['#7c3aed', '#ec4899'], ['#06b6d4', '#3b82f6'], ['#f59e0b', '#ef4444'],
      ['#10b981', '#06b6d4'], ['#8b5cf6', '#06b6d4'], ['#ec4899', '#f59e0b'],
    ][i];
    return t;
  });
}

module.exports = { readAll, writeAll, ensure };
