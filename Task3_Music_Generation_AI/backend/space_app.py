#!/usr/bin/env python3
"""
Auralis HF Space App — deploy to HuggingFace Spaces (free T4 GPU).
Exposes Gradio API: prompt, duration, guidance -> wav file.

Deploy:
  1. Create Space at https://huggingface.co/new-space (SDK: Gradio)
  2. Upload this file as app.py
  3. Set requirements (auto from requirements.txt below)
  4. Copy the Space URL -> in Auralis: set HF_SPACES_URL=https://<username>-<space>.hf.space
  5. Restart Auralis with: npm run start:neural:cloud

Local test: python backend/space_app.py  (needs torch, transformers, gradio)
"""
import os, tempfile
import gradio as gr

MODEL_ID = os.environ.get("MUSICGEN_MODEL", "facebook/musicgen-small")
_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    from transformers import MusicGenPipeline
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"[space] Loading {MODEL_ID} on {device}...")
    _pipeline = MusicGenPipeline.from_pretrained(MODEL_ID, torch_dtype=dtype, device=device)
    return _pipeline

def generate(prompt: str, duration: float, guidance: float):
    if not prompt or not prompt.strip():
        raise gr.Error("Prompt is empty.")
    duration = max(5.0, min(30.0, float(duration or 10)))
    guidance = float(guidance or 3.0)
    pipeline = get_pipeline()
    import numpy as np, scipy.io.wavfile as wav
    inputs = pipeline(str(prompt)[:500], return_tensors="pt", do_sample=True, guidance_scale=guidance)
    if isinstance(inputs, dict):
        audio, sr = inputs["audio_values"][0].cpu(), inputs["sampling_rate"]
    else:
        audio, sr = inputs.audio_values[0].cpu(), inputs.sampling_rate
    arr = np.transpose(audio.numpy(), (1, 0)) if audio.ndim == 2 else audio.numpy()
    target = int(sr * duration)
    if len(arr) > target:
        arr = arr[:target]
    maxabs = np.max(np.abs(arr)) or 1.0
    arr = (arr / maxabs * 0.9 * 32767).astype(np.int16)
    if arr.ndim == 1:
        arr = arr[:, None]
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    wav.write(out, int(sr), arr)
    return out

with gr.Blocks(title="Auralis MusicGen") as demo:
    gr.Markdown("## 🎧 Auralis MusicGen — internal neural backend\nPrompt → MusicGen audio (T4 GPU). Set `HF_SPACES_URL` in Auralis to use this Space.")
    with gr.Row():
        prompt = gr.Textbox(label="Prompt", placeholder="Piano lullaby, soft and dreamy", lines=2)
        duration = gr.Slider(5, 30, value=10, step=1, label="Duration (sec)")
        guidance = gr.Slider(1, 10, value=3.0, step=0.5, label="Guidance")
    btn = gr.Button("Generate", variant="primary")
    out = gr.Audio(label="Generated WAV", type="filepath")
    btn.click(fn=generate, inputs=[prompt, duration, guidance], outputs=out)

if __name__ == "__main__":
    demo.launch()
