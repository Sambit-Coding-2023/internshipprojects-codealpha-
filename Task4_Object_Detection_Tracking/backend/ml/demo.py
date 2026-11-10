"""Built-in demo clip generator.

The demo uses a *real* road photograph (the classic Ultralytics bus image,
which YOLOv8 demonstrably detects) and renders a short clip from it with a
slow simulated camera pan, a drawn stop line, a cycling traffic light and a
direction arrow. Every detection / tracking / speed / violation number is
still computed by the real ML engine on this footage - only the camera
motion is synthetic, and it is clearly labelled as such in the UI.

Recommended settings for the demo (config.DEMO_CONFIG):
  speed_limit_kmh = 50, pixels_per_meter = 0.5, light red 7s / green 7s
  (starts RED), stop line at y = 55%, allowed direction = downwards.
With these settings the bus crosses the stop line on RED (~3 s in) and is
travelling just over the limit, so red-light + overspeed fire for real.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import numpy as np

import config
from backend.ml.engine import light_is_red

SOURCE_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/bus.jpg"
ASSET_PATH = config.ASSET_DIR / "demo_bus.jpg"

W, H, FPS, SECONDS = 720, 960, 25, 10
FRAMES = FPS * SECONDS
CROP_Y_START, CROP_Y_END = 300, 0       # camera pan range (in resized image px)
STOP_LINE_Y = 0.55                        # normalised - matches DEMO_CONFIG
LIGHT_CYCLE = {"red_seconds": 7, "green_seconds": 7, "initial": "red"}


def ensure_asset() -> Path:
    """Download the real road photo once (needs internet on first run)."""
    if ASSET_PATH.exists() and cv2.imread(str(ASSET_PATH)) is not None:
        return ASSET_PATH
    try:
        urllib.request.urlretrieve(SOURCE_URL, str(ASSET_PATH))
    except Exception as exc:  # network etc.
        raise RuntimeError(
            "Demo clip needs a one-time download of a sample road photo, "
            "but the download failed (offline?). Please upload your own "
            f"traffic video instead. ({exc})"
        ) from exc
    if cv2.imread(str(ASSET_PATH)) is None:
        raise RuntimeError("Downloaded demo asset is not a readable image.")
    return ASSET_PATH


def build_demo_clip(out_path: Path) -> dict:
    """Render the demo clip. Returns info incl. the recommended config."""
    src = ensure_asset()
    img = cv2.imread(str(src))
    img = cv2.resize(img, (1080, 1440))  # 810x1080 -> 1080x1440

    writer = cv2.VideoWriter(str(out_path),
                             cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(FRAMES):
        frac = i / (FRAMES - 1)
        y0 = int(CROP_Y_START + (CROP_Y_END - CROP_Y_START) * frac)
        y0 = max(0, min(1440 - H, y0))
        frame = img[y0:y0 + H, 180:180 + W].copy()  # centre crop
        t = i / FPS
        red = light_is_red(t, LIGHT_CYCLE)

        # stop line
        ly = int(STOP_LINE_Y * H)
        cv2.line(frame, (int(0.08 * W), ly), (int(0.92 * W), ly),
                 (0, 220, 255), 4, cv2.LINE_AA)
        cv2.putText(frame, "STOP LINE", (int(W * 0.32), ly - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2, cv2.LINE_AA)

        # allowed direction (downwards - vehicles in the demo move down)
        ox, oy = int(0.08 * W), int(0.88 * H)
        cv2.arrowedLine(frame, (ox, oy), (ox, oy + 90), (0, 255, 150), 4,
                        cv2.LINE_AA, tipLength=0.35)
        cv2.putText(frame, "ALLOWED", (ox - 5, oy + 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 150), 2, cv2.LINE_AA)

        # traffic light (state mirrors the analysis clock)
        lx, ly2 = W - 60, 70
        cv2.rectangle(frame, (lx - 26, ly2 - 50), (lx + 26, ly2 + 50),
                      (15, 15, 15), -1, cv2.LINE_AA)
        cv2.circle(frame, (lx, ly2 - 28), 15,
                   (0, 0, 255) if red else (70, 70, 70), -1, cv2.LINE_AA)
        cv2.circle(frame, (lx, ly2 + 28), 15,
                   (0, 255, 0) if not red else (70, 70, 70), -1, cv2.LINE_AA)
        cv2.putText(frame, "RED" if red else "GREEN", (lx - 30, ly2 + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        # HUD
        cv2.rectangle(frame, (0, H - 44), (W, H), (0, 0, 0), -1)
        cv2.putText(frame,
                    f"DEMO CLIP  t={t:.1f}s  (real photo, simulated camera motion)",
                    (12, H - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
        writer.write(frame)
    writer.release()
    return {
        "file": out_path.name,
        "width": W, "height": H, "fps": FPS, "seconds": SECONDS,
        "note": ("Built-in demo: real road photo with simulated camera pan. "
                 "Detections are real YOLOv8 output on real photo content."),
        "recommended_config": config.DEMO_CONFIG,
    }
