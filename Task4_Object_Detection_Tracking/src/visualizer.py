"""
Visualization and Real-Time HUD Overlay Module for Object Detection and Tracking
Draws bounding boxes, persistent ID tags, speed & heading vectors, motion trails,
virtual tripwire counting lines, ROI monitoring zones, and density heatmaps.
"""

import colorsys
import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


class Visualizer:
    def __init__(self):
        self.color_cache: Dict[int, Tuple[int, int, int]] = {}
        # Heatmap accumulator: 2D float array
        self.heatmap_accum: Optional[np.ndarray] = None
        self.heatmap_decay: float = 0.985

    def get_track_color(self, track_id: int) -> Tuple[int, int, int]:
        """Generates a consistent, distinct vibrant BGR color for any integer track ID."""
        if track_id not in self.color_cache:
            golden_ratio = 0.618033988749895
            hue = (track_id * golden_ratio) % 1.0
            saturation = 0.90
            value = 0.95
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            self.color_cache[track_id] = (int(b * 255), int(g * 255), int(r * 255))
        return self.color_cache[track_id]

    def draw_corner_box(
        self,
        img: np.ndarray,
        box: List[float],
        color: Tuple[int, int, int],
        in_zone: bool = False,
        thickness: int = 2,
        corner_len: int = 16
    ):
        """Draws a clean bounding box with emphasized modern tech corners."""
        x1, y1, x2, y2 = [int(v) for v in box]

        # Use amber/red warning color if object is inside monitoring zone
        box_color = (0, 140, 255) if in_zone else color

        # Semi-transparent box background fill
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), box_color, -1)
        cv2.addWeighted(overlay, 0.10 if in_zone else 0.07, img, 0.90 if in_zone else 0.93, 0, img)

        # Thin border
        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 1)

        # Emphasized corners
        cl = min(corner_len, (x2 - x1) // 3, (y2 - y1) // 3)
        th = thickness + (1 if in_zone else 0)

        # Top-left
        cv2.line(img, (x1, y1), (x1 + cl, y1), box_color, th + 1)
        cv2.line(img, (x1, y1), (x1, y1 + cl), box_color, th + 1)
        # Top-right
        cv2.line(img, (x2, y1), (x2 - cl, y1), box_color, th + 1)
        cv2.line(img, (x2, y1), (x2, y1 + cl), box_color, th + 1)
        # Bottom-left
        cv2.line(img, (x1, y2), (x1 + cl, y2), box_color, th + 1)
        cv2.line(img, (x1, y2), (x1, y2 - cl), box_color, th + 1)
        # Bottom-right
        cv2.line(img, (x2, y2), (x2 - cl, y2), box_color, th + 1)
        cv2.line(img, (x2, y2), (x2, y2 - cl), box_color, th + 1)

    def draw_track_label(
        self,
        img: np.ndarray,
        box: List[float],
        track_id: int,
        class_name: str,
        confidence: float,
        speed_kmh: float,
        direction: str,
        color: Tuple[int, int, int],
        in_zone: bool = False,
        show_speed: bool = True
    ):
        """Draws an aesthetic label pill above the tracked bounding box."""
        x1, y1, x2, y2 = [int(v) for v in box]

        zone_badge = " [ZONE]" if in_zone else ""
        if show_speed and speed_kmh > 0.5:
            label = f"#{track_id} {class_name.upper()} {int(confidence * 100)}% | {speed_kmh:.0f}km/h {direction}{zone_badge}"
        else:
            label = f"#{track_id} {class_name.upper()} {int(confidence * 100)}%{zone_badge}"

        pill_color = (0, 140, 255) if in_zone else color

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.42
        font_thickness = 1

        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
        pill_y1 = max(0, y1 - text_h - 10)
        pill_y2 = y1
        pill_x2 = min(img.shape[1], x1 + text_w + 14)

        # Draw label background pill
        cv2.rectangle(img, (x1, pill_y1), (pill_x2, pill_y2), pill_color, -1)
        # Label text
        cv2.putText(
            img, label, (x1 + 6, pill_y2 - 5),
            font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA
        )

    def draw_velocity_vector(
        self,
        img: np.ndarray,
        centroid: Tuple[int, int],
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        scale: float = 3.0
    ):
        """Draws a forward velocity vector arrow from the object centroid."""
        speed = math.sqrt(vx ** 2 + vy ** 2)
        if speed < 0.5:
            return

        end_x = int(centroid[0] + vx * scale)
        end_y = int(centroid[1] + vy * scale)
        cv2.arrowedLine(img, centroid, (end_x, end_y), (0, 255, 255), 2, cv2.LINE_AA, tipLength=0.35)

    def draw_trajectory(
        self,
        img: np.ndarray,
        trajectory: List[Tuple[int, int]],
        color: Tuple[int, int, int]
    ):
        """Draws motion history trail line behind the tracked object."""
        if len(trajectory) < 2:
            return

        for i in range(1, len(trajectory)):
            pt1 = trajectory[i - 1]
            pt2 = trajectory[i]
            thickness = int(np.sqrt(float(i) / len(trajectory)) * 3) + 1
            cv2.line(img, pt1, pt2, color, thickness, cv2.LINE_AA)

        # Draw centroid dot at current position
        cv2.circle(img, trajectory[-1], 4, color, -1, cv2.LINE_AA)
        cv2.circle(img, trajectory[-1], 6, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_tripwire(
        self,
        img: np.ndarray,
        y_ratio: float,
        in_count: int,
        out_count: int
    ):
        """Draws the virtual tripwire counting line across the frame with stats."""
        h, w = img.shape[:2]
        line_y = int(h * y_ratio)

        # Draw dashed line
        dash_len = 15
        gap_len = 10
        x = 0
        while x < w:
            end_x = min(x + dash_len, w)
            cv2.line(img, (x, line_y), (end_x, line_y), (0, 242, 254), 2, cv2.LINE_AA)
            x += dash_len + gap_len

        # Tripwire telemetry pill on left
        in_pill = f"▲ IN: {in_count}"
        cv2.rectangle(img, (15, line_y - 24), (115, line_y - 4), (16, 185, 129), -1)
        cv2.putText(img, in_pill, (22, line_y - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Tripwire telemetry pill on right
        out_pill = f"▼ OUT: {out_count}"
        cv2.rectangle(img, (w - 125, line_y - 24), (w - 15, line_y - 4), (239, 68, 68), -1)
        cv2.putText(img, out_pill, (w - 118, line_y - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Center indicator tag
        cv2.putText(img, "[ VIRTUAL TRIPWIRE ]", (w // 2 - 80, line_y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 242, 254), 1, cv2.LINE_AA)

    def draw_roi_zone(
        self,
        img: np.ndarray,
        zone: List[float],
        in_zone_count: int
    ):
        """Draws the Region of Interest (ROI) surveillance zone."""
        h, w = img.shape[:2]
        x1 = int(zone[0] * w)
        y1 = int(zone[1] * h)
        x2 = int(zone[2] * w)
        y2 = int(zone[3] * h)

        # Semi-transparent fill
        overlay = img.copy()
        zone_color = (0, 140, 255) if in_zone_count > 0 else (120, 100, 40)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), zone_color, -1)
        cv2.addWeighted(overlay, 0.12, img, 0.88, 0, img)

        # Dashed border
        cv2.rectangle(img, (x1, y1), (x2, y2), zone_color, 1)

        # Header tag
        tag = f"⚠️ SURVEILLANCE ZONE (INTRUDERS: {in_zone_count})"
        cv2.putText(img, tag, (x1 + 10, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1, cv2.LINE_AA)

    def update_heatmap(self, h: int, w: int, tracks: List[dict]):
        """Accumulates motion density for the heatmap."""
        if self.heatmap_accum is None or self.heatmap_accum.shape != (h, w):
            self.heatmap_accum = np.zeros((h, w), dtype=np.float32)

        # Decay previous density
        self.heatmap_accum *= self.heatmap_decay

        # Splat Gaussian density at each track position
        radius = 25
        for trk in tracks:
            box = trk["box"]
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)

            y_min = max(0, cy - radius)
            y_max = min(h, cy + radius)
            x_min = max(0, cx - radius)
            x_max = min(w, cx + radius)

            if x_max > x_min and y_max > y_min:
                self.heatmap_accum[y_min:y_max, x_min:x_max] += 0.8

    def render_heatmap_overlay(self, img: np.ndarray) -> np.ndarray:
        """Renders the accumulated density as a thermal color overlay."""
        if self.heatmap_accum is None:
            return img

        norm_heat = np.clip(self.heatmap_accum / (np.max(self.heatmap_accum) + 1e-5) * 255, 0, 255).astype(np.uint8)
        heatmap_color = cv2.applyColorMap(norm_heat, cv2.COLORMAP_TURBO)
        mask = norm_heat > 20
        overlay = img.copy()
        overlay[mask] = cv2.addWeighted(img[mask], 0.45, heatmap_color[mask], 0.55, 0)
        return overlay

    def draw_telemetry_hud(
        self,
        img: np.ndarray,
        fps: float,
        active_count: int,
        cumulative_count: int,
        in_count: int,
        out_count: int,
        in_zone_count: int,
        class_counts: Dict[str, int]
    ):
        """Draws top information dashboard HUD with stats."""
        h, w = img.shape[:2]
        hud_h = 50

        # Semi-transparent top HUD bar
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (8, 12, 20), -1)
        cv2.addWeighted(overlay, 0.80, img, 0.20, 0, img)
        cv2.line(img, (0, hud_h), (w, hud_h), (40, 50, 70), 1)

        # FPS indicator
        fps_color = (0, 255, 128) if fps >= 20 else (0, 165, 255)
        cv2.putText(img, f"FPS: {fps:.1f}", (15, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, fps_color, 2, cv2.LINE_AA)

        # Active tracked objects
        cv2.putText(img, f"ACTIVE: {active_count}", (125, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

        # Cumulative unique tracks
        cv2.putText(img, f"TOTAL: {cumulative_count}", (240, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 180, 50), 1, cv2.LINE_AA)

        # Tripwire In/Out
        cv2.putText(img, f"IN: {in_count} | OUT: {out_count}", (365, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 242, 254), 1, cv2.LINE_AA)

        # Zone Intrusions
        zone_color = (0, 140, 255) if in_zone_count > 0 else (160, 170, 180)
        cv2.putText(img, f"ZONE: {in_zone_count}", (525, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, zone_color, 1, cv2.LINE_AA)

        # Class breakdown pills on the right
        classes_str = " ".join(f"[{k}:{v}]" for k, v in class_counts.items() if v > 0)
        if classes_str:
            (cw, _), _ = cv2.getTextSize(classes_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.putText(img, classes_str, (max(620, w - cw - 15), 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1, cv2.LINE_AA)

    def render(
        self,
        frame: np.ndarray,
        tracks: List[dict],
        fps: float,
        cumulative_count: int,
        in_count: int = 0,
        out_count: int = 0,
        in_zone_count: int = 0,
        tripwire_y: float = 0.5,
        roi_zone: Optional[List[float]] = None,
        show_trails: bool = True,
        show_boxes: bool = True,
        show_speed: bool = True,
        show_tripwire: bool = True,
        show_zone: bool = True,
        show_heatmap: bool = False
    ) -> np.ndarray:
        """Complete rendering pass over the video frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        class_counts: Dict[str, int] = {}

        # 1. Update and optionally render heatmap overlay
        self.update_heatmap(h, w, tracks)
        if show_heatmap:
            annotated = self.render_heatmap_overlay(annotated)

        # 2. Render ROI Surveillance Zone
        if show_zone and roi_zone:
            self.draw_roi_zone(annotated, roi_zone, in_zone_count)

        # 3. Render Virtual Tripwire
        if show_tripwire:
            self.draw_tripwire(annotated, tripwire_y, in_count, out_count)

        # 4. Render Tracked Objects (Trails, Corner Boxes, Velocity Vectors, Labels)
        for trk in tracks:
            track_id = trk["track_id"]
            box = trk["box"]
            cls_name = trk.get("class_name", "object")
            conf = trk.get("confidence", 1.0)
            trajectory = trk.get("trajectory", [])
            speed_kmh = trk.get("speed_kmh", 0.0)
            direction = trk.get("direction", "STATIONARY")
            in_zone = trk.get("in_zone", False)
            vx = trk.get("vx", 0.0)
            vy = trk.get("vy", 0.0)

            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
            color = self.get_track_color(track_id)

            if show_trails and trajectory:
                self.draw_trajectory(annotated, trajectory, color)

            if show_boxes:
                self.draw_corner_box(annotated, box, color, in_zone=in_zone)
                self.draw_track_label(
                    annotated, box, track_id, cls_name, conf,
                    speed_kmh, direction, color, in_zone=in_zone, show_speed=show_speed
                )
                if show_speed:
                    centroid = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
                    self.draw_velocity_vector(annotated, centroid, vx, vy, color)

        # 5. Top Telemetry HUD
        self.draw_telemetry_hud(
            annotated,
            fps=fps,
            active_count=len(tracks),
            cumulative_count=cumulative_count,
            in_count=in_count,
            out_count=out_count,
            in_zone_count=in_zone_count,
            class_counts=class_counts
        )

        return annotated
