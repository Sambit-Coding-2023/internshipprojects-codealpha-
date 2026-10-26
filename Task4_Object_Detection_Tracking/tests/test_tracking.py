"""
Unit and Integration Tests for Task 4: Object Detection & Tracking
Tests detector, Kalman filter tracker, Hungarian association, tripwire counting,
and Flask API endpoints.
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src.") or mod == "app":
        del sys.modules[mod]
while str(project_root) in sys.path:
    sys.path.remove(str(project_root))
sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from src.detector import ObjectDetector, COCO_PRESETS
from src.sort_tracker import (
    KalmanBoxTracker,
    SortTracker,
    associate_detections_to_trackers,
    convert_bbox_to_z,
    convert_x_to_bbox,
    get_compass_direction,
    iou_batch
)
from app import app


class TestDetectionAndTracking:
    def test_detector_initialization(self):
        detector = ObjectDetector()
        info = detector.get_model_info()
        assert "yolov8" in info["model_name"].lower()
        assert info["total_classes"] == 80
        assert "vehicles" in info["presets"]
        assert "traffic" in info["presets"]

    def test_detector_image_analysis(self):
        detector = ObjectDetector()
        # Test on dummy synthetic 3-channel frame
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.detect_image(dummy, conf_threshold=0.35)
        assert "detections" in result
        assert "class_counts" in result
        assert "inference_time_ms" in result
        assert result["image_dimensions"]["width"] == 640

    def test_kalman_box_conversions(self):
        bbox = np.array([100, 100, 200, 300]) # w=100, h=200, area=20000, ratio=0.5
        z = convert_bbox_to_z(bbox)
        assert z.shape == (4, 1)
        assert z[0, 0] == 150.0 # x_center
        assert z[1, 0] == 200.0 # y_center
        assert z[2, 0] == 20000.0 # scale
        assert z[3, 0] == 0.5 # aspect ratio

        reconstructed = convert_x_to_bbox(z)[0]
        np.testing.assert_allclose(reconstructed, bbox, atol=1e-3)

    def test_iou_batch(self):
        bb1 = np.array([[0, 0, 100, 100]])
        bb2 = np.array([[0, 0, 100, 100], [200, 200, 300, 300]])
        ious = iou_batch(bb1, bb2)
        assert ious.shape == (1, 2)
        assert round(float(ious[0, 0]), 2) == 1.0 # Exact overlap
        assert round(float(ious[0, 1]), 2) == 0.0 # Disjoint boxes

    def test_compass_direction(self):
        assert get_compass_direction(0, 0) == "STATIONARY"
        assert get_compass_direction(5.0, 0.0) == "E"
        assert get_compass_direction(-5.0, 0.0) == "W"
        assert get_compass_direction(0.0, -5.0) == "N"  # -vy because image y is down
        assert get_compass_direction(0.0, 5.0) == "S"

    def test_kalman_tracker_lifecycle(self):
        KalmanBoxTracker.count = 0
        trk = KalmanBoxTracker(np.array([50, 50, 150, 150]), class_name="car", confidence=0.92)
        assert trk.id == 0
        assert trk.class_name == "car"

        # Frame 2: simulate object moving right and down
        pred = trk.predict()
        assert pred is not None
        trk.update(np.array([60, 60, 160, 160]), class_name="car", confidence=0.94)

        assert trk.hits == 2
        assert len(trk.trajectory) >= 2
        assert trk.vx > 0  # Positive horizontal velocity

    def test_hungarian_association(self):
        dets = np.array([
            [10, 10, 50, 50],
            [200, 200, 250, 250]
        ])
        trks = np.array([
            [12, 11, 52, 51], # Close to det 0
            [500, 500, 550, 550] # Unmatched
        ])
        matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets, trks, iou_threshold=0.3)
        assert len(matched) == 1
        assert matched[0][0] == 0 # det 0 matches trk 0
        assert matched[0][1] == 0
        assert 1 in unmatched_dets # det 1 unmatched
        assert 1 in unmatched_trks # trk 1 unmatched

    def test_sort_tracker_tripwire_and_zone(self):
        tracker = SortTracker(max_age=10, min_hits=1, iou_threshold=0.1, tripwire_y=0.5)
        tracker.reset()

        # Object starts above tripwire (line at y=250 in 500h frame, box centroid y=210)
        dets_frame1 = [{"box": [100, 170, 200, 250], "class_name": "car", "confidence": 0.9}]
        tracks1 = tracker.update(dets_frame1, frame_shape=(500, 800))
        assert len(tracks1) == 1

        # Object moves downwards crossing tripwire (centroid y=270)
        dets_frame2 = [{"box": [100, 230, 200, 310], "class_name": "car", "confidence": 0.92}]
        tracks2 = tracker.update(dets_frame2, frame_shape=(500, 800))
        assert len(tracks2) == 1
        assert tracker.in_count == 1  # Crossed IN downwards!

        events = tracker.get_events()
        assert len(events) >= 1
        assert events[0]["event_type"] == "LINE_CROSSING"
        assert "IN" in events[0]["details"]

    def test_flask_endpoints(self):
        client = app.test_client()

        # Test GET /api/stats
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "fps" in data
        assert "active_count" in data
        assert "total_tracks" in data
        assert "in_count" in data
        assert "out_count" in data

        # Test POST /api/settings
        set_resp = client.post("/api/settings", json={
            "conf_threshold": 0.40,
            "show_speed": True,
            "show_tripwire": True
        })
        assert set_resp.status_code == 200
        assert set_resp.get_json()["success"] is True

        # Test GET /api/export_events
        csv_resp = client.get("/api/export_events")
        assert csv_resp.status_code == 200
        assert b"Timestamp,Track_ID,Class" in csv_resp.data


if __name__ == "__main__":
    pytest.main(["-v", __file__])
