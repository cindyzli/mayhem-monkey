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
RESULTS_FILE = BASE_DIR / "results" / "scan_results.json"

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

@app.route("/start", methods=["POST"])
def start():
    return jsonify({
        "capture": _start_script("capture", CAPTURE_SCRIPT),
        "open_url": _start_script("open_url", OPEN_URL_SCRIPT),
    })


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
    if not RESULTS_FILE.exists():
        return jsonify({"status": "pending", "message": "No results yet"}), 202
    try:
        with open(RESULTS_FILE) as f:
            data = json.load(f)
        return jsonify({"status": "complete", "data": data})
    except (json.JSONDecodeError, OSError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# --- Scanner (attacker/gemini_router.py) endpoints ---

@app.route("/scan/start", methods=["POST"])
def scan_start():
    """Launch the Gemini chaos scanner for a given URL."""
    body = request.get_json(force=True) or {}
    url = body.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400

    # Remove stale results so the frontend knows the new scan is in progress
    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()

    proc = _processes.get("scanner")
    if proc and proc.poll() is None:
        return jsonify({"status": "already_running", "pid": proc.pid})

    proc = subprocess.Popen(
        [sys.executable, SCANNER_SCRIPT, url],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _processes["scanner"] = proc
    return jsonify({"status": "started", "pid": proc.pid})


@app.route("/scan/status", methods=["GET"])
def scan_status():
    """Check whether the scanner is still running and whether results exist."""
    proc = _processes.get("scanner")
    running = proc is not None and proc.poll() is None
    return jsonify({
        "running": running,
        "has_results": RESULTS_FILE.exists(),
    })


@app.route("/scan/stop", methods=["POST"])
def scan_stop():
    """Kill a running scanner."""
    return jsonify(_stop_script("scanner"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
