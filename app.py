"""
Flask API to start/stop capture.py (mic streaming) and open_url.py (voice listener).
"""

import json
import os
import subprocess
import sys
import signal
import pathlib

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = pathlib.Path(__file__).resolve().parent
CAPTURE_SCRIPT = str(BASE_DIR / "voice" / "capture.py")
OPEN_URL_SCRIPT = str(BASE_DIR / "voice" / "open_url.py")
SCANNER_SCRIPT = str(BASE_DIR / "attacker" / "gemini_router.py")
RESULTS_FILE = str(BASE_DIR / "results" / "scan_results.json")

# Track running subprocesses
_processes: dict[str, subprocess.Popen] = {}


def _start_script(name: str, script_path: str) -> dict:
    if name in _processes and _processes[name].poll() is None:
        return {"status": "already_running", "name": name, "pid": _processes[name].pid}

    proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _processes[name] = proc
    return {"status": "started", "name": name, "pid": proc.pid}


def _stop_script(name: str) -> dict:
    proc = _processes.get(name)
    if proc is None or proc.poll() is not None:
        _processes.pop(name, None)
        return {"status": "not_running", "name": name}

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    _processes.pop(name, None)
    return {"status": "stopped", "name": name}


def _script_status(name: str) -> dict:
    proc = _processes.get(name)
    if proc is None or proc.poll() is not None:
        return {"name": name, "running": False}
    return {"name": name, "running": True, "pid": proc.pid}


# --- Routes ---

def _launch_scanner(url: str) -> tuple[dict, int]:
    """Start the Gemini scanner subprocess."""
    print(f"[_launch_scanner] Received URL: {url!r}")
    clean_url = (url or "").strip()
    if not clean_url:
        return {"error": "url is required"}, 400
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    print(f"[_launch_scanner] Cleaned URL: {clean_url!r}")
    print(f"[_launch_scanner] Spawning: {sys.executable} {SCANNER_SCRIPT} {clean_url}")

    if os.path.exists(RESULTS_FILE):
        os.remove(RESULTS_FILE)

    proc = _processes.get("scanner")
    if proc and proc.poll() is None:
        return {"status": "already_running", "pid": proc.pid, "url": clean_url}, 200

    proc = subprocess.Popen(
        [sys.executable, SCANNER_SCRIPT, clean_url],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _processes["scanner"] = proc
    return {"status": "started", "pid": proc.pid, "url": clean_url}, 200


@app.route("/start", methods=["GET", "POST"])
def start():
    if request.method == "POST":
        # URL provided — launch scanner only, no mic needed
        body = request.get_json(silent=True) or {}
        scanner_status, code = _launch_scanner(body.get("url", ""))
        return jsonify({"scanner": scanner_status}), code

    # No URL — start voice pipeline (mic + listener) so user can speak a URL
    payload = {
        "capture": _start_script("capture", CAPTURE_SCRIPT),
        "open_url": _start_script("open_url", OPEN_URL_SCRIPT),
    }
    return jsonify(payload)


@app.route("/start/capture", methods=["POST"])
def start_capture():
    return jsonify(_start_script("capture", CAPTURE_SCRIPT))


@app.route("/start/open_url", methods=["POST"])
def start_open_url():
    return jsonify(_start_script("open_url", OPEN_URL_SCRIPT))


@app.route("/stop", methods=["POST"])
def stop():
    return jsonify({
        "capture": _stop_script("capture"),
        "open_url": _stop_script("open_url"),
    })


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "capture": _script_status("capture"),
        "open_url": _script_status("open_url"),
    })


@app.route("/results", methods=["GET"])
def results():
    if not os.path.exists(RESULTS_FILE):
        return jsonify({"status": "pending", "message": "No results yet"}), 202
    try:
        with open(RESULTS_FILE) as f:
            data = json.load(f)
            print(f"data: {data}")
        return jsonify({"status": "complete", "data": data}), 200
    except (json.JSONDecodeError, OSError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# --- Scanner (attacker/gemini_router.py) endpoints ---

@app.route("/scan/start", methods=["POST"])
def scan_start():
    """Launch the Gemini chaos scanner for a given URL."""
    body = request.get_json(force=True) or {}
    status, code = _launch_scanner(body.get("url", ""))
    return jsonify(status), code


@app.route("/scan/status", methods=["GET"])
def scan_status():
    """Check whether the scanner is still running and whether results exist."""
    proc = _processes.get("scanner")
    running = proc is not None and proc.poll() is None
    return jsonify({
        "running": running,
        "has_results": os.path.exists(RESULTS_FILE),
    })


@app.route("/scan/stop", methods=["POST"])
def scan_stop():
    """Kill a running scanner."""
    return jsonify(_stop_script("scanner"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
