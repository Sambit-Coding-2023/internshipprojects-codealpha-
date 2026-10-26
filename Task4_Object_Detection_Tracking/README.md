# Task 4: Intelligent Real-Time Object Detection & Multi-Object Tracking Studio

An advanced Computer Vision and Intelligent Video Analytics (IVA) system for real-time multi-object detection, trajectory tracking, speed estimation, virtual tripwire counting, and zone intrusion detection.

Powered by **YOLOv8** (Single-Stage CSPDarknet + PANet), **7D Kalman Filtering**, and the **Hungarian Algorithm (SORT)**.

---

## Key Highlights & Capabilities

- **Deep Neural Object Detection**: Powered by Ultralytics YOLOv8n with support for 80 COCO benchmark classes, confidence tuning, and rapid class-category filtering (Vehicles, Pedestrians, Traffic, Common Items).
- **SORT Multi-Object Tracking**: Continuous tracking with 7D Kalman state estimation ($[u, v, s, r, \dot{u}, \dot{v}, \dot{s}]^T$) and minimum-cost linear assignment (Hungarian Algorithm) over bounding box Intersection-over-Union (IoU).
- **Velocity & Heading Vectors**: Estimates real-time object velocity ($v_x, v_y$), speed ($km/h$), and 8-point compass heading direction (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`) with directional velocity arrows.
- **Bi-Directional Virtual Tripwire (Line Crossing)**: Configurable counting line that detects when tracked objects traverse across the tripwire, maintaining persistent `IN` and `OUT` counters.
- **Surveillance Zone Intrusion (ROI)**: User-defined Region of Interest monitoring zone with entry/exit tracking, intruder counts, and visual hazard warnings.
- **Motion Density Heatmap**: Dynamic 2D Gaussian thermal density accumulator overlaid onto live video displaying high-traffic and dwell zones over time.
- **Dual Execution Modes**:
  1. **Web Vision Studio (`app.py`)**: Cyber-surveillance command console on port 5003 with live MJPEG streaming, interactive parameter sliders, web audio chimes, static image inspector, and audit log exports.
  2. **Desktop OpenCV CLI (`run_video.py`)**: Hardware-accelerated desktop player with keyboard shortcuts, MP4 export, and CSV telemetry logging.
- **Static Image Inspector**: Dedicated image analysis tab allowing users to drag-and-drop or upload any image to extract bounding box coordinates, confidence scores, and detection tables.
- **Incident Audit Logging & CSV Export**: Real-time event log tracking all line-crossing and intrusion events, downloadable as CSV.

---

## System Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │          Video Stream Ingestion               │
                  │   (Real Traffic / Synthetic / Webcam / MP4)   │
                  └──────────────────────┬────────────────────────┘
                                         │
                                [Frame Decimation]
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         [YOLOv8 Object Detector]                 [Kalman Filter Predictor]
         • Backbone: CSPDarknet                   • State: [u, v, s, r, u', v', s']
         • Neck: PANet Feature Pyramid            • State Extrapolation: x_k|k-1 = F * x
         • 80 COCO Classes / Filters              • Covariance Prediction: P = F P F^T + Q
                    │                                         │
             Detector Boxes                             Track Projections
                    └────────────────────┬────────────────────┘
                                         ▼
                        [Hungarian Data Association]
                        • Cost Matrix: C_ij = -IoU(det_i, trk_j)
                        • Linear Sum Assignment (min cost)
                        • Threshold Gating (IoU >= 0.3)
                                         │
                                         ▼
                           [Active Track Lifecycle]
                        • Kalman Measurement Update (H, R)
                        • Instantaneous Velocity (u', v')
                        • Speed (km/h) & Heading Angle
                        • Dwell Time & Hit Streak Tracking
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         [Virtual Tripwire & ROI]                    [Thermal Density Heatmap]
         • Vector Line Crossing (IN / OUT)           • 2D Gaussian Splatting
         • Polygon Zone Intrusion Test               • Exponential Decay Factor
         • Real-Time Incident Logging                • Turbo / Jet Colormap Blend
                    └────────────────────┬────────────────────┘
                                         ▼
                           [Cyber Visualizer Engine]
                        • Corner Bracket Bounding Boxes
                        • Persistent Track ID & Speed Pills
                        • Fading Gradient Trajectory Trails
                        • Velocity Vector Direction Arrows
                        • Top Telemetry Information HUD
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
          [MJPEG Web Console]                       [Desktop Video Exporter]
            (Port 5003 Flask)                         (OpenCV / CSV Telemetry)
```

---

## Mathematical Formulation

### 1. Kalman Filter State Representation
Each tracked bounding box is modeled by a 7-dimensional continuous state vector:
$$\mathbf{x} = \begin{bmatrix} u & v & s & r & \dot{u} & \dot{v} & \dot{s} \end{bmatrix}^T$$
where:
- $(u, v)$ denotes the 2D pixel coordinates of the bounding box center.
- $s = w \times h$ represents the bounding box scale (area).
- $r = w / h$ is the bounding box aspect ratio (assumed approximately constant during tracking).
- $(\dot{u}, \dot{v}, \dot{s})$ represent the respective velocities.

The measurement vector $\mathbf{z}$ contains the directly observed detector outputs:
$$\mathbf{z} = \begin{bmatrix} u & v & s & r \end{bmatrix}^T$$

### 2. Velocity and Direction Estimation
Instantaneous velocity magnitude $V$ in pixels per frame:
$$V = \sqrt{\dot{u}^2 + \dot{v}^2}$$
Heading orientation $\theta$:
$$\theta = \text{atan2}(-\dot{v}, \dot{u})$$
Mapped to 8-point compass sectors (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`).

### 3. Virtual Tripwire Line Crossing
Given a virtual horizontal counting line at $y = y_{line}$:
A crossing event is registered when consecutive trajectory centroids $(x_{t-1}, y_{t-1})$ and $(x_t, y_t)$ satisfy:
$$\text{Direction} = \begin{cases} \text{IN} (\downarrow) & \text{if } y_{t-1} < y_{line} \le y_t \\ \text{OUT} (\uparrow) & \text{if } y_{t-1} > y_{line} \ge y_t \end{cases}$$

---

## Directory Structure

```
Task4_Object_Detection_Tracking/
├── models/
│   └── yolov8n.pt               # YOLOv8 neural network weights
├── sample_media/
│   ├── real_traffic.mp4         # Real surveillance traffic footage
│   ├── sample_traffic.mp4       # Pre-generated synthetic traffic video
│   ├── bus.jpg                  # Sample test image for image inspector
│   └── create_sample_video.py   # Procedural traffic video generator
├── outputs/
│   ├── tracked_output.mp4       # Exported annotated video file
│   └── tracking_telemetry.csv   # Frame-by-frame tracking telemetry
├── src/
│   ├── __init__.py
│   ├── detector.py              # YOLOv8 detector with category presets & image mode
│   ├── sort_tracker.py          # Kalman Filter, Hungarian matching, Tripwire & ROI
│   └── visualizer.py            # Sci-Fi corner boxes, velocity arrows, heatmaps & HUD
├── static/
│   ├── css/style.css            # Cyber-surveillance glassmorphism UI theme
│   └── js/app.js                # Web controller, audio alerts, image analyzer & telemetry
├── templates/
│   └── index.html               # Multi-tab monitoring studio dashboard
├── tests/
│   └── test_tracking.py         # Complete pytest test suite (9 test cases)
├── app.py                       # Flask streaming server (Port 5003)
├── run_video.py                 # Desktop OpenCV video runner & exporter
├── requirements.txt             # Dependency manifest
└── README.md                    # Technical documentation
```

---

## Quickstart Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Vision Studio
```bash
python app.py
```
Open **`http://localhost:5003`** in your browser.

**Features in Web Console:**
- **Live Stream Tab**:
  - Switch feeds: *Real Traffic*, *Synthetic Sim*, *Live Webcam*, or *Upload MP4*.
  - Class filter pills: *All COCO*, *Vehicles*, *Pedestrians*, *Traffic Scene*, *Common Items*.
  - Live toggles: Bounding Boxes, Trajectory Trails, Speed Vectors, Virtual Tripwire, Surveillance Zone, Motion Heatmap.
  - Interactive Tripwire Position slider.
  - Audio chimes for line-crossing events.
  - Snapshot button for instant JPEG downloads.
- **Image Inspector Tab**:
  - Drop or upload any image, or click *"Load Sample Street Scene"*.
  - View detection boxes, inference latency ($ms$), and coordinate table.
- **Incident Audit Log Tab**:
  - View full history of line crossings and zone intrusions.
  - One-click CSV export.

---

### 3. Run Desktop CLI Tracking (OpenCV Player)
```bash
# Run real traffic sample
python run_video.py --source real --max_frames 200

# Run with density heatmap overlay and export telemetry CSV
python run_video.py --source real --heatmap --export-csv outputs/telemetry.csv

# Filter specific classes only (e.g. cars and persons)
python run_video.py --source real --classes car person

# Run live webcam tracking
python run_video.py --source 0
```

#### Desktop Keyboard Shortcuts
| Key | Action |
|:---:|:---|
| `q` | Quit application |
| `p` | Pause / Resume video playback |
| `s` | Capture and save frame snapshot |
| `t` | Toggle motion trajectory trails |
| `b` | Toggle bounding boxes and labels |
| `h` | Toggle motion density heatmap |
| `l` | Toggle virtual tripwire line |
| `z` | Toggle surveillance monitoring zone |

---

## Automated Test Suite

Run the full unit and integration test suite:
```bash
python -m pytest tests/test_tracking.py -v
```

**Coverage:**
- Detector initialization & COCO presets
- Single-image detection & timing
- Kalman filter state conversions & velocity
- Batch IoU computation
- Compass heading angle calculations
- Hungarian linear sum assignment association
- Tripwire bi-directional line-crossing events
- Flask API routes (`/api/stats`, `/api/settings`, `/api/export_events`)

---

## API Reference

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/video_feed` | `GET` | Multipart MJPEG real-time annotated video stream |
| `/api/stats` | `GET` | Returns JSON of live FPS, active objects, tripwire counts, and recent events |
| `/api/settings` | `POST` | Updates pipeline settings (source, thresholds, class filters, layer toggles) |
| `/api/upload` | `POST` | Uploads a custom video file (`.mp4`, `.avi`, `.mov`, `.webm`) |
| `/api/detect_image` | `POST` | Runs single-image YOLOv8 inference and returns annotated base64 image + detections |
| `/api/snapshot` | `GET` | Downloads current annotated frame as a high-resolution JPEG |
| `/api/export_events` | `GET` | Downloads all line-crossing and intrusion events as a CSV file |
| `/api/clear_events` | `POST` | Clears the incident event log |
