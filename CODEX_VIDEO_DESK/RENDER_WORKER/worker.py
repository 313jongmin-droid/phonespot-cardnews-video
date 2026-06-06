# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"
RESULTS = ROOT / "CODEX_VIDEO_DESK" / "RESULTS"
URL_FILE = Path(__file__).resolve().parent / "panel_url.txt"
SAVED_URL = URL_FILE.read_text(encoding="utf-8-sig", errors="replace").strip() if URL_FILE.exists() else ""
SERVER = (os.environ.get("PHONESPOT_PANEL_URL") or SAVED_URL or "http://127.0.0.1:4901").rstrip("/")
WORKER_ID = os.environ.get("PHONESPOT_WORKER_ID") or socket.gethostname()
VERSION = "render-worker-v1"


def json_request(path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    body = None
    headers = {}
    method = "GET"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(SERVER + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def send_log(job_id: str, text: str) -> None:
    try:
        json_request("/api/worker/log", {"job_id": job_id, "worker_id": WORKER_ID, "text": text}, 10)
    except Exception:
        pass


def safe_extract(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            name = member.filename.replace("\\", "/")
            if name == "remote_job.json":
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError(f"unsafe package path: {name}")
            target = ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not member.is_dir():
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def download_package(job: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="phonespot_render_") as temp:
        target = Path(temp) / "job.zip"
        with urllib.request.urlopen(SERVER + f"/api/worker/package?job_id={urllib.parse.quote(job['id'])}", timeout=180) as response:
            target.write_bytes(response.read())
        safe_extract(target)


def result_after(slug: str, started: float) -> Path | None:
    if not RESULTS.exists():
        return None
    candidates = []
    for folder in RESULTS.iterdir():
        try:
            if folder.is_dir() and slug in folder.name and folder.stat().st_mtime >= started - 5:
                candidates.extend(folder.glob("*.mp4"))
        except OSError:
            pass
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def upload_result(job_id: str, path: Path) -> None:
    request = urllib.request.Request(
        SERVER + f"/api/worker/result?job_id={urllib.parse.quote(job_id)}",
        data=path.read_bytes(),
        headers={"Content-Type": "video/mp4", "X-File-Name": path.name},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        response.read()


def commands_for(job: dict) -> list[list[str]]:
    slug = job["slug"]
    if job["action"] == "video_import_render":
        return [
            ["python", str(SHORTS / "scripts" / "codex_import_downloads.py")],
            ["cmd", "/c", str(SHORTS / "run_codex_casual.bat"), slug],
        ]
    if job["action"] == "video_render_selected":
        return [["cmd", "/c", str(SHORTS / "run_codex_casual.bat"), slug]]
    raise RuntimeError(f"unsupported worker action: {job['action']}")


def run_job(job: dict) -> tuple[bool, int, str]:
    job_id = job["id"]
    slug = job["slug"]
    heartbeat_stop = threading.Event()

    def heartbeat_loop() -> None:
        while not heartbeat_stop.wait(5):
            try:
                json_request("/api/worker/register", {
                    "worker_id": WORKER_ID,
                    "name": socket.gethostname(),
                    "root": str(ROOT),
                    "version": VERSION,
                    "capabilities": ["remotion"],
                }, 10)
            except Exception:
                pass

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    send_log(job_id, f"[WORKER] {WORKER_ID}\n[DOWNLOAD] {slug}\n")
    try:
        download_package(job)
        started = time.time()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        env["PHONESPOT_NO_PAUSE"] = "1"
        commands = commands_for(job)
        for index, command in enumerate(commands, 1):
            send_log(job_id, f"\n----- worker command {index} -----\n{' '.join(command)}\n")
            needs_confirmation = job["action"] == "video_import_render" and index == 1
            process = subprocess.Popen(
                command,
                cwd=str(SHORTS),
                stdin=subprocess.PIPE if needs_confirmation else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            if needs_confirmation and process.stdin is not None:
                process.stdin.write("Y\n")
                process.stdin.close()
            assert process.stdout is not None
            lines = []
            for line in process.stdout:
                lines.append(line)
                if len(lines) >= 8:
                    send_log(job_id, "".join(lines))
                    lines.clear()
            if lines:
                send_log(job_id, "".join(lines))
            exit_code = process.wait()
            if exit_code:
                return False, exit_code, f"command {index} failed"
        result = result_after(slug, started)
        if not result:
            return False, 1, "render completed but result mp4 was not found"
        send_log(job_id, f"[UPLOAD] {result.name}\n")
        upload_result(job_id, result)
        return True, 0, result.name
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1)


def main() -> int:
    print("=" * 60)
    print("PhoneSpot Render Worker")
    print("=" * 60)
    print(f"Worker : {WORKER_ID}")
    print(f"Panel  : {SERVER}")
    print(f"Root   : {ROOT}")
    while True:
        try:
            json_request("/api/worker/register", {
                "worker_id": WORKER_ID,
                "name": socket.gethostname(),
                "root": str(ROOT),
                "version": VERSION,
                "capabilities": ["remotion"],
            })
            response = json_request("/api/worker/claim", {"worker_id": WORKER_ID})
            job = response.get("job")
            if not job:
                time.sleep(3)
                continue
            print(f"[claim] {job['id']} {job['action']} {job['slug']}")
            ok, exit_code, message = run_job(job)
            json_request("/api/worker/complete", {
                "worker_id": WORKER_ID,
                "job_id": job["id"],
                "ok": ok,
                "exit_code": exit_code,
                "message": message,
            })
            print(f"[complete] ok={ok} exit={exit_code} {message}")
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"[wait] {exc}")
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
