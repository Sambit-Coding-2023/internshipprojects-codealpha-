"""Core ML engine: YOLOv8 detection + ByteTrack tracking + violation logic.

Pipeline (per uploaded video):
  1. YOLOv8 (COCO) detects vehicles / persons / motorcycles / buses / trucks.
  2. ByteTrack (via Ultralytics ``model.track``) assigns stable track IDs.
  3. For every track we track centroid history and estimate speed in km/h
     from frame-to-frame pixel displacement + user calibration
     (pixels_per_meter, video fps).
  4. Four violation detectors run on top of the tracks:
       * overspeed   - smoothed speed above the user limit
       * red light   - track path crosses the drawn stop line while the
                       traffic-light clock (user red/green cycle) is RED
       * wrong way   - track movement is opposite to the allowed direction
       * helmet      - a rider (person overlapping a motorcycle) whose
                       head region shows no helmet-coloured dome
                       (colour heuristic - indicative, not certified, see README)
  5. An annotated video (boxes, IDs, speeds, violation badges, stop line,
     direction arrow, live traffic-light state) + per-violation evidence
     stills are written to disk.

All detection is genuinely performed by the model on the user's video;
nothing is simulated except where the user asks for the built-in demo clip.
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

import config

# ---------------------------------------------------------------------------
# model singleton (loading YOLO ~torch is slow, so load once per process)
# ---------------------------------------------------------------------------
_MODEL = None
_MODEL_LOCK = threading.Lock()


def get_model():
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            from ultralytics import YOLO

            _MODEL = YOLO("yolov8n.pt")  # COCO-pretrained, downloaded once
        return _MODEL


# ---------------------------------------------------------------------------
# pure helpers (unit-tested in tests/test_engine.py)
# ---------------------------------------------------------------------------
def segments_cross(p1, p2, p3, p4) -> bool:
    """True if segments p1-p2 and p3-p4 intersect (2D)."""
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(v) < 1e-9:
            return 0
        return 1 if v > 0 else 2

    def on_seg(a, b, c):  # b collinear with a-c; is b on segment a-c?
        return (min(a[0], c[0]) - 1e-9 <= b[0] <= max(a[0], c[0]) + 1e-9
                and min(a[1], c[1]) - 1e-9 <= b[1] <= max(a[1], c[1]) + 1e-9)

    o1, o2, o3, o4 = orient(p1, p2, p3), orient(p1, p2, p4), orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and on_seg(p1, p3, p2)) or (o2 == 0 and on_seg(p1, p4, p2))
            or (o3 == 0 and on_seg(p3, p1, p4)) or (o4 == 0 and on_seg(p3, p2, p4)))


def light_is_red(t_seconds: float, cycle: dict | None) -> bool:
    """Traffic-light clock.

    cycle = {"red_seconds": R, "green_seconds": G, "initial": "red"|"green"}.
    Returns True when the light is red at time t. Without a cycle the
    light is assumed permanently red (conservative: any stop-line crossing
    in a user-drawn zone is reported).
    """
    if not cycle:
        return True
    red = max(float(cycle.get("red_seconds", 10)), 1.0)
    green = max(float(cycle.get("green_seconds", 10)), 1.0)
    period = red + green
    t = max(float(t_seconds), 0.0) % period
    if cycle.get("initial", "red") == "green":
        t = (t + green) % period  # shift: cycle starts mid-way (green phase)
    return t < red


def estimate_speed_kmh(prev_c, curr_c, pixels_per_meter: float, fps: float) -> float:
    """Instantaneous centroid speed in km/h."""
    dx = curr_c[0] - prev_c[0]
    dy = curr_c[1] - prev_c[1]
    dist_px = math.hypot(dx, dy)
    return dist_px * pixels_per_meter * fps * 3.6


def helmet_present(head_bgr: np.ndarray) -> bool:
    """Helmet colour heuristic on a rider head crop.

    A helmet appears as a solid, fairly saturated coloured dome covering
    most of the top of the head region, whereas a bare head shows skin /
    hair (low saturation or high-frequency texture). We convert to HSV and
    check the fraction of strongly-saturated pixels in the upper 60% of
    the crop. This is an *indicative* signal, tuned to be conservative
    (when in doubt we say "no helmet" only if the crop is clearly bare).
    """
    if head_bgr is None or head_bgr.size == 0:
        return False
    h = head_bgr.shape[0]
    upper = head_bgr[: max(1, int(h * 0.6)), :]
    hsv = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    coloured = ((sat > 90) & (val > 60) & (val < 250)).mean()
    return bool(coloured > 0.18)


def estimate_light_state(frame_bgr: np.ndarray, box) -> str:
    """Read red/green from a detected traffic-light bbox (colour sampling).

    COCO's 'traffic light' class gives us the box; the active lamp glows
    with saturated red or green. We sample the central patch in HSV and
    compare red vs green pixel counts. Returns 'red' | 'green' | 'unknown'.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return "unknown"
    x1, y1, x2, y2 = (int(v) for v in box)
    h, w = frame_bgr.shape[:2]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, w), min(y2, h)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return "unknown"
    # central 60% patch (avoids housing borders)
    bw, bh = x2 - x1, y2 - y1
    patch = frame_bgr[y1 + int(bh * 0.2): y1 + int(bh * 0.8),
                      x1 + int(bw * 0.2): x1 + int(bw * 0.8)]
    if patch.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    bright = (sat > 110) & (val > 90)
    red = bright & ((hue < 10) | (hue > 170))
    green = bright & (hue >= 35) & (hue <= 95)
    r, g = int(red.sum()), int(green.sum())
    total = patch.shape[0] * patch.shape[1]
    if max(r, g) < max(12, int(0.02 * total)):
        return "unknown"
    return "red" if r > g else "green"


def bbox_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / max(area_a + area_b - inter, 1e-6)


# ---------------------------------------------------------------------------
# colours for annotation (BGR)
# ---------------------------------------------------------------------------
_CLASS_COLORS = {
    "car": (240, 150, 30), "bus": (60, 200, 80), "truck": (60, 200, 80),
    "motorcycle": (200, 120, 255), "bicycle": (120, 220, 220), "person": (255, 220, 120),
}
_VIOLATION_COLORS = {
    "overspeed": (0, 0, 255),
    "red_light": (0, 0, 255),
    "wrong_way": (0, 140, 255),
    "helmet": (0, 100, 255),
}
_VIOLATION_LABELS = {
    "overspeed": "OVERSPEED",
    "red_light": "RED LIGHT",
    "wrong_way": "WRONG WAY",
    "helmet": "NO HELMET",
}


class TrafficAnalyzer:
    """Analyses one video and returns a JSON-serialisable result dict."""

    def __init__(self, cfg: dict):
        self.cfg = {**config.DEFAULT_CONFIG, **cfg}
        self.cfg["violations"] = {
            **config.DEFAULT_CONFIG["violations"],
            **cfg.get("violations", {}),
        }
        self.violations: list[dict] = []
        self._violation_id = 0
        # unique violating vehicles (tracks) — one vehicle = one count,
        # no matter how many violation events it triggers
        self._violating_tracks: dict[str, set[int]] = defaultdict(set)

        # per-track state
        self._prev_centroid: dict[int, tuple[float, float]] = {}
        self._speed_smooth: dict[int, float] = {}
        self._last_seen: dict[int, int] = {}
        self._class_of_track: dict[int, str] = {}
        self._conf_of_track: dict[int, float] = {}
        # cooldowns so one continuous breach = one violation record
        self._cooldown: dict[tuple[int, str], int] = {}
        # per-track centroid path history (last ~30 points)
        self._path: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # -- internal -----------------------------------------------------------
    def _report(self, vtype: str, track_id: int, vehicle: str, t: float,
                frame_no: int, speed: float, detail: str,
                frame_bgr, evidence_dir: Path) -> None:
        self._violation_id += 1
        self._violating_tracks[vtype].add(int(track_id))
        ev_name = f"ev_{vtype}_{self._violation_id:03d}_t{int(t)}s_f{frame_no}.jpg"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(evidence_dir / ev_name), frame_bgr,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        self.violations.append({
            "id": self._violation_id,
            "type": vtype,
            "label": _VIOLATION_LABELS[vtype],
            "track_id": int(track_id),
            "vehicle": vehicle,
            "timestamp_s": round(float(t), 2),
            "frame": int(frame_no),
            "speed_kmh": round(float(speed), 1),
            "evidence": ev_name,
            "detail": detail,
        })

    def _ready(self, track_id: int, vtype: str, frame_no: int, cooldown_frames: int) -> bool:
        last = self._cooldown.get((track_id, vtype), -10**9)
        if frame_no - last < cooldown_frames:
            return False
        self._cooldown[(track_id, vtype)] = frame_no
        return True

    # -- main ---------------------------------------------------------------
    def analyze(self, video_path: Path, output_path: Path, evidence_dir: Path,
                on_progress: Callable[[int], None] | None = None) -> dict:
        model = get_model()
        cfg = self.cfg
        auto = bool(cfg.get("auto_mode", True))
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        stop = cfg.get("stop_line")
        stop_px = None
        if stop:
            stop_px = ((stop["x1"] * W, stop["y1"] * H), (stop["x2"] * W, stop["y2"] * H))
        allowed = cfg.get("allowed_direction")
        allowed_v = None
        if allowed:
            n = math.hypot(allowed.get("dx", 0), allowed.get("dy", 0)) or 1.0
            allowed_v = (allowed.get("dx", 0) / n, allowed.get("dy", 0) / n)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (W, H))

        results = model.track(
            source=str(video_path),
            tracker="bytetrack.yaml",
            classes=config.DETECT_CLASSES,
            conf=float(cfg.get("conf", 0.4)),
            persist=True,
            stream=True,
            verbose=False,
        )

        ppm = max(float(cfg.get("pixels_per_meter", 1.0)), 0.05)
        ppm_mode = cfg.get("ppm_mode", "auto" if auto else "manual")
        speed_limit = float(cfg.get("speed_limit_kmh", 50))
        v = cfg["violations"]

        # --- auto-mode state ------------------------------------------------
        width_samples: list[float] = []     # car widths (px) for auto ppm
        light_votes: list[str] = []         # recent raw light readings
        light_state_now = "unknown"         # smoothed current state
        auto_stop_y: float | None = None    # auto stop-line height (px)
        motion_samples: list[tuple[float, float]] = []  # unit movement dirs
        auto_allowed: tuple[float, float] | None = None
        headlight = None                    # last light bbox (for HUD)

        unique_tracks: set[int] = set()
        class_counts: defaultdict[str, int] = defaultdict(int)
        timeline: list[dict] = []
        frame_no = 0
        last_timeline_frame = -999

        for res in results:
            frame_no += 1
            frame = res.orig_img
            t = (frame_no - 1) / fps

            boxes = res.boxes
            dets = []  # (track_id, cls_name, conf, xyxy, centroid)
            if boxes is not None and len(boxes):
                ids = boxes.id
                cls_ids = boxes.cls.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                xyxy = boxes.xyxy.cpu().numpy()
                for i in range(len(boxes)):
                    if ids is None:
                        continue
                    tid = int(ids[i])
                    cname = config.CLASS_NAMES.get(int(cls_ids[i]), "vehicle")
                    box = tuple(float(x) for x in xyxy[i])
                    cx = (box[0] + box[2]) / 2.0
                    cy = (box[1] + box[3]) / 2.0
                    dets.append((tid, cname, float(confs[i]), box, (cx, cy)))

            # --- bookkeeping + speed -------------------------------------
            speeds: dict[int, float] = {}
            for tid, cname, conf, box, cent in dets:
                if cname == "traffic light":
                    continue  # lights are read separately, not vehicles
                # persons are tracked only for the helmet rule; they are not
                # vehicles, so they don't count towards vehicle totals
                # --- auto speed calibration from car widths ---
                if auto and ppm_mode != "manual" and cname == "car":
                    width_samples.append(box[2] - box[0])
                    if len(width_samples) > 400:
                        width_samples.pop(0)
                    if len(width_samples) >= 10:
                        median_w = float(np.median(width_samples))
                        if median_w > 10:
                            # average real car width ≈ 1.8 m -> px per metre
                            ppm = median_w / 1.8
                if cname != "person":
                    if tid not in self._class_of_track:
                        class_counts[cname] += 1
                    unique_tracks.add(tid)
                self._class_of_track[tid] = cname
                self._conf_of_track[tid] = conf
                unique_tracks.add(tid)
                prev = self._prev_centroid.get(tid)
                if prev is not None:
                    inst = estimate_speed_kmh(prev, cent, ppm, fps)
                    prev_s = self._speed_smooth.get(tid, inst)
                    smooth = 0.6 * prev_s + 0.4 * inst
                    self._speed_smooth[tid] = smooth
                    speeds[tid] = smooth
                self._prev_centroid[tid] = cent
                self._last_seen[tid] = frame_no

            # centroid path history for this frame (used by line-crossing +
            # wrong-way checks below, which compare the last two points)
            for tid, cname, conf, box, cent in dets:
                hist = self._path[tid]
                hist.append(cent)
                if len(hist) > 30:
                    hist.pop(0)

            # --- auto: traffic-light reading + flow direction ------------
            if auto:
                lights = [d for d in dets if d[1] == "traffic light"]
                if lights:
                    best = max(lights, key=lambda d: d[2])
                    headlight = best[3]
                    raw = estimate_light_state(frame, best[3])
                    light_votes.append(raw)
                    if len(light_votes) > 30:
                        light_votes.pop(0)
                    known = [x for x in light_votes if x in ("red", "green")]
                    if len(known) >= 5:
                        light_state_now = (
                            "red" if known.count("red") >= known.count("green") else "green"
                        )
                    # stop line just in front of the light (below its box)
                    auto_stop_y = min(H * 0.95, best[3][3] + H * 0.05)
                # dominant flow: unit movement vectors of all vehicles
                for tid, cname, conf, box, cent in dets:
                    if cname in ("person", "traffic light"):
                        continue
                    hist = self._path.get(tid, [])
                    if len(hist) >= 6:
                        dx, dy = cent[0] - hist[-6][0], cent[1] - hist[-6][1]
                        n = math.hypot(dx, dy)
                        if n > 10:
                            motion_samples.append((dx / n, dy / n))
                            if len(motion_samples) > 2000:
                                motion_samples.pop(0)
                if len(motion_samples) >= 40:
                    mx = sum(s[0] for s in motion_samples) / len(motion_samples)
                    my = sum(s[1] for s in motion_samples) / len(motion_samples)
                    mn = math.hypot(mx, my)
                    if mn > 0.15:
                        auto_allowed = (mx / mn, my / mn)

            # --- overspeed ------------------------------------------------
            if v.get("overspeed"):
                for tid, cname, conf, box, cent in dets:
                    if cname == "person":
                        continue
                    s = speeds.get(tid, 0.0)
                    if s > speed_limit and self._ready(tid, "overspeed", frame_no, int(fps * 4)):
                        self._report(
                            "overspeed", tid, cname, t, frame_no, s,
                            f"{cname} travelling at {s:.0f} km/h (limit {speed_limit:.0f})",
                            frame, evidence_dir)

            # effective stop line + red signal (manual clock vs auto light)
            eff_stop = stop_px
            eff_red = light_is_red(t, cfg.get("light_cycle"))
            if auto:
                if auto_stop_y is not None:
                    eff_stop = ((0.0, auto_stop_y), (float(W), auto_stop_y))
                    eff_red = (light_state_now == "red")
                else:
                    eff_stop = None  # no light seen yet -> rule stays off
                # manual line still wins if the user drew one
                if stop_px:
                    eff_stop = stop_px
                    eff_red = light_is_red(t, cfg.get("light_cycle"))

            # --- red light (stop-line crossing while red) -----------------
            if v.get("red_light") and eff_stop:
                red = eff_red
                for tid, cname, conf, box, cent in dets:
                    if cname == "person":
                        continue
                    # previous centroid = centroid 1 frame ago is not stored
                    # separately; approximate with the smoothed path endpoint
                    # by re-deriving from speed history: use prev centroid
                    # stored before this frame's update is gone, so we keep a
                    # tiny 2-point history per track.
                    hist = self._path.get(tid, [])
                    if len(hist) >= 2:
                        prev_c, curr_c = hist[-2], hist[-1]
                        if (segments_cross(prev_c, curr_c, eff_stop[0], eff_stop[1])
                                and red
                                and self._ready(tid, "red_light", frame_no, int(fps * 4))):
                            self._report(
                                "red_light", tid, cname, t, frame_no, speeds.get(tid, 0.0),
                                f"{cname} crossed the stop line on RED", frame, evidence_dir)
            # (path history updated below for every detection)

            # --- wrong way (manual arrow wins; else auto dominant flow) ---
            eff_allowed = allowed_v if allowed_v else (auto_allowed if auto else None)
            if v.get("wrong_way") and eff_allowed:
                for tid, cname, conf, box, cent in dets:
                    if cname == "person":
                        continue
                    hist = self._path.get(tid, [])
                    if len(hist) >= 6:
                        p_old = hist[-6]
                        dx, dy = cent[0] - p_old[0], cent[1] - p_old[1]
                        move_len = math.hypot(dx, dy)
                        s = speeds.get(tid, 0.0)
                        if move_len > 8 and s > 8:
                            dot = (dx / move_len) * eff_allowed[0] + (dy / move_len) * eff_allowed[1]
                            if dot < -0.35 and self._ready(tid, "wrong_way", frame_no, int(fps * 6)):
                                self._report(
                                    "wrong_way", tid, cname, t, frame_no, s,
                                    f"{cname} moving opposite to the allowed direction",
                                    frame, evidence_dir)

            # --- helmet (rider without helmet on a motorcycle) ------------
            if v.get("helmet"):
                persons = [d for d in dets if d[1] == "person"]
                bikes = [d for d in dets if d[1] == "motorcycle"]
                for btid, _, bconf, bbox, bcent in bikes:
                    for ptid, _, pconf, pbox, pcent in persons:
                        if bbox_iou(bbox, pbox) < 0.03:
                            # allow "person above bike" overlap as well
                            px1, py1, px2, py2 = pbox
                            cx_inside = bbox[0] - 10 <= pcent[0] <= bbox[2] + 10
                            cy_above = pcent[1] <= bbox[3] + 5
                            if not (cx_inside and cy_above):
                                continue
                        px1, py1, px2, py2 = (int(x) for x in pbox)
                        px1, py1 = max(px1, 0), max(py1, 0)
                        px2, py2 = max(px2, px1 + 4), max(py2, py1 + 4)
                        head = frame[py1:py1 + max(4, int((py2 - py1) * 0.35)), px1:px2]
                        if head.size and helmet_present(head):
                            continue  # helmet detected -> compliant
                        if self._ready(btid, "helmet", frame_no, int(fps * 4)):
                            self._report(
                                "helmet", btid, "motorcycle", t, frame_no, speeds.get(btid, 0.0),
                                "Rider on motorcycle without a detectable helmet",
                                frame, evidence_dir)
                        break  # one rider per bike is enough

            # --- annotation ------------------------------------------------
            frame = self._annotate(frame, dets, speeds, eff_stop, eff_allowed,
                                   (None if auto else cfg.get("light_cycle")),
                                   t, frame_no, fps,
                                   light_state=(light_state_now if auto else None))
            writer.write(frame)

            # --- timeline sampling (for charts: every ~0.5 s) -------------
            if frame_no - last_timeline_frame >= max(1, int(fps / 2)):
                last_timeline_frame = frame_no
                timeline.append({
                    "t": round(t, 2),
                    "visible": len(dets),
                    "cumulative_vehicles": len(unique_tracks),
                    "cumulative_violations": len(self.violations),
                })

            if on_progress and total_frames:
                on_progress(min(99, int(frame_no / total_frames * 100)))

        writer.release()
        if on_progress:
            on_progress(100)

        violation_counts = defaultdict(int)
        for vl in self.violations:
            violation_counts[vl["type"]] += 1

        all_violating = set().union(*self._violating_tracks.values()) if self._violating_tracks else set()
        total_vehicles = len(unique_tracks)
        return {
            "fps": round(fps, 2),
            "width": W,
            "height": H,
            "total_frames": frame_no,
            "duration_s": round(frame_no / fps, 2) if fps else 0,
            "total_vehicles": total_vehicles,
            "vehicle_counts": dict(class_counts),
            # headline metric: how many distinct vehicles broke any rule
            "total_violating_vehicles": len(all_violating),
            "violating_vehicles_by_type": {
                k: len(v) for k, v in self._violating_tracks.items()
            },
            "compliant_vehicles": max(0, total_vehicles - len(all_violating)),
            "total_violations": len(self.violations),
            "violation_counts": dict(violation_counts),
            "violations": self.violations,
            "timeline": timeline,
            "annotated_video": output_path.name,
        }

    # -- drawing --------------------------------------------------------------
    def _annotate(self, frame, dets, speeds, stop_px, allowed_v, cycle, t,
                  frame_no, fps, light_state=None):
        H, W = frame.shape[:2]
        active_violations = {
            vl["track_id"] for vl in self.violations
            if abs(vl["frame"] - frame_no) <= int(fps * 2)
        }

        # stop line
        if stop_px:
            cv2.line(frame, tuple(map(int, stop_px[0])), tuple(map(int, stop_px[1])),
                     (0, 220, 255), 3, cv2.LINE_AA)
            mx, my = int((stop_px[0][0] + stop_px[1][0]) / 2), int((stop_px[0][1] + stop_px[1][1]) / 2)
            cv2.putText(frame, "STOP LINE", (mx - 45, max(my - 10, 18)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)

        # allowed direction arrow
        if allowed_v:
            ox, oy = int(W * 0.08), int(H * 0.88)
            ex, ey = ox + int(allowed_v[0] * 90), oy + int(allowed_v[1] * 90)
            cv2.arrowedLine(frame, (ox, oy), (ex, ey), (0, 255, 150), 3,
                            cv2.LINE_AA, tipLength=0.35)
            cv2.putText(frame, "ALLOWED", (ox - 5, oy + 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 150), 2, cv2.LINE_AA)

        for tid, cname, conf, box, cent in dets:
            x1, y1, x2, y2 = map(int, box)
            bad = tid in active_violations
            color = (0, 0, 255) if bad else _CLASS_COLORS.get(cname, (200, 200, 200))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            s = speeds.get(tid, 0.0)
            label = f"#{tid} {cname} {conf:.2f} {s:.0f}km/h"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, max(y1 - th - 10, 0)), (x1 + tw + 8, y1), color, -1)
            cv2.putText(frame, label, (x1 + 4, max(y1 - 5, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 2, cv2.LINE_AA)

        # violation badges (recent)
        recent = [vl for vl in self.violations if frame_no - vl["frame"] <= int(fps * 2)]
        y0 = 28
        for vl in recent:
            txt = f"{vl['label']} #{vl['track_id']} {vl['vehicle']} @ {vl['timestamp_s']:.0f}s"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (10, y0 - th - 6), (10 + tw + 12, y0 + 4),
                          (0, 0, 255), -1)
            cv2.putText(frame, txt, (16, y0), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (255, 255, 255), 2, cv2.LINE_AA)
            y0 += th + 10

        # HUD: time + traffic light state (auto-detected or clock)
        if light_state is not None:
            red = (light_state == "red")
            known = light_state in ("red", "green")
        else:
            red = light_is_red(t, cycle)
            known = bool(cycle)
        hud = f"t={t:.1f}s  frame={frame_no}"
        cv2.putText(frame, hud, (W - 260, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2, cv2.LINE_AA)
        lx, ly = W - 70, 60
        cv2.rectangle(frame, (lx - 18, ly - 34), (lx + 18, ly + 34), (20, 20, 20), -1)
        cv2.circle(frame, (lx, ly - 20), 10, (60, 60, 60) if red else (0, 255, 0), -1, cv2.LINE_AA)
        cv2.circle(frame, (lx, ly + 20), 10, (0, 0, 255) if red else (60, 60, 60), -1, cv2.LINE_AA)
        if known:
            cv2.putText(frame, "RED" if red else "GREEN", (lx - 34, ly + 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
        elif light_state == "unknown":
            cv2.putText(frame, "LIGHT ?", (lx - 42, ly + 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2, cv2.LINE_AA)
        return frame
