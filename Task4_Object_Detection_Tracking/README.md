# TrafficGuard AI — Traffic Violation Detection & Tracking

Upload **real traffic video**, and the system counts how many vehicles violate
traffic rules — **overspeeding, red-light jumping, wrong-way driving and
no-helmet riding** — using **YOLOv8 + ByteTrack + OpenCV** behind a
Flask API, with a polished dark web UI.

## Try it in 60 seconds

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000  ->  create an account  ->  click
# "▶ Get built-in demo clip"  ->  "🚦 Run AI detection"
```

The first run downloads `yolov8n.pt` (~6 MB) and a real sample road photo
(supplying the demo clip) once; everything after that works offline.

## How it works

```
video ──► YOLOv8 detection (car/bus/truck/motorcycle/bicycle/person/traffic light)
        ──► ByteTrack  (stable per-vehicle track IDs)
        ──► centroid motion × px-per-metre × fps  =  speed (km/h)
        ──► rule engines (FULLY AUTOMATIC by default, no drawing needed):
              overspeed   speed > your limit, scale auto-calibrated from
                          detected car widths (avg. car ≈ 1.8 m wide)
              red light   traffic-light colour read from the video;
                          stop line auto-placed at the light
              wrong way   allowed flow = where most vehicles move;
                          opposite movers are flagged
              helmet      rider on a motorcycle whose head region shows
                          no helmet-coloured dome (colour heuristic)
        ──► manual-zone mode still available: draw stop line + flow arrow
            and set the light cycle yourself
        ──► annotated video + evidence stills + violation log + CSV/PDF
```

## Features

- **Accounts** (register/login, JWT, per-user analysis history)
- **Upload** drag-&-drop MP4/AVI/MOV/MKV/WEBM up to 200 MB, or use the
  built-in demo clip
- **Scene calibration**: draw the stop line and allowed-direction arrow on
  the video itself; tune speed limit, pixels-per-metre and confidence
- **Results**: annotated video (boxes, IDs, speeds, live light state),
  KPI cards, charts, timestamped violation log, evidence frames, CSV + PDF
- **Dashboard**: totals, violations by type, vehicles by class, recent runs
- **Guide page** explaining the pipeline and its honest limits

## Project structure

```
app.py                  Flask entrypoint (serves API + frontend)
config.py               paths, defaults, demo preset
backend/
  api.py                REST API (auth, jobs, analysis, exports, stats)
  db.py                 SQLite users + jobs
  reports.py            PDF report (reportlab)
  ml/
    engine.py           YOLOv8 + ByteTrack + speed + 4 violation detectors
    demo.py             demo clip builder (real photo + simulated pan)
frontend/               SPA (index.html, css/style.css, js/app.js)
scripts/smoke_test.py   end-to-end CLI test: demo clip -> report
tests/test_engine.py    unit tests for speed / light clock / crossing / helmet
uploads/ outputs/ evidence/ assets/ instance/   created at runtime
```

## API

| Method | Route | Auth | What it does |
|---|---|---|---|
| POST | `/api/auth/register` · `/api/auth/login` | – | account + JWT |
| GET | `/api/auth/me` | JWT | current user |
| POST | `/api/analyze` | JWT | multipart `video` + `config` JSON → `202 {job_id}` (async) |
| POST | `/api/demo/generate` | JWT | build/return demo clip + recommended config |
| GET | `/api/jobs` · `/api/jobs/<id>` | JWT | list / detail (polled for progress) |
| GET | `/api/jobs/<id>/video` · `/evidence/<f>` | JWT* | annotated video / evidence stills |
| GET | `/api/jobs/<id>/export.csv` · `export.pdf` | JWT* | downloads |
| GET | `/api/stats` · `/api/presets` | JWT | dashboard aggregates / config |

\* file routes accept the JWT as `?token=` because `<video>`/`<img>` tags
cannot send `Authorization` headers.

Analysis `config` shape:

```json
{
  "auto_mode": true,
  "ppm_mode": "auto",
  "speed_limit_kmh": 50,
  "pixels_per_meter": 1.0,
  "conf": 0.4,
  "violations": {"overspeed": true, "red_light": true, "wrong_way": true, "helmet": true},
  "stop_line": null,
  "allowed_direction": null,
  "light_cycle": null
}
```

In `auto_mode` only `speed_limit_kmh`, `conf` and the violation toggles
matter — everything else is inferred from the footage. In manual mode
(`auto_mode: false`) you must supply `stop_line` / `allowed_direction` /
`light_cycle` as drawn in the UI; `ppm_mode: "manual"` then uses
`pixels_per_meter`. Coordinates are normalised 0–1.

## Tests

```bash
python -m pytest tests/ -q        # pure-logic unit tests (no model)
python scripts/smoke_test.py      # full ML run on the demo clip
python app.py  # then, in another terminal:
python scripts/api_smoke_test.py  # HTTP API end-to-end (auth, jobs, files)
```

## Honest limitations

- **Speed** is only as good as your `pixels_per_meter` calibration — measure
  a known road length in your footage and divide its pixel length by metres.
  In automatic mode the scale is estimated from detected car widths
  (avg. car ≈ 1.8 m); switch to manual mode for precise calibration.
- **Automatic red-light detection** needs the traffic light to be visible
  and large enough in the footage for colour reading; if no light is ever
  seen, that rule stays off (check the annotated video's HUD) — fall back
  to manual mode.
- The **traffic-light clock** (manual mode only) is user-defined.
- **Helmet** detection uses a colour heuristic on the rider's head region —
  indicative, not certified. Motorcycle + rider overlap is required.
- The **demo clip** uses a real road photograph with simulated camera motion
  so the full pipeline runs on real detections without needing a sample
  video upload; production footage should be real video.

## Tech

Python · Flask · Ultralytics YOLOv8 · ByteTrack · OpenCV · SQLite ·
reportlab · Vanilla HTML/CSS/JS · Chart.js
