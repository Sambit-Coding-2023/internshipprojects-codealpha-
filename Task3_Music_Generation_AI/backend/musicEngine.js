// Auralis AI Music Engine — procedural generative music
// Seeded composition from prompt + genre + mood params

const NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const SCALES = {
  'C Major': [0,2,4,5,7,9,11],
  'A Minor': [0,2,3,5,7,8,10],
  'G Major': [7,9,11,0,2,4,6], // normalized below
  'D Major': [2,4,6,7,9,11,1],
  'E Minor': [4,6,7,9,11,0,2],
  'F Major': [5,7,9,10,0,2,4],
  'Pentatonic': [0,2,4,7,9],
};
const GENRE_PROFILES = {
  'Pop':        { chords: [[0,4,7],[5,7,12],[7,11,14],[9,12,16]], tempo: 100, brightness: 0.7, drum: 'pop', melodic: 0.5 },
  'Lo-Fi':      { chords: [[0,4,7,10],[ -4,0,4,7],[-2,2,5,9],[5,9,12,15]], tempo: 76, brightness: 0.35, drum: 'lofi', melodic: 0.3 },
  'Synthwave':  { chords: [[0,3,7],[8,12,15],[5,9,12],[3,7,10]], tempo: 102, brightness: 0.85, drum: 'synth', melodic: 0.6 },
  'Classical':  { chords: [[0,4,7],[5,9,12],[7,11,14],[0,4,7]], tempo: 72, brightness: 0.5, drum: 'none', melodic: 0.8 },
  'EDM':        { chords: [[0,4,7],[0,4,7],[5,9,12],[7,11,14]], tempo: 128, brightness: 0.9, drum: 'edm', melodic: 0.4 },
  'Jazz':       { chords: [[0,4,7,11],[2,5,9,12],[4,7,11,14],[7,10,14,17]], tempo: 98, brightness: 0.5, drum: 'lofi', melodic: 0.7 },
  'Ambient':    { chords: [[0,4,7,11],[2,7,11,14],[-2,2,5,9],[9,12,16,19]], tempo: 60, brightness: 0.25, drum: 'none', melodic: 0.25 },
  'Rock':       { chords: [[0,4,7],[3,7,10],[5,9,12],[7,11,14]], tempo: 120, brightness: 0.75, drum: 'edm', melodic: 0.55 },
  'Cinematic':  { chords: [[0,4,7],[8,12,16],[5,9,12],[7,11,14]], tempo: 84, brightness: 0.6, drum: 'none', melodic: 0.65 },
};

function hashSeed(str) {
  let h = 2166136261;
  const s = String(str || 'auralis');
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h) >>> 0;
}
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function midiToFreq(m) { return Math.round(440 * Math.pow(2, (m - 69) / 12) * 100) / 100; }

function resolveScale(rootName, scaleName) {
  const rootIdx = NOTE_NAMES.indexOf(rootName || 'C');
  const base = SCALES[scaleName] || SCALES['C Major'];
  // normalize so intervals are from 0
  const intervals = base.map(v => (v - base[0] + 12) % 12);
  return { root: (rootIdx >= 0 ? rootIdx : 0) + 60, intervals };
}

function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }

function generateTrack(opts = {}) {
  const {
    prompt = 'A beautiful morning melody',
    genre = 'Pop',
    bpm = null,
    mood = { energy: 0.5, brightness: 0.5, complexity: 0.5 },
    root = 'C',
    scale = 'C Major',
    duration = 30, // seconds
    instruments = { melody: true, chords: true, bass: true, drums: true },
  } = opts;

  const profile = GENRE_PROFILES[genre] || GENRE_PROFILES.Pop;
  const finalBpm = bpm || profile.tempo;
  const beatSec = 60 / finalBpm;
  const seed = hashSeed(prompt + genre + finalBpm + root + scale);
  const rng = mulberry32(seed);

  const { root: rootMidi, intervals } = resolveScale(root, scale);
  const complexity = mood.complexity ?? 0.5;
  const energy = mood.energy ?? 0.5;

  const totalBeats = Math.max(8, Math.floor(duration / beatSec));
  // bar = 4 beats, chords per bar
  const numBars = Math.ceil(totalBeats / 4);

  const notes = []; // {time, midi, dur, instr, vel, type}

  for (let bar = 0; bar < numBars; bar++) {
    const chordTones = profile.chords[bar % profile.chords.length];
    const chordStart = bar * 4 * beatSec;
    const chordRootMidi = rootMidi + (chordTones[0]);
    const chordQuality = chordTones;

    // Chords
    if (instruments.chords) {
      chordQuality.forEach((iv, i) => {
        const m = rootMidi + iv + (i === 0 ? 0 : 0); // keep voicing
        const dur = 4 * beatSec * 0.92;
        // pad on beat 1
        notes.push({ time: +chordStart.toFixed(3), midi: m, dur: +dur.toFixed(3), instr: 'pad', vel: 0.35, bar, beat: 0 });
      });
      // variation: fifth/bass emphasis
    }

    // Bass — root note each beat or half-beat
    if (instruments.bass) {
      const bassNotesPerBar = energy > 0.6 ? 4 : (complexity > 0.6 ? 4 : 2);
      const bassRoot = rootMidi - 12 + (chordTones[0] % 12 === 0 ? 0 : chordTones[0] - intervals[0]);
      const bassMidi = Math.max(36, rootMidi - 12 + chordTones[0]);
      for (let b = 0; b < bassNotesPerBar; b++) {
        const t = chordStart + b * (4 / bassNotesPerBar) * beatSec;
        const m = bassMidi + (b === 3 && complexity > 0.5 ? 7 : 0);
        notes.push({ time: +t.toFixed(3), midi: m, dur: +(beatSec * 0.8).toFixed(3), instr: 'bass', vel: 0.6, bar, beat: b });
      }
    }

    // Melody — Markov-ish random walk on scale
    if (instruments.melody) {
      let degree = 2 + Math.floor(rng() * 3); // start mid-scale
      const stepsPerBar = complexity > 0.7 ? 6 : (complexity > 0.4 ? 4 : 3);
      for (let s = 0; s < stepsPerBar; s++) {
        if (rng() < 0.15) continue; // rests
        const delta = pick(rng, [-2, -1, -1, 0, 1, 1, 2, 3]);
        degree = Math.max(0, Math.min(intervals.length * 2 - 1, degree + delta));
        const octave = Math.floor(degree / intervals.length);
        const degInScale = degree % intervals.length;
        const iv = intervals[degInScale];
        // melody in octave 5-ish
        const m = rootMidi + 12 + iv + octave * 12;
        const t = chordStart + (s / stepsPerBar) * 4 * beatSec;
        const dur = (beatSec * (rng() < 0.3 ? 0.5 : 1) * 0.9);
        const vel = 0.4 + rng() * 0.45;
        notes.push({ time: +t.toFixed(3), midi: m, dur: +dur.toFixed(3), instr: 'pluck', vel: +vel.toFixed(2), bar, beat: s });
      }
    }

    // Drums
    if (instruments.drums && profile.drum !== 'none') {
      const kickPattern = profile.drum === 'lofi' ? [0, 2] : profile.drum === 'synth' ? [0, 2] : profile.drum === 'edm' ? [0, 1, 2, 3] : [0, 2];
      kickPattern.forEach(b => {
        notes.push({ time: +(chordStart + b * beatSec).toFixed(3), midi: 36, dur: 0.15, instr: 'kick', vel: 0.9, bar, beat: b });
      });
      // snare/clap on 2&4
      [1, 3].forEach(b => {
        notes.push({ time: +(chordStart + b * beatSec).toFixed(3), midi: 38, dur: 0.18, instr: 'snare', vel: 0.7, bar, beat: b });
      });
      // hats
      const hatDensity = energy > 0.5 ? 8 : 4;
      for (let h = 0; h < hatDensity; h++) {
        const t = chordStart + (h / hatDensity) * 4 * beatSec;
        notes.push({ time: +t.toFixed(3), midi: 42, dur: 0.06, instr: 'hat', vel: h % 2 === 0 ? 0.4 : 0.25, bar, beat: h });
      }
    }
  }

  notes.sort((a, b) => a.time - b.time);
  notes.forEach(n => { n.freq = midiToFreq(n.midi); });

  const trackId = 'trk_' + seed.toString(16) + '_' + Math.floor(rng() * 1e6).toString(36);
  const title = prompt.length > 40 ? prompt.slice(0, 42) + '…' : prompt;
  const meta = {
    id: trackId,
    title,
    prompt,
    genre,
    bpm: finalBpm,
    root, scale,
    duration: Math.round((totalBeats * beatSec) * 10) / 10,
    mood, instruments,
    seed,
    createdAt: new Date().toISOString(),
    author: 'You',
    plays: 0, likes: 0, liked: false,
    notes,
    waveform: buildWaveformSummary(notes),
    palette: pick(rng, [
      ['#7c3aed','#ec4899'], ['#06b6d4','#3b82f6'], ['#f59e0b','#ef4444'],
      ['#10b981','#06b6d4'], ['#8b5cf6','#06b6d4'], ['#ec4899','#f59e0b']
    ]),
    key: `${root} ${scale.split(' ')[1]}`,
  };
  return meta;
}

function buildWaveformSummary(notes) {
  // 64 buckets energy
  const buckets = new Array(64).fill(0);
  const maxTime = notes.reduce((m, n) => Math.max(m, n.time + n.dur), 1) || 1;
  notes.forEach(n => {
    const idx = Math.min(63, Math.floor((n.time / maxTime) * 64));
    buckets[idx] += n.vel || 0.5;
  });
  const max = Math.max(...buckets, 0.01);
  return buckets.map(v => Math.round((v / max) * 100) / 100);
}

function toMidiLike(notes) {
  // lightweight MIDI-ish export object
  return { format: 1, notes: notes.map(n => ({ tick: Math.round(n.time * 480), midi: n.midi, dur: n.dur, instr: n.instr })) };
}

module.exports = { generateTrack, hashSeed, midiToFreq, GENRE_PROFILES, SCALES, NOTE_NAMES };
