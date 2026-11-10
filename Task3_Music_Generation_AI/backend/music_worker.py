#!/usr/bin/env python3
"""
Auralis Neural Music Worker — MusicGen (facebook/musicgen-small/large)
Reads a JSON input file, generates audio, writes WAV.
Usage: python music_worker.py <input.json>

Input JSON: { "prompt": "...", "output_path": "...wav", "duration": 10, "guidance": 3.0, "model": "facebook/musicgen-small" }

Requires: pip install -r backend/requirements.txt
CPU works but slow. Use MPS/GPU if available.
"""
import sys, json, os, traceback

def main():
    if len(sys.argv) < 2:
        print("Usage: python music_worker.py <input.json>", file=sys.stderr); sys.exit(2)
    input_path = sys.argv[1]
    with open(input_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    prompt = str(cfg.get("prompt", "Beautiful melody"))[:500]
    out_path = cfg.get("output_path", "out.wav")
    duration = float(cfg.get("duration", 10))
    guidance = float(cfg.get("guidance", 3.0))
    model_id = cfg.get("model", os.environ.get("MUSICGEN_MODEL", "facebook/musicgen-small"))

    # duration -> max_new_tokens approx: MusicGen supports musicgen-melody etc; we generate then trim.
    # Using transformers MusicGenPipeline text-to-music
    try:
        from transformers import MusicGenPipeline
        import numpy as np, scipy.io.wavfile as wav, torch
    except Exception as e:
        print(f"Missing deps. Run: pip install -r backend/requirements.txt\nImport error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # GPU-first: CUDA > MPS > CPU. Use fp16 on GPU for ~2x speed.
    device = "cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
    dtype = torch.float32 if device == "cpu" else torch.float16
    accel = os.environ.get("NEURAL_DEVICE", "auto")  # override if needed
    if accel in ("cuda", "cpu", "mps") and device != accel:
        print(f"[neural] NEURAL_DEVICE={accel} overrides auto-detected {device}")

    print(f"[neural] Loading {model_id} on {device} (fp{'16' if device!='cpu' else '32'})...", flush=True)
    try:
        pipeline = MusicGenPipeline.from_pretrained(model_id, torch_dtype=dtype, device=device)
    except Exception as e:
        print(f"LOAD FAILED: {e}", file=sys.stderr)
        print("Hint: check internet / HuggingFace access. Try model facebook/musicgen-small first.", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    print(f"[neural] Generating '{prompt}' for {duration}s (guidance={guidance})...", flush=True)
    try:
        # Faster sampling: temperature/top_p tuned for music; on GPU this is ~8-15s/10s clip
        inputs = pipeline(
            prompt,
            return_tensors="pt",
            do_sample=True,
            guidance_scale=guidance,
            temperature=0.9,
            top_p=0.95,
        )
        # inputs can be dict or object depending on transformers version
        if isinstance(inputs, dict):
            audio = inputs["audio_values"][0].cpu()
            sr = inputs["sampling_rate"]
        else:
            audio = inputs.audio_values[0].cpu()
            sr = inputs.sampling_rate
    except Exception as e:
        print(f"GEN FAILED: {e}", file=sys.stderr)
        traceback.print_exc()
        # fallback: generate silence + pentatonic so user never gets empty error? No — fail clearly
        sys.exit(1)

    # audio shape: (channels, samples) -> numpy (samples, channels) int16
    if audio.ndim == 2:
        arr = np.transpose(audio.numpy(), (1, 0))  # samples, channels
    else:
        arr = audio.numpy()
    # trim/pad to duration
    target = int(sr * duration)
    if arr.shape[0] > target:
        arr = arr[:target]
    elif arr.shape[0] < target:
        pad = np.zeros((target - arr.shape[0], arr.shape[1] if arr.ndim == 2 else 1), dtype=arr.dtype)
        arr = np.concatenate([arr, pad], axis=0) if arr.ndim == 2 else np.concatenate([arr, np.zeros(target - len(arr))])

    # normalize to int16
    maxabs = np.max(np.abs(arr)) or 1.0
    arr = (arr / maxabs * 0.9 * 32767).astype(np.int16)
    if arr.ndim == 1:
        arr = arr[:, None]

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wav.write(out_path, sr, arr)
    print(f"[neural] Wrote {out_path} ({arr.shape[0]/sr:.1f}s @ {sr}Hz)", flush=True)
    # also print JSON receipt for node to parse
    print(json.dumps({"ok": True, "file": out_path, "duration": arr.shape[0]/sr, "sr": int(sr), "model": model_id}))

if __name__ == "__main__":
    main()
