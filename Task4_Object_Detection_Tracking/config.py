"""Central configuration for the Traffic Violation Detection & Tracking system."""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
EVIDENCE_DIR = BASE_DIR / "evidence"
ASSET_DIR = BASE_DIR / "assets"
DB_PATH = BASE_DIR / "instance" / "traffic.db"

for _d in (UPLOAD_DIR, OUTPUT_DIR, EVIDENCE_DIR, ASSET_DIR, DB_PATH.parent):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-in-production-32chars!")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ACCESS_TOKEN_EXPIRES = False  # tokens stay valid while the user is logged in

# ---------------------------------------------------------------------------
# ML / analysis defaults (all user-overridable in the UI)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "auto_mode": True,            # True = fully automatic (no zones needed)
    "ppm_mode": "auto",           # "auto" (from vehicle sizes) | "manual"
    "speed_limit_kmh": 50,
    "pixels_per_meter": 1.0,
    "conf": 0.4,
    "violations": {
        "overspeed": True,
        "red_light": True,
        "wrong_way": True,
        "helmet": True,
    },
    # normalised 0..1 coordinates, None = disabled
    "stop_line": None,          # {"x1":..,"y1":..,"x2":..,"y2":..}
    "allowed_direction": None,   # {"dx":..,"dy":..}
    "light_cycle": None,         # {"red_seconds":..,"green_seconds":..,"initial":"red"|"green"}
}

# Preset tuned for the built-in demo clip (see backend/ml/demo.py)
DEMO_CONFIG = {
    **DEFAULT_CONFIG,
    "auto_mode": False,
    "ppm_mode": "manual",
    "speed_limit_kmh": 50,
    "pixels_per_meter": 0.5,
    "conf": 0.35,
    "stop_line": {"x1": 0.08, "y1": 0.55, "x2": 0.92, "y2": 0.55},
    "allowed_direction": {"dx": 0.0, "dy": 1.0},
    "light_cycle": {"red_seconds": 7, "green_seconds": 7, "initial": "red"},
}

# COCO classes we care about (YOLOv8)
# 0 person, 1 bicycle, 2 car, 3 motorcycle, 5 bus, 7 truck, 9 traffic light
DETECT_CLASSES = [0, 1, 2, 3, 5, 7, 9]
CLASS_NAMES = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus",
               7: "truck", 9: "traffic light"}

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "200"))
MAX_VIDEO_BYTES = MAX_VIDEO_MB * 1024 * 1024
