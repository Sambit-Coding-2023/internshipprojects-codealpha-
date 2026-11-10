/* Auralis Player — Web Audio + Neural WAV playback, visualizer, WAV export */
(() => {
  let actx = null, master = null, analyser = null;
  let scheduledSources = [];
  let currentTrack = null, startAt = 0, pausedAt = 0, isPlaying = false, timer = null;
  let listeners = { progress: [], state: [] };
  const audioEl = new Audio();
  audioEl.preload = 'auto';
  audioEl.addEventListener('timeupdate', () => {
    if (currentTrack?.audioUrl) listeners.progress.forEach(fn => fn(audioEl.currentTime || 0, audioEl.duration || currentTrack.duration || 10));
  });
  audioEl.addEventListener('ended', () => { isPlaying = false; emitState(false); listeners.progress.forEach(fn => fn(0, audioEl.duration || currentTrack?.duration || 10)); });
  audioEl.addEventListener('play', () => { isPlaying = true; emitState(true); });
  audioEl.addEventListener('pause', () => { if (currentTrack?.audioUrl) isPlaying = false; });

  function ensureCtx() {
    if (!actx) {
      actx = new (window.AudioContext || window.webkitAudioContext)();
      master = actx.createGain(); master.gain.value = 0.8;
      analyser = actx.createAnalyser(); analyser.fftSize = 512;
      master.connect(analyser); analyser.connect(actx.destination);
    }
    if (actx.state === 'suspended') actx.resume();
    return actx;
  }
  function setVolume(v) { ensureCtx(); master.gain.value = v; audioEl.volume = v; }

  function playInstrument(time, freq, dur, instr, vel = 0.5) {
    const o = actx.createOscillator(), g = actx.createGain();
    const when = time;
    const d = Math.max(0.05, dur);
    if (instr === 'pad') {
      o.type = 'sawtooth'; o.frequency.value = freq;
      const f = actx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 900; f.Q.value = 0.6;
      g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(vel * 0.22, when + 0.08); g.gain.setValueAtTime(vel * 0.22, when + Math.max(0.09, d - 0.1)); g.gain.linearRampToValueAtTime(0, when + d);
      o.connect(f); f.connect(g); g.connect(master);
    } else if (instr === 'bass') {
      o.type = 'triangle'; o.frequency.value = freq;
      g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(vel * 0.5, when + 0.02); g.gain.exponentialRampToValueAtTime(0.001, when + d);
      o.connect(g); g.connect(master);
    } else if (instr === 'pluck') {
      o.type = 'square'; o.frequency.value = freq;
      const f = actx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 2200;
      g.gain.setValueAtTime(vel * 0.28, when); g.gain.exponentialRampToValueAtTime(0.001, when + d);
      o.connect(f); f.connect(g); g.connect(master);
    } else if (instr === 'kick' || instr === 'snare' || instr === 'hat') {
      if (instr === 'kick') {
        o.type = 'sine'; o.frequency.setValueAtTime(150, when); o.frequency.exponentialRampToValueAtTime(40, when + 0.12);
        g.gain.setValueAtTime(vel, when); g.gain.exponentialRampToValueAtTime(0.001, when + 0.16);
        o.connect(g); g.connect(master);
      } else {
        const buf = actx.createBuffer(1, Math.floor(actx.sampleRate * 0.2), actx.sampleRate);
        const ch = buf.getChannelData(0);
        for (let i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * (1 - i / ch.length);
        const src = actx.createBufferSource(); src.buffer = buf;
        const f = actx.createBiquadFilter();
        if (instr === 'snare') { f.type = 'bandpass'; f.frequency.value = 1800; } else { f.type = 'highpass'; f.frequency.value = 7000; }
        g.gain.setValueAtTime(vel * (instr === 'snare' ? 0.5 : 0.2), when); g.gain.exponentialRampToValueAtTime(0.001, when + (instr === 'snare' ? 0.14 : 0.06));
        src.connect(f); f.connect(g); g.connect(master);
        src.start(when); src.stop(when + 0.2);
        scheduledSources.push(src);
      }
      o.start(when); o.stop(when + d);
      scheduledSources.push(o);
      return;
    } else {
      o.type = 'sine'; o.frequency.value = freq;
      g.gain.setValueAtTime(vel * 0.3, when); g.gain.exponentialRampToValueAtTime(0.001, when + d);
      o.connect(g); g.connect(master);
    }
    o.start(when); o.stop(when + d + 0.05);
    scheduledSources.push(o);
  }

  function stopAll() {
    scheduledSources.forEach(s => { try { s.stop(); s.disconnect(); } catch {} });
    scheduledSources = [];
    if (timer) clearInterval(timer);
    try { audioEl.pause(); audioEl.currentTime = 0; } catch {}
    isPlaying = false;
    emitState(false);
  }

  function play(track, { rate = 1, volume = 0.8 } = {}) {
    if (track?.audioUrl) {
      stopAll();
      currentTrack = track;
      audioEl.src = track.audioUrl;
      audioEl.volume = volume;
      audioEl.playbackRate = rate;
      audioEl.currentTime = 0;
      audioEl.play().catch(() => {});
      isPlaying = true; emitState(true);
      return;
    }
    ensureCtx(); stopAll();
    currentTrack = track;
    setVolume(volume);
    const when = actx.currentTime + 0.08;
    const notes = track.notes || [];
    startAt = when; pausedAt = 0;
    notes.forEach(n => playInstrument(when + n.time / rate, n.freq || 440, n.dur / rate, n.instr, n.vel || 0.5));
    isPlaying = true; emitState(true);
    const total = (track.duration || 30) / rate;
    timer = setInterval(() => {
      const el = actx.currentTime - startAt;
      listeners.progress.forEach(fn => fn(el, total));
      if (el >= total) { stopAll(); listeners.progress.forEach(fn => fn(0, total)); }
    }, 100);
  }

  function pause() {
    if (!isPlaying) return;
    if (currentTrack?.audioUrl) { try { audioEl.pause(); } catch {} isPlaying = false; emitState(false); return; }
    pausedAt = actx.currentTime - startAt;
    stopAll();
    emitState(false);
  }
  function resume() {
    if (!currentTrack) return;
    if (currentTrack.audioUrl) { audioEl.play().catch(() => {}); isPlaying = true; emitState(true); return; }
    ensureCtx(); stopAll();
    const offset = pausedAt || 0;
    const when = actx.currentTime + 0.08;
    startAt = when - offset;
    (currentTrack.notes || []).forEach(n => { if (n.time < offset) return; playInstrument(when + (n.time - offset), n.freq || 440, n.dur, n.instr, n.vel || 0.5); });
    isPlaying = true; emitState(true);
    const total = currentTrack.duration || 30;
    timer = setInterval(() => {
      const el = actx.currentTime - startAt;
      listeners.progress.forEach(fn => fn(el, total));
      if (el >= total) { stopAll(); listeners.progress.forEach(fn => fn(0, total)); }
    }, 100);
  }
  function seek(sec) {
    if (currentTrack?.audioUrl) { try { audioEl.currentTime = Math.max(0, sec); listeners.progress.forEach(fn => fn(audioEl.currentTime, audioEl.duration || currentTrack.duration || 10)); } catch {} return; }
    pausedAt = sec;
    if (isPlaying) { resume(); } else { listeners.progress.forEach(fn => fn(sec, currentTrack?.duration || 30)); }
  }
  function onProgress(fn) { listeners.progress.push(fn); }
  function onState(fn) { listeners.state.push(fn); }
  function emitState(v) { listeners.state.forEach(fn => fn(v)); }
  function getAnalyser() { return analyser; }
  function isActive() { return isPlaying; }

  async function downloadWav(track) {
    if (track?.audioUrl) {
      const a = document.createElement('a'); a.href = track.audioUrl; a.download = (track.title || 'auralis-neural').replace(/[^a-z0-9]+/gi, '-').slice(0, 40) + '.wav'; a.click();
      return;
    }
    const sr = 44100;
    const dur = Math.ceil((track.duration || 30) + 0.5);
    const off = new OfflineAudioContext(2, sr * dur, sr);
    const out = off.createGain(); out.gain.value = 0.8; out.connect(off.destination);
    (track.notes || []).forEach(n => {
      const t = n.time, d = n.dur, f = n.freq || 440;
      const o = off.createOscillator(), g = off.createGain();
      if (n.instr === 'pad') { o.type = 'sawtooth'; o.frequency.value = f; const fl = off.createBiquadFilter(); fl.type = 'lowpass'; fl.frequency.value = 900; g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime((n.vel || 0.4) * 0.2, t + 0.08); g.gain.linearRampToValueAtTime(0.0001, t + d); o.connect(fl); fl.connect(g); }
      else if (n.instr === 'bass') { o.type = 'triangle'; o.frequency.value = f; g.gain.setValueAtTime((n.vel || 0.5) * 0.4, t); g.gain.exponentialRampToValueAtTime(0.001, t + d); o.connect(g); }
      else if (n.instr === 'kick') { o.type = 'sine'; o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.12); g.gain.setValueAtTime(0.7, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.16); o.connect(g); }
      else if (n.instr === 'snare' || n.instr === 'hat') { const buf = off.createBuffer(1, Math.floor(sr * 0.2), sr); const ch = buf.getChannelData(0); for (let i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * (1 - i / ch.length); const src = off.createBufferSource(); src.buffer = buf; const fl = off.createBiquadFilter(); fl.type = n.instr === 'snare' ? 'bandpass' : 'highpass'; fl.frequency.value = n.instr === 'snare' ? 1800 : 7000; g.gain.setValueAtTime(n.instr === 'snare' ? 0.4 : 0.15, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.12); src.connect(fl); fl.connect(g); src.start(t); src.stop(t + 0.2); g.connect(out); return; }
      else { o.type = n.instr === 'pluck' ? 'square' : 'sine'; o.frequency.value = f; g.gain.setValueAtTime((n.vel || 0.4) * 0.3, t); g.gain.exponentialRampToValueAtTime(0.001, t + d); o.connect(g); if (n.instr === 'pluck') { const fl = off.createBiquadFilter(); fl.type = 'lowpass'; fl.frequency.value = 2200; o.disconnect(); o.connect(fl); fl.connect(g); } }
      g.connect(out); o.start(t); o.stop(t + d + 0.05);
    });
    const rendered = await off.startRendering();
    const wav = audioBufferToWav(rendered);
    const blob = new Blob([wav], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = (track.title || 'auralis').replace(/[^a-z0-9]+/gi, '-').slice(0, 40) + '.wav'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  function audioBufferToWav(buffer) {
    const numCh = Math.min(2, buffer.numberOfChannels), sr = buffer.sampleRate, len = buffer.length * numCh * 2 + 44;
    const out = new ArrayBuffer(len), v = new DataView(out);
    const ch0 = buffer.getChannelData(0), ch1 = numCh > 1 ? buffer.getChannelData(1) : ch0;
    let off = 0;
    const ws = s => { for (let i = 0; i < s.length; i++) v.setUint8(off++, s.charCodeAt(i)); };
    const w32 = n => { v.setUint32(off, n, true); off += 4; }; const w16 = n => { v.setUint16(off, n, true); off += 2; };
    ws('RIFF'); w32(len - 8); ws('WAVEfmt '); w32(16); w16(1); w16(numCh); w32(sr); w32(sr * numCh * 2); w16(numCh * 2); w16(16); ws('data'); w32(len - off - 4);
    for (let i = 0; i < buffer.length; i++) { const s0 = Math.max(-1, Math.min(1, ch0[i])), s1 = Math.max(-1, Math.min(1, ch1[i])); v.setInt16(off, s0 * 32767, true); off += 2; if (numCh > 1) { v.setInt16(off, s1 * 32767, true); off += 2; } }
    return out;
  }

  function localGenerate(opts) {
    const scales = { 'C Major': [0, 2, 4, 5, 7, 9, 11], 'A Minor': [0, 2, 3, 5, 7, 8, 10], 'G Major': [0, 2, 4, 5, 7, 9, 11], 'D Major': [0, 2, 4, 6, 7, 9, 11], 'E Minor': [0, 2, 3, 5, 7, 8, 10], 'F Major': [0, 2, 4, 5, 7, 9, 10], 'Pentatonic': [0, 2, 4, 7, 9] };
    const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const rootIdx = Math.max(0, noteNames.indexOf(opts.root || 'C'));
    const iv = scales[opts.scale] || scales['C Major'];
    let seed = 1; const s = String(opts.prompt || 'auralis') + String(opts.bpm || 100);
    for (let i = 0; i < s.length; i++) { seed = (seed * 31 + s.charCodeAt(i)) >>> 0; }
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const bpm = opts.bpm || 100, beat = 60 / bpm, bars = Math.ceil((opts.duration || 30) / beat / 4);
    const notes = []; const rootMidi = 60 + rootIdx;
    const chords = opts.genre === 'Lo-Fi' || opts.genre === 'Jazz' ? [[0, 4, 7, 10], [4, 7, 11, 14], [2, 5, 9, 12], [5, 9, 12, 15]] : [[0, 4, 7], [5, 9, 12], [7, 11, 14], [9, 12, 16]];
    for (let bar = 0; bar < bars; bar++) {
      const ch = chords[bar % chords.length]; const cs = bar * 4 * beat;
      ch.forEach(v => notes.push({ time: +cs.toFixed(3), midi: rootMidi + v, dur: +(4 * beat * 0.92).toFixed(3), instr: 'pad', vel: 0.35, bar, beat: 0, freq: 440 * Math.pow(2, (rootMidi + v - 69) / 12) }));
      for (let b = 0; b < 4; b++) { const bm = rootMidi - 12 + ch[0]; notes.push({ time: +(cs + b * beat).toFixed(3), midi: bm, dur: +(beat * 0.8).toFixed(3), instr: 'bass', vel: 0.55, bar, beat: b, freq: 440 * Math.pow(2, (bm - 69) / 12) }); }
      let deg = 2 + Math.floor(rnd() * 3);
      for (let k = 0; k < 4; k++) { deg = Math.max(0, Math.min(iv.length * 2 - 1, deg + [-1, 0, 1, 2][Math.floor(rnd() * 4)])); const m = rootMidi + 12 + iv[deg % iv.length] + Math.floor(deg / iv.length) * 12; notes.push({ time: +(cs + k * beat + Math.floor(rnd() * 2) * beat * 0.5).toFixed(3), midi: m, dur: +(beat * 0.7).toFixed(3), instr: 'pluck', vel: 0.5, bar, beat: k, freq: 440 * Math.pow(2, (m - 69) / 12) }); }
      [0, 2].forEach(b => notes.push({ time: +(cs + b * beat).toFixed(3), midi: 36, dur: 0.15, instr: 'kick', vel: 0.8, bar, beat: b, freq: 65 }));
      [1, 3].forEach(b => notes.push({ time: +(cs + b * beat).toFixed(3), midi: 38, dur: 0.18, instr: 'snare', vel: 0.6, bar, beat: b, freq: 180 }));
      for (let h = 0; h < 8; h++) notes.push({ time: +(cs + h * beat * 0.5).toFixed(3), midi: 42, dur: 0.06, instr: 'hat', vel: h % 2 ? 0.2 : 0.35, bar, beat: h, freq: 8000 });
    }
    notes.sort((a, b) => a.time - b.time);
    return { id: 'local_' + Date.now().toString(36), title: opts.prompt || 'AI track', prompt: opts.prompt || 'AI track', genre: opts.genre || 'Pop', bpm, root: opts.root || 'C', scale: opts.scale || 'C Major', duration: opts.duration || 30, mood: opts.mood, instruments: opts.instruments, seed, createdAt: new Date().toISOString(), author: 'You', plays: 0, likes: 0, liked: false, notes, palette: ['#7c3aed', '#ec4899'], waveform: notes.slice(0, 64).map(() => 0.3 + Math.random() * 0.7) };
  }

  window.AuralisPlayer = { play, pause, resume, stop: stopAll, seek, setVolume, onProgress, onState, getAnalyser, isActive: () => isPlaying, downloadWav, localGenerate, getCurrent: () => currentTrack };
})();
