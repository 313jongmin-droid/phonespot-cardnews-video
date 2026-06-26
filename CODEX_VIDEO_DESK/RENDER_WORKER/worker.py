# -*- coding: utf-8 -*-
from __future__ import annotations

import atexit
import http.client
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"
RESULTS = ROOT / "CODEX_VIDEO_DESK" / "RESULTS"
URL_FILE = Path(__file__).resolve().parent / "panel_url.txt"
SAVED_URL = URL_FILE.read_text(encoding="utf-8-sig", errors="replace").strip() if URL_FILE.exists() else ""
SERVER = (os.environ.get("PHONESPOT_PANEL_URL") or SAVED_URL or "http://127.0.0.1:4901").rstrip("/")
# 로컬 패널이면 결과가 이미 RESULTS/<키>/ 에 있으므로 업로드/패키지 다운로드(=remote_ 폴더) 불필요
LOCAL_PANEL = ("127.0.0.1" in SERVER) or ("localhost" in SERVER)
WORKER_ID = os.environ.get("PHONESPOT_WORKER_ID") or socket.gethostname()
VERSION = "render-worker-v4"
INSTANCE_ID = uuid4().hex
PID_FILE = Path(os.environ["PHONESPOT_WORKER_PID_FILE"]) if os.environ.get("PHONESPOT_WORKER_PID_FILE") else None


def register_pid() -> None:
    if not PID_FILE:
        return
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="ascii")

    def cleanup() -> None:
        try:
            if PID_FILE.exists() and PID_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
                PID_FILE.unlink()
        except OSError:
            pass

    atexit.register(cleanup)


def readiness() -> dict:
    checks = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "node": shutil.which("node") or "",
        "npm": shutil.which("npm") or "",
        "remotion": str(SHORTS / "node_modules" / "@remotion" / "cli"),
        "ffmpeg": str(SHORTS / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe"),
        "disk_free_gb": round(shutil.disk_usage(ROOT).free / (1024 ** 3), 1),
    }
    issues: list[str] = []
    if sys.version_info < (3, 10):
        issues.append("Python 3.10 이상 필요")
    if not checks["node"]:
        issues.append("Node.js 없음")
    if not checks["npm"]:
        issues.append("npm 없음")
    if not Path(checks["remotion"]).exists():
        issues.append("Remotion 미설치")
    if not Path(checks["ffmpeg"]).exists():
        issues.append("FFmpeg 미설치")
    required_modules = {
        "edge_tts": "edge-tts",
        "PIL": "Pillow",
        "mutagen": "mutagen",
        "requests": "requests",
        "playwright": "Playwright",
    }
    for module, label in required_modules.items():
        if importlib.util.find_spec(module) is None:
            issues.append(f"{label} 미설치")
    browser_root = ROOT / ".playwright"
    if not any(browser_root.glob("chromium-*")):
        issues.append("Playwright Chromium 미설치")
    if not (SHORTS / "run_codex_casual.bat").exists():
        issues.append("영상 실행 파일 없음")
    if checks["disk_free_gb"] < 2:
        issues.append("저장 공간 2GB 미만")
    return {"ready": not issues, "issues": issues, "checks": checks}


def registration_payload(status: dict | None = None) -> dict:
    status = status or readiness()
    return {
        "worker_id": WORKER_ID,
        "name": socket.gethostname(),
        "root": str(ROOT),
        "version": VERSION,
        "instance_id": INSTANCE_ID,
        "capabilities": ["remotion"],
        **status,
    }


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
        request = urllib.request.Request(SERVER + f"/api/worker/package?job_id={urllib.parse.quote(job['id'])}")
        with urllib.request.urlopen(request, timeout=180) as response:
            target.write_bytes(response.read())
        safe_extract(target)


def _slug_in_folder(slug: str, folder_name: str) -> bool:
    # 경계 안전 매칭: slug 양옆을 "_"로 감싸 비교 -> "031"이 "0310_..."에 오매칭되지 않음.
    # 실제 폴더명(예: 20260622_031_..._codex_remotion, NN_label_preset_promo)에서
    # slug는 항상 "_"로 구분되는 세그먼트라 안전하다.
    return ("_" + slug + "_") in ("_" + folder_name + "_")


def snapshot_mp4s() -> dict:
    # 렌더 시작 직전 RESULTS의 모든 mp4 경로->mtime 스냅샷(결정적 결과 탐지용).
    snap: dict = {}
    if not RESULTS.exists():
        return snap
    for folder in RESULTS.iterdir():
        try:
            if folder.is_dir():
                for mp4 in folder.glob("*.mp4"):
                    try:
                        snap[str(mp4)] = mp4.stat().st_mtime
                    except OSError:
                        pass
        except OSError:
            pass
    return snap


def result_after(slug: str, started: float, before: dict | None = None) -> Path | None:
    # 우선순위: 스냅샷(before) 대비 '신규/갱신'된 mp4 -> 없으면 시간창 폴백.
    # slug 매칭은 경계 안전(_slug_in_folder). 동일 워커는 잡을 순차 실행하므로
    # 신규 diff가 곧 이번 렌더 산출물이다.
    if not RESULTS.exists():
        return None
    before = before or {}
    fresh: list[Path] = []
    fallback: list[Path] = []
    for folder in RESULTS.iterdir():
        try:
            if not (folder.is_dir() and _slug_in_folder(slug, folder.name)):
                continue
            for mp4 in folder.glob("*.mp4"):
                try:
                    mtime = mp4.stat().st_mtime
                except OSError:
                    continue
                if mtime >= started - 5:
                    fallback.append(mp4)
                prev = before.get(str(mp4))
                if prev is None or mtime > prev + 0.001:
                    fresh.append(mp4)
        except OSError:
            pass
    pool = fresh or fallback
    return max(pool, key=lambda path: path.stat().st_mtime) if pool else None


def upload_result(job_id: str, path: Path) -> None:
    parsed = urllib.parse.urlsplit(SERVER)
    connection_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(parsed.hostname, parsed.port, timeout=600)
    base_path = parsed.path.rstrip("/")
    request_path = f"{base_path}/api/worker/result?job_id={urllib.parse.quote(job_id)}"
    total = path.stat().st_size
    sent = 0
    progress_step = 0
    try:
        connection.putrequest("POST", request_path)
        connection.putheader("Content-Type", "video/mp4")
        connection.putheader("X-File-Name", path.name)
        connection.putheader("Content-Length", str(total))
        connection.endheaders()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                connection.send(chunk)
                sent += len(chunk)
                next_step = min(10, int(sent * 10 / total)) if total else 10
                if next_step > progress_step:
                    progress_step = next_step
                    send_log(job_id, f"[UPLOAD] {next_step * 10}% ({sent}/{total} bytes)\n")
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            detail = body.decode("utf-8", errors="replace")
            raise RuntimeError(f"result upload failed: HTTP {response.status} {detail}")
    finally:
        connection.close()


def commands_for(job: dict) -> list[list[str]]:
    slug = job["slug"]
    if job["action"] == "video_import_render":
        return [
            ["python", str(SHORTS / "scripts" / "codex_import_downloads.py")],
            ["cmd", "/c", str(SHORTS / "run_codex_casual.bat"), slug],
        ]
    if job["action"] == "video_render_selected":
        return [["cmd", "/c", str(SHORTS / "run_codex_casual.bat"), slug]]
    if job["action"] == "promo_render":
        # slug = "{NN}_{label}_{preset}" -> num=int(NN), preset=마지막 토큰
        parts = slug.split("_")
        num = str(int(parts[0]))
        preset = parts[-1]
        return [["cmd", "/c", str(SHORTS / "run_promo.bat"), num, preset]]
    raise RuntimeError(f"unsupported worker action: {job['action']}")


def run_job(job: dict) -> tuple[bool, int, str]:
    job_id = job["id"]
    slug = job["slug"]
    heartbeat_stop = threading.Event()
    cancel_requested = threading.Event()

    def heartbeat_loop() -> None:
        while not heartbeat_stop.wait(5):
            try:
                json_request("/api/worker/register", registration_payload(), 10)
                check = json_request("/api/worker/check", {
                    "worker_id": WORKER_ID,
                    "job_id": job_id,
                }, 10)
                if check.get("cancel_requested"):
                    cancel_requested.set()
            except Exception:
                pass

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    send_log(job_id, f"[WORKER] {WORKER_ID}\n[DOWNLOAD] {slug}\n")
    try:
        if not LOCAL_PANEL:
            download_package(job)
        before_mp4s = snapshot_mp4s()
        started = time.time()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        env["PHONESPOT_NO_PAUSE"] = "1"
        commands = commands_for(job)
        for index, command in enumerate(commands, 1):
            send_log(job_id, f"\n----- worker command {index} -----\n{' '.join(command)}\n")
            # (2026-06) 렌더 직전: 공유 허브와 양방향 동기화.
            #   - 허브에서 최신 일러스트 pull(다른 PC가 올린 그림 반영)
            #   - 직전 단계(가져오기)에서 새로 들어온 그림은 push
            # best-effort: 허브 미설정/접근불가/오류여도 잡을 실패시키지 않는다(조용히 건너뜀).
            if "run_codex_casual" in " ".join(command):
                try:
                    sp = subprocess.run(
                        ["python", str(SHORTS / "scripts" / "codex_library_sync.py")],
                        cwd=str(SHORTS), text=True, encoding="utf-8", errors="replace",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=900,
                    )
                    send_log(job_id, "\n----- 렌더 전 라이브러리 동기화 -----\n" + (sp.stdout or ""))
                except Exception as exc:
                    send_log(job_id, f"\n[lib_sync] 동기화 건너뜀(무해): {exc}\n")
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
            def cancel_monitor() -> None:
                cancel_requested.wait()
                if process.poll() is None:
                    process.terminate()

            monitor = threading.Thread(target=cancel_monitor, daemon=True)
            monitor.start()
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
            if cancel_requested.is_set():
                return False, 96, "cancelled by user"
            if exit_code:
                return False, exit_code, f"command {index} failed"
        result = result_after(slug, started, before_mp4s)
        if not result:
            return False, 1, "render completed but result mp4 was not found"
        if LOCAL_PANEL:
            send_log(job_id, f"[LOCAL] 결과 보관: {result.name} (업로드/remote 폴더 생성 생략)\n")
        else:
            send_log(job_id, f"[UPLOAD] {result.name}\n")
            upload_result(job_id, result)
        return True, 0, result.name
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1)


def main() -> int:
    register_pid()
    print("=" * 60)
    print("PhoneSpot Render Worker")
    print("=" * 60)
    print(f"Worker : {WORKER_ID}")
    print(f"Panel  : {SERVER}")
    print(f"Root   : {ROOT}")
    last_issues: tuple[str, ...] | None = None
    while True:
        try:
            status = readiness()
            issues = tuple(status["issues"])
            if issues != last_issues:
                if issues:
                    print("[setup required] " + ", ".join(issues))
                else:
                    print("[ready] render dependencies passed")
                last_issues = issues
            json_request("/api/worker/register", registration_payload(status))
            if not status["ready"]:
                time.sleep(5)
                continue
            response = json_request("/api/worker/claim", {
                "worker_id": WORKER_ID,
                "instance_id": INSTANCE_ID,
            })
            job = response.get("job")
            if not job:
                time.sleep(1)
                continue
            print(f"[claim] {job['id']} {job['action']} {job['slug']}")
            try:
                ok, exit_code, message = run_job(job)
            except Exception as exc:
                ok, exit_code, message = False, 99, f"worker exception: {exc}"
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
