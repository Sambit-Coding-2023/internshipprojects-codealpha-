"""API smoke test: register -> demo -> analyze -> poll -> files."""
import json
import time
import urllib.request

BASE = "http://127.0.0.1:5000"
EMAIL = "smoke@test.dev"


def call(path, token=None, body=None, method="POST"):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    # register (or login if already exists)
    try:
        reg = call("/api/auth/register", body={"name": "Smoke", "email": EMAIL, "password": "smoke123"})
    except Exception:
        reg = call("/api/auth/login", body={"email": EMAIL, "password": "smoke123"})
    token = reg["token"]
    print("auth OK:", reg["user"]["email"])

    info = call("/api/demo/generate", token=token)
    print("demo OK:", info.get("file"), "| cached:", info.get("cached"))

    # analyze demo with recommended config (multipart, single part field)
    import uuid
    boundary = "----" + uuid.uuid4().hex
    cfg = json.dumps(info["recommended_config"])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"\r\n\r\ndemo\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"config\"\r\n\r\n{cfg}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(BASE + "/api/analyze", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        job = json.loads(r.read().decode())
    print("job queued:", job)

    deadline = time.time() + 300
    while time.time() < deadline:
        detail = call(f"/api/jobs/{job['job_id']}", token=token, method="GET")
        j = detail["job"]
        print(f"  status={j['status']} progress={j['progress']}%")
        if j["status"] in ("done", "error"):
            break
        time.sleep(3)
    assert j["status"] == "done", f"job failed: {j['error']}"
    r = j["result"]
    print(f"results: vehicles={r['total_vehicles']} violations={r['total_violations']} {r['violation_counts']}")

    # file routes via ?token=
    for suffix in ("video", "export.csv", "export.pdf"):
        url = f"{BASE}/api/jobs/{job['job_id']}/{suffix}?token={token}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            payload = resp.read()
        print(f"{suffix}: HTTP 200, {len(payload)} bytes")

    stats = call("/api/stats", token=token, method="GET")
    print("stats OK:", stats["total_jobs"], "jobs,",
          stats["total_vehicles"], "vehicles,", stats["total_violations"], "violations")
    print("API SMOKE TEST OK")


if __name__ == "__main__":
    main()
