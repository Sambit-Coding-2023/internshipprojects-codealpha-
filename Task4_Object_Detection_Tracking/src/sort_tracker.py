"""
SORT (Simple Online and Realtime Tracking) Algorithm with Velocity Estimation,
Virtual Tripwire (Line Crossing), and Zone Intrusion Detection (ROI)
"""

from collections import deque
from datetime import datetime
import math
import time
from typing import Any, Dict, List, Optional, Tuple
from filterpy.kalman import KalmanFilter
import numpy as np
from scipy.optimize import linear_sum_assignment


def convert_bbox_to_z(bbox: np.ndarray) -> np.ndarray:
    """
    Converts [x1, y1, x2, y2] to [x_center, y_center, scale(area), aspect_ratio]
    """
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2.0
    y = bbox[1] + h / 2.0
    s = w * h
    r = w / float(h) if h > 0 else 1.0
    return np.array([x, y, s, r]).reshape((4, 1))


def convert_x_to_bbox(x: np.ndarray) -> np.ndarray:
    """
    Converts Kalman state [x_center, y_center, scale, aspect_ratio, ...] back to [x1, y1, x2, y2]
    """
    w = np.sqrt(max(0, x[2] * x[3]))
    h = x[2] / w if w > 0 else 0
    return np.array([x[0] - w / 2.0, x[1] - h / 2.0, x[0] + w / 2.0, x[1] + h / 2.0]).reshape((1, 4))


def iou_batch(bb_test: np.ndarray, bb_gt: np.ndarray) -> np.ndarray:
    """
    Computes Intersection over Union (IoU) between two sets of bounding boxes.
    """
    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)

    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])
    w = np.maximum(0.0, xx2 - xx1)
    h = np.maximum(0.0, yy2 - yy1)
    wh = w * h
    o = wh / (
        (bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])
        + (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1])
        - wh
    )
    return o


def get_compass_direction(vx: float, vy: float) -> str:
    """
    Converts (vx, vy) velocity components into an 8-point compass direction.
    Note: In computer vision images, y increases downward.
    """
    if abs(vx) < 0.3 and abs(vy) < 0.3:
        return "STATIONARY"

    # angle in degrees from x-axis, -vy because image y is inverted
    angle = math.degrees(math.atan2(-vy, vx))
    if angle < 0:
        angle += 360

    if 22.5 <= angle < 67.5:
        return "NE"
    elif 67.5 <= angle < 112.5:
        return "N"
    elif 112.5 <= angle < 157.5:
        return "NW"
    elif 157.5 <= angle < 202.5:
        return "W"
    elif 202.5 <= angle < 247.5:
        return "SW"
    elif 247.5 <= angle < 292.5:
        return "S"
    elif 292.5 <= angle < 337.5:
        return "SE"
    else:
        return "E"


class KalmanBoxTracker:
    count = 0

    def __init__(self, bbox: np.ndarray, class_name: str = "object", confidence: float = 1.0):
        # 7-dimensional state vector: [u, v, s, r, u_dot, v_dot, s_dot]
        self.kf = KalmanFilter(dim_x=7, dim_z=4)

        # State transition matrix F
        self.kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 1]
        ])

        # Measurement function H
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0]
        ])

        # Measurement uncertainty R
        self.kf.R[2:, 2:] *= 10.0

        # State covariance P
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.P *= 10.0

        # Process noise Q
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)

        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 1
        self.hit_streak = 1
        self.age = 0
        self.class_name = class_name
        self.confidence = confidence

        x_center = int(self.kf.x[0][0])
        y_center = int(self.kf.x[1][0])
        self.trajectory: List[Tuple[int, int]] = [(x_center, y_center)]

        # Velocity & Analytics
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.0
        self.direction = "STATIONARY"
        self.first_seen_time = time.time()
        self.counted_tripwire = False
        self.in_zone = False

    def update(self, bbox: np.ndarray, class_name: str = None, confidence: float = None):
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(convert_bbox_to_z(bbox))
        if class_name:
            self.class_name = class_name
        if confidence:
            self.confidence = confidence

        # Record trajectory centroid
        x_center = int(self.kf.x[0][0])
        y_center = int(self.kf.x[1][0])
        self.trajectory.append((x_center, y_center))
        if len(self.trajectory) > 40:
            self.trajectory.pop(0)

        # Extract estimated velocities from state vector (u_dot, v_dot)
        self.vx = float(self.kf.x[4][0])
        self.vy = float(self.kf.x[5][0])
        self.speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        self.direction = get_compass_direction(self.vx, self.vy)

    def predict(self) -> np.ndarray:
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] = 0.0
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        return self.history[-1]

    def get_state(self) -> np.ndarray:
        return convert_x_to_bbox(self.kf.x)


def associate_detections_to_trackers(
    detections: np.ndarray,
    trackers: np.ndarray,
    iou_threshold: float = 0.3
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Associates detections to tracked object bounding boxes using Hungarian Algorithm.
    """
    if len(trackers) == 0:
        return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0,), dtype=int)

    iou_matrix = iou_batch(detections, trackers)

    if min(iou_matrix.shape) > 0:
        a = (iou_matrix > iou_threshold).astype(np.int32)
        if a.sum(1).max() == 1 and a.sum(0).max() == 1:
            matched_indices = np.stack(np.where(a), axis=1)
        else:
            # Linear Sum Assignment (Hungarian) on cost = -IoU
            row_ind, col_ind = linear_sum_assignment(-iou_matrix)
            matched_indices = np.stack((row_ind, col_ind), axis=1)
    else:
        matched_indices = np.empty(shape=(0, 2), dtype=int)

    unmatched_detections = []
    for d, det in enumerate(detections):
        if d not in matched_indices[:, 0]:
            unmatched_detections.append(d)

    unmatched_trackers = []
    for t, trk in enumerate(trackers):
        if t not in matched_indices[:, 1]:
            unmatched_trackers.append(t)

    # Filter out matches with low IoU
    matches = []
    for m in matched_indices:
        if iou_matrix[m[0], m[1]] < iou_threshold:
            unmatched_detections.append(m[0])
            unmatched_trackers.append(m[1])
        else:
            matches.append(m.reshape(1, 2))

    if len(matches) == 0:
        matches = np.empty((0, 2), dtype=int)
    else:
        matches = np.concatenate(matches, axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_trackers)


class SortTracker:
    def __init__(
        self,
        max_age: int = 25,
        min_hits: int = 2,
        iou_threshold: float = 0.3,
        tripwire_y: float = 0.5,  # Normalized Y position of counting line (0.0 to 1.0)
        roi_zone: Optional[List[float]] = None  # [x1, y1, x2, y2] normalized 0.0 to 1.0
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: List[KalmanBoxTracker] = []
        self.frame_count = 0
        self.total_unique_objects = 0

        # Tripwire Line Crossing Configuration
        self.tripwire_y_ratio = tripwire_y
        self.in_count = 0
        self.out_count = 0

        # Region of Interest (ROI) Zone: [x_min, y_min, x_max, y_max] normalized
        self.roi_zone = roi_zone or [0.15, 0.25, 0.85, 0.85]
        self.in_zone_count = 0

        # Live Incident & Event Feed (capped at 100 recent entries)
        self.events: deque = deque(maxlen=100)

    def reset(self):
        KalmanBoxTracker.count = 0
        self.trackers = []
        self.frame_count = 0
        self.total_unique_objects = 0
        self.in_count = 0
        self.out_count = 0
        self.in_zone_count = 0
        self.events.clear()

    def set_tripwire(self, y_ratio: float):
        """Sets normalized vertical position for the tripwire line (0.1 to 0.9)."""
        self.tripwire_y_ratio = max(0.1, min(0.9, y_ratio))

    def set_roi_zone(self, zone: List[float]):
        """Sets normalized [x1, y1, x2, y2] boundaries for the monitoring zone."""
        if len(zone) == 4:
            self.roi_zone = zone

    def _check_tripwire_crossing(
        self,
        trk: KalmanBoxTracker,
        prev_pt: Tuple[int, int],
        curr_pt: Tuple[int, int],
        frame_height: int
    ):
        """
        Evaluates whether a tracked centroid crossed the horizontal tripwire.
        Moving downward (prev_y < line_y <= curr_y) -> IN
        Moving upward (prev_y > line_y >= curr_y) -> OUT
        """
        line_y = int(frame_height * self.tripwire_y_ratio)
        prev_y = prev_pt[1]
        curr_y = curr_pt[1]

        if not trk.counted_tripwire:
            # Crossing down
            if prev_y < line_y <= curr_y:
                self.in_count += 1
                trk.counted_tripwire = True
                self._record_event(
                    track_id=trk.id,
                    class_name=trk.class_name,
                    event_type="LINE_CROSSING",
                    details="Crossed Tripwire (IN)",
                    speed=trk.speed
                )
            # Crossing up
            elif prev_y > line_y >= curr_y:
                self.out_count += 1
                trk.counted_tripwire = True
                self._record_event(
                    track_id=trk.id,
                    class_name=trk.class_name,
                    event_type="LINE_CROSSING",
                    details="Crossed Tripwire (OUT)",
                    speed=trk.speed
                )

    def _check_zone_status(
        self,
        trk: KalmanBoxTracker,
        centroid: Tuple[int, int],
        frame_width: int,
        frame_height: int
    ) -> bool:
        """
        Checks if centroid is within the ROI monitoring zone.
        """
        zx1 = int(self.roi_zone[0] * frame_width)
        zy1 = int(self.roi_zone[1] * frame_height)
        zx2 = int(self.roi_zone[2] * frame_width)
        zy2 = int(self.roi_zone[3] * frame_height)

        is_inside = (zx1 <= centroid[0] <= zx2) and (zy1 <= centroid[1] <= zy2)

        # Detect transition into zone
        if is_inside and not trk.in_zone:
            trk.in_zone = True
            self._record_event(
                track_id=trk.id,
                class_name=trk.class_name,
                event_type="ZONE_INTRUSION",
                details="Entered Monitoring Zone",
                speed=trk.speed
            )
        elif not is_inside and trk.in_zone:
            trk.in_zone = False

        return is_inside

    def _record_event(
        self,
        track_id: int,
        class_name: str,
        event_type: str,
        details: str,
        speed: float = 0.0
    ):
        event = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "track_id": track_id,
            "class_name": class_name,
            "event_type": event_type,
            "details": details,
            "speed_kmh": round(speed * 3.6, 1)  # Approximate pixel velocity to km/h scale
        }
        self.events.appendleft(event)

    def update(
        self,
        detections: List[dict],
        frame_shape: Optional[Tuple[int, int]] = None
    ) -> List[dict]:
        """
        Processes detections for current frame, associates with existing tracks,
        computes velocity, checks tripwire crossings and zone intrusion.
        """
        self.frame_count += 1
        frame_h = frame_shape[0] if frame_shape else 500
        frame_w = frame_shape[1] if frame_shape else 800

        # Predict positions from existing trackers
        trks = np.zeros((len(self.trackers), 4))
        to_del = []
        for t, trk in enumerate(trks):
            pos = self.trackers[t].predict()[0]
            trk[:] = [pos[0], pos[1], pos[2], pos[3]]
            if np.any(np.isnan(pos)):
                to_del.append(t)

        for t in reversed(to_del):
            self.trackers.pop(t)

        # Prepare detection boxes array
        if len(detections) > 0:
            dets = np.array([d['box'] for d in detections])
        else:
            dets = np.empty((0, 4))

        # Hungarian matching
        matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(
            dets, trks, self.iou_threshold
        )

        # Update matched trackers
        for m in matched:
            det_idx = m[0]
            trk_idx = m[1]
            det_info = detections[det_idx]
            self.trackers[trk_idx].update(
                bbox=dets[det_idx],
                class_name=det_info.get('class_name'),
                confidence=det_info.get('confidence')
            )

        # Initialize new trackers for unmatched detections
        for i in unmatched_dets:
            det_info = detections[i]
            trk = KalmanBoxTracker(
                bbox=dets[i],
                class_name=det_info.get('class_name', 'object'),
                confidence=det_info.get('confidence', 1.0)
            )
            self.trackers.append(trk)
            self.total_unique_objects += 1

        # Collect active tracks and perform tripwire/zone analysis
        active_tracks = []
        current_in_zone = 0
        i = len(self.trackers)

        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            if (trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
                centroid = (int((d[0] + d[2]) / 2), int((d[1] + d[3]) / 2))

                # Check line crossing if we have at least 2 points in trajectory
                if len(trk.trajectory) >= 2:
                    self._check_tripwire_crossing(
                        trk=trk,
                        prev_pt=trk.trajectory[-2],
                        curr_pt=centroid,
                        frame_height=frame_h
                    )

                # Check zone status
                in_zone = self._check_zone_status(
                    trk=trk,
                    centroid=centroid,
                    frame_width=frame_w,
                    frame_height=frame_h
                )
                if in_zone:
                    current_in_zone += 1

                dwell_sec = round(time.time() - trk.first_seen_time, 1)

                active_tracks.append({
                    "track_id": trk.id,
                    "box": [float(d[0]), float(d[1]), float(d[2]), float(d[3])],
                    "class_name": trk.class_name,
                    "confidence": float(trk.confidence),
                    "trajectory": list(trk.trajectory),
                    "vx": trk.vx,
                    "vy": trk.vy,
                    "speed": round(trk.speed, 1),
                    "speed_kmh": round(trk.speed * 3.6, 1),
                    "direction": trk.direction,
                    "in_zone": in_zone,
                    "dwell_sec": dwell_sec,
                    "age": trk.age,
                    "hits": trk.hits
                })

            i -= 1
            # Remove stale tracks
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)

        self.in_zone_count = current_in_zone
        return active_tracks

    def get_events(self) -> List[Dict[str, Any]]:
        """Returns the list of recent tracking incident events."""
        return list(self.events)


if __name__ == "__main__":
    tracker = SortTracker()
    sample_dets = [
        {"box": [100, 100, 150, 150], "class_name": "car", "confidence": 0.9},
        {"box": [300, 200, 340, 280], "class_name": "person", "confidence": 0.85}
    ]
    tracks = tracker.update(sample_dets, frame_shape=(500, 800))
    print(f"Tracked count: {len(tracks)}")
    for t in tracks:
        print(f"ID #{t['track_id']} | {t['class_name']} | Speed: {t['speed_kmh']} km/h | Dir: {t['direction']}")
