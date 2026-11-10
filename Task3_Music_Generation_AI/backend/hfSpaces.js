// Auralis HF Spaces / HF Inference client for MusicGen
// Backends (in priority):
//  1. HF_SPACES_URL — your Gradio Space (e.g. https://your-space.hf.space) using Gradio API
//  2. HF_TOKEN + MUSICGEN_MODEL — HuggingFace Inference API (serverless, CUDA hosted by HF)
//
// Local GPU remains primary via neuralClient.js (music_worker.py). This file lets you offload
// to free tier GPU on HF Spaces (T4) — ~8-15s per 10s clip vs 40-60s CPU.
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.join(__dirname, '..', 'public', 'generated');
function ensureOut(){ if(!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR,{recursive:true}); }

function getHFConfig(){
  return {
    spacesUrl: process.env.HF_SPACES_URL || null,
    tokenConfigured: !!(process.env.HF_TOKEN || process.env.HUGGINGFACE_TOKEN),
    model: process.env.MUSICGEN_MODEL || 'facebook/musicgen-small',
    backendPreference: process.env.NEURAL_BACKEND || 'local',
    hint: process.env.HF_SPACES_URL
      ? 'HF Spaces configured — generation will try cloud GPU first.'
      : 'To use free GPU: deploy backend/space_app.py to HF Spaces, set HF_SPACES_URL=https://<your-space>.hf.space',
  };
}

/**
 * Generate via HF Inference API (router).
 * POST https://router.huggingface.co/hf-inference/models/{model}
 * Returns WAV buffer.
 */
async function generateViaHFAPI({ prompt, duration = 10 }){
  const token = process.env.HF_TOKEN || process.env.HUGGINGFACE_TOKEN;
  if(!token) return { ok:false, reason:'HF_TOKEN missing' };
  const model = process.env.MUSICGEN_MODEL || 'facebook/musicgen-small';
  const url = `https://router.huggingface.co/hf-inference/models/${encodeURIComponent(model)}`;
  try{
    const res = await fetch(url, {
      method:'POST',
      headers:{ 'Content-Type':'application/json', 'Authorization':`Bearer ${token}`, 'x-use-cache':'false' },
      body: JSON.stringify({ inputs: String(prompt||'Beautiful melody').slice(0,500), parameters:{ guidance_scale: 3.0 } }),
    });
    if(!res.ok){
      const txt = await res.text();
      return { ok:false, reason:`HF Inference API ${res.status}: ${txt.slice(0,600)}` };
    }
    const buf = Buffer.from(await res.arrayBuffer());
    if(buf.length < 1000) return { ok:false, reason:'HF Inference returned tiny payload' };
    ensureOut();
    const id = 'hfapi_' + Date.now().toString(36) + Math.random().toString(36).slice(2,5);
    const outFile = path.join(OUT_DIR, id + '.wav');
    fs.writeFileSync(outFile, buf);
    return { ok:true, file:outFile, url:`/generated/${path.basename(outFile)}`, duration, model, size:buf.length };
  }catch(e){ return { ok:false, reason:'HF API fetch failed: '+e.message }; }
}

/**
 * Generate via Gradio Space (backend/space_app.py deploys a Gradio app with same prompt->wav API).
 * Gradio 4 queue API:
 *   POST {SPACE}/queue/join  -> {event_id}
 *   GET  {SPACE}/queue/data?session_hash=...&event_id=...
 */
async function generateViaSpaces({ prompt, duration = 10, guidance = 3.0 }){
  const space = (process.env.HF_SPACES_URL || '').replace(/\/+$/,'');
  if(!space) return { ok:false, reason:'HF_SPACES_URL missing' };
  const session = 'auralis_' + Math.random().toString(36).slice(2,10);
  try{
    const join = await fetch(`${space}/gradio_api/queue/join`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ data:[ String(prompt||'Beautiful melody').slice(0,500), Number(duration)||10, Number(guidance)||3.0 ], fn_index:0 }),
    });
    if(!join.ok) return { ok:false, reason:`Spaces join ${join.status}: ${(await join.text()).slice(0,400)}` };
    const { event_id } = await join.json().catch(()=>({}));
    if(!event_id) return { ok:false, reason:'Spaces no event_id' };

    // poll for completion (up to 180s)
    const start = Date.now();
    while(Date.now()-start < 180000){
      await new Promise(r=>setTimeout(r,1500));
      const res = await fetch(`${space}/gradio_api/queue/data?session_hash=${session}&event_id=${event_id}`);
      if(!res.ok) continue;
      const text = await res.text();
      // Gradio streams SSE-ish; look for audio url / path
      if(text.includes('complete')){
        const m = text.match(/\/file=\/tmp\/[^"']+\.wav|https?:[^"']+\.wav|\/gradio_api\/file=[^"']+/);
        // Gradio 4 returns JSON with "data":[{"path":..., "url":...}]
        try{
          const j = JSON.parse(text.split('\n').find(l=>l.startsWith('data:')||l.startsWith('{'))?.replace(/^data:\s*/,'') || '{}');
          const url = j?.data?.[0]?.url || j?.data?.[0]?.path || null;
          if(url){
            const full = url.startsWith('http') ? url : `${space}${url.startsWith('/')?'':'/'}${url}`;
            return { ok:true, remoteUrl: full, duration, model:'space-musicgen' };
          }
        }catch{}
        if(m) return { ok:true, remoteUrl: m[0].startsWith('http')? m[0] : `${space}${m[0]}`, duration, model:'space-musicgen' };
        return { ok:false, reason:'Spaces complete but no audio Url in response: '+text.slice(0,600) };
      }
    }
    return { ok:false, reason:'Spaces timeout after 180s' };
  }catch(e){ return { ok:false, reason:'Spaces call failed: '+e.message }; }
}

/**
 * Download remote WAV -> local /generated and return local Url so frontend <audio> works without CORS.
 */
async function downloadRemoteToLocal(url){
  ensureOut();
  const res = await fetch(url);
  if(!res.ok) return { ok:false, reason:`Download ${res.status}` };
  const buf = Buffer.from(await res.arrayBuffer());
  const id = 'spaces_' + Date.now().toString(36) + Math.random().toString(36).slice(2,5);
  const outFile = path.join(OUT_DIR, id + '.wav');
  fs.writeFileSync(outFile, buf);
  return { ok:true, file:outFile, url:`/generated/${path.basename(outFile)}`, size:buf.length };
}

async function generateCloud({ prompt, duration = 10 }){
  const cfg = getHFConfig();
  // try spaces first if configured
  if(cfg.spacesUrl){
    const r = await generateViaSpaces({ prompt, duration });
    if(r.ok && r.remoteUrl){
      const d = await downloadRemoteToLocal(r.remoteUrl);
      if(d.ok) return { ...d, via:'hf-spaces', duration };
      return { ok:false, reason:'Failed to download Spaces audio: '+d.reason };
    }
    // fallback to HF API if spaces fails and token exists
    if(cfg.tokenConfigured){
      const f = await generateViaHFAPI({ prompt, duration });
      if(f.ok) return { ...f, via:'hf-api' };
    }
    return { ok:false, reason:r.reason || 'Spaces failed' };
  }
  if(cfg.tokenConfigured){
    const f = await generateViaHFAPI({ prompt, duration });
    if(f.ok) return { ...f, via:'hf-api' };
    return f;
  }
  return { ok:false, reason:'No cloud backend configured (set HF_SPACES_URL or HF_TOKEN)' };
}

module.exports = { getHFConfig, generateViaHFAPI, generateViaSpaces, generateCloud, downloadRemoteToLocal };
