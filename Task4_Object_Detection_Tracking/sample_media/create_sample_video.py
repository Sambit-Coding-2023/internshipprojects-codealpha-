"""
Sample Video Generator for Task 4: Object Detection & Tracking
Generates a realistic multi-object video stream with moving objects, crossing paths,
and occlusions so users without webcams or video files can test immediately.
"""

from pathlib import Path
import cv2
import numpy as np


def generate_synthetic_surveillance_video(
    output_path: Path,
    width: int = 800,
    height: int = 500,
    fps: int = 30,
    duration_sec: int = 10
):
    """
    Creates a simulated traffic / surveillance environment with multiple moving objects
    (cars, pedestrians, bicycles) moving across lanes with realistic speeds and occlusions.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    total_frames = fps * duration_sec

    # Simulated objects with start pos, velocity, size, color, label
    objects = [
        # Car 1 moving right
        {"x": 50, "y": 280, "vx": 4.5, "vy": 0, "w": 90, "h": 50, "color": (50, 100, 220), "label": "car"},
        # Car 2 moving right (faster)
        {"x": 10, "y": 350, "vx": 6.0, "vy": 0, "w": 100, "h": 55, "color": (200, 80, 50), "label": "car"},
        # Person 1 walking across sidewalk
        {"x": 750, "y": 140, "vx": -2.0, "vy": 0.5, "w": 30, "h": 70, "color": (50, 200, 120), "label": "person"},
        # Person 2 walking along street
        {"x": 60, "y": 160, "vx": 2.2, "vy": 0, "w": 28, "h": 65, "color": (220, 180, 40), "label": "person"},
        # Bicycle moving left
        {"x": 780, "y": 220, "vx": -3.5, "vy": 0, "w": 45, "h": 50, "color": (180, 50, 200), "label": "bicycle"},
    ]

    for frame_idx in range(total_frames):
        # Background: Road with lane markings and sidewalk
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (35, 38, 46) # Dark asphalt

        # Sidewalk
        cv2.rectangle(frame, (0, 100), (width, 200), (60, 65, 75), -1)
        cv2.line(frame, (0, 200), (width, 200), (120, 130, 140), 2)

        # Dashed lane divider
        for x in range(0, width, 50):
            cv2.line(frame, (x, 325), (x + 30, 325), (255, 255, 255), 2)

        # Bottom curb
        cv2.rectangle(frame, (0, 440), (width, 500), (60, 65, 75), -1)

        # Update and draw moving objects
        for obj in objects:
            obj["x"] += obj["vx"]
            obj["y"] += obj["vy"]

            # Wrap around boundaries
            if obj["vx"] > 0 and obj["x"] > width:
                obj["x"] = -obj["w"]
            elif obj["vx"] < 0 and obj["x"] < -obj["w"]:
                obj["x"] = width

            x1 = int(obj["x"])
            y1 = int(obj["y"])
            x2 = x1 + obj["w"]
            y2 = y1 + obj["h"]

            # Draw body
            cv2.rectangle(frame, (x1, y1), (x2, y2), obj["color"], -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

            # Details: wheels / head
            if obj["label"] == "car":
                # Car windows
                cv2.rectangle(frame, (x1 + 20, y1 + 8), (x2 - 20, y1 + 25), (180, 220, 240), -1)
                # Wheels
                cv2.circle(frame, (x1 + 20, y2), 8, (20, 20, 20), -1)
                cv2.circle(frame, (x2 - 20, y2), 8, (20, 20, 20), -1)
            elif obj["label"] == "person":
                # Head
                cv2.circle(frame, (int((x1 + x2) / 2), y1 - 10), 10, (230, 200, 180), -1)

        # Overlay timestamp and simulated camera watermark
        cv2.putText(frame, f"CAM-01 [LIVE] FRAME: {frame_idx:04d}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 2)

        out.write(frame)

    out.release()
    print(f"Generated synthetic surveillance video at: {output_path} ({total_frames} frames)")
    return output_path


if __name__ == "__main__":
    out_file = Path(__file__).parent / "sample_traffic.mp4"
    generate_synthetic_surveillance_video(out_file)
