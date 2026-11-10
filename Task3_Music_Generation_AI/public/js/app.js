/* Auralis AI v2 — Auth + Neural + Player */
(() => {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const state = { tracks: [], current: null, genre: 'Pop', query: '', view: 'create', user: null, token: localStorage.getItem('auralis_token') || null, engine: 'fast', backend: 'auto' };
  try { state.user = JSON.parse(localStorage.getItem('auralis_user') || 'null'); } catch {}
  const GENRES_FALLBACK = ['Pop','Lo-Fi','Synthwave','Classical','EDM','Jazz','Ambient','Rock','Cinematic'];
  const EMOJIS = ['🎹','🎸','🥁','🎺','🎻','🎷','🔥','✨','🌙','⚡'];

  function toast(msg){ const t=$('#toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2800); }
  function fmtTime(s){ s=Math.max(0,Math.floor(s)); return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); }
  function waveHtml(wf){ return (wf||Array.from({length:32},()=>0.4+Math.random()*0.6)).map(v=>`<i style="height:${Math.round(v*100)}%"></i>`).join(''); }
  function artEmoji(t){ return EMOJIS[Math.abs((t.seed||0))%EMOJIS.length]; }
  function authHeaders(){ return state.token ? { 'Authorization': 'Bearer '+state.token } : {}; }

  // Auth UI
  function renderAuth(){
    const area = $('#authArea');
    if (state.user) {
      area.innerHTML = `<div class="user-chip"><div class="avatar">${esc(state.user.displayName.slice(0,1).toUpperCase())}</div><span style="font-size:13px;font-weight:700">${esc(state.user.displayName)}</span><button id="logoutBtn">Logout</button></div>`;
      $('#logoutBtn').onclick = () => { state.user=null; state.token=null; localStorage.removeItem('auralis_token'); localStorage.removeItem('auralis_user'); renderAuth(); loadTracks(); toast('Logged out'); };
    } else {
      area.innerHTML = `<button class="btn primary sm" id="loginBtn">🔐 Login</button>`;
      $('#loginBtn').onclick = openAuth;
    }
  }
  function openAuth(){ $('#authModal').classList.add('show'); $('#authModal').setAttribute('aria-hidden','false'); }
  function closeAuth(){ $('#authModal').classList.remove('show'); $('#authModal').setAttribute('aria-hidden','true'); }
  function switchTab(tab){
    $$('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===tab));
    $('#loginForm').hidden = tab!=='login'; $('#signupForm').hidden = tab!=='signup';
    $('#authTitle').textContent = tab==='login' ? '🎧 Welcome back' : '✨ Join Auralis AI';
    $('#authSub').textContent = tab==='login' ? 'Login to save your songs to your account.' : 'Create free account to publish and remix.';
  }
  $$('.tab').forEach(t=>t.onclick=()=>switchTab(t.dataset.tab));
  $('#authClose').onclick=closeAuth;
  $('#authModal').addEventListener('click', e=>{ if(e.target.id==='authModal') closeAuth(); });
  $('#loginBtn')?.addEventListener('click', openAuth);
  $('#loginForm').onsubmit = async (e)=>{ e.preventDefault(); const email=$('#loginEmail').value.trim(), password=$('#loginPassword').value; try{ const d=await api('/api/auth/login',{method:'POST', body:{email,password}}); saveSession(d); closeAuth(); toast(`Hi ${d.user.displayName} 👋`); await loadTracks(); }catch(err){ toast('Login failed: '+err.message); } };
  $('#signupForm').onsubmit = async (e)=>{ e.preventDefault(); const displayName=$('#signupName').value.trim(), email=$('#signupEmail').value.trim(), password=$('#signupPassword').value; try{ const d=await api('/api/auth/register',{method:'POST', body:{email,password,displayName}}); saveSession(d); closeAuth(); toast(`Account created, ${d.user.displayName}! 🎉`); await loadTracks(); }catch(err){ toast('Signup failed: '+err.message); } };
  function saveSession(d){ state.user=d.user; state.token=d.token; localStorage.setItem('auralis_token', d.token); localStorage.setItem('auralis_user', JSON.stringify(d.user)); renderAuth(); }

  // Neural badge
  async function loadNeuralStatus(){
    try{ const d=await api('/api/neural/status'); $('#neuralState').textContent = d.enabledByEnv ? 'Neural ON' : 'Fast'; $('#neuralBadge').title = d.hint; }catch{ $('#neuralState').textContent='Fast'; }
  }
  $('#neuralBadge').onclick = async ()=>{
    try{ const d=await api('/api/neural/status'); toast(d.hint); }catch{}
  };

  // Engine chips
  $$('#engineChips .chip').forEach(c=>c.onclick=()=>{ state.engine=c.dataset.engine; $$('#engineChips .chip').forEach(x=>x.classList.toggle('sel', x===c)); $('#engineHint').textContent = state.engine==='neural' ? 'Neural MusicGen: Auto tries HF Spaces GPU first, then local. Falls back to Fast if unavailable.' : 'Fast = procedural AI, instant — recommended for demos.'; });
  $$('#backendChips .chip').forEach(c=>c.onclick=()=>{ state.backend=c.dataset.backend; $$('#backendChips .chip').forEach(x=>x.classList.toggle('sel', x===c)); toast('Neural backend: '+state.backend); });

  // Firebase Google Auth
  async function initFirebase(){
    const hint = $('#googleHint');
    try{
      const fbAuth = window.firebaseAuth;
      const fbProvider = window.firebaseGoogleProvider;
      if(!fbAuth || !fbProvider){ hint.textContent = 'Firebase SDK loading…'; setTimeout(initFirebase, 600); return; }
      hint.textContent = 'One-tap Google sign-in';
      let cfg = { enabled: true };
      try{ cfg = await api('/api/auth/firebase/config'); }catch(e){}
      if(!cfg.enabled){ hint.textContent = 'Firebase enabled on server pending service-account setup — Google sign-in will attempt anyway.'; }
      $('#googleFirebaseBtn').onclick = async () => {
        try{
          hint.textContent = 'Connecting to Google…';
          const result = await fbAuth.signInWithPopup(fbProvider);
          const idToken = result.credential?.idToken;
          if(!idToken) throw new Error('No Firebase idToken returned');
          const d = await api('/api/auth/firebase/google', { method:'POST', body:{ idToken } });
          saveSession(d); closeAuth(); toast(`Hi ${d.user.displayName} (Google) 👋`);
          await loadTracks();
        }catch(e){ toast('Google login failed: '+e.message); hint.textContent='One-tap Google sign-in'; }
      };
    }catch(e){ hint.textContent = 'Google sign-in unavailable: '+e.message; }
  }

  // Genre chips
  let genreChips = $('#genreChips');
  function renderGenres(list){
    genreChips.innerHTML = list.map(g=>`<button class="chip ${g===state.genre?'sel':''}" data-g="${g}">${g}</button>`).join('');
    genreChips.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{state.genre=c.dataset.g; renderGenres(list); toast('Genre: '+state.genre);});
    const lg=$('#libGenre'); lg.innerHTML='<option>All</option>'+list.map(g=>`<option>${g}</option>`).join('');
    $('#topGenres').innerHTML=list.slice(0,6).map(g=>`<button class="chip" data-tg="${g}">${g}</button>`).join('');
    $$('#topGenres .chip').forEach(b=>b.onclick=()=>{state.genre=b.dataset.tg; switchView('create'); renderGenres(list); toast('Genre: '+state.genre); $('#promptInput').focus();});
  }

  const bpmR=$('#bpmRange'), durR=$('#durRange'), eR=$('#energyRange'), bR=$('#brightRange'), cR=$('#complexRange');
  function syncLabels(){ $('#bpmOut').textContent=bpmR.value+' BPM'; $('#durOut').textContent=durR.value+'s'; $('#energyOut').textContent=eR.value+'%'; $('#brightOut').textContent=bR.value+'%'; $('#complexOut').textContent=cR.value+'%'; }
  [bpmR,durR,eR,bR,cR].forEach(el=>el.addEventListener('input',syncLabels)); syncLabels();

  function switchView(v){
    state.view=v;
    $$('.view').forEach(s=>s.classList.remove('active'));
    $('#view-'+v).classList.add('active');
    $$('.pill').forEach(p=>p.classList.toggle('active', p.dataset.view===v));
    if(v==='library') loadLibrary();
    if(v==='explore') loadExplore();
    if(v==='studio') loadStats();
  }
  $$('.pill').forEach(p=>p.onclick=()=>switchView(p.dataset.view));
  $$('[data-goto]').forEach(b=>b.onclick=()=>switchView(b.dataset.goto));

  async function api(path, opts={}){
    const headers = { 'Content-Type':'application/json', ...authHeaders(), ...(opts.headers||{}) };
    const r=await fetch(path, { headers, ...opts, body: opts.body? JSON.stringify(opts.body): undefined });
    const text = await r.text();
    let data; try{ data=JSON.parse(text); }catch{ data={error:text}; }
    if(!r.ok) throw new Error(data.error || r.statusText);
    return data;
  }

  async function loadTracks(){
    try{ const d=await api('/api/tracks'); state.tracks=d.tracks; renderAll(); }catch(e){ console.warn('API offline', e); }
  }
  async function loadLibrary(){
    const q=($('#libSearch').value||'').toLowerCase(); const g=$('#libGenre').value; const sort=$('#libSort').value;
    let list=[...state.tracks]; if(q) list=list.filter(t=>(t.title+' '+t.prompt+' '+t.genre).toLowerCase().includes(q)); if(g!=='All') list=list.filter(t=>t.genre===g);
    if(sort==='popular') list.sort((a,b)=>(b.plays||0)-(a.plays||0)); else if(sort==='liked') list.sort((a,b)=>(b.likes||0)-(a.likes||0)); else list.sort((a,b)=>new Date(b.createdAt)-new Date(a.createdAt));
    renderGrid('#libGrid', list);
    $('#libEmpty').style.display=list.length?'none':'block';
    $('#libCount').textContent=state.tracks.length;
  }
  async function loadExplore(){
    let list=[...state.tracks].sort((a,b)=>(b.plays||0)-(a.plays||0));
    renderGrid('#exploreGrid', list);
  }
  function renderAll(){
    renderGrid('#recentGrid', [...state.tracks].slice(0,6));
    if(state.view==='library') loadLibrary();
    if(state.view==='explore') loadExplore();
    $('#libCount').textContent=state.tracks.length;
    if(state.tracks.length){
      const top=[...state.tracks].sort((a,b)=>(b.plays||0)-(a.plays||0))[0];
      $('#trendingTitle').textContent=top.title; $('#trendingMeta').textContent=`${top.genre} • ${top.bpm} BPM • ${top.plays||0} plays • by ${top.author||'Guest'}`;
      $('#miniWave').innerHTML=waveHtml(top.waveform);
    }
  }

  function renderGrid(sel, list){
    const el=$(sel); if(!el) return;
    el.innerHTML = list.map(t=>`
      <article class="track-card" data-id="${t.id}">
        <div class="tc-top"><div class="tc-art" style="background:linear-gradient(135deg, ${t.palette?.[0]||'#7c3aed'}, ${t.palette?.[1]||'#ec4899'})">${artEmoji(t)}</div>
        <div><div class="tc-title">${esc(t.title)} ${t.engine==='musicgen'?'🧠':''}</div><div class="tc-meta">${t.genre} • ${t.bpm} BPM • ${fmtTime(t.duration||30)} • ▶ ${t.plays||0} • ♥ ${t.likes||0} • by ${esc(t.author||'Guest')}</div></div></div>
        <div class="tc-wave">${waveHtml(t.waveform)}</div>
        <div class="tc-actions">
          <button class="btn primary sm" data-act="play">▶ Play</button>
          <button class="btn ghost sm" data-act="like">${t.liked?'❤️':'🤍'} ${t.likes||0}</button>
          <button class="btn ghost sm" data-act="remix">🔀 Remix</button>
          <button class="btn ghost sm" data-act="dl">⬇ WAV</button>
          <button class="btn ghost sm" data-act="del">🗑</button>
        </div>
      </article>`).join('') || '<p class="muted">No tracks match.</p>';
    el.querySelectorAll('.track-card').forEach(card=>{
      const id=card.dataset.id;
      card.querySelectorAll('[data-act]').forEach(btn=>{
        btn.onclick=async (e)=>{
          e.stopPropagation();
          const act=btn.dataset.act; const track=state.tracks.find(x=>x.id===id); if(!track) return;
          if(act==='play'){ playTrack(track); }
          else if(act==='like'){ try{ const d=await api(`/api/tracks/${id}/like`,{method:'POST'}); Object.assign(track, d.track); renderAll(); toast(d.track.liked?'Liked ❤️':'Unliked'); }catch{ toast('Like failed'); } }
          else if(act==='remix'){ try{ toast('Remixing…'); const d=await api(`/api/tracks/${id}/remix`,{method:'POST', body:{genre: state.genre}}); state.tracks.unshift(d.track); renderAll(); playTrack(d.track); toast('Remix ready! ✨'); }catch{ toast('Remix failed'); } }
          else if(act==='dl'){ toast('Exporting WAV…'); await window.AuralisPlayer.downloadWav(track); }
          else if(act==='del'){ if(!confirm('Delete this track?')) return; try{ await api(`/api/tracks/${id}`,{method:'DELETE'}); state.tracks=state.tracks.filter(x=>x.id!==id); renderAll(); toast('Deleted'); }catch{ toast('Delete failed'); } }
        };
      });
      card.onclick=(e)=>{ if(e.target.closest('button')) return; const track=state.tracks.find(x=>x.id===id); if(track) playTrack(track); };
    });
  }
  function esc(s){ return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  let playbackRate=1;
  function playTrack(track){
    state.current=track; switchView('create');
    $('#nowTitle').textContent=track.title;
    $('#nowMeta').textContent=`${track.genre} • ${track.bpm} BPM • ${track.root} ${track.scale} • by ${track.author||'Guest'}${track.engine==='musicgen'?' • 🧠 MusicGen':''}`;
    $('#nowTags').innerHTML=`<span>${track.genre}</span><span>${track.bpm} BPM</span><span>${track.key||''}</span><span>${track.engine||'fast'}</span><span>▶ ${track.plays||0}</span>`;
    $('#artwork').textContent=track.engine==='musicgen'?'🧠':artEmoji(track); $('#artwork').style.background=`linear-gradient(135deg, ${track.palette?.[0]||'#7c3aed'}, ${track.palette?.[1]||'#ec4899'})`;
    $('#waveBig').innerHTML=waveHtml(track.waveform);
    $('#durTime').textContent=fmtTime(track.duration||30);
    $('#bbTitle').textContent=track.title; $('#bbMeta').textContent=`${track.genre} • ${track.bpm} BPM • ${track.author||''}`;
    $('#likeBtn').textContent=`${track.liked?'❤️':'🤍'} ${track.likes||0}`;
    $('#emptyState').style.display='none';
    window.AuralisPlayer.play(track, { volume: $('#volume').value/100 });
    api(`/api/tracks/${track.id}/play`,{method:'POST'}).then(d=>{ Object.assign(track, d.track); renderAll(); }).catch(()=>{});
  }
  $('#playBtn').onclick=()=>{
    if(!state.current){ toast('Generate a track first ✨'); return; }
    if(window.AuralisPlayer.isActive()) window.AuralisPlayer.pause(); else window.AuralisPlayer.resume();
  };
  window.AuralisPlayer.onState(isPlaying=>{
    $('#playBtn').textContent=isPlaying?'⏸':'▶';
    $('#bbPlay').textContent=isPlaying?'⏸ Pause':'▶ Play';
  });
  window.AuralisPlayer.onProgress((cur, total)=>{
    $('#progress').style.width=(total? (cur/total*100):0)+'%';
    $('#curTime').textContent=fmtTime(cur);
    const bars=[...$('#waveBig').children]; if(bars.length){ const p=cur/(total||1); bars.forEach((b,i)=>{ b.classList.toggle('on', i/bars.length<=p); b.classList.toggle('played', i/bars.length<=p*0.6); }); }
  });
  $('#bbPlay').onclick=()=>$('#playBtn').click();
  $('#prevBtn').onclick=()=>window.AuralisPlayer.seek(Math.max(0, (parseFloat($('#curTime').textContent)||0)-5));
  $('#nextBtn').onclick=()=>window.AuralisPlayer.seek((parseFloat($('#curTime').textContent)||0)+5);
  $('#volume').oninput=e=>window.AuralisPlayer.setVolume(e.target.value/100);
  $('#playbackRate').oninput=e=>{ playbackRate=e.target.value/100; $('#rateOut').textContent=playbackRate.toFixed(1)+'×'; if(state.current && window.AuralisPlayer.isActive()) window.AuralisPlayer.play(state.current,{volume:$('#volume').value/100}); };
  $('#likeBtn').onclick=async ()=>{ if(!state.current) return; try{ const d=await api(`/api/tracks/${state.current.id}/like`,{method:'POST'}); Object.assign(state.current, d.track); $('#likeBtn').textContent=`${state.current.liked?'❤️':'🤍'} ${state.current.likes||0}`; renderAll(); }catch{ toast('Like failed'); } };
  $('#bbLike').onclick=()=>$('#likeBtn').click();
  $('#downloadBtn').onclick=async ()=>{ if(!state.current) return toast('No track loaded'); toast('Exporting WAV…'); await window.AuralisPlayer.downloadWav(state.current); toast('WAV downloaded ⬇'); };
  $('#remixBtn').onclick=async ()=>{ if(!state.current) return toast('Load a track to remix'); toast('Remixing…'); try{ const d=await api(`/api/tracks/${state.current.id}/remix`,{method:'POST',body:{genre:state.genre}}); state.tracks.unshift(d.track); renderAll(); playTrack(d.track); toast('Remix ready!'); }catch(e){ toast('Remix failed: '+e.message); } };
  $('#deleteBtn').onclick=async ()=>{
    if(!state.current) return toast('No track loaded');
    if(!confirm('Delete this track?')) return;
    const id=state.current.id;
    try{ await api(`/api/tracks/${id}`,{method:'DELETE'}); }catch(e){ toast(e.message); return; }
    state.tracks=state.tracks.filter(x=>x.id!==id); state.current=null;
    $('#nowTitle').textContent='Your AI track'; $('#nowMeta').textContent='Press Generate to create your first song'; $('#nowTags').innerHTML=''; $('#waveBig').innerHTML=''; $('#emptyState').style.display='block'; $('#progress').style.width='0%';
    window.AuralisPlayer.stop(); renderAll(); toast('Deleted');
  };

  $('#generateBtn').onclick=async ()=>{
    const btn=$('#generateBtn'); btn.classList.add('loading');
    btn.textContent = state.engine==='neural' ? '🧠 Neural generating (20–60s)…' : '🎼 Composing…';
    const payload={
      prompt: $('#promptInput').value.trim()||'Beautiful AI melody',
      genre: state.genre, bpm: +bpmR.value, duration: +durR.value,
      root: $('#rootSelect').value, scale: $('#scaleSelect').value,
      mood: { energy: eR.value/100, brightness: bR.value/100, complexity: cR.value/100 },
      instruments: { melody: $('#chkMelody').checked, chords: $('#chkChords').checked, bass: $('#chkBass').checked, drums: $('#chkDrums').checked },
      engine: state.engine,
      backend: state.backend,
    };
    let track=null;
    try{ const d=await api('/api/generate',{method:'POST', body: payload}); track=d.track; if(track.fallbackReason) toast('Neural fallback: '+track.fallbackReason.slice(0,120)); }
    catch(e){ console.warn('Falling back to local generator', e); if(state.engine==='neural') toast('Neural failed, using fast engine'); track=window.AuralisPlayer.localGenerate(payload); }
    state.tracks.unshift(track);
    try{ const ls=JSON.parse(localStorage.getItem('auralis_tracks')||'[]'); ls.unshift(track); localStorage.setItem('auralis_tracks', JSON.stringify(ls.slice(0,50))); }catch{}
    renderAll(); playTrack(track);
    btn.classList.remove('loading'); btn.textContent='✨ Generate music';
    toast(track.engine==='musicgen' ? 'Neural song ready! 🧠🎵' : 'Your song is ready! 🎵');
  };
  $('#shuffleBtn').onclick=()=>{
    const insp=['Epic battle theme','Dreamy lullaby','Funky disco night','Calm forest morning','Space adventure','Paris café morning'];
    $('#promptInput').value=insp[Math.floor(Math.random()*insp.length)];
    const g=GENRES_FALLBACK[Math.floor(Math.random()*GENRES_FALLBACK.length)]; state.genre=g; renderGenres(GENRES_FALLBACK);
    bpmR.value=70+Math.floor(Math.random()*60); durR.value=20+Math.floor(Math.random()*40/2)*2; eR.value=20+Math.floor(Math.random()*60); bR.value=20+Math.floor(Math.random()*60); cR.value=30+Math.floor(Math.random()*50); syncLabels();
    toast('Randomized — hit Generate!');
  };
  $('#promptChips').addEventListener('click',e=>{ const b=e.target.closest('.chip'); if(b){ $('#promptInput').value=b.textContent; $('#promptInput').focus(); } });
  $('#surpriseBtn').onclick=()=>$('#shuffleBtn').click();

  $('#topSearch').addEventListener('input',e=>{ state.query=e.target.value; if(state.view!=='library'){ switchView('library'); } $('#libSearch').value=e.target.value; loadLibrary(); });
  $('#libSearch').addEventListener('input',loadLibrary);
  $('#libGenre').addEventListener('change',loadLibrary);
  $('#libSort').addEventListener('change',loadLibrary);
  $('#clearMine').onclick=async ()=>{ if(!confirm('Clear my tracks?')) return; try{ await api('/api/tracks/clear-mine',{method:'POST'});}catch{} await loadTracks(); toast('Cleared'); };
  $('#playTrending').onclick=()=>{ if(state.tracks.length) playTrack(state.tracks[0]); else toast('No tracks yet'); };

  async function loadStats(){
    let s={totalTracks:state.tracks.length, totalPlays:state.tracks.reduce((a,t)=>a+(t.plays||0),0), totalLikes:state.tracks.reduce((a,t)=>a+(t.likes||0),0), mine:state.tracks.filter(t=>t.author===(state.user?.displayName||'Guest')).length, genresCount:new Set(state.tracks.map(t=>t.genre)).size, artistCount:new Set(state.tracks.map(t=>t.author)).size};
    try{ const d=await api('/api/stats'); s={...s, ...d}; }catch{}
    $('#stTracks').textContent=s.totalTracks; $('#stPlays').textContent=s.totalPlays; $('#stLikes').textContent=s.totalLikes; $('#stMine').textContent=s.mine; $('#stGenres').textContent=s.genresCount; $('#stArtists').textContent=s.artistCount;
  }

  const canvas=$('#visualizer'), ctx=canvas.getContext('2d');
  let bars=new Array(64).fill(0);
  let vizActive=false, vizLast=0;
  function drawViz(){
    const analyser=window.AuralisPlayer.getAnalyser();
    ctx.clearRect(0,0,canvas.width,canvas.height);
    const grad=ctx.createLinearGradient(0,0,canvas.width,0); grad.addColorStop(0,'#7c3aed'); grad.addColorStop(1,'#ec4899');
    ctx.fillStyle=grad;
    if(analyser){
      const data=new Uint8Array(analyser.frequencyBinCount); analyser.getByteFrequencyData(data);
      for(let i=0;i<64;i++){ const v=data[i]/255; bars[i]=bars[i]*0.7+v*0.3; }
    } else { bars=bars.map((v,i)=> v*0.9 + (0.15+0.1*Math.sin(Date.now()/600+i))*0.1); }
    const w=canvas.width/64;
    bars.forEach((v,i)=>{ const h=Math.max(4, v*canvas.height); ctx.beginPath(); ctx.roundRect(i*w+1, (canvas.height-h)/2, w-3, h, 4); ctx.fill(); });
  }
  function startViz(){
    if(vizActive) return; vizActive=true; vizLast=0;
    const loop=()=>{
      const now=performance.now();
      if(now - vizLast > 33){ vizLast=now; drawViz(); }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  function stopViz(){ vizActive=false; }
  window.AuralisViz={start,startViz,stop:stopViz};
  startViz();

  document.addEventListener('keydown',e=>{
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||$('#authModal').classList.contains('show')) return;
    if(e.code==='Space'){ e.preventDefault(); $('#playBtn').click(); }
  });

  renderGenres(GENRES_FALLBACK);
  renderAuth();
  initFirebase();
  (async ()=>{
    const [gRes, tRes, nRes, sRes] = await Promise.allSettled([
      api('/api/genres').catch(()=>null),
      api('/api/tracks').catch(()=>null),
      api('/api/neural/status').catch(()=>null),
      api('/api/stats').catch(()=>null),
    ]);
    if(gRes.status==='fulfilled' && gRes.value){ renderGenres(gRes.value.genres); }
    if(tRes.status==='fulfilled'){ state.tracks=tRes.value.tracks; renderAll(); }
    if(nRes.status==='fulfilled'){ $('#neuralState').textContent = nRes.value.enabledByEnv ? 'Neural ON' : 'Fast'; $('#neuralBadge').title = nRes.value.hint; }
    if(sRes.status==='fulfilled'){ await loadStats(); }
    if(state.token){ try{ const d=await api('/api/auth/me'); state.user=d.user; renderAuth(); }catch{ state.token=null; localStorage.removeItem('auralis_token'); renderAuth(); } }
    if(!state.tracks.length){
      try{ const ls=JSON.parse(localStorage.getItem('auralis_tracks')||'[]'); if(ls.length){ state.tracks=ls; renderAll(); } }catch{}
    }
  })();
})();
