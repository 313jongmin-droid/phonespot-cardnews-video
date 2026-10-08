# -*- coding: utf-8 -*-
"""원격 렌더 잡 큐 (패널 서버 프로세스 전용).

저장 구조 (2026-10 재설계):
- TEMP/remote_render_jobs.json / remote_render_workers.json = 상태 정본. 이 파일의 유일한 writer는
  패널 서버 프로세스 하나이므로 메모리 캐시를 정본으로 쓰고 디스크엔 기록만 한다.
- 잡 로그 전체 = TEMP/remote_logs/<job_id>.log (append-only). JSON엔 마지막 LOG_TAIL 자만 둔다.
  (과거: 끝난 잡 로그 전체가 JSON에 남아 2.2MB 파일을 로그 8줄마다 2회씩 통째 재기록했다.)
- 상태 변경(enqueue/claim/complete/cancel/retry/recover/결과저장) = 즉시 저장.
  로그 추가·heartbeat = dirty 표시 후 SAVE_INTERVAL 마다 백그라운드 플러시(크래시 시 최대 수 초 유실).
"""
from __future__ import annotations

import io
import json
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4


LOCK = threading.RLock()
WORKER_TTL_SECONDS = 20
JOB_LEASE_SECONDS = 90
MAX_RETRIES = 1
MAX_JOBS = 200
LOG_TAIL = 8000          # JSON에 남기는 로그 꼬리 길이(글자)
SAVE_INTERVAL = 2.0      # 비중요 변경 디스크 기록 최소 간격(초)


class RemoteQueue:
    def __init__(self, root: Path):
        self.root = root
        self.desk = root / "CODEX_VIDEO_DESK"
        self.cardnews = root / "cardnews"
        self.jobs_path = self.desk / "TEMP" / "remote_render_jobs.json"
        self.workers_path = self.desk / "TEMP" / "remote_render_workers.json"
        self.log_dir = self.desk / "TEMP" / "remote_logs"
        self.results = self.desk / "RESULTS"
        self._jobs: list[dict] | None = None
        self._workers: dict | None = None
        self._jobs_dirty = False
        self._workers_dirty = False
        self._jobs_saved_at = 0.0
        self._workers_saved_at = 0.0
        self._stop = threading.Event()
        self._flusher = threading.Thread(target=self._flush_loop, name="remote-queue-flush", daemon=True)
        self._flusher.start()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def now_epoch() -> float:
        return time.time()

    def _read(self, path: Path, fallback):
        if not path.exists():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return fallback

    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)

    def _log_path(self, job_id: str) -> Path:
        safe = "".join(ch for ch in str(job_id) if ch.isalnum()) or "unknown"
        return self.log_dir / f"{safe}.log"

    def _append_job_log(self, job: dict, text: str) -> None:
        """잡 로그 추가: 파일(전체, append) + JSON(꼬리)."""
        if not text:
            return
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path(job.get("id") or "").open("a", encoding="utf-8", errors="replace") as fh:
                fh.write(text)
        except OSError:
            pass
        job["log"] = ((job.get("log") or "") + text)[-LOG_TAIL:]

    # ----------------------------------------------------------- jobs storage
    def _load_jobs(self) -> list[dict]:
        if self._jobs is None:
            jobs = self._read(self.jobs_path, {"jobs": []}).get("jobs", []) or []
            migrated = False
            for job in jobs:
                log = job.get("log") or ""
                path = self._log_path(job.get("id") or "")
                if log and not path.exists():
                    try:
                        self.log_dir.mkdir(parents=True, exist_ok=True)
                        path.write_text(log, encoding="utf-8")
                    except OSError:
                        pass
                if len(log) > LOG_TAIL:
                    job["log"] = log[-LOG_TAIL:]
                    migrated = True
            self._jobs = jobs
            if migrated:
                self._save_jobs(force=True)
        return self._jobs

    def _save_jobs(self, force: bool = False) -> None:
        if self._jobs is None:
            return
        now = self.now_epoch()
        if not force and now - self._jobs_saved_at < SAVE_INTERVAL:
            self._jobs_dirty = True
            return
        self._write(self.jobs_path, {"version": 2, "updated_at": self.now(), "jobs": self._jobs})
        self._jobs_saved_at = now
        self._jobs_dirty = False

    # -------------------------------------------------------- workers storage
    def _load_workers(self) -> dict:
        if self._workers is None:
            self._workers = self._read(self.workers_path, {"workers": {}}).get("workers", {}) or {}
        return self._workers

    def _save_workers(self, force: bool = False) -> None:
        if self._workers is None:
            return
        now = self.now_epoch()
        if not force and now - self._workers_saved_at < SAVE_INTERVAL:
            self._workers_dirty = True
            return
        clean = {wid: {k: v for k, v in w.items() if k != "online"} for wid, w in self._workers.items()}
        self._write(self.workers_path, {"version": 1, "updated_at": self.now(), "workers": clean})
        self._workers_saved_at = now
        self._workers_dirty = False

    def flush(self) -> None:
        with LOCK:
            if self._jobs_dirty:
                self._save_jobs(force=True)
            if self._workers_dirty:
                self._save_workers(force=True)

    def _flush_loop(self) -> None:
        while not self._stop.wait(0.5):
            try:
                with LOCK:
                    now = self.now_epoch()
                    if self._jobs_dirty and now - self._jobs_saved_at >= SAVE_INTERVAL:
                        self._save_jobs(force=True)
                    if self._workers_dirty and now - self._workers_saved_at >= SAVE_INTERVAL:
                        self._save_workers(force=True)
            except Exception:
                pass

    # ------------------------------------------------------------- public API
    def jobs(self) -> list[dict]:
        with LOCK:
            return list(self._load_jobs())

    def workers(self) -> dict:
        with LOCK:
            workers = self._load_workers()
            now = self.now_epoch()
            for worker in workers.values():
                worker["online"] = now - float(worker.get("last_seen_epoch") or 0) <= WORKER_TTL_SECONDS
            return {wid: dict(w) for wid, w in workers.items()}

    def recover_stale_jobs(self) -> int:
        with LOCK:
            jobs = self._load_jobs()
            workers = self.workers()
            now = self.now_epoch()
            changed = 0
            for job in jobs:
                if job.get("status") != "running":
                    continue
                worker = workers.get(job.get("worker_id") or "", {})
                worker_online = bool(worker.get("online"))
                lease_at = float(job.get("lease_epoch") or 0)
                if worker_online and now - lease_at <= JOB_LEASE_SECONDS:
                    continue
                retries = int(job.get("retry_count") or 0)
                if retries < MAX_RETRIES:
                    job["status"] = "pending"
                    job["worker_id"] = ""
                    job["started_at"] = ""
                    job["retry_count"] = retries + 1
                    job["updated_at"] = self.now()
                    self._append_job_log(job, f"\n[RECOVERED] worker lease expired; retry {retries + 1}/{MAX_RETRIES}\n")
                else:
                    job["status"] = "failed"
                    job["exit_code"] = 97
                    job["message"] = "worker disconnected or stopped responding"
                    job["finished_at"] = self.now()
                    job["updated_at"] = self.now()
                    self._append_job_log(job, "\n[FAILED] worker lease expired\n")
                changed += 1
            if changed:
                self._save_jobs(force=True)
            return changed

    def online_workers(self) -> list[dict]:
        return [{"id": worker_id, **worker} for worker_id, worker in self.workers().items() if worker.get("online")]

    def enqueue(self, action: str, slug: str, target_worker: str = "") -> dict:
        with LOCK:
            jobs = self._load_jobs()
            for job in jobs:
                if job.get("slug") == slug and job.get("action") == action and job.get("status") in {"pending", "running"}:
                    return dict(job)
            job = {
                "id": uuid4().hex[:12],
                "action": action,
                "slug": slug,
                "status": "pending",
                "worker_id": "",
                "target_worker": target_worker,
                "created_at": self.now(),
                "updated_at": self.now(),
                "started_at": "",
                "finished_at": "",
                "exit_code": None,
                "message": "",
                "log": "",
                "result_files": [],
                "retry_count": 0,
                "lease_epoch": 0,
            }
            self._append_job_log(job, f"[QUEUED] {action} / {slug}\n")
            jobs.append(job)
            if len(jobs) > MAX_JOBS:
                for old in jobs[:-MAX_JOBS]:
                    try:
                        self._log_path(old.get("id") or "").unlink(missing_ok=True)
                    except OSError:
                        pass
                del jobs[:-MAX_JOBS]
            self._save_jobs(force=True)
            return dict(job)

    def register(self, worker_id: str, payload: dict) -> dict:
        with LOCK:
            workers = self._load_workers()
            previous = workers.get(worker_id, {})
            workers[worker_id] = {
                **previous,
                "name": payload.get("name") or worker_id,
                "root": payload.get("root") or "",
                "version": payload.get("version") or "",
                "instance_id": payload.get("instance_id") or previous.get("instance_id") or "",
                "capabilities": payload.get("capabilities") or ["remotion"],
                "ready": bool(payload.get("ready", True)),
                "issues": payload.get("issues") or [],
                "checks": payload.get("checks") or {},
                "status": previous.get("status") if previous.get("status") == "running" else "idle",
                "job_id": previous.get("job_id") or "",
                "last_seen": self.now(),
                "last_seen_epoch": self.now_epoch(),
            }
            changed = (previous.get("ready") != workers[worker_id]["ready"]
                       or previous.get("instance_id") != workers[worker_id]["instance_id"])
            self._save_workers(force=changed)
            return dict(workers[worker_id])

    def heartbeat(self, worker_id: str, status: str = "", job_id: str = "") -> None:
        with LOCK:
            workers = self._load_workers()
            worker = workers.setdefault(worker_id, {"name": worker_id})
            worker["last_seen"] = self.now()
            worker["last_seen_epoch"] = self.now_epoch()
            status_changed = bool(status) and worker.get("status") != status
            if status:
                worker["status"] = status
            if job_id or status == "idle":
                worker["job_id"] = job_id
            self._save_workers(force=status_changed)
            if job_id:
                for job in self._load_jobs():
                    if job.get("id") == job_id and job.get("status") == "running":
                        job["lease_epoch"] = self.now_epoch()
                        job["updated_at"] = self.now()
                        self._save_jobs()
                        break

    def claim(self, worker_id: str, instance_id: str = "") -> dict | None:
        with LOCK:
            self.recover_stale_jobs()
            self.heartbeat(worker_id)
            worker = self.workers().get(worker_id, {})
            if not worker.get("online") or not worker.get("ready", True):
                return None
            active_instance = str(worker.get("instance_id") or "")
            if active_instance and instance_id != active_instance:
                return None
            claimed = None
            for job in self._load_jobs():
                if job.get("status") == "pending":
                    target_worker = str(job.get("target_worker") or "")
                    if target_worker and target_worker != worker_id:
                        continue
                    job["status"] = "running"
                    job["worker_id"] = worker_id
                    job["started_at"] = self.now()
                    job["updated_at"] = self.now()
                    job["lease_epoch"] = self.now_epoch()
                    self._append_job_log(job, f"[CLAIMED] {worker_id}\n")
                    claimed = dict(job)
                    break
            if claimed:
                self._save_jobs(force=True)
                self.heartbeat(worker_id, "running", claimed["id"])
            return claimed

    def append_log(self, job_id: str, text: str) -> None:
        with LOCK:
            for job in self._load_jobs():
                if job.get("id") == job_id:
                    self._append_job_log(job, text)
                    job["updated_at"] = self.now()
                    job["lease_epoch"] = self.now_epoch()
                    self._save_jobs()
                    break

    def job_log(self, job_id: str, tail: int | None = None) -> str | None:
        """잡 로그(전체 파일 기준). 잡이 없으면 None. tail 지정 시 마지막 tail 글자."""
        with LOCK:
            job = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            if job is None:
                return None
            path = self._log_path(job_id)
            fallback = job.get("log") or ""
        try:
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else fallback
        except OSError:
            text = fallback
        if tail and tail > 0 and len(text) > tail:
            return text[-tail:]
        return text

    def complete(self, job_id: str, worker_id: str, ok: bool, exit_code: int, message: str) -> dict:
        with LOCK:
            target = None
            for job in self._load_jobs():
                if job.get("id") == job_id:
                    job["status"] = "done" if ok else "failed"
                    job["exit_code"] = exit_code
                    job["message"] = message
                    job["finished_at"] = self.now()
                    job["updated_at"] = self.now()
                    self._append_job_log(job, f"\n[{'DONE' if ok else 'FAILED'}] exit={exit_code} {message}\n")
                    target = dict(job)
                    break
            self._save_jobs(force=True)
            self.heartbeat(worker_id, "idle", "")
            if target is None:
                raise RuntimeError("remote job not found")
            return target

    def panel_job(self) -> dict | None:
        self.recover_stale_jobs()
        jobs = self.jobs()
        active = [job for job in jobs if job.get("status") in {"pending", "running"}]
        target = active[-1] if active else (jobs[-1] if jobs else None)
        if not target:
            return None
        return {
            "running": target.get("status") in {"pending", "running"},
            "name": f"{target.get('action')} · {target.get('slug')}",
            "started": target.get("started_at") or target.get("created_at") or "",
            "ended": target.get("finished_at") or "",
            "exit_code": target.get("exit_code"),
            "log": target.get("log") or "",
            "remote": True,
            "status": target.get("status"),
            "worker_id": target.get("worker_id") or "",
            "job_id": target.get("id") or "",
            "target_worker": target.get("target_worker") or "",
        }

    def package_bytes(self, job_id: str) -> bytes:
        jobs = self.jobs()
        job = next((item for item in jobs if item.get("id") == job_id), None)
        if not job:
            raise RuntimeError("remote job not found")
        slug = job["slug"]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            article = self.cardnews / "articles" / f"{slug}.json"
            if article.exists():
                zf.write(article, f"cardnews/articles/{article.name}")
            roots = [
                (self.cardnews / "images" / slug, f"cardnews/images/{slug}"),
                (self.cardnews / "output" / slug, f"cardnews/output/{slug}"),
            ]
            prompt = self._read(self.desk / "LATEST_PROMPT.json", {})
            requested_names = {
                str(item.get("filename") or "")
                for item in (prompt.get("requests") or [])
                if item.get("filename")
            }
            illustration_drop = self.desk / "ILLUSTRATION_DROP"
            for filename in sorted(requested_names):
                path = illustration_drop / filename
                if path.exists() and path.is_file():
                    zf.write(path, f"CODEX_VIDEO_DESK/ILLUSTRATION_DROP/{path.name}")
            override = self.desk / "CHUNK_OVERRIDES" / f"{slug}.json"
            if override.exists():
                zf.write(override, f"CODEX_VIDEO_DESK/CHUNK_OVERRIDES/{override.name}")
            for runtime_name in ("LATEST_SLUG.txt", "LATEST_PROMPT.json", "LATEST_PROMPT.md"):
                runtime_path = self.desk / runtime_name
                if runtime_path.exists():
                    zf.write(runtime_path, f"CODEX_VIDEO_DESK/{runtime_name}")
            for root, archive_root in roots:
                if not root.exists():
                    continue
                for path in root.rglob("*"):
                    if path.is_file():
                        zf.write(path, f"{archive_root}/{path.relative_to(root).as_posix()}")
            zf.writestr("remote_job.json", json.dumps(job, ensure_ascii=False, indent=2))
        return buf.getvalue()

    def save_result_stream(self, job_id: str, filename: str, source, length: int,
                           max_bytes: int = 4 * 1024 ** 3) -> Path:
        if length <= 0:
            raise RuntimeError("result file is empty")
        if length > max_bytes:
            raise RuntimeError(f"result file too large: {length} bytes (max {max_bytes})")
        with LOCK:
            job = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            if not job:
                raise RuntimeError("remote job not found")
            safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename) or "result.mp4"
            folder = self.results / f"remote_{job_id}_{job['slug']}"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / safe_name
            temp = target.with_suffix(target.suffix + ".uploading")

        received = 0
        try:
            with temp.open("wb") as output:
                remaining = length
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError(
                            f"result upload ended early: received {received} of {length} bytes"
                        )
                    output.write(chunk)
                    received += len(chunk)
                    remaining -= len(chunk)
            temp.replace(target)
        except Exception:
            temp.unlink(missing_ok=True)
            raise

        with LOCK:
            job = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            if not job:
                target.unlink(missing_ok=True)
                raise RuntimeError("remote job not found")
            result_files = job.setdefault("result_files", [])
            target_text = str(target)
            if target_text not in result_files:
                result_files.append(target_text)
            job["result_size"] = received
            job["result_uploaded_at"] = self.now()
            job["updated_at"] = self.now()
            self._save_jobs(force=True)
            return target

    def cancel(self, job_id: str) -> dict:
        with LOCK:
            job = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            if not job:
                raise RuntimeError("remote job not found")
            if job.get("status") == "running":
                job["cancel_requested"] = True
                self._append_job_log(job, "\n[CANCEL REQUESTED]\n")
            elif job.get("status") == "pending":
                job["status"] = "cancelled"
                job["finished_at"] = self.now()
                self._append_job_log(job, "\n[CANCELLED]\n")
            job["updated_at"] = self.now()
            self._save_jobs(force=True)
            return dict(job)

    def retry(self, job_id: str) -> dict:
        with LOCK:
            source = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            if not source:
                raise RuntimeError("remote job not found")
            if source.get("status") in {"pending", "running"}:
                return dict(source)
            source["status"] = "pending"
            source["worker_id"] = ""
            source["started_at"] = ""
            source["finished_at"] = ""
            source["exit_code"] = None
            source["message"] = ""
            source["cancel_requested"] = False
            source["retry_count"] = 0
            source["lease_epoch"] = 0
            source["updated_at"] = self.now()
            self._append_job_log(source, "\n[MANUAL RETRY]\n")
            self._save_jobs(force=True)
            return dict(source)

    def is_cancel_requested(self, job_id: str) -> bool:
        with LOCK:
            job = next((item for item in self._load_jobs() if item.get("id") == job_id), None)
            return bool(job and job.get("cancel_requested"))
