"""REST API: auth, analysis jobs, demo clip, stats, exports."""
from __future__ import annotations

import csv
import io
import threading
import traceback
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import config
from backend import db

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------
def _uid() -> int:
    """User id from the Authorization header OR a ?token= query param.

    Media tags (<video>, <img>) cannot send headers, so file routes accept
    the JWT in the query string as well. Header is preferred.
    """
    from flask_jwt_extended import get_jwt_identity as _get

    try:
        return int(_get())
    except Exception:
        pass
    token = request.args.get("token", "")
    if not token:
        raise Exception("Missing token")
    import jwt as _jwt

    payload = _jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"],
                          options={"verify_exp": False})
    return int(payload["sub"])


def _auth_file_route(fn):
    """Decorator for file routes: JWT via header or ?token= (no 401 page)."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            uid = _uid()
        except Exception:
            return jsonify(error="Authentication required."), 401
        return fn(uid, *args, **kwargs)

    return wrapper
@api_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if len(name) < 2:
        return jsonify(error="Please enter your name (at least 2 characters)."), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Please enter a valid email address."), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters."), 400
    try:
        uid = db.create_user(name, email, generate_password_hash(password))
    except Exception:
        return jsonify(error="An account with this email already exists."), 409
    user = db.get_user_by_id(uid)
    token = create_access_token(identity=str(uid))
    return jsonify(user={"id": uid, "name": user["name"], "email": user["email"]},
                   token=token), 201


@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = db.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Invalid email or password."), 401
    token = create_access_token(identity=str(user["id"]))
    return jsonify(user={"id": user["id"], "name": user["name"], "email": user["email"]},
                   token=token)


@api_bp.get("/auth/me")
@jwt_required()
def me():
    user = db.get_user_by_id(int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found."), 404
    return jsonify(user={"id": user["id"], "name": user["name"], "email": user["email"]})


# ---------------------------------------------------------------------------
# demo clip
# ---------------------------------------------------------------------------
@api_bp.post("/demo/generate")
@jwt_required()
def demo_generate():
    demo_path = config.UPLOAD_DIR / "demo_clip.mp4"
    info = {"cached": demo_path.exists()}
    if not demo_path.exists():
        from backend.ml.demo import build_demo_clip

        try:
            info = build_demo_clip(demo_path)
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503
        except Exception as exc:  # pragma: no cover
            return jsonify(error=f"Could not build demo clip: {exc}"), 500
    else:
        from backend.ml.demo import LIGHT_CYCLE, STOP_LINE_Y

        info.update({
            "file": demo_path.name, "cached": True, "width": 720, "height": 960,
            "fps": 25, "seconds": 10,
            "note": "Built-in demo clip (cached). Real photo, simulated camera pan.",
            "light_cycle": LIGHT_CYCLE, "stop_line_y": STOP_LINE_Y,
            "recommended_config": config.DEMO_CONFIG,
        })
    return jsonify(info)


@api_bp.get("/demo/file")
@_auth_file_route
def demo_file(uid: int):
    demo_path = config.UPLOAD_DIR / "demo_clip.mp4"
    if not demo_path.exists():
        return jsonify(error="Demo clip not generated yet."), 404
    return send_file(demo_path, mimetype="video/mp4", conditional=True)


# ---------------------------------------------------------------------------
# analysis jobs
# ---------------------------------------------------------------------------
def _run_job(job_id: str, video_path: Path, cfg: dict, out_path: Path,
             evidence_dir: Path) -> None:
    from backend.ml.engine import TrafficAnalyzer

    try:
        db.set_job_status(job_id, "processing", 1)
        analyzer = TrafficAnalyzer(cfg)
        result = analyzer.analyze(
            video_path, out_path, evidence_dir,
            on_progress=lambda p: db.set_job_progress(job_id, p),
        )
        result["output_video"] = str(out_path.relative_to(config.BASE_DIR))
        result["evidence_dir"] = str(evidence_dir.relative_to(config.BASE_DIR))
        db.finish_job(job_id, result)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        traceback.print_exc()
        db.fail_job(job_id, f"{type(exc).__name__}: {exc}")


@api_bp.post("/analyze")
@jwt_required()
def analyze():
    uid = int(get_jwt_identity())
    job_id = uuid.uuid4().hex[:12]

    try:
        cfg = json.loads(request.form.get("config") or "{}")
    except Exception:
        return jsonify(error="Invalid config JSON."), 400

    if request.form.get("source") == "demo":
        # case 1: analyse the built-in demo clip
        demo_path = config.UPLOAD_DIR / "demo_clip.mp4"
        if not demo_path.exists():
            return jsonify(error="Generate the demo clip first (click 'Get demo clip')."), 400
        filename = "demo_clip.mp4"
        video_rel = str(demo_path.relative_to(config.BASE_DIR))
    else:
        # case 2: uploaded video
        upload = request.files.get("video")
        if upload is None or upload.filename == "":
            return jsonify(error="Please choose a video file to upload."), 400
        ext = Path(upload.filename).suffix.lower()
        if ext not in config.ALLOWED_VIDEO_EXTENSIONS:
            return jsonify(error=f"Unsupported file type '{ext}'. "
                                 f"Allowed: {', '.join(sorted(config.ALLOWED_VIDEO_EXTENSIONS))}"), 400
        safe = secure_filename(upload.filename)
        video_path = config.UPLOAD_DIR / f"{job_id}_{safe}"
        upload.save(video_path)
        filename = upload.filename
        video_rel = str(video_path.relative_to(config.BASE_DIR))

    out_path = config.OUTPUT_DIR / f"{job_id}_annotated.mp4"
    evidence_dir = config.EVIDENCE_DIR / job_id

    db.create_job(job_id, uid, filename, video_rel, cfg)
    threading.Thread(
        target=_run_job, args=(job_id, config.BASE_DIR / video_rel, cfg, out_path, evidence_dir),
        daemon=True, name=f"job-{job_id}",
    ).start()
    return jsonify(job_id=job_id, status="queued"), 202


@api_bp.get("/jobs")
@jwt_required()
def jobs():
    uid = int(get_jwt_identity())
    return jsonify(jobs=[db.job_to_dict(r, include_result=False)
                         for r in db.list_jobs(uid)])


@api_bp.get("/jobs/<job_id>")
@jwt_required()
def job_detail(job_id: str):
    uid = int(get_jwt_identity())
    row = db.get_job(job_id)
    if not row or row["owner_id"] != uid:
        return jsonify(error="Job not found."), 404
    return jsonify(job=db.job_to_dict(row, include_result=True))


@api_bp.get("/jobs/<job_id>/video")
@_auth_file_route
def job_video(uid: int, job_id: str):
    row = db.get_job(job_id)
    if not row or row["owner_id"] != uid:
        return jsonify(error="Job not found."), 404
    import json as _json
    result = _json.loads(row["result_json"]) if row["result_json"] else {}
    rel = result.get("output_video")
    if not rel:
        return jsonify(error="Annotated video is not ready yet."), 404
    path = db.project_path(rel)
    if not path.exists():
        return jsonify(error="Annotated video file is missing."), 404
    return send_file(path, mimetype="video/mp4", conditional=True)


@api_bp.get("/jobs/<job_id>/evidence/<name>")
@_auth_file_route
def job_evidence(uid: int, job_id: str, name: str):
    row = db.get_job(job_id)
    if not row or row["owner_id"] != uid:
        return jsonify(error="Job not found."), 404
    path = config.EVIDENCE_DIR / job_id / secure_filename(name)
    if not path.exists():
        return jsonify(error="Evidence frame not found."), 404
    return send_file(path, mimetype="image/jpeg")


@api_bp.get("/jobs/<job_id>/export.csv")
@_auth_file_route
def job_csv(uid: int, job_id: str):
    row = db.get_job(job_id)
    if not row or row["owner_id"] != uid:
        return jsonify(error="Job not found."), 404
    import json as _json
    result = _json.loads(row["result_json"]) if row["result_json"] else {}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["violation_id", "type", "label", "track_id", "vehicle",
                "timestamp_s", "frame", "speed_kmh", "detail"])
    for v in result.get("violations", []):
        w.writerow([v["id"], v["type"], v["label"], v["track_id"], v["vehicle"],
                    v["timestamp_s"], v["frame"], v["speed_kmh"], v["detail"]])
    resp = send_file(io.BytesIO(buf.getvalue().encode("utf-8")),
                     mimetype="text/csv", as_attachment=True,
                     download_name=f"violations_{job_id}.csv")
    return resp


@api_bp.get("/jobs/<job_id>/export.pdf")
@_auth_file_route
def job_pdf(uid: int, job_id: str):
    row = db.get_job(job_id)
    if not row or row["owner_id"] != uid:
        return jsonify(error="Job not found."), 404
    import json as _json
    result = _json.loads(row["result_json"]) if row["result_json"] else {}
    try:
        from backend.reports import build_report_pdf
    except ImportError:
        return jsonify(error="PDF reporting is unavailable (reportlab not installed)."), 501
    out = config.OUTPUT_DIR / f"report_{job_id}.pdf"
    build_report_pdf(job_id, row, result, out)
    return send_file(out, mimetype="application/pdf", as_attachment=True,
                     download_name=f"report_{job_id}.pdf")


# ---------------------------------------------------------------------------
# dashboard stats
# ---------------------------------------------------------------------------
@api_bp.get("/stats")
@jwt_required()
def stats():
    uid = int(get_jwt_identity())
    rows = db.list_jobs(uid, limit=200)
    done = [r for r in rows if r["status"] == "done"]
    total_vehicles = total_violations = total_violating = 0
    by_type: dict[str, int] = {}
    violating_by_type: dict[str, int] = {}
    by_class: dict[str, int] = {}
    merged_timeline: list[dict] = []
    for r in done:
        import json as _json
        res = _json.loads(r["result_json"]) if r["result_json"] else {}
        total_vehicles += int(res.get("total_vehicles", 0))
        total_violations += int(res.get("total_violations", 0))
        total_violating += int(res.get("total_violating_vehicles", 0))
        for k, val in (res.get("violating_vehicles_by_type") or {}).items():
            violating_by_type[k] = violating_by_type.get(k, 0) + int(val)
        for k, val in (res.get("vehicle_counts") or {}).items():
            by_class[k] = by_class.get(k, 0) + int(val)
        merged_timeline.append({
            "job": r["filename"], "created_at": r["created_at"],
            "violations": res.get("violations", [])[:50],
            "timeline": res.get("timeline", []),
        })
    return jsonify({
        "total_jobs": len(rows),
        "completed_jobs": len(done),
        "total_vehicles": total_vehicles,
        "total_violating_vehicles": total_violating,
        "total_violations": total_violations,
        "violations_by_type": by_type,
        "violating_vehicles_by_type": violating_by_type,
        "vehicles_by_class": by_class,
        "recent": [db.job_to_dict(r, include_result=False) for r in rows[:6]],
    })


# ---------------------------------------------------------------------------
# config presets
# ---------------------------------------------------------------------------
@api_bp.get("/presets")
@jwt_required()
def presets():
    return jsonify({
        "defaults": config.DEFAULT_CONFIG,
        "demo": config.DEMO_CONFIG,
    })


import json  # noqa: E402  (used in analyze())
