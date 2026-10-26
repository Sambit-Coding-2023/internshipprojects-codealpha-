"""
Real-Time Video & Webcam Object Detection and Tracking Desktop Runner
Processes video files or live webcams, runs YOLOv8 detection + SORT multi-object tracking,
calculates velocity vectors, virtual tripwire in/out counting, and density heatmaps.
"""

import argparse
from pathlib import Path
import time
from typing import List, Optional
import cv2
from src.detector import ObjectDetector, COCO_PRESETS
from src.sort_tracker import SortTracker
from src.visualizer import Visualizer


def run_detection_and_tracking(
    source: str = "real",
    conf_threshold: float = 0.35,
    iou_threshold: float = 0.3,
    save_output: bool = True,
    output_path: str = "outputs/tracked_output.mp4",
    export_csv: Optional[str] = "outputs/tracking_telemetry.csv",
    headless: bool = False,
    frame_skip: int = 2,
    max_frames: int = 200,
    classes: Optional[List[str]] = None,
    show_tripwire: bool = True,
    show_zone: bool = True,
    show_heatmap: bool = False
):
    print("=" * 75, flush=True)
    print("    INTELLIGENT VISION & MULTI-OBJECT TRACKING STUDIO (Task 4 CLI)    ", flush=True)
    print("=" * 75, flush=True)

    base_media = Path(__file__).parent / "sample_media"

    # Resolve shorthand source names
    if source == "real":
        video_src = str(base_media / "real_traffic.mp4")
        is_webcam = False
        is_synthetic = False
    elif source == "sample":
        video_src = str(base_media / "sample_traffic.mp4")
        is_webcam = False
        is_synthetic = True
    elif source.isdigit():
        video_src = int(source)
        is_webcam = True
        is_synthetic = False
    else:
        src_path = Path(source)
        if not src_path.is_absolute():
            src_path = Path(__file__).parent / source
        video_src = str(src_path)
        is_webcam = False
        is_synthetic = "sample_traffic" in video_src

    print(f"Connecting to video source: {video_src}", flush=True)
    cap = cv2.VideoCapture(video_src)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {video_src}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    input_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_webcam else 0

    print(f"Video Geometry: {width}x{height} | Target Rate: {input_fps:.1f} FPS", flush=True)

    # Initialize components
    print("Loading YOLOv8 neural network...", flush=True)
    detector = ObjectDetector()
    print("Initializing SORT Kalman Filter Tracker + Tripwire Engine...", flush=True)
    tracker = SortTracker(max_age=25, min_hits=2, iou_threshold=iou_threshold, tripwire_y=0.52)
    visualizer = Visualizer()

    # Output writer setup
    writer = None
    if save_output:
        out_file = Path(output_path)
        if not out_file.is_absolute():
            out_file = Path(__file__).parent / output_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_file), fourcc, input_fps, (width, height))
        print(f"Exporting tracked video to: {out_file}", flush=True)

    # CSV Telemetry setup
    csv_records = []
    if export_csv:
        csv_file = Path(export_csv)
        if not csv_file.is_absolute():
            csv_file = Path(__file__).parent / export_csv
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        csv_records.append("frame,timestamp_sec,track_id,class_name,confidence,speed_kmh,direction,in_zone,x1,y1,x2,y2\n")

    print("-" * 75, flush=True)
    if not headless:
        print("Live Controls: [q] Quit  [p] Pause  [s] Screenshot  [t] Trails  [b] Boxes  [h] Heatmap  [l] Tripwire", flush=True)
    print("-" * 75, flush=True)

    frame_idx = 0
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = input_fps
    cached_detections = []

    show_trails = True
    show_boxes = True
    show_speed = True

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            fps_counter += 1

            if max_frames > 0 and frame_idx > max_frames and not is_webcam:
                print(f"Reached requested frame limit ({max_frames}). Stopping.", flush=True)
                break

            # Calculate FPS every 10 frames
            if fps_counter >= 10:
                elapsed = time.time() - fps_start_time
                current_fps = fps_counter / elapsed if elapsed > 0 else input_fps
                fps_counter = 0
                fps_start_time = time.time()

            # 1. Detection (Run every frame_skip frames for CPU decimation)
            if frame_idx % frame_skip == 0 or frame_idx == 1:
                cached_detections = detector.detect(
                    frame,
                    conf_threshold=conf_threshold,
                    target_classes=classes,
                    is_synthetic=is_synthetic
                )

            # 2. Multi-Object Tracking & Analytics
            tracked_objects = tracker.update(cached_detections, frame_shape=(height, width))

            # Record CSV Telemetry
            if export_csv:
                t_sec = round(frame_idx / input_fps, 2)
                for trk in tracked_objects:
                    b = trk["box"]
                    csv_records.append(
                        f"{frame_idx},{t_sec},{trk['track_id']},{trk['class_name']},{trk['confidence']:.2f},"
                        f"{trk.get('speed_kmh', 0.0)},{trk.get('direction', '')},{trk.get('in_zone', False)},"
                        f"{b[0]:.1f},{b[1]:.1f},{b[2]:.1f},{b[3]:.1f}\n"
                    )

            # 3. Visualizer Rendering
            annotated_frame = visualizer.render(
                frame=frame,
                tracks=tracked_objects,
                fps=current_fps,
                cumulative_count=tracker.total_unique_objects,
                in_count=tracker.in_count,
                out_count=tracker.out_count,
                in_zone_count=tracker.in_zone_count,
                tripwire_y=tracker.tripwire_y_ratio,
                roi_zone=tracker.roi_zone,
                show_trails=show_trails,
                show_boxes=show_boxes,
                show_speed=show_speed,
                show_tripwire=show_tripwire,
                show_zone=show_zone,
                show_heatmap=show_heatmap
            )

            # Write to video file
            if writer is not None:
                writer.write(annotated_frame)

            # Terminal log
            if frame_idx % 20 == 0 or frame_idx == 1:
                status_str = f"Frame [{frame_idx:04d}/{total_frames if total_frames > 0 else 'LIVE'}]"
                print(f"{status_str} | In View: {len(tracked_objects):02d} | Total: {tracker.total_unique_objects:02d} | IN: {tracker.in_count:02d} | OUT: {tracker.out_count:02d} | FPS: {current_fps:.1f}", flush=True)

            # Display GUI window
            if not headless:
                cv2.imshow("Task 4: Object Detection & Tracking Studio", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nUser requested exit.", flush=True)
                    break
                elif key == ord('p'):
                    print("Stream paused. Press any key to resume...", flush=True)
                    cv2.waitKey(0)
                elif key == ord('s'):
                    snap_path = Path(__file__).parent / "outputs" / f"snapshot_{frame_idx}.jpg"
                    snap_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(snap_path), annotated_frame)
                    print(f"Snapshot saved to: {snap_path}", flush=True)
                elif key == ord('t'):
                    show_trails = not show_trails
                elif key == ord('b'):
                    show_boxes = not show_boxes
                elif key == ord('h'):
                    show_heatmap = not show_heatmap
                elif key == ord('l'):
                    show_tripwire = not show_tripwire
                elif key == ord('z'):
                    show_zone = not show_zone

    finally:
        cap.release()
        if writer is not None:
            writer.release()
            print(f"Successfully saved tracked output video to: {output_path}", flush=True)
        if not headless:
            cv2.destroyAllWindows()

        # Save CSV telemetry
        if export_csv and len(csv_records) > 1:
            with open(str(csv_file), "w", encoding="utf-8") as f:
                f.writelines(csv_records)
            print(f"Exported tracking telemetry CSV to: {csv_file} ({len(csv_records)-1} data rows)", flush=True)

    print("=" * 75, flush=True)
    print("Pipeline run completed successfully.")
    print("=" * 75, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task 4: Intelligent Object Detection & Tracking")
    parser.add_argument("--source", type=str, default="real",
                        help="Video source: 'real', 'sample', camera index (e.g. 0), or filepath")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.3, help="SORT IoU association threshold")
    parser.add_argument("--output", type=str, default="outputs/tracked_output.mp4", help="Output video path")
    parser.add_argument("--export-csv", type=str, default="outputs/tracking_telemetry.csv", help="CSV telemetry path")
    parser.add_argument("--headless", action="store_true", help="Run without OpenCV GUI window")
    parser.add_argument("--max_frames", type=int, default=150, help="Max frames to process (0 for full)")
    parser.add_argument("--heatmap", action="store_true", help="Enable density heatmap overlay")
    parser.add_argument("--classes", nargs="*", default=None, help="Filter by specific class names (e.g. car person)")

    args = parser.parse_args()

    run_detection_and_tracking(
        source=args.source,
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        output_path=args.output,
        export_csv=args.export_csv,
        headless=args.headless,
        max_frames=args.max_frames,
        classes=args.classes,
        show_heatmap=args.heatmap
    )
