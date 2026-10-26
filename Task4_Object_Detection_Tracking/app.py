"""
Flask Web Application for Task 4: Real-Time Object Detection & Tracking
Provides high-performance MJPEG live streaming, interactive surveillance HUD telemetry,
standalone image inspection mode, virtual tripwire analytics, and event reporting.
"""

import base64
from io import BytesIO
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import threading
import time
from typing import Any, Dict, List, Optional
import cv2
from flask import Flask, Response, jsonify, render_template, request, send_file
import numpy as np

from src.detector import ObjectDetector, COCO_PRESETS
from src.sort_tracker import SortTracker
from src.visualizer import Visualizer

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


class VideoStreamPipeline:
    def __init__(self):
        self.detector = ObjectDetector()
        self.tracker = SortTracker(
            max_age=25,
            min_hits=2,
            iou_threshold=0.3,
            tripwire_y=0.52
        )
        self.visualizer = Visualizer()

        # Source Configuration: "real_traffic", "sample", "webcam", or "custom"
        self.source_mode = "real_traffic"
        self.custom_video_path: Optional[str] = None
        self.source_note = ""

        # Detection & Analytics Parameters
        self.conf_threshold = 0.35
        self.iou_threshold = 0.45
        self.class_filter: List[str] = []  # Empty means all classes

        # Display Toggles
        self.show_trails = True
        self.show_boxes = True
        self.show_speed = True
        self.show_tripwire = True
        self.show_zone = True
        self.show_heatmap = False

        self.is_running = True

        # Telemetry Metrics
        self.current_fps = 0.0
        self.active_count = 0
        self.total_tracks = 0
        self.in_count = 0
        self.out_count = 0
        self.in_zone_count = 0
        self.class_counts: Dict[str, int] = {}

        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.cap = None
        self.lock = threading.Lock()
        self._init_capture()

    def _init_capture(self):
        with self.lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

            self.source_note = ""
            base_media = Path(__file__).parent / "sample_media"

            if self.source_mode == "webcam":
                temp_cap = cv2.VideoCapture(0)
                if temp_cap is not None and temp_cap.isOpened():
                    ret_test, _ = temp_cap.read()
                    if ret_test:
                        self.cap = temp_cap
                        self.source_note = "Live Webcam Active (Camera 0)"
                    else:
                        temp_cap.release()
                        self.source_mode = "real_traffic"
                        self.source_note = "Webcam detected but feed unreadable. Fallback to real traffic."
                        self.cap = cv2.VideoCapture(str(base_media / "real_traffic.mp4"))
                else:
                    self.source_mode = "real_traffic"
                    self.source_note = "Webcam not available. Fallback to real traffic."
                    self.cap = cv2.VideoCapture(str(base_media / "real_traffic.mp4"))

            elif self.source_mode == "sample":
                sample_file = base_media / "sample_traffic.mp4"
                if not sample_file.exists():
                    from sample_media.create_sample_video import generate_synthetic_surveillance_video
                    generate_synthetic_surveillance_video(sample_file)
                self.cap = cv2.VideoCapture(str(sample_file))
                self.source_note = "Synthetic Traffic Simulation (Contour/YOLO)"

            elif self.source_mode == "real_traffic":
                real_file = base_media / "real_traffic.mp4"
                if real_file.exists():
                    self.cap = cv2.VideoCapture(str(real_file))
                    self.source_note = "Surveillance Video Stream (YOLOv8)"
                else:
                    # Fallback to sample
                    self.source_mode = "sample"
                    self.cap = cv2.VideoCapture(str(base_media / "sample_traffic.mp4"))
                    self.source_note = "Sample Traffic Simulation"

            elif self.source_mode == "custom" and self.custom_video_path and Path(self.custom_video_path).exists():
                self.cap = cv2.VideoCapture(str(self.custom_video_path))
                self.source_note = f"Custom Video: {Path(self.custom_video_path).name}"
            else:
                self.source_mode = "real_traffic"
                self.cap = cv2.VideoCapture(str(base_media / "real_traffic.mp4"))
                self.source_note = "Surveillance Video Stream"

            self.tracker.reset()

    def set_source(self, mode: str, custom_path: Optional[str] = None):
        if custom_path:
            self.custom_video_path = custom_path
            self.source_mode = "custom"
            self._init_capture()
        elif mode in ["real_traffic", "sample", "webcam"] and (mode != self.source_mode or self.cap is None):
            self.source_mode = mode
            self._init_capture()

    def reset_tracking(self):
        with self.lock:
            self.tracker.reset()

    def generate_frames(self):
        frame_idx = 0
        fps_start = time.time()
        fps_count = 0
        cached_dets = []

        while self.is_running:
            with self.lock:
                if self.cap is None or not self.cap.isOpened():
                    self._init_capture()
                    time.sleep(0.1)
                    if self.cap is None or not self.cap.isOpened():
                        time.sleep(0.2)
                        continue

                ret, frame = self.cap.read()
                if not ret:
                    # Loop video if sample or custom video
                    if self.source_mode in ["sample", "real_traffic", "custom"]:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                    else:
                        time.sleep(0.05)
                        continue

            frame_idx += 1
            fps_count += 1

            if fps_count >= 10:
                dt = time.time() - fps_start
                self.current_fps = round(fps_count / dt, 1) if dt > 0 else 30.0
                fps_count = 0
                fps_start = time.time()

            h, w = frame.shape[:2]

            # Run detection every 2 frames for CPU throughput
            is_synth = (self.source_mode == "sample")
            if frame_idx % 2 == 0 or frame_idx == 1:
                cached_dets = self.detector.detect(
                    frame,
                    conf_threshold=self.conf_threshold,
                    iou_threshold=self.iou_threshold,
                    target_classes=self.class_filter,
                    is_synthetic=is_synth
                )

            # SORT tracking update with velocity & tripwire analysis
            tracks = self.tracker.update(cached_dets, frame_shape=(h, w))
            self.active_count = len(tracks)
            self.total_tracks = self.tracker.total_unique_objects
            self.in_count = self.tracker.in_count
            self.out_count = self.tracker.out_count
            self.in_zone_count = self.tracker.in_zone_count

            # Class breakdown
            c_dict = {}
            for t in tracks:
                cls_name = t.get("class_name", "object")
                c_dict[cls_name] = c_dict.get(cls_name, 0) + 1
            self.class_counts = c_dict

            # Visualizer rendering
            annotated = self.visualizer.render(
                frame=frame,
                tracks=tracks,
                fps=self.current_fps,
                cumulative_count=self.total_tracks,
                in_count=self.in_count,
                out_count=self.out_count,
                in_zone_count=self.in_zone_count,
                tripwire_y=self.tracker.tripwire_y_ratio,
                roi_zone=self.tracker.roi_zone,
                show_trails=self.show_trails,
                show_boxes=self.show_boxes,
                show_speed=self.show_speed,
                show_tripwire=self.show_tripwire,
                show_zone=self.show_zone,
                show_heatmap=self.show_heatmap
            )

            # Draw note banner if active
            if self.source_note and ("Fallback" in self.source_note or "Simulation" in self.source_note):
                cv2.putText(
                    annotated,
                    f"INFO: {self.source_note}",
                    (20, annotated.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.50,
                    (0, 220, 255),
                    1,
                    cv2.LINE_AA
                )

            self.latest_annotated_frame = annotated

            # Encode frame as JPEG
            ret_encode, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret_encode:
                continue

            frame_bytes = buffer.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

            time.sleep(0.015)


pipeline = VideoStreamPipeline()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        pipeline.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/stats")
def get_stats():
    return jsonify({
        "fps": pipeline.current_fps,
        "active_count": pipeline.active_count,
        "total_tracks": pipeline.total_tracks,
        "in_count": pipeline.in_count,
        "out_count": pipeline.out_count,
        "in_zone_count": pipeline.in_zone_count,
        "class_counts": pipeline.class_counts,
        "source": pipeline.source_mode,
        "source_note": pipeline.source_note,
        "conf_threshold": pipeline.conf_threshold,
        "iou_threshold": pipeline.iou_threshold,
        "class_filter": pipeline.class_filter,
        "show_trails": pipeline.show_trails,
        "show_boxes": pipeline.show_boxes,
        "show_speed": pipeline.show_speed,
        "show_tripwire": pipeline.show_tripwire,
        "show_zone": pipeline.show_zone,
        "show_heatmap": pipeline.show_heatmap,
        "recent_events": pipeline.tracker.get_events()[:15]
    })


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(force=True, silent=True) or {}

    if "source" in data:
        pipeline.set_source(data["source"])
    if "conf_threshold" in data:
        pipeline.conf_threshold = float(data["conf_threshold"])
    if "iou_threshold" in data:
        pipeline.iou_threshold = float(data["iou_threshold"])
    if "class_filter" in data:
        pipeline.class_filter = data["class_filter"] if isinstance(data["class_filter"], list) else []
    if "show_trails" in data:
        pipeline.show_trails = bool(data["show_trails"])
    if "show_boxes" in data:
        pipeline.show_boxes = bool(data["show_boxes"])
    if "show_speed" in data:
        pipeline.show_speed = bool(data["show_speed"])
    if "show_tripwire" in data:
        pipeline.show_tripwire = bool(data["show_tripwire"])
    if "show_zone" in data:
        pipeline.show_zone = bool(data["show_zone"])
    if "show_heatmap" in data:
        pipeline.show_heatmap = bool(data["show_heatmap"])
    if "tripwire_y" in data:
        pipeline.tracker.set_tripwire(float(data["tripwire_y"]))
    if data.get("reset"):
        pipeline.reset_tracking()

    return jsonify({
        "success": True,
        "source": pipeline.source_mode,
        "note": pipeline.source_note
    })


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"success": False, "error": "No video file provided in request."}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    allowed_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_exts:
        return jsonify({"success": False, "error": f"Invalid format. Supported: {', '.join(allowed_exts)}"}), 400

    upload_dir = Path(__file__).parent / "sample_media"
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / f"upload_{int(time.time())}_{file.filename}"
    file.save(str(save_path))

    pipeline.set_source("custom", custom_path=str(save_path))
    return jsonify({
        "success": True,
        "filename": file.filename,
        "message": f"Successfully loaded '{file.filename}' into tracking pipeline!"
    })


@app.route("/api/detect_image", methods=["POST"])
def detect_image():
    """
    Endpoint for single-image analysis.
    Accepts an uploaded image or 'sample' flag.
    Returns annotated base64 image and detection table.
    """
    conf = float(request.form.get("conf", 0.35))
    use_sample = request.form.get("use_sample", "false").lower() == "true"

    if use_sample:
        sample_path = Path(__file__).parent / "sample_media" / "bus.jpg"
        if not sample_path.exists():
            return jsonify({"success": False, "error": "Sample image not found"}), 404
        img = cv2.imread(str(sample_path))
    elif "image" in request.files:
        file = request.files["image"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Empty filename"}), 400
        in_memory_file = file.read()
        nparr = np.frombuffer(in_memory_file, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        return jsonify({"success": False, "error": "No image file provided"}), 400

    if img is None:
        return jsonify({"success": False, "error": "Could not decode image"}), 400

    # Run detection
    result = pipeline.detector.detect_image(img, conf_threshold=conf)
    detections = result["detections"]

    # Render visualizer boxes on copy
    annotated = img.copy()
    for idx, d in enumerate(detections):
        box = d["box"]
        cls_name = d["class_name"]
        confidence = d["confidence"]
        color = pipeline.visualizer.get_track_color(idx + 1)
        pipeline.visualizer.draw_corner_box(annotated, box, color)
        pipeline.visualizer.draw_track_label(
            annotated, box, idx + 1, cls_name, confidence,
            speed_kmh=0.0, direction="", color=color, show_speed=False
        )

    # Encode to base64
    ret, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ret:
        return jsonify({"success": False, "error": "Failed to encode image"}), 500

    b64_str = base64.b64encode(buffer).decode("utf-8")

    return jsonify({
        "success": True,
        "total_detections": result["total_detections"],
        "detections": detections,
        "class_counts": result["class_counts"],
        "inference_time_ms": result["inference_time_ms"],
        "image_dimensions": result["image_dimensions"],
        "annotated_image": f"data:image/jpeg;base64,{b64_str}"
    })


@app.route("/api/snapshot")
def get_snapshot():
    """Returns the most recent annotated frame as a downloadable JPEG."""
    frame = pipeline.latest_annotated_frame
    if frame is None:
        # Capture one frame on demand if live stream has not yet started
        with pipeline.lock:
            if pipeline.cap is not None and pipeline.cap.isOpened():
                ret, raw_frame = pipeline.cap.read()
                if ret:
                    dets = pipeline.detector.detect(
                        raw_frame,
                        conf_threshold=pipeline.conf_threshold,
                        iou_threshold=pipeline.iou_threshold,
                        target_classes=pipeline.class_filter
                    )
                    tracks = pipeline.tracker.update(dets, frame_shape=raw_frame.shape[:2])
                    frame = pipeline.visualizer.render(
                        frame=raw_frame,
                        tracks=tracks,
                        fps=30.0,
                        cumulative_count=pipeline.total_tracks,
                        in_count=pipeline.in_count,
                        out_count=pipeline.out_count,
                        in_zone_count=pipeline.in_zone_count,
                        tripwire_y=pipeline.tracker.tripwire_y_ratio,
                        roi_zone=pipeline.tracker.roi_zone
                    )

    if frame is None:
        return "No frame available.", 404

    ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ret:
        return "Encoding error", 500

    return send_file(
        BytesIO(buffer.tobytes()),
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=f"surveillance_snapshot_{int(time.time())}.jpg"
    )


@app.route("/api/export_events")
def export_events():
    """Exports all logged tracking events as a CSV file."""
    events = pipeline.tracker.get_events()
    csv_lines = ["Timestamp,Track_ID,Class,Event_Type,Details,Speed_KMH\n"]
    for e in events:
        csv_lines.append(f"{e.get('timestamp')},{e.get('track_id')},{e.get('class_name')},{e.get('event_type')},\"{e.get('details')}\",{e.get('speed_kmh', 0)}\n")

    csv_data = "".join(csv_lines)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=tracking_events_{int(time.time())}.csv"}
    )


@app.route("/api/clear_events", methods=["POST"])
def clear_events():
    pipeline.tracker.events.clear()
    return jsonify({"success": True})


if __name__ == "__main__":
    print("=" * 70)
    print("Task 4 Intelligent Object Detection & Tracking System")
    print("Web Console running on: http://localhost:5003")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5003, debug=False, threaded=True)
