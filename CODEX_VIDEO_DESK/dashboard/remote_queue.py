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

    def _save_workers(self, workers: dict) -> None:
        clean = {}
        for worker_id, worker in workers.items():
            clean[worker_id] = {key: value for key, value in worker.items() if key != "online"}
        self._write(self.workers_path, {"version": 1, "updated_at": self.now(), "workers": clean})

    def online_workers(self) -> list[dict]:
        return [{"id": worker_id, **worker} for worker_id, worker in self.workers().items() if worker.get("online")]

    def enqueue(self, action: str, slug: str) -> dict:
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
                "created_at": self.now(),
                "updated_at": self.now(),
                "started_at": "",
                "finished_at": "",
                "exit_code": None,
                "message": "",
                "log": f"[QUEUED] {action} / {slug}\n",
                "result_files": [],
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
                "capabilities": payload.get("capabilities") or ["remotion"],
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

    def claim(self, worker_id: str) -> dict | None:
        with LOCK:
            self.heartbeat(worker_id)
            jobs = self.jobs()
            claimed = None
            for job in jobs:
                if job.get("status") == "pending":
                    job["status"] = "running"
                    job["worker_id"] = worker_id
                    job["started_at"] = self.now()
                    job["updated_at"] = self.now()
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
                (self.desk / "ILLUSTRATION_DROP", "CODEX_VIDEO_DESK/ILLUSTRATION_DROP"),
            ]
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

    def save_result(self, job_id: str, filename: str, data: bytes) -> Path:
        with LOCK:
            jobs = self.jobs()
            job = next((item for item in jobs if item.get("id") == job_id), None)
            if not job:
                raise RuntimeError("remote job not found")
            safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename) or "result.mp4"
            folder = self.results / f"remote_{job_id}_{job['slug']}"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / safe_name
            target.write_bytes(data)
            job.setdefault("result_files", []).append(str(target))
            job["updated_at"] = self.now()
            self._save_jobs(jobs)
            return target
