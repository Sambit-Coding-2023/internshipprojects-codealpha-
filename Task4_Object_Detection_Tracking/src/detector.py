"""
Object Detection Engine using Pre-Trained YOLOv8 and Adaptive Detection
Processes video frames and images, identifies objects with bounding boxes,
labels, confidence metrics, and category filtering.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from ultralytics import YOLO

# Standard COCO 80 Category Presets for quick filtering
COCO_PRESETS = {
    "all": [],
    "vehicles": ["car", "truck", "bus", "motorcycle", "bicycle", "train", "airplane", "boat"],
    "people": ["person"],
    "traffic": ["car", "truck", "bus", "motorcycle", "bicycle", "person", "traffic light", "stop sign"],
    "animals": ["dog", "cat", "bird", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"],
    "objects": ["backpack", "umbrella", "handbag", "suitcase", "sports ball", "bottle", "cup", "chair", "cell phone", "laptop"]
}


class ObjectDetector:
    def __init__(self, model_path: Optional[str] = None):
        base_dir = Path(__file__).parent.parent
        if model_path is None:
            model_path = str(base_dir / "models" / "yolov8n.pt")

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            print(f"Downloading/loading YOLOv8n to {self.model_path}...")
            self.model = YOLO("yolov8n.pt")
            self.model.save(str(self.model_path))
        else:
            self.model = YOLO(str(self.model_path))

        self.class_names = self.model.names
        # Motion detection fallback for synthetic surveillance simulation
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40, detectShadows=False)

    def get_model_info(self) -> Dict[str, Any]:
        """Returns metadata about the active detection model."""
        return {
            "model_name": self.model_path.name,
            "total_classes": len(self.class_names),
            "classes": list(self.class_names.values()),
            "presets": list(COCO_PRESETS.keys())
        }

    def detect_yolo(
        self,
        frame: np.ndarray,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs YOLOv8 object detection on a BGR video frame.
        Returns:
            List of detected objects: [{'box': [x1, y1, x2, y2], 'confidence': float, 'class_name': str, 'class_id': int}]
        """
        # Resolve target classes if passed as preset key
        if target_classes and len(target_classes) == 1 and target_classes[0] in COCO_PRESETS:
            target_classes = COCO_PRESETS[target_classes[0]]

        results = self.model.predict(
            source=frame,
            conf=conf_threshold,
            iou=iou_threshold,
            verbose=False,
            device="cpu"
        )

        detections = []
        if not results:
            return detections

        first_res = results[0]
        boxes = first_res.boxes

        if boxes is None:
            return detections

        for box in boxes:
            coords = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = self.class_names.get(cls_id, f"class_{cls_id}")

            if target_classes and len(target_classes) > 0 and cls_name not in target_classes:
                continue

            detections.append({
                "box": [float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])],
                "confidence": round(conf, 3),
                "class_name": cls_name,
                "class_id": cls_id
            })

        return detections

    def detect_synthetic_simulation(
        self,
        frame: np.ndarray,
        min_area: int = 400,
        target_classes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Contour-based detector specifically for the simulated synthetic traffic video,
        allowing testing even without real camera/webcam footage.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fg_mask = self.bg_subtractor.apply(gray)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []

        if target_classes and len(target_classes) == 1 and target_classes[0] in COCO_PRESETS:
            target_classes = COCO_PRESETS[target_classes[0]]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Filter out road lines / watermark text
            if y < 80 or y > 460 or w < 20 or h < 30:
                continue

            # Heuristic classification based on aspect ratio
            aspect_ratio = w / float(h)
            if aspect_ratio > 1.2:
                cls_name = "car"
                cls_id = 2
            elif aspect_ratio < 0.6:
                cls_name = "person"
                cls_id = 0
            else:
                cls_name = "bicycle"
                cls_id = 1

            if target_classes and len(target_classes) > 0 and cls_name not in target_classes:
                continue

            detections.append({
                "box": [float(x), float(y), float(x + w), float(y + h)],
                "confidence": 0.88,
                "class_name": cls_name,
                "class_id": cls_id
            })

        return detections

    def detect(
        self,
        frame: np.ndarray,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[str]] = None,
        is_synthetic: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Unified detection method. Runs YOLOv8 by default, or synthetic fallback if configured.
        """
        if is_synthetic:
            # First try YOLO
            dets = self.detect_yolo(
                frame,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                target_classes=target_classes
            )
            if len(dets) == 0:
                # Fallback to contour detection for synthetic simulation
                dets = self.detect_synthetic_simulation(
                    frame,
                    target_classes=target_classes
                )
            return dets

        return self.detect_yolo(
            frame,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            target_classes=target_classes
        )

    def detect_image(
        self,
        image: np.ndarray,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Performs standalone detection on a static image with timing and summary analysis.
        """
        start_t = time.time()
        detections = self.detect_yolo(
            image,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            target_classes=target_classes
        )
        inference_time_ms = round((time.time() - start_t) * 1000, 1)

        # Class breakdown
        class_counts: Dict[str, int] = {}
        for d in detections:
            c = d["class_name"]
            class_counts[c] = class_counts.get(c, 0) + 1

        return {
            "total_detections": len(detections),
            "detections": detections,
            "class_counts": class_counts,
            "inference_time_ms": inference_time_ms,
            "image_dimensions": {"width": image.shape[1], "height": image.shape[0]}
        }


if __name__ == "__main__":
    detector = ObjectDetector()
    info = detector.get_model_info()
    print("Detector loaded:", info["model_name"])
    print("Total COCO Classes:", info["total_classes"])
    print("Presets available:", info["presets"])
