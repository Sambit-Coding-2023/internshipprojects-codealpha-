"""End-to-end smoke test: demo clip -> engine -> report.

Usage:  python scripts/smoke_test.py
Needs internet the first run (downloads yolov8n.pt + the demo photo once).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from backend.ml.demo import build_demo_clip
from backend.ml.engine import TrafficAnalyzer


def main() -> int:
    demo_path = config.UPLOAD_DIR / "demo_clip.mp4"
    if not demo_path.exists():
        print("Building demo clip (one-time download of a real road photo)…")
        build_demo_clip(demo_path)
    out_path = config.OUTPUT_DIR / "smoke_annotated.mp4"
    evidence_dir = config.EVIDENCE_DIR / "smoke"

    print(f"Analysing {demo_path} with DEMO_CONFIG…")
    result = TrafficAnalyzer(config.DEMO_CONFIG).analyze(
        demo_path, out_path, evidence_dir,
        on_progress=lambda p: print(f"  progress {p}%", end="\r"),
    )
    print()
    print(f"vehicles tracked : {result['total_vehicles']}")
    print(f"violating vehicles: {result['total_violating_vehicles']} "
          f"{result['violating_vehicles_by_type']} "
          f"(compliant: {result['compliant_vehicles']})")
    print(f"violation events : {result['total_violations']} {result['violation_counts']}")
    for v in result["violations"]:
        print(f"  - {v['type']:10s} track #{v['track_id']} {v['vehicle']} "
              f"@ {v['timestamp_s']}s  {v['speed_kmh']} km/h  ({v['detail']})")
    print(f"annotated video  : {out_path}  ({out_path.stat().st_size // 1024} KB)")
    if result["total_vehicles"] == 0:
        print("WARNING: no vehicles detected - is yolov8n.pt cached / network available?")
        return 1
    if result["total_violations"] == 0:
        print("NOTE: vehicles detected but no violations - check DEMO_CONFIG calibration.")
    print("SMOKE TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
