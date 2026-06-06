# -*- coding: utf-8 -*-
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


class RemoteQueue:
    def __init__(self, root: Path):
        self.root = root
        self.desk = root / "CODEX_VIDEO_DESK"
        self.cardnews = root / "cardnews"
        self.jobs_path = self.desk / "TEMP" / "remote_render_jobs.json"
        self.workers_path = self.desk / "TEMP" / "remote_render_workers.json"
        self.results = self.desk / "RESULTS"

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

    def jobs(self) -> list[dict]:
        with LOCK:
            return self._read(self.jobs_path, {"jobs": []}).get("jobs", [])

    def _save_jobs(self, jobs: list[dict]) -> None:
        self._write(self.jobs_path, {"version": 1, "updated_at": self.now(), "jobs": jobs})

    def workers(self) -> dict:
        with LOCK:
            workers = self._read(self.workers_path, {"workers": {}}).get("workers", {})
            now = self.now_epoch()
            for worker in workers.values():
                worker["online"] = now - float(worker.get("last_seen_epoch") or 0) <= WORKER_TTL_SECONDS
            return workers

    def recover_stale_jobs(self) -> int:
        with LOCK:
            jobs = self.jobs()
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
                    job["log"] += f"\n[RECOVERED] worker lease expired; retry {retries + 1}/{MAX_RETRIES}\n"
                else:
                    job["status"] = "failed"
                    job["exit_code"] = 97
                    job["message"] = "worker disconnected or stopped responding"
                    job["finished_at"] = self.now()
                    job["updated_at"] = self.now()
                    job["log"] += "\n[FAILED] worker lease expired\n"
                changed += 1
            if changed:
                self._save_jobs(jobs)
            return changed

    def _save_workers(self, workers: dict) -> None:
        clean = {}
        for worker_id, worker in workers.items():
            clean[worker_id] = {key: value for key, value in worker.items() if key != "online"}
        self._write(self.workers_path, {"version": 1, "updated_at": self.now(), "workers": clean})

    def online_workers(self) -> list[dict]:
        return [{"id": worker_id, **worker} for worker_id, worker in self.workers().items() if worker.get("online")]

    def enqueue(self, action: str, slug: str, target_worker: str = "") -> dict:
        with LOCK:
            jobs = self.jobs()
            for job in jobs:
                if job.get("slug") == slug and job.get("action") == action and job.get("status") in {"pending", "running"}:
                    return job
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
                "log": f"[QUEUED] {action} / {slug}\n",
                "result_files": [],
                "retry_count": 0,
                "lease_epoch": 0,
            }
            jobs.append(job)
            self._save_jobs(jobs[-200:])
            return job

    def register(self, worker_id: str, payload: dict) -> dict:
        with LOCK:
            workers = self.workers()
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
            self._save_workers(workers)
            return workers[worker_id]

    def heartbeat(self, worker_id: str, status: str = "", job_id: str = "") -> None:
        with LOCK:
            workers = self.workers()
            worker = workers.setdefault(worker_id, {"name": worker_id})
            worker["last_seen"] = self.now()
            worker["last_seen_epoch"] = self.now_epoch()
            if status:
                worker["status"] = status
            if job_id or status == "idle":
                worker["job_id"] = job_id
            self._save_workers(workers)
            if job_id:
                jobs = self.jobs()
                for job in jobs:
                    if job.get("id") == job_id and job.get("status") == "running":
                        job["lease_epoch"] = self.now_epoch()
                        job["updated_at"] = self.now()
                        break
                self._save_jobs(jobs)

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
            jobs = self.jobs()
            claimed = None
            for job in jobs:
                if job.get("status") == "pending":
                    target_worker = str(job.get("target_worker") or "")
                    if target_worker and target_worker != worker_id:
                        continue
                    job["status"] = "running"
                    job["worker_id"] = worker_id
                    job["started_at"] = self.now()
                    job["updated_at"] = self.now()
                    job["lease_epoch"] = self.now_epoch()
                    job["log"] += f"[CLAIMED] {worker_id}\n"
                    claimed = dict(job)
                    break
            if claimed:
                self._save_jobs(jobs)
                self.heartbeat(worker_id, "running", claimed["id"])
            return claimed

    def append_log(self, job_id: str, text: str) -> None:
        with LOCK:
            jobs = self.jobs()
            for job in jobs:
                if job.get("id") == job_id:
                    job["log"] = ((job.get("log") or "") + text)[-260000:]
                    job["updated_at"] = self.now()
                    job["lease_epoch"] = self.now_epoch()
                    break
            self._save_jobs(jobs)

    def complete(self, job_id: str, worker_id: str, ok: bool, exit_code: int, message: str) -> dict:
        with LOCK:
            jobs = self.jobs()
            target = None
            for job in jobs:
                if job.get("id") == job_id:
                    job["status"] = "done" if ok else "failed"
                    job["exit_code"] = exit_code
                    job["message"] = message
                    job["finished_at"] = self.now()
                    job["updated_at"] = self.now()
                    job["log"] += f"\n[{'DONE' if ok else 'FAILED'}] exit={exit_code} {message}\n"
                    target = dict(job)
                    break
            self._save_jobs(jobs)
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

    def save_result_stream(self, job_id: str, filename: str, source, length: int) -> Path:
        if length <= 0:
            raise RuntimeError("result file is empty")
        with LOCK:
            jobs = self.jobs()
            job = next((item for item in jobs if item.get("id") == job_id), None)
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
            jobs = self.jobs()
            job = next((item for item in jobs if item.get("id") == job_id), None)
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
            self._save_jobs(jobs)
            return target

    def cancel(self, job_id: str) -> dict:
        with LOCK:
            jobs = self.jobs()
            job = next((item for item in jobs if item.get("id") == job_id), None)
            if not job:
                raise RuntimeError("remote job not found")
            if job.get("status") == "running":
                job["cancel_requested"] = True
                job["log"] += "\n[CANCEL REQUESTED]\n"
            elif job.get("status") == "pending":
                job["status"] = "cancelled"
                job["finished_at"] = self.now()
                job["log"] += "\n[CANCELLED]\n"
            job["updated_at"] = self.now()
            self._save_jobs(jobs)
            return job

    def retry(self, job_id: str) -> dict:
        with LOCK:
            jobs = self.jobs()
            source = next((item for item in jobs if item.get("id") == job_id), None)
            if not source:
                raise RuntimeError("remote job not found")
            if source.get("status") in {"pending", "running"}:
                return source
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
            source["log"] += "\n[MANUAL RETRY]\n"
            self._save_jobs(jobs)
            return source

    def is_cancel_requested(self, job_id: str) -> bool:
        job = next((item for item in self.jobs() if item.get("id") == job_id), None)
        return bool(job and job.get("cancel_requested"))
