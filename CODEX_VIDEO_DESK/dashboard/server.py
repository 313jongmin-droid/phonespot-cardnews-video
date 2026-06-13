# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from remote_queue import RemoteQueue

ROOT = Path(__file__).resolve().parent.parent.parent
DESK = ROOT / "CODEX_VIDEO_DESK"
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
CARDNEWS = ROOT / "cardnews"
CARD_OUTPUT = CARDNEWS / "output"
CARD_IMAGES = CARDNEWS / "images"
CARD_ARTICLES = CARDNEWS / "articles"
SECRETS = ROOT / "_secrets"
TELEGRAM_TOKEN_FILE = SECRETS / "telegram_token.txt"
TELEGRAM_CHAT_ID_FILE = SECRETS / "telegram_chat_id.txt"
DOWNLOADS = Path.home() / "Downloads"
CHUNK_OVERRIDES = DESK / "CHUNK_OVERRIDES"
WORK_QUEUE = DESK / "WORK_QUEUE"
PORT = int(os.environ.get("PHONESPOT_PANEL_PORT", "4878"))
PANEL_VERSION = "phonespot-web-v26"
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,160}$")
REMOTE_QUEUE = RemoteQueue(ROOT)
LOCAL_HISTORY_PATH = DESK / "TEMP" / "local_job_history.json"
LOCAL_WORKER_PROCESS: subprocess.Popen | None = None
LOCAL_WORKER_STREAMS: list = []

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from codex_caption_lockstep import ABSOLUTE_MAX_UNITS, forbidden_boundary, split_tts_caption, units
from codex_chunk_overrides import (
    apply_overrides as apply_shared_chunk_overrides,
    display_chunk as normalize_display_chunk,
    flatten_chunk as normalize_caption_chunk,
    section_tts_hash,
    validate_effective_section,
)

STATE_LOCK = threading.Lock()
LOCAL_HISTORY_LOCK = threading.RLock()
JOB = {
    "job_id": "",
    "running": False,
    "name": "",
    "worker_id": socket.gethostname(),
    "started": 0.0,
    "ended": 0.0,
    "exit_code": None,
    "log": "",
}


def read_local_history() -> list[dict]:
    with LOCAL_HISTORY_LOCK:
        if not LOCAL_HISTORY_PATH.exists():
            return []
        try:
            payload = json.loads(LOCAL_HISTORY_PATH.read_text(encoding="utf-8", errors="replace"))
            return payload.get("jobs", []) if isinstance(payload, dict) else []
        except Exception:
            return []


def update_local_history(job_id: str, changes: dict) -> None:
    with LOCAL_HISTORY_LOCK:
        jobs = read_local_history()
        job = next((item for item in jobs if item.get("id") == job_id), None)
        if job is None:
            job = {"id": job_id}
            jobs.append(job)
        job.update(changes)
        LOCAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = LOCAL_HISTORY_PATH.with_suffix(LOCAL_HISTORY_PATH.suffix + ".tmp")
        temp.write_text(
            json.dumps({"version": 1, "jobs": jobs[-100:]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.replace(LOCAL_HISTORY_PATH)


def append_log(text: str) -> None:
    with STATE_LOCK:
        JOB["log"] += text
        if len(JOB["log"]) > 260_000:
            JOB["log"] = JOB["log"][-260_000:]


def start_local_worker() -> None:
    global LOCAL_WORKER_PROCESS
    if os.environ.get("PHONESPOT_AUTO_WORKER", "1") == "0":
        return
    worker_script = DESK / "RENDER_WORKER" / "worker.py"
    if not worker_script.exists():
        return
    pid_file = DESK / "TEMP" / "worker" / "local_worker.pid"
    if pid_file.exists():
        try:
            os.kill(int(pid_file.read_text(encoding="ascii").strip()), 0)
            return
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
    log_dir = DESK / "TEMP" / "worker" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout = (log_dir / f"worker_{stamp}.out.log").open("a", encoding="utf-8")
    stderr = (log_dir / f"worker_{stamp}.err.log").open("a", encoding="utf-8")
    LOCAL_WORKER_STREAMS.extend([stdout, stderr])
    env = os.environ.copy()
    env["PHONESPOT_PANEL_URL"] = f"http://127.0.0.1:{PORT}"
    env["PHONESPOT_WORKER_PID_FILE"] = str(pid_file)
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / ".playwright")
    env["PYTHONUNBUFFERED"] = "1"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    LOCAL_WORKER_PROCESS = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=str(DESK),
        stdout=stdout,
        stderr=stderr,
        env=env,
        creationflags=creationflags,
    )


def stop_local_worker() -> None:
    if LOCAL_WORKER_PROCESS and LOCAL_WORKER_PROCESS.poll() is None:
        try:
            LOCAL_WORKER_PROCESS.terminate()
            LOCAL_WORKER_PROCESS.wait(timeout=5)
        except Exception:
            try:
                LOCAL_WORKER_PROCESS.kill()
            except Exception:
                pass


def telegram_send(message: str) -> bool:
    if os.environ.get("PHONESPOT_DISABLE_TELEGRAM") == "1":
        append_log("[telegram] disabled for this server.\n")
        return False
    if not TELEGRAM_TOKEN_FILE.exists() or not TELEGRAM_CHAT_ID_FILE.exists():
        append_log("[telegram] token/chat_id missing; skipped.\n")
        return False
    token = TELEGRAM_TOKEN_FILE.read_text(encoding="utf-8", errors="replace").strip()
    chat_id = TELEGRAM_CHAT_ID_FILE.read_text(encoding="utf-8", errors="replace").strip()
    if not token or not chat_id or ":" not in token:
        append_log("[telegram] invalid token/chat_id; skipped.\n")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = b'"ok":true' in resp.read(400)
        append_log("[telegram] sent.\n" if ok else "[telegram] send returned non-ok.\n")
        return ok
    except (urllib.error.URLError, OSError) as exc:
        append_log(f"[telegram] send failed: {exc}\n")
        return False


def telegram_escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def telegram_job_message(name: str, exit_code: int) -> str:
    ok = exit_code == 0
    icon = "✅" if ok else "❌"
    status = "완료" if ok else f"실패(exit={exit_code})"
    safe_name = telegram_escape(name)
    if "카드뉴스 생성" in name:
        next_step = "다음 단계: 패널에서 <b>6. 영상으로 넘기기</b>를 실행하세요."
    elif "카드뉴스를 영상 준비" in name or "영상 이미지 프롬프트" in name:
        next_step = "다음 단계: GPT 이미지가 필요하면 생성 후 <b>2. 이미지 가져오기 + 렌더</b>를 실행하세요."
    elif "영상 렌더" in name or "이미지 가져오기 + 영상 렌더" in name:
        next_step = "다음 단계: <b>결과 폴더</b>에서 MP4와 발행 패키지를 확인하세요."
    else:
        next_step = "패널에서 다음 단계를 확인하세요."
    return f"{icon} <b>폰스팟 제작 패널</b>\n{safe_name} {status}\n{next_step}"


def run_job(name: str, commands: list[list[str]], cwd: Path, stdin_text: str | None = None) -> bool:
    job_id = uuid4().hex[:12]
    started = time.time()
    with STATE_LOCK:
        if JOB["running"]:
            return False
        JOB.update({
            "job_id": job_id,
            "running": True,
            "name": name,
            "worker_id": socket.gethostname(),
            "started": started,
            "ended": 0.0,
            "exit_code": None,
            "log": f"[START] {name}\n",
        })
    update_local_history(job_id, {
        "kind": "local",
        "name": name,
        "status": "running",
        "worker_id": socket.gethostname(),
        "created_at": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "started_at": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "finished_at": "",
        "exit_code": None,
        "message": "",
        "result_files": [],
    })

    def worker() -> None:
        exit_code = 0
        try:
            for index, command in enumerate(commands, 1):
                append_log("\n")
                append_log(f"----- command {index}/{len(commands)} -----\n")
                append_log(" ".join(command) + "\n")
                use_stdin = stdin_text if index == 1 and stdin_text is not None else None
                process_env = os.environ.copy()
                process_env["PYTHONIOENCODING"] = "utf-8"
                process_env["PYTHONUTF8"] = "1"
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    stdin=subprocess.PIPE if use_stdin is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=process_env,
                )
                if use_stdin is not None and process.stdin is not None:
                    process.stdin.write(use_stdin)
                    process.stdin.close()
                assert process.stdout is not None
                for line in process.stdout:
                    append_log(line)
                exit_code = process.wait()
                append_log(f"\n[EXIT] {exit_code}\n")
                if exit_code:
                    break
        except Exception as exc:
            exit_code = 99
            append_log(f"\n[SERVER ERROR] {exc}\n")
        finally:
            ended = time.time()
            with STATE_LOCK:
                JOB["running"] = False
                JOB["ended"] = ended
                JOB["exit_code"] = exit_code
                JOB["log"] += "\n[DONE]\n" if exit_code == 0 else "\n[FAILED]\n"
            update_local_history(job_id, {
                "status": "done" if exit_code == 0 else "failed",
                "finished_at": datetime.fromtimestamp(ended).isoformat(timespec="seconds"),
                "exit_code": exit_code,
                "message": "완료" if exit_code == 0 else f"종료 코드 {exit_code}",
            })
            telegram_send(telegram_job_message(name, exit_code))

    threading.Thread(target=worker, daemon=True).start()
    return True


def select_panel_job(local_job: dict, remote_job: dict | None) -> dict:
    if local_job.get("running"):
        return local_job
    if remote_job and remote_job.get("running"):
        return remote_job
    remote_ended = 0.0
    if remote_job:
        remote_stamp = remote_job.get("ended") or remote_job.get("started") or ""
        try:
            remote_ended = datetime.fromisoformat(str(remote_stamp)).timestamp()
        except (TypeError, ValueError):
            pass
    local_ended = float(local_job.get("ended") or local_job.get("started") or 0)
    if local_job.get("name") and local_ended >= remote_ended:
        return local_job
    return remote_job or local_job


def run_capture(command: list[str], cwd: Path = SHORTS) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def parse_slugs(raw: str) -> list[dict]:
    rows = []
    pattern = re.compile(r"^\s*(\d+)\.\s+(\d{4}\.\d{2}\.\d{2})\s+\[([^\]]+)\]\s+(.+?)\s*$")
    for line in raw.splitlines():
        match = pattern.match(line)
        if match:
            rows.append({
                "number": int(match.group(1)),
                "date": match.group(2),
                "flag": match.group(3),
                "slug": match.group(4),
            })
    return rows


def get_video_slugs() -> list[dict]:
    # 영상 탭도 카드 탭과 동일 소스(articles+images+output)를 사용 → 기사만 있는
    # 슬러그도 영상 탭에 노출되어 6번(영상으로 넘기기) 없이 바로 영상 준비가 가능.
    # (예전엔 list_slugs.py = output 폴더 있는 슬러그만 노출되어 6번이 사실상 진입점이었음.)
    return get_cardnews_rows()


def validate_slug(slug: str) -> str:
    slug = (slug or "").strip()
    if not slug or not SAFE_SLUG.match(slug):
        raise RuntimeError(f"잘못된 슬러그입니다: {slug!r}")
    return slug


def card_prefix(slug: str) -> str:
    return validate_slug(slug).split("_", 1)[0]


def latest_slug() -> str:
    path = DESK / "LATEST_SLUG.txt"
    return path.read_text(encoding="utf-8", errors="replace").strip() if path.exists() else ""


def prompt_payload() -> dict:
    path = DESK / "LATEST_PROMPT.json"
    if not path.exists():
        return {"requests": [], "uncovered_gaps": []}
    try:
        txt = path.read_bytes().decode("utf-8-sig", errors="replace").replace("\x00", " ")
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            # NUL/꼬리 쓰레기(부분 쓰기·동기화 사고)가 붙어도 첫 JSON 객체를 복원.
            obj, _ = json.JSONDecoder().raw_decode(txt.lstrip())
            return obj
    except Exception:
        return {"requests": [], "uncovered_gaps": [], "parse_error": True}


def available_visuals() -> dict:
    illust_dir = DESK / "ILLUSTRATION_DROP"
    if not illust_dir.exists():
        illust_dir = SHORTS / "public" / "assets" / "illustrations"
    logo_dir = SHORTS / "public" / "assets" / "logos"
    return {
        "illust": sorted(p.stem for p in illust_dir.glob("*.png")) if illust_dir.exists() else [],
        "logo": sorted(p.name for p in logo_dir.glob("*.png")) if logo_dir.exists() else [],
        "image": [f"{i}.png" for i in range(1, 6)],
        "mascot": ["surprised", "suspicious", "thinking", "serious", "satisfied"],
    }


def weak_mapping_rows(limit: int = 80) -> list[dict]:
    payload = prompt_payload()
    rows = []
    for item in (payload.get("uncovered_gaps") or [])[:limit]:
        try:
            raw_chunk = int(item.get("chunk_index", 0))
            chunk_num = raw_chunk + 1
        except Exception:
            raw_chunk = item.get("chunk_index", "")
            chunk_num = item.get("chunk_index", "")
        rows.append({
            "section": item.get("section", ""),
            "chunk": chunk_num,
            "chunk_index": raw_chunk,
            "variant": item.get("variant", ""),
            "text": item.get("text", ""),
            "suggestion": weak_mapping_suggestion(item.get("text", ""), item.get("variant", "")),
        })
    return rows


def weak_mapping_suggestion(text: str, variant: str) -> str:
    t = text or ""
    rules = [
        (("위약", "약정", "반환", "할인", "지원금"), "penalty_refund / contract_month / telecom_fee"),
        (("법", "시행령", "조항", "약관"), "law_document / policy_notice"),
        (("개월", "만료", "기간", "잔여"), "contract_calendar / month_timeline"),
        (("통신사", "SKT", "KT", "LGU", "T world"), "telecom_app / carrier_check"),
        (("조회", "확인", "계산"), "checklist / calculator"),
        (("대납", "프로모션", "보전"), "promo_support / refund_arrow"),
        (("도난", "사망", "해외", "특별 사유"), "exception_case / shield_document"),
    ]
    for keys, suggestion in rules:
        if any(k in t for k in keys):
            return suggestion
    if variant in {"aluminum_label", "appliance", "battery_overheat", "biometric"}:
        return "문맥 전용 일러스트 필요"
    return "검토 권장"


def count_recent_downloads() -> int:
    report = DESK / "LATEST_PROMPT.json"
    if not report.exists() or not DOWNLOADS.exists():
        return 0
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    threshold = report.stat().st_mtime - 2
    count = 0
    for item in DOWNLOADS.iterdir():
        try:
            if item.is_file() and item.suffix.lower() in allowed and item.stat().st_size >= 10_000 and item.stat().st_mtime >= threshold:
                count += 1
        except OSError:
            pass
    return count


def missing_requests(payload: dict) -> list[dict]:
    rows = []
    illust = DESK / "ILLUSTRATION_DROP"
    runtime_illust = SHORTS / "public" / "assets" / "illustrations"
    for item in payload.get("requests", []) or []:
        filename = item.get("filename")
        if filename and not (illust / filename).exists() and not (runtime_illust / filename).exists():
            rows.append(item)
    return rows


def results_list() -> list[dict]:
    root = DESK / "RESULTS"
    if not root.exists():
        return []
    rows = []
    for folder in root.iterdir():
        if folder.is_dir():
            mp4s = sorted(folder.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not mp4s:
                continue
            rows.append({
                "name": folder.name,
                "mp4": mp4s[0].name,
                "mtime": mp4s[0].stat().st_mtime,
            })
    rows.sort(key=lambda item: float(item.get("mtime") or 0), reverse=True)
    return rows[:30]


def timestamp_value(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def history_result_files(paths: list[str]) -> list[dict]:
    result_root = (DESK / "RESULTS").resolve()
    rows = []
    for raw_path in paths:
        try:
            path = Path(raw_path).resolve()
            if result_root not in path.parents or not path.is_file():
                continue
            rows.append({"name": path.name, "folder": path.parent.name, "file": path.name})
        except OSError:
            continue
    return rows


def job_history(limit: int = 50) -> list[dict]:
    action_names = {
        "video_import_render": "이미지 가져오기 + 렌더",
        "video_render_selected": "선택 영상만 렌더",
    }
    rows = []
    for job in REMOTE_QUEUE.jobs():
        action = str(job.get("action") or "원격 작업")
        slug = str(job.get("slug") or "")
        started_at = job.get("started_at") or ""
        finished_at = job.get("finished_at") or ""
        started_epoch = timestamp_value(started_at)
        finished_epoch = timestamp_value(finished_at)
        duration = None
        if started_epoch:
            duration = max(0, round((finished_epoch or time.time()) - started_epoch))
        rows.append({
            "id": job.get("id") or "",
            "kind": "remote",
            "name": f"{action_names.get(action, action)}: {slug}" if slug else action_names.get(action, action),
            "status": job.get("status") or "pending",
            "worker_id": job.get("worker_id") or job.get("target_worker") or "",
            "created_at": job.get("created_at") or "",
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "exit_code": job.get("exit_code"),
            "message": job.get("message") or "",
            "retry_count": int(job.get("retry_count") or 0),
            "result_files": history_result_files(job.get("result_files") or []),
        })
    for job in read_local_history():
        started_at = job.get("started_at") or job.get("created_at") or ""
        finished_at = job.get("finished_at") or ""
        started_epoch = timestamp_value(started_at)
        finished_epoch = timestamp_value(finished_at)
        duration = None
        if started_epoch:
            duration = max(0, round((finished_epoch or time.time()) - started_epoch))
        rows.append({
            "id": job.get("id") or "",
            "kind": "local",
            "name": job.get("name") or "로컬 작업",
            "status": job.get("status") or "done",
            "worker_id": job.get("worker_id") or socket.gethostname(),
            "created_at": job.get("created_at") or "",
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "exit_code": job.get("exit_code"),
            "message": job.get("message") or "",
            "retry_count": 0,
            "result_files": history_result_files(job.get("result_files") or []),
        })
    rows.sort(
        key=lambda item: timestamp_value(
            item.get("finished_at") or item.get("started_at") or item.get("created_at")
        ),
        reverse=True,
    )
    return rows[:max(1, min(limit, 100))]


def count_files(root: Path, patterns: tuple[str, ...], recursive: bool = True) -> int:
    if not root.exists():
        return 0
    count = 0
    for pattern in patterns:
        count += len(list(root.rglob(pattern) if recursive else root.glob(pattern)))
    return count


def card_image_count(slug: str) -> int:
    img = CARD_IMAGES / slug
    if not img.exists():
        return 0
    count = 0
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        for path in img.glob(pattern):
            name = path.name.lower()
            if name.startswith(("card_", "logo_")) or name == "cover.png" or name == "prompt.md":
                continue
            count += 1
    return count


def card_done(slug: str) -> bool:
    out = CARD_OUTPUT / slug
    if not out.exists():
        return False
    cards = list(out.rglob("card_*.jpg"))
    if len(cards) < 18:
        return False
    if not (out / "captions.md").exists():
        return False
    return not any(p.stat().st_size < 30 * 1024 for p in cards)


def article_title(slug: str) -> str:
    path = CARD_ARTICLES / f"{slug}.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data.get("title", "") or ""
    except Exception:
        return ""


def script_path_for_slug(slug: str) -> Path:
    slug = validate_slug(slug)
    candidates = [
        CARD_OUTPUT / slug / "shorts_script.json",
        SHORTS / "public" / "shorts_script.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError(f"shorts_script.json not found: {slug}")


def get_section_obj(data: dict, section: str) -> dict:
    if section == "hook":
        obj = data.get("hook")
        if isinstance(obj, dict):
            return obj
    if section == "cta":
        obj = data.get("cta")
        if isinstance(obj, dict):
            return obj
    if section.startswith("fact_"):
        try:
            index = int(section.split("_", 1)[1]) - 1
        except Exception:
            index = -1
        facts = data.get("facts") or []
        if 0 <= index < len(facts) and isinstance(facts[index], dict):
            return facts[index]
    raise RuntimeError(f"section not found: {section}")


def normalize_visual(kind: str, value: str) -> dict:
    kind = (kind or "").strip()
    value = (value or "").strip()
    if not kind or not value:
        raise RuntimeError("visual type/value is empty")
    if kind not in {"illust", "image", "logo", "mascot"}:
        raise RuntimeError(f"unsupported visual type: {kind}")
    if not re.match(r"^[A-Za-z0-9_.:/+-]+$", value):
        raise RuntimeError(f"unsafe visual value: {value}")
    return {"type": kind, "value": value}


def update_chunk_visual(slug: str, section: str, chunk_index: int, visual_type: str, visual_value: str) -> Path:
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    sec = get_section_obj(data, section)
    visuals = sec.setdefault("chunk_visuals", [])
    if not isinstance(visuals, list):
        raise RuntimeError(f"{section}.chunk_visuals is not a list")
    while len(visuals) <= chunk_index:
        if visuals and isinstance(visuals[-1], dict):
            visuals.append(dict(visuals[-1]))
        elif sec.get("background_image"):
            visuals.append({"type": "image", "value": sec["background_image"]})
        else:
            visuals.append({"type": "logo", "value": None})
    visuals[chunk_index] = normalize_visual(visual_type, visual_value)
    data["_codex_manual_visual_edit"] = True
    data["_codex_manual_visual_edit_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    backup = path.with_suffix(path.suffix + f".bak_visual_edit_{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    runtime = SHORTS / "public" / "shorts_script.json"
    if path != runtime and runtime.exists():
        runtime.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return path


def override_path_for_slug(slug: str) -> Path:
    return CHUNK_OVERRIDES / f"{validate_slug(slug)}.json"


def section_names(data: dict) -> list[tuple[str, dict]]:
    result: list[tuple[str, dict]] = []
    if isinstance(data.get("hook"), dict):
        result.append(("hook", data["hook"]))
    for idx, fact in enumerate(data.get("facts") or [], 1):
        if isinstance(fact, dict):
            result.append((f"fact_{idx}", fact))
    if isinstance(data.get("cta"), dict):
        result.append(("cta", data["cta"]))
    return result


def apply_chunk_overrides(data: dict, slug: str) -> None:
    apply_shared_chunk_overrides(data, slug, override_path_for_slug(slug), strict=True)


def strip_display_period(text: str) -> str:
    return str(text or "").strip().rstrip(".。.!?！？").strip()


def flatten_chunk_text(text: str) -> str:
    return " ".join(str(text or "").replace("\\n", " ").replace("\n", " ").split())


def chunk_source(sec: dict) -> list[str]:
    chunks = sec.get("caption_chunks")
    if not isinstance(chunks, list) or not chunks:
        chunks = sec.get("display_chunks")
    if not isinstance(chunks, list):
        return []
    return [str(x) for x in chunks]


def compare_text(text: str) -> str:
    value = re.sub(r"\s+", "", str(text or ""))
    return re.sub(r"[.。,!！?？、，]", "", value)


def save_chunk_override(
    slug: str,
    section: str,
    sec: dict,
    chunks: list[str],
    display_chunks: list[str],
    visuals: list[dict],
) -> Path:
    clean_chunks = [normalize_caption_chunk(value) for value in chunks if normalize_caption_chunk(value)]
    clean_display = [normalize_display_chunk(value) for value in display_chunks if normalize_display_chunk(value)]
    candidate = dict(sec)
    candidate["caption_chunks"] = clean_chunks
    candidate["display_chunks"] = clean_display
    candidate["chunk_visuals"] = visuals
    errors = validate_effective_section(section, candidate)
    if errors:
        raise RuntimeError("청크 편집 검증 실패\n- " + "\n- ".join(errors))
    CHUNK_OVERRIDES.mkdir(parents=True, exist_ok=True)
    path = override_path_for_slug(slug)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    else:
        payload = {"version": 2, "slug": slug, "sections": {}}
    payload["version"] = 2
    payload.setdefault("sections", {})[section] = {
        "source_tts_sha256": section_tts_hash(sec),
        "chunks": clean_chunks,
        "display_chunks": clean_display,
        "visuals": visuals,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "policy": "TTS text is preserved; semantic chunks, locked display lines, and visuals stay aligned.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def chunk_rows_for_slug(slug: str) -> list[dict]:
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    rows = []
    for section, sec in section_names(data):
        chunks = [normalize_caption_chunk(value) for value in sec.get("caption_chunks") or []]
        display_chunks = sec.get("display_chunks") or chunks
        visuals = sec.get("chunk_visuals") or []
        for index, chunk in enumerate(chunks):
            visual = visuals[index] if index < len(visuals) and isinstance(visuals[index], dict) else {}
            display_value = display_chunks[index] if index < len(display_chunks) else chunk
            previous = chunks[index - 1] if index > 0 else ""
            following = chunks[index + 1] if index + 1 < len(chunks) else ""
            rows.append({
                "section": section,
                "chunk_index": index,
                "chunk": index + 1,
                "text": normalize_display_chunk(display_value),
                "visual": f"{visual.get('type', '-')}: {visual.get('value', '-')}",
                "chars": len(flatten_chunk_text(chunk).replace(" ", "")),
                "override": bool(sec.get("_codex_chunk_override")),
                "section_first": index == 0,
                "can_merge_prev": index > 0 and units(previous + " " + chunk) <= ABSOLUTE_MAX_UNITS,
                "can_merge_next": index < len(chunks) - 1
                and units(chunk + " " + following) <= ABSOLUTE_MAX_UNITS,
                "can_split": best_split_index(chunk) >= 0,
            })
    return rows


def best_split_index(text: str) -> int:
    plain = flatten_chunk_text(text)
    if units(plain) < 12:
        return -1
    candidates: list[tuple[int, int]] = []
    for match in re.finditer(r"\s+", plain):
        split = match.end()
        left = plain[:split].strip()
        right = plain[split:].strip()
        if min(units(left), units(right)) < 4:
            continue
        if max(units(left), units(right)) > ABSOLUTE_MAX_UNITS:
            continue
        left_word = left.split()[-1] if left.split() else ""
        right_word = right.split()[0] if right.split() else ""
        if forbidden_boundary(left_word, right_word):
            continue
        candidates.append((abs(units(left) - units(right)), split))
    return min(candidates)[1] if candidates else -1


def auto_linebreak(text: str) -> str:
    plain = flatten_chunk_text(text)
    if len(plain) <= 18:
        return strip_display_period(plain)
    idx = best_split_index(plain)
    if idx < 0:
        return strip_display_period(plain)
    left = plain[:idx].strip(" ,")
    right = plain[idx:].strip(" ,")
    if not left or not right:
        return strip_display_period(plain)
    return strip_display_period(left) + "\n" + strip_display_period(right)


def fallback_visual(sec: dict, visuals: list[dict], index: int) -> dict:
    if 0 <= index < len(visuals) and isinstance(visuals[index], dict):
        return dict(visuals[index])
    if visuals and isinstance(visuals[-1], dict):
        return dict(visuals[-1])
    background = sec.get("background_image")
    if background:
        return {"type": "image", "value": background}
    return {"type": "logo", "value": None}


def remap_visuals(
    sec: dict,
    old_chunks: list[str],
    old_visuals: list[dict],
    new_chunks: list[str],
) -> list[dict]:
    if not old_chunks:
        return [fallback_visual(sec, old_visuals, 0) for _ in new_chunks]
    old_ends: list[int] = []
    running = 0
    for chunk in old_chunks:
        running += max(1, units(chunk))
        old_ends.append(running)
    result: list[dict] = []
    new_cursor = 0
    for chunk in new_chunks:
        length = max(1, units(chunk))
        midpoint = new_cursor + (length / 2)
        old_index = next((idx for idx, end in enumerate(old_ends) if midpoint <= end), len(old_ends) - 1)
        result.append(fallback_visual(sec, old_visuals, old_index))
        new_cursor += length
    return result


def adjust_chunk_boundary(slug: str, section: str, chunk_index: int, op: str) -> Path:
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    sec = get_section_obj(data, section)
    chunks = [normalize_caption_chunk(value) for value in sec.get("caption_chunks") or []]
    if not chunks:
        raise RuntimeError(f"{section} has no chunks")
    if not (0 <= chunk_index < len(chunks)):
        raise RuntimeError(f"chunk index out of range: {chunk_index}")
    display_chunks = [
        normalize_display_chunk(value)
        for value in (sec.get("display_chunks") or chunks)
    ]
    if len(display_chunks) != len(chunks):
        display_chunks = [normalize_display_chunk(value) for value in chunks]
    visuals = sec.setdefault("chunk_visuals", [])
    if not isinstance(visuals, list):
        visuals = []
    visuals = [dict(v) if isinstance(v, dict) else fallback_visual(sec, [], 0) for v in visuals]
    while len(visuals) < len(chunks):
        visuals.append(fallback_visual(sec, visuals, len(visuals)))

    if op == "linebreak":
        display_chunks[chunk_index] = auto_linebreak(display_chunks[chunk_index])
    elif op == "merge_prev":
        if chunk_index <= 0:
            raise RuntimeError("first chunk cannot merge previous")
        chunks[chunk_index - 1] = (
            flatten_chunk_text(chunks[chunk_index - 1]).rstrip(" ,")
            + " "
            + flatten_chunk_text(chunks[chunk_index]).lstrip()
        ).strip()
        display_chunks[chunk_index - 1] = normalize_display_chunk(chunks[chunk_index - 1])
        del chunks[chunk_index]
        del display_chunks[chunk_index]
        if len(visuals) > chunk_index:
            del visuals[chunk_index]
    elif op == "merge_next":
        if chunk_index >= len(chunks) - 1:
            raise RuntimeError("last chunk cannot merge next")
        chunks[chunk_index] = (
            flatten_chunk_text(chunks[chunk_index]).rstrip(" ,")
            + " "
            + flatten_chunk_text(chunks[chunk_index + 1]).lstrip()
        ).strip()
        display_chunks[chunk_index] = normalize_display_chunk(chunks[chunk_index])
        del chunks[chunk_index + 1]
        del display_chunks[chunk_index + 1]
        if len(visuals) > chunk_index + 1:
            del visuals[chunk_index + 1]
    elif op == "split_auto":
        plain = flatten_chunk_text(chunks[chunk_index])
        split = best_split_index(plain)
        if split < 0:
            raise RuntimeError("this chunk is too short or has no safe split point")
        left = plain[:split].strip(" ,")
        right = plain[split:].strip(" ,")
        chunks[chunk_index] = left
        chunks.insert(chunk_index + 1, right)
        display_chunks[chunk_index] = normalize_display_chunk(left)
        display_chunks.insert(chunk_index + 1, normalize_display_chunk(right))
        visuals.insert(chunk_index + 1, fallback_visual(sec, visuals, chunk_index))
    elif op == "rebalance_section":
        narration = str(sec.get("tts") or "").strip()
        if not narration:
            raise RuntimeError(f"{section} has no TTS narration")
        new_chunks = split_tts_caption(narration)
        visuals = remap_visuals(sec, chunks, visuals, new_chunks)
        chunks = new_chunks
        display_chunks = [normalize_display_chunk(value) for value in chunks]
    else:
        raise RuntimeError(f"unknown chunk operation: {op}")

    while len(visuals) > len(chunks):
        visuals.pop()
    return save_chunk_override(slug, section, sec, chunks, display_chunks, visuals)


def set_section_chunks(slug: str, section: str, raw_text: str) -> Path:
    """사용자가 직접 끊은 자막 경계를 적용한다. 각 줄 = 자막 1개.
    글자(단어)는 나레이션과 동일해야 한다 → 렌더가 edge-tts 단어 경계에 다시 맞추므로
    끊는 위치만 바꾸면 TTS/화면 싱크는 안 깨진다. 글자가 달라지면 거부한다."""
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    sec = get_section_obj(data, section)
    old_chunks = [normalize_caption_chunk(value) for value in sec.get("caption_chunks") or []]
    new_lines = [ln.strip() for ln in str(raw_text or "").replace("\r", "").split("\n") if ln.strip()]
    if not new_lines:
        raise RuntimeError("내용이 비었습니다. 최소 한 줄(=자막 1개)이 필요합니다.")

    def _norm(s: str) -> str:
        return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(s))

    narration = str(sec.get("tts") or "").strip()
    ref = narration if narration else " ".join(flatten_chunk_text(c) for c in old_chunks)
    if _norm("".join(new_lines)) != _norm(ref):
        raise RuntimeError("글자가 나레이션과 달라졌습니다. 줄바꿈(끊는 위치)만 바꾸고 글자는 그대로 두세요.")

    chunks = new_lines
    display_chunks = [normalize_display_chunk(value) for value in chunks]
    visuals = sec.get("chunk_visuals") or []
    visuals = [dict(v) if isinstance(v, dict) else fallback_visual(sec, [], 0) for v in visuals]
    visuals = remap_visuals(sec, old_chunks, visuals, chunks)
    return save_chunk_override(slug, section, sec, chunks, display_chunks, visuals)


def cardnews_summary(limit: int = 12) -> str:
    rows = get_cardnews_rows()[:limit]
    if not rows:
        return "카드뉴스 후보가 없습니다."
    lines = ["📋 <b>카드뉴스 후보 현황</b>"]
    for item in rows:
        slug = telegram_escape(item.get("slug", ""))
        title = telegram_escape(item.get("title", ""))[:56]
        lines.append(
            f"- <b>{slug}</b> · {item.get('status')} · 이미지 {item.get('images')}/5 · 카드 {item.get('cards')}\n  {title}"
        )
    lines.append("\n후보가 준비됐으면 패널에서 카드뉴스 탭 → 프롬프트 보기 → 이미지 업로드 폴더 순서로 진행하세요.")
    return "\n".join(lines)



def rendered_video_exists(slug: str) -> bool:
    for root in (DESK / "RESULTS", SHORTS / "out_codex", SHORTS / "out"):
        if not root.exists():
            continue
        patterns = [
            f"{slug}*.mp4",
            f"*{slug}*.mp4",
        ]
        for pattern in patterns:
            if any(root.rglob(pattern)):
                return True
    return False


def card_stage(row: dict) -> str:
    if rendered_video_exists(row["slug"]):
        return "렌더 완료"
    if row.get("script"):
        return "영상 준비됨"
    if row.get("done"):
        return "카드뉴스 완료"
    if (row.get("images") or 0) >= 5:
        return "이미지 있음"
    if row.get("article"):
        return "기사만"
    return "부분"


def stage_class(stage: str) -> str:
    if stage in {"렌더 완료", "영상 준비됨", "카드뉴스 완료"}:
        return "ok"
    if stage in {"이미지 있음"}:
        return "warn"
    return "muted"

def card_row(slug: str) -> dict:
    out = CARD_OUTPUT / slug
    img = CARD_IMAGES / slug
    article = CARD_ARTICLES / f"{slug}.json"
    captions = out / "captions.md"
    prompt_md = img / "prompt.md"
    shorts_script = out / "shorts_script.json"
    image_count = card_image_count(slug)
    card_count = count_files(out, ("card_*.jpg", "card_*.png"))
    mtimes = []
    for path in (out, img, article, captions, prompt_md, shorts_script):
        try:
            if path.exists():
                mtimes.append(path.stat().st_mtime)
        except OSError:
            pass
    mtime = max(mtimes) if mtimes else 0.0
    done = card_done(slug)
    if done:
        status = "완료"
    elif image_count >= 5:
        status = "렌더 준비"
    elif prompt_md.exists():
        status = "이미지 대기"
    elif article.exists():
        status = "후보"
    else:
        status = "부분"
    row = {
        "slug": slug,
        "title": article_title(slug),
        "status": status,
        "cards": card_count,
        "images": image_count,
        "article": article.exists(),
        "captions": captions.exists(),
        "prompt": prompt_md.exists(),
        "script": shorts_script.exists(),
        "done": done,
        "mtime": mtime,
        "date": time.strftime("%Y.%m.%d", time.localtime(mtime)) if mtime else "",
    }
    stage = card_stage(row)
    row["stage"] = stage
    row["stageClass"] = stage_class(stage)
    return row


def slug_sort_key(item: dict) -> tuple[int, str]:
    slug = str(item.get("slug") or "")
    head = slug.split("_", 1)[0]
    if head.isdigit():
        return (int(head), slug)
    return (999999, slug)


def get_cardnews_rows() -> list[dict]:
    names: set[str] = set()
    for root in (CARD_OUTPUT, CARD_IMAGES):
        if root.exists():
            names.update(p.name for p in root.iterdir() if p.is_dir())
    if CARD_ARTICLES.exists():
        names.update(p.stem for p in CARD_ARTICLES.glob("*.json"))
    rows = [card_row(name) for name in names if SAFE_SLUG.match(name)]
    rows.sort(key=slug_sort_key)
    return rows[:80]




def github_status() -> dict:
    status_file = DESK / "TEMP" / "github_status.json"
    script = DESK / "MAINTENANCE" / "codex_github_status.py"
    cached = None
    if status_file.exists():
        try:
            cached = json.loads(status_file.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            cached = None
    try:
        stale = (not status_file.exists()) or (time.time() - status_file.stat().st_mtime > 60)
        if stale and script.exists():
            subprocess.run(
                [sys.executable, str(script)],
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=25,
            )
            if status_file.exists():
                cached = json.loads(status_file.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "class": "warn", "message": "GitHub 상태 확인 실패", "detail": str(exc)}
    return cached or {"ok": False, "class": "warn", "message": "GitHub 상태 미확인", "detail": "상태 파일 없음"}


def sync_status() -> dict:
    status_file = DESK / "TEMP" / "cardnews_sync_status.json"
    local_root = str(ROOT)
    network = local_root.startswith("\\\\")
    status = {
        "ok": False,
        "message": "아직 동기화 기록이 없습니다.",
        "source": "",
        "target": str(CARDNEWS),
        "endedAt": "",
        "articles": len(list(CARD_ARTICLES.glob("*.json"))) if CARD_ARTICLES.exists() else 0,
        "images": len([p for p in CARD_IMAGES.iterdir() if p.is_dir()]) if CARD_IMAGES.exists() else 0,
        "output": len([p for p in CARD_OUTPUT.iterdir() if p.is_dir()]) if CARD_OUTPUT.exists() else 0,
        "rootMode": "네트워크 실행" if network else "로컬 실행",
        "rootOk": not network,
    }
    if status_file.exists():
        try:
            saved = json.loads(status_file.read_text(encoding="utf-8-sig"))
            if isinstance(saved, dict):
                status.update(saved)
        except Exception as exc:
            status["message"] = f"동기화 상태 파일 읽기 실패: {exc}"
    return status

def cors_headers(handler: BaseHTTPRequestHandler) -> None:
    origin = handler.headers.get("Origin", "")
    if origin and origin_allowed(handler, origin):
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def origin_allowed(handler: BaseHTTPRequestHandler, origin: str) -> bool:
    if not origin:
        return True
    host = handler.headers.get("Host", "")
    if origin in {f"http://{host}", f"https://{host}"}:
        return True
    return origin.startswith("https://script.google.com") or origin.endswith(".googleusercontent.com")


def json_response(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    cors_headers(handler)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def html_response(handler: BaseHTTPRequestHandler, page: str, status: int = 200) -> None:
    payload = page.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    cors_headers(handler)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def bytes_response(
    handler: BaseHTTPRequestHandler,
    payload: bytes,
    content_type: str,
    status: int = 200,
    filename: str = "",
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    cors_headers(handler)
    if filename:
        handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def file_response(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
    cors_headers(handler)
    handler.send_header("Content-Length", str(path.stat().st_size))
    handler.end_headers()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            handler.wfile.write(chunk)


def read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8", errors="replace")
    return json.loads(raw or "{}")


def cmd_video_runner(slug: str) -> list[str]:
    return [str(SHORTS / "run_codex_casual.bat"), validate_slug(slug)]


def cmd_card_runner(slug: str) -> list[str]:
    return [str(CARDNEWS / "run_pngs.bat"), card_prefix(slug)]


def safe_open(path: Path) -> None:
    if path.is_dir():
        os.startfile(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    os.startfile(path)


def safe_open_existing(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"경로가 없습니다: {path}")
    os.startfile(path)


def start_card_webui(slug: str = "") -> None:
    start_bat = CARDNEWS / "webui" / "start.bat"
    if start_bat.exists():
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
             f"Start-Process -FilePath '{start_bat}' -WorkingDirectory '{start_bat.parent}' -WindowStyle Minimized"],
            cwd=str(CARDNEWS),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    target = f"http://localhost:8080/slug/{slug}" if slug else "http://localhost:8080/"
    webbrowser.open(target)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        cors_headers(self)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            json_response(self, {"ok": True, "service": "phonespot-panel", "version": PANEL_VERSION})
            return
        if parsed.path == "/api/illust-thumb":
            # 검수 모달용 썸네일. 허용된 폴더(DROP/Downloads/일러스트) 안의 이미지만 제공.
            query = urllib.parse.parse_qs(parsed.query)
            raw = (query.get("path") or [""])[0]
            roots = (DESK / "ILLUSTRATION_DROP", DOWNLOADS, SHORTS / "public" / "assets" / "illustrations", CARD_IMAGES)
            try:
                target = Path(unquote(raw)).resolve()
            except Exception:
                json_response(self, {"ok": False, "error": "bad path"}, 400)
                return
            allowed = False
            for root in roots:
                try:
                    target.relative_to(root.resolve())
                    allowed = True
                    break
                except (ValueError, OSError):
                    continue
            if (not allowed) or (not target.is_file()) or target.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                json_response(self, {"ok": False, "error": "not allowed"}, 403)
                return
            ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(target.suffix.lower().lstrip("."), "application/octet-stream")
            try:
                bytes_response(self, target.read_bytes(), ctype)
            except OSError:
                json_response(self, {"ok": False, "error": "read fail"}, 404)
            return
        if parsed.path == "/":
            html_response(self, INDEX_HTML)
            return
        if parsed.path == "/prompt":
            path = DESK / "LATEST_PROMPT.md"
            body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "LATEST_PROMPT.md가 없습니다."
            page = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>최신 이미지 프롬프트</title>"
                "<style>body{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}"
                "pre{white-space:pre-wrap;font-size:15px;background:#f7f7f8;border:1px solid #ddd;padding:18px;border-radius:8px}"
                "button{padding:10px 14px;border:0;border-radius:8px;background:#111;color:white;cursor:pointer}"
                "button:hover{background:#F74B0B}</style>"
                "<script>async function copyAllPrompt(){const el=document.getElementById('promptText');const text=el?el.innerText:'';try{await navigator.clipboard.writeText(text);alert('전체 복사했습니다.');}catch(e){const t=document.createElement('textarea');t.value=text;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();alert('전체 복사했습니다.');}}</script>"
                "</head><body><h1>최신 영상용 이미지 프롬프트</h1><p><button onclick='copyAllPrompt()'>전체 복사</button></p><pre id='promptText'>"
                + html.escape(body)
                + "</pre></body></html>"
            )
            html_response(self, page)
            return
        if parsed.path.startswith("/illustration-requests/"):
            slug = validate_slug(unquote(parsed.path.split("/illustration-requests/", 1)[1]))
            path = CARD_OUTPUT / slug / "codex_illustration_requests.md"
            body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "아직 생성된 일러스트 요청서가 없습니다. 먼저 영상용 프롬프트 준비를 실행하세요."
            page = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>영상 일러스트 요청서</title>"
                "<style>"
                "body{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}"
                ".bar{display:flex;gap:8px;align-items:center;margin:12px 0 18px}"
                "pre{white-space:pre-wrap;font-size:15px;background:#f7f7f8;border:1px solid #ddd;padding:18px;border-radius:8px}"
                "button{padding:10px 14px;border:0;border-radius:8px;background:#111;color:white;cursor:pointer}"
                "button:hover{background:#F74B0B}"
                ".hint{color:#64748b;font-size:13px}"
                "</style>"
                "<script>"
                "async function copyAllPrompt(){"
                "const el=document.getElementById('promptText');"
                "const text=el?el.innerText:'';"
                "try{await navigator.clipboard.writeText(text);alert('전체 복사했습니다.');}"
                "catch(e){const t=document.createElement('textarea');t.value=text;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();alert('전체 복사했습니다.');}"
                "}"
                "</script>"
                "</head><body><h1>영상 일러스트 요청서</h1><p><b>"
                + html.escape(slug)
                + "</b></p><div class='bar'><button onclick='copyAllPrompt()'>전체 복사</button>"
                + "<span class='hint'>GPT Plus에 붙여넣고, 생성 이미지를 ILLUSTRATION_DROP에 저장하세요.</span></div>"
                + "<pre id='promptText'>"
                + html.escape(body)
                + "</pre></body></html>"
            )
            html_response(self, page)
            return
        if parsed.path.startswith("/card-prompt/"):
            slug = validate_slug(unquote(parsed.path.split("/card-prompt/", 1)[1]))
            path = CARD_IMAGES / slug / "prompt.md"
            body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "prompt.md가 없습니다."
            page = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>카드뉴스 이미지 프롬프트</title>"
                "<style>"
                "body{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}"
                "pre{white-space:pre-wrap;font-size:15px;background:#f7f7f8;border:1px solid #ddd;padding:18px;border-radius:8px}"
                "button{padding:10px 14px;border:0;border-radius:8px;background:#111;color:white;cursor:pointer}"
                "button:hover{background:#F74B0B}"
                "</style>"
                "<script>"
                "async function copyAllPrompt(){"
                "const el=document.getElementById('promptText');"
                "const text=el?el.innerText:'';"
                "try{await navigator.clipboard.writeText(text);alert('전체 복사했습니다.');}"
                "catch(e){const t=document.createElement('textarea');t.value=text;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();alert('전체 복사했습니다.');}"
                "}"
                "</script>"
                "</head><body><h1>카드뉴스 이미지 프롬프트</h1><p>"
                + html.escape(slug)
                + "</p><p><button onclick='copyAllPrompt()'>전체 복사</button></p><pre id='promptText'>"
                + html.escape(body)
                + "</pre></body></html>"
            )
            html_response(self, page)
            return
        if parsed.path == "/api/state":
            payload = prompt_payload()
            missing = missing_requests(payload)
            gaps = payload.get("uncovered_gaps", []) or []
            with STATE_LOCK:
                local_job = dict(JOB)
            remote_job = REMOTE_QUEUE.panel_job()
            job = select_panel_job(local_job, remote_job)
            workers = REMOTE_QUEUE.workers()
            online_workers = [worker for worker in workers.values() if worker.get("online")]
            json_response(self, {
                "root": str(ROOT),
                "version": PANEL_VERSION,
                "desk": str(DESK),
                "latestSlug": latest_slug(),
                "requests": len(payload.get("requests", []) or []),
                "missingRequests": len(missing),
                "recentDownloads": count_recent_downloads(),
                "weakMappings": len(gaps),
                "canImport": len(missing) == 0,
                "job": job,
                "workers": workers,
                "onlineWorkers": len(online_workers),
                "readyWorkers": len([worker for worker in online_workers if worker.get("ready", True)]),
                "results": results_list(),
                "sync": sync_status(),
                "github": github_status(),
            })
            return
        if parsed.path == "/api/slugs":
            json_response(self, {"slugs": get_video_slugs()})
            return
        if parsed.path == "/api/cardnews/slugs":
            json_response(self, {"rows": get_cardnews_rows()})
            return
        if parsed.path == "/api/illustration-requests":
            query = urllib.parse.parse_qs(parsed.query)
            slug = validate_slug((query.get("slug") or [""])[0])
            md_path = CARD_OUTPUT / slug / "codex_illustration_requests.md"
            json_path = CARD_OUTPUT / slug / "codex_illustration_requests.json"
            payload = {"slug": slug, "exists": md_path.exists(), "count": 0, "gaps": 0, "path": str(md_path)}
            if json_path.exists():
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8-sig"))
                    payload["count"] = len(data.get("requests") or [])
                    payload["gaps"] = len(data.get("uncovered_gaps") or [])
                    payload["requests"] = data.get("requests") or []
                except Exception as exc:
                    payload["error"] = str(exc)
            json_response(self, payload)
            return
        if parsed.path == "/api/preflight":
            query = urllib.parse.parse_qs(parsed.query)
            slug = validate_slug((query.get("slug") or [""])[0])
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "codex_preflight_check.py"), slug, "--json"],
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            try:
                payload = json.loads(proc.stdout)
            except Exception:
                payload = {"slug": slug, "status": "ERROR", "errors": 1, "warnings": 0, "items": [
                    {"level": "ERROR", "message": "사전검사 결과를 읽지 못했습니다.", "detail": (proc.stdout + "\n" + proc.stderr).strip()}
                ]}
            payload["exitCode"] = proc.returncode
            json_response(self, payload)
            return
        if parsed.path == "/api/weak-mappings":
            payload = prompt_payload()
            gaps = payload.get("uncovered_gaps", []) or []
            json_response(self, {
                "count": len(gaps),
                "rows": weak_mapping_rows(),
                "visuals": available_visuals(),
                "parseError": bool(payload.get("parse_error")),
            })
            return
        if parsed.path == "/api/chunks":
            query = urllib.parse.parse_qs(parsed.query)
            slug = validate_slug((query.get("slug") or [latest_slug()])[0])
            json_response(self, {"slug": slug, "rows": chunk_rows_for_slug(slug)})
            return
        if parsed.path == "/api/job":
            remote_job = REMOTE_QUEUE.panel_job()
            with STATE_LOCK:
                local_job = dict(JOB)
            job = select_panel_job(local_job, remote_job)
            json_response(self, {"job": job})
            return
        if parsed.path == "/api/jobs":
            query = urllib.parse.parse_qs(parsed.query)
            try:
                limit = int((query.get("limit") or ["50"])[0])
            except ValueError:
                limit = 50
            json_response(self, {"rows": job_history(limit)})
            return
        if parsed.path == "/api/result":
            query = urllib.parse.parse_qs(parsed.query)
            folder_name = validate_slug((query.get("folder") or [""])[0])
            file_name = Path((query.get("file") or [""])[0]).name
            if not file_name.lower().endswith(".mp4"):
                raise RuntimeError("MP4 파일만 다운로드할 수 있습니다.")
            result_root = (DESK / "RESULTS").resolve()
            path = (result_root / folder_name / file_name).resolve()
            if result_root not in path.parents or not path.is_file():
                raise RuntimeError("결과 파일이 없습니다.")
            file_response(self, path, "video/mp4")
            return
        if parsed.path == "/api/worker/package":
            query = urllib.parse.parse_qs(parsed.query)
            job_id = (query.get("job_id") or [""])[0]
            payload = REMOTE_QUEUE.package_bytes(job_id)
            bytes_response(self, payload, "application/zip", filename=f"phonespot_job_{job_id}.zip")
            return
        json_response(self, {"error": "not found"}, 404)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            origin = self.headers.get("Origin", "")
            if origin and not origin_allowed(self, origin):
                json_response(self, {"ok": False, "error": "origin not allowed"}, 403)
                return
            if parsed.path == "/api/shutdown":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    json_response(self, {"ok": False, "error": "local request required"}, 403)
                    return
                json_response(self, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if parsed.path == "/api/worker/result":
                query = urllib.parse.parse_qs(parsed.query)
                job_id = (query.get("job_id") or [""])[0]
                length = int(self.headers.get("Content-Length", "0") or "0")
                filename = self.headers.get("X-File-Name", "result.mp4")
                path = REMOTE_QUEUE.save_result_stream(job_id, filename, self.rfile, length)
                json_response(self, {"ok": True, "path": str(path)})
                return
            if parsed.path == "/api/upload":
                query = urllib.parse.parse_qs(parsed.query)
                kind = (query.get("kind") or [""])[0]
                slug = (query.get("slug") or [""])[0]
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0 or length > 30 * 1024 * 1024:
                    raise RuntimeError("이미지 파일은 30MB 이하만 업로드할 수 있습니다.")
                filename = Path(self.headers.get("X-File-Name", "")).name
                suffix = Path(filename).suffix.lower()
                if not filename or suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                    raise RuntimeError("PNG, JPG, JPEG, WEBP 이미지만 업로드할 수 있습니다.")
                if kind == "card":
                    target_dir = CARD_IMAGES / validate_slug(slug)
                elif kind == "illustration":
                    target_dir = DESK / "ILLUSTRATION_DROP"
                else:
                    raise RuntimeError("알 수 없는 업로드 종류입니다.")
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / filename
                target.write_bytes(self.rfile.read(length))
                json_response(self, {"ok": True, "name": filename, "path": str(target)})
                return
            data = read_body(self)
            if parsed.path == "/api/worker/register":
                worker_id = str(data.get("worker_id") or "").strip()
                if not worker_id:
                    raise RuntimeError("worker_id is required")
                worker = REMOTE_QUEUE.register(worker_id, data)
                json_response(self, {"ok": True, "worker": worker})
                return
            if parsed.path == "/api/worker/claim":
                worker_id = str(data.get("worker_id") or "").strip()
                if not worker_id:
                    raise RuntimeError("worker_id is required")
                job = REMOTE_QUEUE.claim(worker_id, str(data.get("instance_id") or ""))
                json_response(self, {"ok": True, "job": job})
                return
            if parsed.path == "/api/worker/check":
                job_id = str(data.get("job_id") or "").strip()
                worker_id = str(data.get("worker_id") or "").strip()
                # 워커가 5초마다 보내는 이 핑으로 job 리스를 갱신한다. 이게 없으면
                # Remotion 렌더가 90초 넘게 조용한 구간(번들링/프레임)에서 리스가 만료돼
                # 살아있는 워커의 렌더가 헛되이 재시작된다(worker lease expired; retry).
                if worker_id and job_id:
                    REMOTE_QUEUE.heartbeat(worker_id, "running", job_id)
                json_response(self, {
                    "ok": True,
                    "cancel_requested": REMOTE_QUEUE.is_cancel_requested(job_id),
                })
                return
            if parsed.path == "/api/worker/log":
                worker_id = str(data.get("worker_id") or "").strip()
                job_id = str(data.get("job_id") or "").strip()
                REMOTE_QUEUE.append_log(job_id, str(data.get("text") or ""))
                if worker_id:
                    REMOTE_QUEUE.heartbeat(worker_id, "running", job_id)
                json_response(self, {"ok": True})
                return
            if parsed.path == "/api/worker/complete":
                job = REMOTE_QUEUE.complete(
                    str(data.get("job_id") or ""),
                    str(data.get("worker_id") or ""),
                    bool(data.get("ok")),
                    int(data.get("exit_code") or 0),
                    str(data.get("message") or ""),
                )
                telegram_send(telegram_job_message(f"remote render: {job.get('slug')}", int(job.get("exit_code") or 0)))
                json_response(self, {"ok": True, "job": job})
                return
            action = data.get("action")
            slug = (data.get("slug") or latest_slug()).strip()
            if action == "sync_cardnews":
                sync_script = DESK / "SYNC_CARDNEWS_WORKSPACE_FROM_MAIN_PC.ps1"
                if not sync_script.exists():
                    json_response(self, {"ok": False, "message": f"동기화 스크립트가 없습니다: {sync_script}"})
                    return
                ok = run_job("카드뉴스 동기화 새로고침", [["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_script)]], DESK)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "library_sync":
                # 일러스트 라이브러리 공유 허브와 양방향 추가병합(비파괴). 결과는 실행 로그에.
                ok = run_job("일러스트 라이브러리 공유 동기화",
                             [[sys.executable, str(SCRIPTS / "codex_library_sync.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "라이브러리 동기화 실행 — 실행 로그에서 가져옴/올림 개수를 확인하세요."})
                return
            if action == "library_dedup":
                # 라이브러리 근접중복 '리포트만'(읽기전용, 안전). 실제 정리는 bat --apply.
                ok = run_job("라이브러리 중복 점검(리포트)",
                             [[sys.executable, str(SCRIPTS / "codex_library_dedup.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "중복 점검 완료 — 실행 로그와 codex/library_dedup_report.md 확인."})
                return
            if action == "library_backup":
                # 라이브러리(로컬+허브) 타임스탬프 스냅샷 백업(회전보관). 결과는 실행 로그에.
                ok = run_job("라이브러리 백업 스냅샷",
                             [[sys.executable, str(SCRIPTS / "codex_library_backup.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "라이브러리 백업 완료 — 실행 로그에서 위치/개수를 확인하세요."})
                return
            if action == "producer_check":
                # 이 PC가 카드뉴스 생성 + 영상 렌더를 모두 독립으로 할 수 있는지 자원 점검. 결과는 실행 로그에.
                ok = run_job("환경 점검(풀-생산기 자원)",
                             [[sys.executable, str(SCRIPTS / "codex_producer_check.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "환경 점검 실행 — 실행 로그에서 PASS/FAIL을 확인하세요."})
                return
            if action == "delete_slug":
                # 슬러그(주제) 삭제: 기사 JSON + 카드 output/images + 청크오버라이드 + 렌더 결과를 로컬에서 제거.
                # 안전: SAFE_SLUG 검증으로 경로 탈출 방지. best-effort(없는 건 건너뜀).
                try:
                    slug_now = validate_slug(slug)
                except RuntimeError as exc:
                    json_response(self, {"ok": False, "message": str(exc)})
                    return
                targets = [
                    CARD_ARTICLES / f"{slug_now}.json",
                    CARD_OUTPUT / slug_now,
                    CARD_IMAGES / slug_now,
                    CHUNK_OVERRIDES / f"{slug_now}.json",
                ]
                rroot = DESK / "RESULTS"
                if rroot.exists():
                    for p in rroot.iterdir():
                        if slug_now in p.name:
                            targets.append(p)
                deleted = 0
                for t in targets:
                    try:
                        if t.is_dir():
                            shutil.rmtree(t, ignore_errors=True)
                            deleted += 1
                        elif t.exists():
                            t.unlink()
                            deleted += 1
                    except OSError:
                        pass
                json_response(self, {
                    "ok": True,
                    "message": f"'{slug_now}' 삭제: 항목 {deleted}개 제거. (git 추적 기사라면 push해야 다른 PC에도 반영)",
                })
                return
            if action == "video_prepare":
                slug = validate_slug(slug)
                commands = [
                    [sys.executable, str(SCRIPTS / "codex_prepare_illustrations.py"), slug],
                    [sys.executable, str(SCRIPTS / "codex_clean_latest_prompt.py"), slug],
                ]
                ok = run_job("영상 이미지 프롬프트 준비", commands, SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "video_import_propose":
                # 그림 내용(CLIP)으로 후보 -> 요청 자동 배정을 '제안'만 한다(파일 미이동).
                slug_now = validate_slug(slug)
                proc = subprocess.run(
                    [sys.executable, str(SCRIPTS / "codex_import_propose.py"), slug_now],
                    cwd=str(SHORTS), text=True, encoding="utf-8", errors="replace",
                    capture_output=True,
                )
                proposal_path = DESK / "IMPORT_PROPOSAL.json"
                proposal = {}
                if proposal_path.exists():
                    try:
                        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        json_response(self, {"ok": False, "message": f"제안 파일을 읽지 못했습니다: {exc}"})
                        return
                else:
                    json_response(self, {"ok": False, "message": "제안을 생성하지 못했습니다.\n" + (proc.stdout or "")[-400:]})
                    return
                json_response(self, {"ok": True, "proposal": proposal})
                return
            if action == "video_import_confirm":
                # 사람이 패널에서 확정한 매핑을 기록한 뒤, 기존 렌더 대기열에 등록.
                slug_now = validate_slug(slug)
                raw_mapping = data.get("mapping") or []
                roots = (DESK / "ILLUSTRATION_DROP", DOWNLOADS, SHORTS / "public" / "assets" / "illustrations")
                allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
                mapping = []
                seen_fn = set()
                for entry in raw_mapping:
                    fn = str((entry or {}).get("filename") or "").strip()
                    src_raw = str((entry or {}).get("candidate_path") or "").strip()
                    if not fn or not src_raw:
                        continue
                    if fn != Path(fn).name or Path(fn).suffix.lower() not in allowed_ext:
                        json_response(self, {"ok": False, "message": f"잘못된 대상 파일명: {fn}"})
                        return
                    if fn in seen_fn:
                        json_response(self, {"ok": False, "message": f"같은 파일명이 두 번 선택됐습니다: {fn}"})
                        return
                    try:
                        src = Path(src_raw).resolve()
                    except OSError:
                        json_response(self, {"ok": False, "message": "잘못된 경로"})
                        return
                    ok_root = False
                    for root in roots:
                        try:
                            src.relative_to(root.resolve())
                            ok_root = True
                            break
                        except (ValueError, OSError):
                            continue
                    if not ok_root or not src.is_file() or src.suffix.lower() not in allowed_ext:
                        json_response(self, {"ok": False, "message": f"허용되지 않은 파일: {src_raw}"})
                        return
                    seen_fn.add(fn)
                    mapping.append({"candidate_path": str(src), "filename": fn})
                if not mapping:
                    json_response(self, {"ok": False, "message": "확정할 매핑이 없습니다. 최소 한 장은 배정하세요."})
                    return
                confirmed = {"slug": slug_now, "generated_at": time.time(), "mapping": mapping}
                (DESK / "IMPORT_CONFIRMED.json").write_text(
                    json.dumps(confirmed, ensure_ascii=False, indent=2), encoding="utf-8")
                job = REMOTE_QUEUE.enqueue(
                    "video_import_render", slug_now, str(data.get("target_worker") or ""))
                json_response(self, {
                    "ok": True, "queued": True, "job": job,
                    "message": f"{len(mapping)}장 확정 → 가져오고 렌더 대기열에 등록했습니다.",
                })
                return
            if action == "card_import_propose":
                # 카드뉴스: 다운로드 그림을 슬라이드 내용(CLIP)으로 N.png 에 자동 배정 '제안'.
                slug_now = validate_slug(slug)
                proc = subprocess.run(
                    [sys.executable, str(SCRIPTS / "cardnews_import_propose.py"), slug_now],
                    cwd=str(SHORTS), text=True, encoding="utf-8", errors="replace",
                    capture_output=True,
                )
                proposal_path = DESK / "CARD_IMPORT_PROPOSAL.json"
                if proposal_path.exists():
                    try:
                        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        json_response(self, {"ok": False, "message": f"제안 파일을 읽지 못했습니다: {exc}"})
                        return
                else:
                    json_response(self, {"ok": False, "message": "제안을 생성하지 못했습니다.\n" + (proc.stdout or "")[-400:]})
                    return
                json_response(self, {"ok": True, "proposal": proposal})
                return
            if action == "card_import_confirm":
                # 사람이 확정한 매핑대로 카드 이미지 폴더에 N.png 로 복사(렌더 큐 안 씀).
                slug_now = validate_slug(slug)
                raw_mapping = data.get("mapping") or []
                img_dir = CARD_IMAGES / slug_now
                roots = (CARD_IMAGES, DOWNLOADS)
                allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
                plan = []
                seen_fn = set()
                for entry in raw_mapping:
                    fn = str((entry or {}).get("filename") or "").strip()
                    src_raw = str((entry or {}).get("candidate_path") or "").strip()
                    if not fn or not src_raw:
                        continue
                    if not re.fullmatch(r"\d+\.png", fn):
                        json_response(self, {"ok": False, "message": f"잘못된 슬라이드 파일명: {fn}"})
                        return
                    if fn in seen_fn:
                        json_response(self, {"ok": False, "message": f"같은 슬라이드가 두 번 선택됐습니다: {fn}"})
                        return
                    try:
                        src = Path(src_raw).resolve()
                    except OSError:
                        json_response(self, {"ok": False, "message": "잘못된 경로"})
                        return
                    ok_root = False
                    for root in roots:
                        try:
                            src.relative_to(root.resolve())
                            ok_root = True
                            break
                        except (ValueError, OSError):
                            continue
                    if not ok_root or not src.is_file() or src.suffix.lower() not in allowed_ext:
                        json_response(self, {"ok": False, "message": f"허용되지 않은 파일: {src_raw}"})
                        return
                    seen_fn.add(fn)
                    plan.append((src, img_dir / fn))
                if not plan:
                    json_response(self, {"ok": False, "message": "확정할 매핑이 없습니다. 최소 한 장은 배정하세요."})
                    return
                img_dir.mkdir(parents=True, exist_ok=True)
                for src, dst in plan:
                    dst.write_bytes(src.read_bytes())
                json_response(self, {"ok": True, "message": f"{len(plan)}장 배정 완료. 이제 '4. 카드뉴스 생성'을 누르세요."})
                return
            if action == "video_import_render":
                slug_now = validate_slug(slug)
                job = REMOTE_QUEUE.enqueue(
                    "video_import_render",
                    slug_now,
                    str(data.get("target_worker") or ""),
                )
                json_response(self, {
                    "ok": True,
                    "queued": True,
                    "job": job,
                    "message": "렌더 작업을 대기열에 등록했습니다.",
                })
                return
            if action == "video_render_selected":
                slug = validate_slug(slug)
                job = REMOTE_QUEUE.enqueue(
                    "video_render_selected",
                    slug,
                    str(data.get("target_worker") or ""),
                )
                json_response(self, {
                    "ok": True,
                    "queued": True,
                    "job": job,
                    "message": "선택 영상 렌더를 대기열에 등록했습니다.",
                })
                return
            if action == "remote_job_cancel":
                job = REMOTE_QUEUE.cancel(str(data.get("job_id") or ""))
                json_response(self, {"ok": True, "job": job})
                return
            if action == "remote_job_retry":
                job = REMOTE_QUEUE.retry(str(data.get("job_id") or ""))
                json_response(self, {"ok": True, "job": job})
                return
            if action == "card_render":
                slug = validate_slug(slug)
                ok = run_job(f"카드뉴스 생성: {slug}", [cmd_card_runner(slug)], CARDNEWS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "card_to_video":
                slug = validate_slug(slug)
                commands = [
                    [sys.executable, str(SCRIPTS / "codex_prepare_illustrations.py"), slug],
                    [sys.executable, str(SCRIPTS / "codex_clean_latest_prompt.py"), slug],
                ]
                ok = run_job("카드뉴스를 영상 준비로 넘기기", commands, SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "delete_slug":
                slug = validate_slug(slug)
                removed = []
                for t in (CARD_ARTICLES / f"{slug}.json", CARD_IMAGES / slug, CARD_OUTPUT / slug):
                    try:
                        if t.is_dir():
                            shutil.rmtree(t); removed.append(t.name)
                        elif t.exists():
                            t.unlink(); removed.append(t.name)
                    except OSError as exc:
                        json_response(self, {"ok": False, "message": f"삭제 실패: {t} ({exc})"})
                        return
                json_response(self, {"ok": True, "message": f"삭제됨: {slug} (" + (", ".join(removed) or "대상 없음") + ")"})
                return
            if action == "open_prompt":
                safe_open(DESK / "LATEST_PROMPT.md")
                json_response(self, {"ok": True})
                return
            if action == "open_results":
                safe_open(DESK / "RESULTS")
                json_response(self, {"ok": True})
                return
            if action == "open_illustrations":
                safe_open(DESK / "ILLUSTRATION_DROP")
                json_response(self, {"ok": True})
                return
            if action == "open_desk":
                safe_open(DESK)
                json_response(self, {"ok": True})
                return
            if action == "work_queue_refresh":
                ok = run_job("작업대장 새로고침", [[sys.executable, str(SCRIPTS / "codex_work_queue.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "open_work_queue":
                WORK_QUEUE.mkdir(parents=True, exist_ok=True)
                safe_open(WORK_QUEUE)
                json_response(self, {"ok": True})
                return
            if action == "open_work_queue_tsv":
                path = WORK_QUEUE / "phonespot_work_queue.tsv"
                if not path.exists():
                    subprocess.run([sys.executable, str(SCRIPTS / "codex_work_queue.py")], cwd=str(ROOT), check=False)
                safe_open_existing(path)
                json_response(self, {"ok": True})
                return
            if action == "open_work_queue_md":
                path = WORK_QUEUE / "phonespot_work_queue.md"
                if not path.exists():
                    subprocess.run([sys.executable, str(SCRIPTS / "codex_work_queue.py")], cwd=str(ROOT), check=False)
                safe_open_existing(path)
                json_response(self, {"ok": True})
                return
            if action == "system_upload":
                ok = run_job("시스템 업로드: GitHub commit/push", [[sys.executable, str(DESK / "MAINTENANCE" / "codex_github_upload.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "system_update":
                ok = run_job("시스템 업데이트: GitHub pull", [[sys.executable, str(DESK / "MAINTENANCE" / "codex_github_update.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "open_card_output":
                slug = validate_slug(slug)
                safe_open_existing(CARD_OUTPUT / slug)
                json_response(self, {"ok": True})
                return
            if action == "open_card_images":
                slug = validate_slug(slug)
                (CARD_IMAGES / slug).mkdir(parents=True, exist_ok=True)
                safe_open(CARD_IMAGES / slug)
                json_response(self, {"ok": True})
                return
            if action == "open_card_prompt":
                slug = validate_slug(slug)
                safe_open_existing(CARD_IMAGES / slug / "prompt.md")
                json_response(self, {"ok": True})
                return
            if action == "open_card_result":
                slug = validate_slug(slug)
                safe_open_existing(CARD_OUTPUT / slug)
                json_response(self, {"ok": True})
                return
            if action == "open_card_webui":
                slug = validate_slug(slug) if slug else ""
                start_card_webui(slug)
                json_response(self, {"ok": True})
                return
            if action == "open_card_root":
                safe_open_existing(CARDNEWS)
                json_response(self, {"ok": True})
                return
            if action == "update_visual":
                slug = validate_slug(data.get("slug") or latest_slug())
                section = data.get("section") or ""
                chunk_index = int(data.get("chunk_index", 0))
                visual_type = data.get("visual_type") or ""
                visual_value = data.get("visual_value") or ""
                path = update_chunk_visual(slug, section, chunk_index, visual_type, visual_value)
                json_response(self, {"ok": True, "path": str(path)})
                return
            if action == "adjust_chunk":
                slug = validate_slug(data.get("slug") or latest_slug())
                section = data.get("section") or ""
                chunk_index = int(data.get("chunk_index", 0))
                op = data.get("op") or ""
                path = adjust_chunk_boundary(slug, section, chunk_index, op)
                json_response(self, {"ok": True, "path": str(path)})
                return
            if action == "set_section_chunks":
                try:
                    slug = validate_slug(data.get("slug") or latest_slug())
                    path = set_section_chunks(slug, data.get("section") or "", data.get("text") or "")
                    json_response(self, {"ok": True, "path": str(path)})
                except Exception as exc:  # noqa: BLE001
                    json_response(self, {"ok": False, "message": str(exc)})
                return
            if action == "telegram_card_summary":
                ok = telegram_send(cardnews_summary())
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "telegram_test":
                ok = telegram_send("✅ <b>폰스팟 제작 패널</b>\n텔레그램 알림 테스트가 정상 전송되었습니다.")
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            raise RuntimeError(f"알 수 없는 액션입니다: {action}")
        except Exception as exc:
            json_response(self, {"ok": False, "error": str(exc)}, 500)


INDEX_HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>폰스팟 통합 제작 패널</title>
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css" />
  <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css');
    :root{
      --system-bg:#F2F2F7; --card-bg:#FFFFFF; --secondary-bg:#F2F2F7; --tertiary-bg:#FAFAFA;
      --label:#1D1D1F; --label-secondary:#3C3C43; --label-tertiary:#86868B; --label-quaternary:#C7C7CC;
      --separator:rgba(60,60,67,.12); --separator-opaque:#E5E5EA;
      --accent:#F74B0B; --accent-hover:#D63E06; --accent-soft:rgba(247,75,11,.10); --accent-tint:rgba(247,75,11,.05);
      --success:#34C759; --warning:#FF9500; --danger:#FF3B30;
      --r-sm:6px; --r-md:10px; --r-lg:14px; --r-xl:18px;
      --shadow-subtle:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04),0 0 0 .5px rgba(0,0,0,.04);
      --shadow-card:0 4px 16px rgba(0,0,0,.06),0 1px 3px rgba(0,0,0,.05),0 0 0 .5px rgba(0,0,0,.03);
      --shadow-elevated:0 12px 32px rgba(0,0,0,.13),0 4px 12px rgba(0,0,0,.07);
      --t-fast:150ms cubic-bezier(.4,0,.2,1);
      /* legacy aliases so existing inline var() refs keep working */
      --bg:var(--system-bg); --panel:var(--card-bg); --ink:var(--label); --muted:var(--label-tertiary);
      --line:var(--separator-opaque); --orange:var(--accent); --orange-soft:var(--accent-soft);
      --blue:#0A84FF; --red:var(--danger); --green:#1B7A3D; --r:var(--r-md);
    }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--system-bg); color:var(--label);
      font-family:'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Segoe UI','Malgun Gothic',sans-serif;
      letter-spacing:-.2px; -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale; }
    header { min-height:60px; display:flex; align-items:center; justify-content:space-between; padding:14px 22px;
      background:rgba(255,255,255,.86); backdrop-filter:saturate(180%) blur(20px); -webkit-backdrop-filter:saturate(180%) blur(20px);
      color:var(--label); border-bottom:.5px solid var(--separator); gap:16px; position:sticky; top:0; z-index:20; }
    header strong { font-size:18px; font-weight:700; letter-spacing:-.4px; }
    header span { color:var(--label-tertiary); font-size:13px; word-break:break-all; }
    main { display:grid; grid-template-columns:400px 1fr; gap:16px; padding:16px; max-width:1540px; margin:0 auto; }
    section { background:var(--card-bg); border-radius:var(--r-xl); overflow:hidden; box-shadow:var(--shadow-card); }
    .head { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:.5px solid var(--separator); background:transparent; gap:10px; }
    h2 { margin:0; font-size:16px; font-weight:600; letter-spacing:-.2px; }
    .small { font-size:12px; color:var(--label-tertiary); }
    .pad { padding:16px; }
    .tabs { display:flex; gap:2px; padding:4px; margin:10px; background:rgba(118,118,128,.08); border-radius:var(--r-md); }
    .tab { flex:1; border:none; background:transparent; border-radius:7px; padding:8px; cursor:pointer; font-weight:600; font-size:13px; color:var(--label); transition:var(--t-fast); }
    .tab:hover { color:var(--accent); }
    .tab.active { background:var(--card-bg); color:var(--accent); box-shadow:0 1px 3px rgba(0,0,0,.10); }
    .list { max-height:715px; overflow:auto; }
    .list { padding:7px; max-height:780px; }
    .row { width:100%; border:0; background:var(--card-bg); text-align:left; cursor:pointer; display:grid; grid-template-columns:38px minmax(0,1fr) auto; gap:12px; align-items:center; font-size:13px; padding:13px 12px; border-radius:13px; margin-bottom:5px; transition:var(--t-fast); }
    .row.video, .row.card { grid-template-columns:38px minmax(0,1fr) auto; }
    .row:hover { background:var(--accent-tint); }
    .row.active { background:var(--accent-soft); box-shadow:inset 0 0 0 1px var(--accent); }
    .row-number { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:11px; background:var(--secondary-bg); color:var(--label-secondary); font-size:14px; font-weight:700; line-height:1; flex-shrink:0; }
    .row.active .row-number { background:var(--accent); color:#fff; }
    .row-main { min-width:0; display:flex; flex-direction:column; gap:3px; }
    .slug-name { font-weight:600; font-size:14px; letter-spacing:-.2px; line-height:1.3; overflow-wrap:anywhere; color:var(--label); }
    .row-sub { font-size:12px; color:var(--label-tertiary); line-height:1.35; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .row-date,.flag { color:var(--label-tertiary); font-size:12px; white-space:nowrap; }
    .title-sub { display:block; color:var(--label-tertiary); font-size:12px; margin-top:2px; font-weight:400; line-height:1.35; }
    .flag { font-weight:600; color:var(--accent); }
    .stage-pill { display:inline-flex; align-items:center; justify-content:center; min-width:82px; padding:4px 8px; border-radius:100px; font-size:11px; font-weight:700; border:none; background:rgba(118,118,128,.12); color:var(--label-secondary); }
    .stage-pill.ok { background:rgba(52,199,89,.15); color:#1B7A3D; }
    .stage-pill.warn { background:rgba(255,149,0,.15); color:#B25A00; }
    .stage-pill.muted { background:rgba(118,118,128,.12); color:var(--label-tertiary); }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(160px,1fr)); gap:12px; }
    .action-head { align-items:flex-start; }
    .selected-badge { min-width:300px; max-width:720px; padding:10px 14px; border:none; border-radius:var(--r-md); background:var(--accent-soft); color:var(--label); }
    .selected-badge span { display:block; font-size:12px; color:var(--accent); font-weight:600; margin-bottom:3px; }
    .selected-badge b { display:block; font-size:15px; line-height:1.3; white-space:normal; word-break:break-all; }
    .status-note { margin-top:8px; padding:11px 13px; background:var(--secondary-bg); border:none; border-radius:var(--r-md); line-height:1.45; }
    .btn { border:.5px solid var(--separator); background:var(--card-bg); color:var(--label); border-radius:var(--r-md); min-height:78px; padding:13px; cursor:pointer; text-align:left; box-shadow:var(--shadow-subtle); transition:var(--t-fast); }
    .btn:hover, .btn:focus-visible { background:var(--accent-tint); border-color:var(--accent); transform:translateY(-1px); box-shadow:var(--shadow-elevated); }
    .btn:active { transform:scale(.99); }
    .btn.primary { background:var(--accent-soft); border-color:transparent; }
    .btn.primary strong { color:var(--accent); }
    .btn.compact { min-height:0; padding:10px 12px; box-shadow:none; }
    .btn.compact strong { margin-bottom:0; font-size:13px; } .btn.compact span { display:none; }
    .btn strong { display:block; font-size:14px; font-weight:600; margin-bottom:6px; } .btn span { font-size:12px; color:var(--label-tertiary); line-height:1.35; }
    .btn:hover strong, .btn:hover span, .btn:focus-visible strong, .btn:focus-visible span { color:inherit; }
    .runtime-strip { max-width:1520px; margin:14px auto 0; padding:0 18px; display:grid; grid-template-columns:1.05fr 1.25fr .9fr .9fr; gap:10px; box-sizing:border-box; }
    .runtime-card { border:none; border-radius:var(--r-lg); background:var(--card-bg); padding:12px 14px; min-height:62px; min-width:0; box-shadow:var(--shadow-card); }
    .runtime-card span { display:block; font-size:11px; color:var(--label-tertiary); margin-bottom:5px; }
    .runtime-card b { display:block; font-size:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .runtime-card.good { background:rgba(52,199,89,.06); box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(52,199,89,.4); }
    .runtime-card.bad { background:rgba(255,59,48,.06); box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(255,59,48,.4); }
    .runtime-card.warn { background:rgba(255,149,0,.06); box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(255,149,0,.4); }
    .runtime-action { margin-top:8px; border:none; background:var(--accent-soft); color:var(--accent); border-radius:8px; padding:6px 10px; font-size:11px; font-weight:700; cursor:pointer; transition:var(--t-fast); }
    .runtime-action:hover { background:var(--accent); color:#fff; }
    .runtime-actions { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .runtime-actions .runtime-action { margin-top:8px; }
    .runtime-select { width:100%; margin-top:7px; border:none; background:var(--secondary-bg); border-radius:8px; padding:6px 8px; font-size:11px; font-family:inherit; color:var(--label); }
    .status { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
    .metric { border:none; border-radius:var(--r-md); padding:12px; background:var(--secondary-bg); min-height:72px; } .metric b { display:block; font-size:19px; font-weight:700; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .metric.slug b { font-size:13px; white-space:normal; word-break:break-all; line-height:1.3; }
    .warn { color:var(--danger); } .ok { color:#1B7A3D; }
    .log { height:390px; overflow:auto; background:#1C1C1E; color:#E5E5EA; padding:16px; font-family:'SF Mono',Consolas,monospace; font-size:12px; white-space:pre-wrap; border-radius:0 0 var(--r-lg) var(--r-lg); }
    .results { max-height:170px; overflow:auto; font-size:13px; } .result-row { display:flex; justify-content:space-between; gap:10px; padding:8px 0; border-bottom:.5px solid var(--separator); }
    .result-row > * { min-width:0; }
    .result-row a { overflow-wrap:anywhere; word-break:break-word; color:var(--accent); }
    .history-scroll { max-height:340px; overflow:auto; }
    .history-table { width:100%; min-width:820px; border-collapse:collapse; font-size:12px; }
    .history-table th,.history-table td { padding:10px; border-bottom:.5px solid var(--separator); text-align:left; vertical-align:top; }
    .history-table th { position:sticky; top:0; z-index:1; background:var(--card-bg); color:var(--label-tertiary); font-weight:600; text-transform:uppercase; letter-spacing:.4px; font-size:11px; }
    .history-table td:nth-child(2) { max-width:340px; overflow-wrap:anywhere; }
    .history-status { font-weight:700; white-space:nowrap; }
    .history-status.done { color:#1B7A3D; }
    .history-status.failed,.history-status.cancelled { color:var(--danger); }
    .history-status.running,.history-status.pending { color:#B25A00; }
    .history-result a { display:block; max-width:190px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--accent); }
    .preflight-panel { display:none; border-top:.5px solid var(--separator); background:var(--tertiary-bg); }
    .preflight-list { display:grid; gap:8px; }
    .preflight-item { border:none; border-radius:var(--r-md); padding:10px 12px; background:var(--card-bg); box-shadow:var(--shadow-subtle); font-size:13px; line-height:1.45; }
    .preflight-item.OK { box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(52,199,89,.4); }
    .preflight-item.WARN { box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(255,149,0,.4); }
    .preflight-item.ERROR { box-shadow:var(--shadow-subtle),inset 0 0 0 1px rgba(255,59,48,.4); }
    .preflight-item pre { white-space:pre-wrap; margin:6px 0 0; font-family:'SF Mono',Consolas,monospace; font-size:12px; color:var(--label-secondary); }
    .weak-panel { display:none; border-top:.5px solid var(--separator); background:var(--accent-tint); }
    .weak-table { width:100%; border-collapse:collapse; font-size:12px; }
    .weak-table th,.weak-table td { border-bottom:.5px solid var(--separator); padding:8px; vertical-align:top; text-align:left; }
    .weak-table th { background:var(--accent-soft); color:var(--accent); position:sticky; top:0; font-weight:600; }
    .weak-scroll { max-height:330px; overflow:auto; }
    .weak-table select,.weak-table input { width:100%; border:none; background:var(--card-bg); border-radius:8px; padding:7px; font-size:12px; box-shadow:inset 0 0 0 1px var(--separator); }
    .mini-btn { border:none; color:var(--accent); background:var(--accent-soft); border-radius:8px; padding:6px 10px; cursor:pointer; font-size:12px; font-weight:600; margin:2px; transition:var(--t-fast); }
    .mini-btn:hover { background:var(--accent); color:#fff; }
    .mini-btn:disabled { color:var(--label-quaternary); background:var(--secondary-bg); cursor:not-allowed; }
    .chunk-panel { display:none; border-top:.5px solid var(--separator); background:#F0F6FF; }
    .chunk-table { width:100%; border-collapse:collapse; font-size:12px; }
    .chunk-table th,.chunk-table td { border-bottom:.5px solid var(--separator); padding:8px; vertical-align:top; text-align:left; }
    .chunk-table th { background:#E5F0FF; color:#0A84FF; position:sticky; top:0; font-weight:600; }
    .chunk-text { white-space:pre-wrap; line-height:1.45; }
    .head > button { background:var(--accent); color:#fff; border:none; padding:8px 14px; border-radius:var(--r-md); font-size:13px; font-weight:600; cursor:pointer; transition:var(--t-fast); }
    .head > button:hover { background:var(--accent-hover); }
    .head > button:active { transform:scale(.98); }
    ::-webkit-scrollbar { width:8px; height:8px; }
    ::-webkit-scrollbar-thumb { background:rgba(118,118,128,.3); border-radius:100px; }
    ::-webkit-scrollbar-thumb:hover { background:rgba(118,118,128,.5); }
    ::-webkit-scrollbar-track { background:transparent; }
    @keyframes fadeIn { from{opacity:0;transform:translateY(8px);} to{opacity:1;transform:translateY(0);} }
    section { animation:fadeIn 220ms cubic-bezier(.4,0,.2,1); }
    @media (prefers-reduced-motion:reduce){ *,*::before,*::after{ animation-duration:.01ms!important; transition-duration:.01ms!important; } }
    @media (max-width:1080px) { main { grid-template-columns:1fr; } .grid,.status { grid-template-columns:1fr 1fr; } }
    @media (max-width:700px) {
      header { padding:12px 14px; flex-wrap:wrap; }
      header > span { width:100%; }
      main { padding:10px; }
      .runtime-strip { grid-template-columns:minmax(0,1fr) minmax(0,1fr); padding:0 10px; }
      .grid,.status { grid-template-columns:1fr; }
      .action-head { align-items:stretch; flex-direction:column; }
      .selected-badge { min-width:0; width:100%; }
      .result-row { flex-direction:column; }
    }
  </style>
</head>
<body>
  <header><div><strong>폰스팟 통합 제작 패널</strong> <span>카드뉴스 + 숏폼 영상</span> <span id="panelVersion" style="margin-left:8px;padding:2px 8px;border-radius:10px;background:#eef;color:#334;font-weight:600;font-size:12px"></span></div><span id="rootText"></span></header>
  <div class="runtime-strip">
    <div class="runtime-card" id="runtimeMode"><span>실행 위치</span><b id="runtimeModeText">확인 중</b><select class="runtime-select" id="targetWorker"><option value="">자동 배정</option></select></div>
    <div class="runtime-card" id="runtimeSync"><span>카드뉴스 동기화</span><b id="runtimeSyncText">확인 중</b></div>
    <div class="runtime-card" id="runtimeJob"><span>실행 상태</span><b id="runtimeJobText">대기 중</b><div class="runtime-actions"><button class="runtime-action" id="cancelJobButton" onclick="cancelRemoteJob()" style="display:none">취소</button><button class="runtime-action" id="retryJobButton" onclick="retryRemoteJob()" style="display:none">재시도</button></div></div>
    <div class="runtime-card" id="runtimeGithub"><span>GitHub</span><b id="runtimeGithubText">확인 중</b><div class="runtime-actions"><button class="runtime-action" id="runtimeGithubDownloadButton" onclick="runGithubDownload(event)">다운로드</button><button class="runtime-action" id="runtimeGithubUploadButton" onclick="runGithubUpload(event)">업로드</button></div></div>
  </div>
  <main>
    <section>
      <div class="tabs">
        <button id="tabVideo" class="tab active" onclick="setMode('video')">영상</button>
        <button id="tabCard" class="tab" onclick="setMode('card')">카드뉴스</button>
      </div>
      <div class="head"><h2 id="listTitle">영상 후보</h2><button onclick="reloadLists()">동기화 새로고침</button></div>
      <div id="videoList" class="list"></div>
      <div id="cardList" class="list" style="display:none"></div>
    </section>
    <div style="display:grid; gap:16px;">
      <section>
        <div class="head action-head"><h2 id="actionTitle">영상 작업</h2><div class="selected-badge"><span id="selectedModeLabel">선택 항목</span><b id="selectedSlug">없음</b></div></div>
        <div id="videoActions" class="pad grid">
          <button class="btn primary" onclick="runAction('video_prepare')"><strong>1. 영상용 프롬프트 준비</strong><span>선택한 카드뉴스 결과를 숏폼 영상 스크립트와 일러스트 요청으로 변환합니다.</span></button>
          <button class="btn primary" onclick="openImportReview()"><strong>2. 이미지 가져오기 + 렌더</strong><span>다운로드한 GPT 이미지를 그림 내용으로 자동 배정 제안 → 확인하고 확정합니다.</span></button>
          <button class="btn primary" onclick="runAction('video_render_selected')"><strong>3. 선택 영상만 렌더</strong><span>추가 이미지 없이 현재 선택한 슬러그를 다시 렌더합니다.</span></button>
          <div style="grid-column:1/-1;font-size:12px;color:#64748b;margin-top:2px">보기 · 편집</div>
          <button class="btn compact" onclick="runPreflight()"><strong>렌더 전 사전검사</strong><span>이미지·스크립트·CTA·한글·중복 사용을 먼저 확인합니다.</span></button>
          <button class="btn compact" onclick="window.open('/prompt','_blank')"><strong>영상 프롬프트 보기</strong><span>최신 영상용 GPT 프롬프트를 브라우저에서 엽니다.</span></button>
          <button class="btn compact" onclick="openIllustrationRequests()"><strong>신규 일러스트 요청서</strong><span>이 영상의 범용 일러스트 추천과 GPT 프롬프트.</span></button>
          <button class="btn compact" onclick="runAction('open_results')"><strong>영상 결과 폴더</strong><span>완성 MP4와 발행 패키지 폴더를 엽니다.</span></button>
          <button class="btn compact" onclick="deleteSlug()"><strong>선택 슬러그 삭제</strong><span>선택 슬러그의 articles·images·output 삭제(되돌릴 수 없음).</span></button>
          <button class="btn compact" onclick="runAction('open_illustrations')"><strong>일러스트 폴더</strong><span>재사용 일러스트 라이브러리와 드롭 폴더.</span></button>
          <button class="btn compact" onclick="showChunks()"><strong>청크 경계 편집</strong><span>내용·TTS는 유지하고 줄바꿈·합치기·분할만 조정합니다.</span></button>
          <button class="btn" id="manageToggle" style="grid-column:1/-1;min-height:0;padding:9px 12px;background:#f3f4f6;text-align:center" onclick="toggleManage()"><strong style="margin:0;font-size:13px">＋ 라이브러리 · 시스템 관리</strong></button>
          <div id="manageActions" style="display:none;grid-column:1/-1;gap:12px;grid-template-columns:repeat(3,minmax(160px,1fr))">
            <button class="btn" onclick="runAction('library_sync')"><strong>일러스트 라이브러리 공유</strong><span>공유 허브와 양방향 병합(비파괴). 허브 경로 먼저 설정. 결과는 실행 로그.</span></button>
            <button class="btn" onclick="runAction('library_dedup')"><strong>라이브러리 중복 점검</strong><span>비슷한 그림 리포트(읽기전용). 정리는 라이브러리_중복정리.bat --apply.</span></button>
            <button class="btn" onclick="runAction('library_backup')"><strong>라이브러리 백업</strong><span>일러스트+태그DB 타임스탬프 스냅샷(회전보관).</span></button>
            <button class="btn" onclick="chooseUpload('illustration')"><strong>일러스트 웹 업로드</strong><span>다른 PC에서 만든 일러스트를 드롭 폴더에 올립니다.</span></button>
            <button class="btn" onclick="runAction('producer_check')"><strong>환경 점검</strong><span>이 PC가 카드뉴스+영상 렌더를 독립으로 할 수 있는지(노드·렌더러·폰트·임베딩) 확인. 결과는 실행 로그.</span></button>
            <button class="btn" onclick="runAction('system_update')"><strong>시스템 업데이트</strong><span>GitHub에서 최신 코드만 받아옵니다(결과물 안 건드림).</span></button>
            <button class="btn" style="border-color:#dc2626;color:#dc2626" onclick="deleteSlug()"><strong>선택 슬러그 삭제</strong><span>선택한 슬러그의 기사·이미지·렌더 결과를 로컬에서 제거(되돌릴 수 없음).</span></button>
          </div>
        </div>
        <div id="cardActions" class="pad grid" style="display:none">
          <button class="btn" onclick="reloadLists()"><strong>1. 후보 새로고침</strong><span>articles·images·output 폴더를 다시 스캔합니다.</span></button>
          <button class="btn primary" onclick="openCardPrompt()"><strong>2. 이미지 프롬프트 보기</strong><span>선택한 카드뉴스의 images/&lt;slug&gt;/prompt.md를 엽니다.</span></button>
          <button class="btn" onclick="runAction('open_card_images')"><strong>3. 이미지 업로드 폴더</strong><span>1.png~5.png를 넣을 카드 이미지 폴더.</span></button>
          <button class="btn" onclick="chooseUpload('card')"><strong>3-1. 이미지 웹 업로드</strong><span>다른 PC에서도 카드 이미지를 바로 올립니다.</span></button>
          <button class="btn primary" onclick="openCardImportReview()"><strong>3-2. 이미지 자동 배정(검수)</strong><span>다운로드 그림을 슬라이드 내용으로 1~5.png에 자동 배정.</span></button>
          <button class="btn primary" onclick="runAction('card_render')"><strong>4. 카드뉴스 생성</strong><span>1x1·4x5·9x16 카드와 captions.md를 생성합니다.</span></button>
          <button class="btn" onclick="runAction('open_card_result')"><strong>5. 결과 확인</strong><span>완성된 카드뉴스 output 폴더를 엽니다.</span></button>
          <button class="btn primary" onclick="runAction('card_to_video')"><strong>6. 영상으로 넘기기</strong><span>완성 카드뉴스를 영상 준비 단계로 넘깁니다.</span></button>
          <div style="grid-column:1/-1;font-size:12px;color:#64748b;margin-top:2px">기타</div>
          <button class="btn" onclick="runAction('telegram_card_summary')"><strong>후보 현황 텔레그램</strong><span>현재 카드뉴스 후보·상태를 텔레그램으로 보냅니다.</span></button>
          <button class="btn" style="border-color:#dc2626;color:#dc2626" onclick="deleteSlug()"><strong>선택 슬러그 삭제</strong><span>선택한 슬러그의 기사·이미지·렌더 결과를 로컬에서 제거(되돌릴 수 없음).</span></button>
        </div>
      </section>
      <section>
        <div class="head"><h2>상태</h2><div style="display:flex;gap:8px;align-items:center"><span class="small" id="jobText">대기 중</span><button class="mini-btn" id="statusCancelButton" onclick="cancelRemoteJob()" style="display:none">중도 취소</button></div></div>
        <div class="pad status">
          <div class="metric slug"><span class="small" id="metric1Label">선택 슬러그</span><b id="latestSlug">-</b></div>
          <div class="metric"><span class="small" id="metric2Label">상태</span><b id="requestCount">-</b></div>
          <div class="metric"><span class="small" id="metric3Label">이미지</span><b id="missingCount">-</b></div>
          <div class="metric"><span class="small" id="metric4Label">카드</span><b id="downloadCount">-</b></div>
          <div class="metric"><span class="small" id="metric5Label">영상 스크립트</span><b id="weakCount">-</b></div>
        </div>
        <div class="pad small" id="advice"></div>
        <div id="preflightPanel" class="preflight-panel">
          <div class="head"><h2>렌더 전 사전검사</h2><button onclick="togglePreflightPanel()">닫기</button></div>
          <div class="pad">
            <div class="status-note" id="preflightSummary">아직 검사하지 않았습니다.</div>
            <div class="preflight-list" id="preflightRows"></div>
          </div>
        </div>
        <div id="illustrationRequestNote" class="pad small"></div>
        <div id="importPanel" class="weak-panel">
          <div class="head"><h2>이미지 가져오기 검수</h2><button onclick="toggleImportPanel()">닫기</button></div>
          <div class="pad small" id="importNote">다운로드한 그림을 그림 <b>내용</b>으로 자동 배정한 제안입니다. 썸네일을 보고 파일명이 맞는지 확인한 뒤 확정하세요. 파일명이 틀린 채로 확정하면 라이브러리가 잘못된 그림으로 채워집니다.</div>
          <div class="weak-scroll"><div id="importRows"></div></div>
          <div class="pad"><button class="btn primary" id="importConfirmBtn" onclick="confirmImport()" style="display:none">확정 → 가져오고 렌더</button></div>
        </div>
        <div id="weakPanel" class="weak-panel">
          <div class="head"><h2>약한 매핑 상세</h2><button onclick="toggleWeakPanel()">닫기</button></div>
          <div class="pad small">이미지/일러스트가 청크 문맥과 약하게 연결된 항목입니다. 10개 이상이면 렌더 전 재매핑을 권장합니다.</div>
          <div class="weak-scroll">
            <table class="weak-table">
              <thead><tr><th>구간</th><th>현재 visual</th><th>청크</th><th>추천 방향</th><th>수정</th></tr></thead>
              <tbody id="weakRows"></tbody>
            </table>
          </div>
        </div>
        <div id="chunkPanel" class="chunk-panel">
          <div class="head"><h2>청크 경계 편집</h2><button onclick="toggleChunkPanel()">닫기</button></div>
          <div class="pad small">문장 내용과 TTS는 유지합니다. "직접 끊기"로 원하는 위치에서 자막을 끊을 수 있고, 렌더 때 실제 TTS 단어 시간에 다시 맞춰져 싱크는 그대로입니다.</div>
          <div class="pad small" id="chunkMessage"></div>
          <div id="manualSplitBox" class="pad" style="display:none;border-top:1px solid var(--line);background:#fffef7">
            <div class="small" style="margin-bottom:6px">직접 끊기 — <b id="manualSplitSection"></b> · <b>줄바꿈(Enter)이 자막을 끊는 지점</b>입니다. 글자는 그대로 두고 위치만 바꾸세요.</div>
            <textarea id="manualSplitText" style="width:100%;min-height:150px;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px;line-height:1.7;font-family:inherit"></textarea>
            <div style="margin-top:8px;display:flex;gap:8px">
              <button class="mini-btn" onclick="applyManualSplit()">이대로 적용</button>
              <button class="mini-btn" onclick="cancelManualSplit()">취소</button>
            </div>
          </div>
          <div class="weak-scroll">
            <table class="chunk-table">
              <thead><tr><th>구간</th><th>청크 문구</th><th>visual</th><th>작업</th></tr></thead>
              <tbody id="chunkRows"></tbody>
            </table>
          </div>
        </div>
      </section>
      <section><div class="head"><h2>실행 로그</h2><div style="display:flex;gap:8px;align-items:center"><span class="small">실패하면 이 로그를 복사해서 보내면 됩니다.</span><button class="mini-btn" onclick="copyLog()">로그 복사</button></div></div><div id="log" class="log"></div></section>
      <section>
        <div class="head"><h2>최근 작업 기록</h2><button onclick="loadJobHistory()">새로고침</button></div>
        <div class="history-scroll">
          <table class="history-table">
            <thead><tr><th>상태</th><th>작업</th><th>실행 PC</th><th>시작</th><th>소요 시간</th><th>결과</th></tr></thead>
            <tbody id="jobHistoryRows"><tr><td colspan="6">기록을 불러오는 중입니다.</td></tr></tbody>
          </table>
        </div>
      </section>
      <section><div class="head"><h2>최근 영상 결과</h2><button onclick="runAction('open_results')">결과 폴더 열기</button></div><div class="pad results" id="results"></div></section>
    </div>
  </main>
  <input id="cardUploadInput" type="file" accept=".png,.jpg,.jpeg,.webp" multiple hidden>
  <input id="illustrationUploadInput" type="file" accept=".png,.jpg,.jpeg,.webp" multiple hidden>
  <script>
    let selected = "";
    let selectedCard = "";
    let mode = "video";
    let videoItems = [];
    let cardItems = [];
    let lastState = null;
    let currentRemoteJob = null;
    async function api(path, options) { const res = await fetch(path, options); if (!res.ok) throw new Error(await res.text()); return await res.json(); }
    function chooseUpload(kind) {
      if (kind === "card" && !selectedCard) {
        alert("카드뉴스 항목을 먼저 선택하세요.");
        return;
      }
      document.getElementById(kind === "card" ? "cardUploadInput" : "illustrationUploadInput").click();
    }
    async function uploadSelectedFiles(kind, files) {
      if (!files.length) return;
      const slug = kind === "card" ? selectedCard : "";
      let uploaded = 0;
      try {
        for (const file of files) {
          const result = await api(`/api/upload?kind=${encodeURIComponent(kind)}&slug=${encodeURIComponent(slug)}`, {
            method: "POST",
            headers: {"Content-Type": file.type || "application/octet-stream", "X-File-Name": file.name},
            body: file
          });
          if (result.ok) uploaded += 1;
        }
        alert(`${uploaded}개 이미지 업로드 완료`);
        await reloadLists();
      } catch (err) {
        alert("이미지 업로드 실패: " + String(err));
      }
    }
    document.getElementById("cardUploadInput").addEventListener("change", event => {
      uploadSelectedFiles("card", [...event.target.files]);
      event.target.value = "";
    });
    document.getElementById("illustrationUploadInput").addEventListener("change", event => {
      uploadSelectedFiles("illustration", [...event.target.files]);
      event.target.value = "";
    });
    function setMode(next) {
      mode = next;
      document.getElementById("tabVideo").classList.toggle("active", next === "video");
      document.getElementById("tabCard").classList.toggle("active", next === "card");
      document.getElementById("videoList").style.display = next === "video" ? "" : "none";
      document.getElementById("cardList").style.display = next === "card" ? "" : "none";
      document.getElementById("videoActions").style.display = next === "video" ? "" : "none";
      document.getElementById("cardActions").style.display = next === "card" ? "" : "none";
      document.getElementById("listTitle").textContent = next === "video" ? "영상 후보" : "카드뉴스 후보";
      document.getElementById("actionTitle").textContent = next === "video" ? "영상 작업" : "카드뉴스 작업";
      updateSelectedStatus();
      refreshIllustrationRequestNote();
    }
    async function loadSlugs() {
      const data = await api("/api/slugs"); videoItems = data.slugs || []; const box = document.getElementById("videoList"); box.innerHTML = "";
      videoItems.forEach(item => {
        const btn = document.createElement("button");
        btn.className = "row video" + (item.slug === selected ? " active" : "");
        btn.innerHTML = `<span class="row-number">${item.number}</span><span class="row-main"><span class="slug-name">${item.slug}</span><span class="row-sub">${item.date}${item.flag && item.flag !== "undefined" ? " · " + item.flag : ""}</span></span><span class="stage-pill ${item.stageClass || "muted"}">${item.stage || "-"}</span>`;
        btn.onclick = () => { selected = item.slug; document.getElementById("selectedSlug").textContent = selected; setMode("video"); updateSelectedStatus(); loadSlugs(); };
        box.appendChild(btn);
      });
      if (!selected && videoItems.length) { selected = videoItems[0].slug; document.getElementById("selectedSlug").textContent = selected; updateSelectedStatus(); loadSlugs(); }
    }
    async function loadCardnews() {
      const data = await api("/api/cardnews/slugs"); cardItems = data.rows || []; const box = document.getElementById("cardList"); box.innerHTML = "";
      cardItems.forEach((item, idx) => {
        const btn = document.createElement("button");
        btn.className = "row card" + (item.slug === selectedCard ? " active" : "");
        btn.innerHTML = `<span class="row-number">${idx + 1}</span><span class="row-main"><span class="slug-name">${item.slug}</span>${item.title ? `<span class="row-sub">${item.title}</span>` : ""}<span class="row-sub">${item.date || "-"} · 이미지 ${item.images}/5 · 카드 ${item.cards} · 프롬프트 ${item.prompt ? "있음" : "없음"}</span></span><span class="stage-pill ${item.stageClass || "muted"}">${item.stage || item.status}</span>`;
        btn.onclick = () => { selectedCard = item.slug; selected = item.slug; document.getElementById("selectedSlug").textContent = selected; setMode("card"); updateSelectedStatus(); loadCardnews(); loadSlugs(); };
        box.appendChild(btn);
      });
    }
    function togglePreflightPanel() {
      const panel = document.getElementById("preflightPanel");
      panel.style.display = panel.style.display === "block" ? "none" : "block";
    }
    function renderPreflight(result) {
      const panel = document.getElementById("preflightPanel");
      const summary = document.getElementById("preflightSummary");
      const rows = document.getElementById("preflightRows");
      panel.style.display = "block";
      const cls = result.status === "OK" ? "ok" : "warn";
      summary.innerHTML = `<b>${escapeHtml(result.slug || selected)}</b> · 상태 ${result.status} · 오류 ${result.errors || 0} · 경고 ${result.warnings || 0}`;
      rows.innerHTML = "";
      (result.items || []).forEach(item => {
        const div = document.createElement("div");
        div.className = `preflight-item ${item.level || ""}`;
        div.innerHTML = `<b>[${escapeHtml(item.level || "-")}] ${escapeHtml(item.message || "")}</b>${item.detail ? `<pre>${escapeHtml(item.detail)}</pre>` : ""}`;
        rows.appendChild(div);
      });
    }
    async function refreshIllustrationRequestNote() {
      const slug = selected || selectedCard;
      const box = document.getElementById("illustrationRequestNote");
      if (!box || !slug) return;
      try {
        const data = await api(`/api/illustration-requests?slug=${encodeURIComponent(slug)}`);
        if (!data.exists) {
          box.innerHTML = `<div class="status-note">신규 일러스트 요청서가 아직 없습니다. 1번 영상용 프롬프트 준비를 먼저 실행하세요.</div>`;
          return;
        }
        const tone = (data.count || 0) > 0 ? "warn" : "ok";
        const text = (data.count || 0) > 0
          ? `신규 일러스트 제안 ${data.count}개 · 문맥 경고 ${data.gaps || 0}개`
          : `신규 일러스트 제안 없음 · 문맥 경고 ${data.gaps || 0}개`;
        box.innerHTML = `<div class="status-note"><b>일러스트 요청서</b> · ${text} <button onclick="openIllustrationRequests()" style="margin-left:8px">열기</button></div>`;
      } catch (e) {
        box.innerHTML = `<div class="status-note">일러스트 요청서 상태 확인 실패: ${escapeHtml(e.message)}</div>`;
      }
    }
    function openIllustrationRequests() {
      const slug = selected || selectedCard;
      if (!slug) { alert("먼저 슬러그를 선택하세요."); return; }
      window.open(`/illustration-requests/${encodeURIComponent(slug)}`, "_blank");
    }
    async function runPreflight() {
      const slug = selected || selectedCard;
      if (!slug) { alert("먼저 슬러그를 선택하세요."); return; }
      try {
        const result = await api(`/api/preflight?slug=${encodeURIComponent(slug)}`);
        renderPreflight(result);
      } catch (e) {
        alert("사전검사 실패: " + e.message);
      }
    }
    async function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }
    async function waitForCurrentJob(maxMs) {
      const started = Date.now();
      while (Date.now() - started < maxMs) {
        const data = await api("/api/job");
        const job = data.job || {};
        if (!job.running) return job;
        document.getElementById("jobText").textContent = `실행 중: ${job.name || "작업"}`;
        await sleep(1200);
      }
      return null;
    }
    async function reloadLists() {
      try {
        const result = await api("/api/action", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({action:"sync_cardnews", slug:selected || selectedCard || ""})
        });
        if (result.ok) {
          await waitForCurrentJob(180000);
        } else if (!result.busy) {
          alert(result.message || "카드뉴스 동기화를 시작하지 못했습니다. 로컬 목록만 새로고침합니다.");
        }
      } catch (e) {
        alert("카드뉴스 동기화 호출 실패: " + e.message + "\n로컬 목록만 새로고침합니다.");
      }
      await loadSlugs();
      await loadCardnews();
      await loadState();
    }
    function findCardRow(slug) {
      return (cardItems || []).find(x => x.slug === slug) || null;
    }
    function findVideoRow(slug) {
      return (videoItems || []).find(x => x.slug === slug) || null;
    }
    function setMetric(id, value, cls) {
      const el = document.getElementById(id);
      el.textContent = value == null || value === "" ? "-" : String(value);
      el.className = cls || "";
    }
    function updateSelectedStatus() {
      const activeSlug = mode === "card" ? (selectedCard || selected) : selected;
      document.getElementById("selectedSlug").textContent = activeSlug || "없음";
      document.getElementById("selectedModeLabel").textContent = mode === "card" ? "선택한 카드뉴스" : "선택한 영상";
      const card = activeSlug ? findCardRow(activeSlug) : null;
      const video = activeSlug ? findVideoRow(activeSlug) : null;

      document.getElementById("metric1Label").textContent = "선택 슬러그";
      document.getElementById("metric2Label").textContent = "상태";
      document.getElementById("metric3Label").textContent = "이미지";
      document.getElementById("metric4Label").textContent = "카드";
      document.getElementById("metric5Label").textContent = "영상 스크립트";
      setMetric("latestSlug", activeSlug || "-");

      if (card) {
        setMetric("requestCount", card.stage || card.status || (card.done ? "완료" : "진행중"), card.stageClass === "ok" ? "ok" : "warn");
        setMetric("missingCount", `${card.images || 0}/5`, (card.images || 0) >= 5 ? "ok" : "warn");
        setMetric("downloadCount", `${card.cards || 0}`, (card.cards || 0) > 0 ? "ok" : "warn");
        setMetric("weakCount", card.script ? "있음" : "없음", card.script ? "ok" : "warn");
        const advice = document.getElementById("advice");
        const parts = [];
        parts.push(`<b>${escapeHtml(activeSlug || "")}</b> 선택 중`);
        if (card.stage) parts.push(`단계 ${card.stage}`);
        parts.push(`기사 ${card.article ? "있음" : "없음"}`);
        parts.push(`프롬프트 ${card.prompt ? "있음" : "없음"}`);
        parts.push(`캡션 ${card.captions ? "있음" : "없음"}`);
        parts.push(`영상 스크립트 ${card.script ? "있음" : "없음"}`);
        if (mode === "video" && video) parts.push(`영상 플래그 [${video.flag}]`);
        advice.innerHTML = `<div class="status-note">${parts.join(" · ")}</div>`;
      } else if (video) {
        setMetric("requestCount", `[${video.flag}]`, video.flag === "OK" ? "ok" : "warn");
        setMetric("missingCount", "-");
        setMetric("downloadCount", "-");
        setMetric("weakCount", "-");
        document.getElementById("advice").innerHTML = `<div class="status-note"><b>${escapeHtml(activeSlug || "")}</b> 선택 중 · 카드뉴스 상세 정보는 아직 로드되지 않았습니다.</div>`;
      } else if (lastState) {
        setMetric("requestCount", "대기");
        setMetric("missingCount", "-");
        setMetric("downloadCount", "-");
        setMetric("weakCount", "-");
        document.getElementById("advice").innerHTML = `<div class="status-note">왼쪽 목록에서 작업할 항목을 선택하세요.</div>`;
      }
    }
    function formatHistoryTime(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleString("ko-KR", {month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit"});
    }
    function formatDuration(seconds) {
      if (seconds === null || seconds === undefined) return "-";
      const total = Math.max(0, Number(seconds) || 0);
      const hours = Math.floor(total / 3600);
      const minutes = Math.floor((total % 3600) / 60);
      const secs = total % 60;
      if (hours) return `${hours}시간 ${minutes}분 ${secs}초`;
      if (minutes) return `${minutes}분 ${secs}초`;
      return `${secs}초`;
    }
    async function loadJobHistory() {
      const body = document.getElementById("jobHistoryRows");
      try {
        const data = await api("/api/jobs?limit=50");
        const rows = data.rows || [];
        if (!rows.length) {
          body.innerHTML = "<tr><td colspan='6'>아직 실행 기록이 없습니다.</td></tr>";
          return;
        }
        const statusLabels = {pending:"대기", running:"실행 중", done:"성공", failed:"실패", cancelled:"취소"};
        body.innerHTML = rows.map(row => {
          const status = ["pending", "running", "done", "failed", "cancelled"].includes(row.status) ? row.status : "failed";
          const results = (row.result_files || []).map(file =>
            `<a href="/api/result?folder=${encodeURIComponent(file.folder)}&file=${encodeURIComponent(file.file)}">${escapeHtml(file.name)}</a>`
          ).join("");
          const worker = row.worker_id || (row.kind === "local" ? "패널 PC" : "배정 대기");
          const detail = row.message ? ` title="${escapeHtml(row.message)}"` : "";
          return `<tr${detail}>
            <td><span class="history-status ${status}">${statusLabels[row.status] || escapeHtml(row.status || "-")}</span></td>
            <td>${escapeHtml(row.name || "-")}</td>
            <td>${escapeHtml(worker)}</td>
            <td>${formatHistoryTime(row.started_at || row.created_at)}</td>
            <td>${formatDuration(row.duration_seconds)}</td>
            <td class="history-result">${results || "-"}</td>
          </tr>`;
        }).join("");
      } catch (err) {
        body.innerHTML = `<tr><td colspan="6">작업 기록을 불러오지 못했습니다: ${escapeHtml(String(err))}</td></tr>`;
      }
    }
    async function loadState() {
      const data = await api("/api/state");
      lastState = data;
      document.getElementById("rootText").textContent = data.root;
      const pv = document.getElementById("panelVersion");
      if (pv) pv.textContent = data.version || "";
      const sync = data.sync || {};
      document.getElementById("runtimeModeText").textContent = `${sync.rootMode || "-"} · 렌더 PC ${data.readyWorkers || 0}/${data.onlineWorkers || 0}대 준비`;
      const workerSelect = document.getElementById("targetWorker");
      const selectedWorker = workerSelect.value;
      workerSelect.innerHTML = `<option value="">자동 배정</option>`;
      Object.entries(data.workers || {}).forEach(([id, worker]) => {
        if (!worker.online) return;
        const option = document.createElement("option");
        option.value = id;
        option.textContent = `${worker.name || id} · ${worker.status || "idle"}`;
        option.disabled = worker.ready === false;
        if (worker.ready === false) {
          option.textContent = `${worker.name || id} · 준비 필요: ${(worker.issues || []).join(", ") || "설정 확인"}`;
        }
        workerSelect.appendChild(option);
      });
      if ([...workerSelect.options].some(option => option.value === selectedWorker)) workerSelect.value = selectedWorker;
      document.getElementById("runtimeMode").className = `runtime-card ${sync.rootOk ? "good" : "bad"}`;
      document.getElementById("runtimeSyncText").textContent = `${sync.ok ? "성공" : "확인 필요"} · ${sync.endedAt || sync.message || "-"}`;
      document.getElementById("runtimeSync").className = `runtime-card ${sync.ok ? "good" : "bad"}`;
      const gh = data.github || {};
      const ghCard = document.getElementById("runtimeGithub");
      const ghText = document.getElementById("runtimeGithubText");
      if (ghText) {
        const commit = gh.local ? " · " + gh.local : "";
        ghText.textContent = `${gh.message || "확인 중"}${commit}`;
      }
      if (ghCard) ghCard.className = `runtime-card ${gh.class || "warn"}`;
      const ghDown = document.getElementById("runtimeGithubDownloadButton");
      const ghUp = document.getElementById("runtimeGithubUploadButton");
      if (ghDown) ghDown.title = gh.detail || "GitHub에서 최신 코드를 받습니다.";
      if (ghUp) ghUp.title = "내 PC의 변경사항을 GitHub에 올립니다.";
      refreshIllustrationRequestNote();
      updateSelectedStatus();
      const job = data.job || {};
      currentRemoteJob = job.remote ? job : null;
      const prog = job.running ? renderProgress(job.log) : "";
      const runtimeJob = document.getElementById("runtimeJob");
      const runtimeJobText = document.getElementById("runtimeJobText");
      if (runtimeJobText) runtimeJobText.textContent = job.running ? (`실행 중 · ${job.name}` + (prog ? ` — ${prog}` : "")) : (job.exit_code === null ? "대기 중" : `마지막 종료 ${job.exit_code}`);
      if (runtimeJob) runtimeJob.className = `runtime-card ${job.running ? "warn" : (job.exit_code === 0 ? "good" : (job.exit_code === null ? "" : "bad"))}`;
      const cancelButton = document.getElementById("cancelJobButton");
      const retryButton = document.getElementById("retryJobButton");
      cancelButton.style.display = job.remote && job.running ? "" : "none";
      retryButton.style.display = job.remote && !job.running && job.exit_code !== 0 ? "" : "none";
      const statusCancel = document.getElementById("statusCancelButton");
      if (statusCancel) statusCancel.style.display = job.remote && job.running ? "" : "none";
      document.getElementById("jobText").textContent = job.running ? (`실행 중: ${job.name}` + (prog ? ` · ${prog}` : "")) : (job.exit_code === null ? "대기 중" : `마지막 종료 코드: ${job.exit_code}`);
      const log = document.getElementById("log"); log.textContent = job.log || ""; log.scrollTop = log.scrollHeight;
      const results = document.getElementById("results"); results.innerHTML = ""; (data.results || []).forEach(r => {
        const div = document.createElement("div");
        div.className = "result-row";
        const link = r.mp4
          ? `<a href="/api/result?folder=${encodeURIComponent(r.name)}&file=${encodeURIComponent(r.mp4)}">${escapeHtml(r.mp4)}</a>`
          : "";
        div.innerHTML = `<span>${escapeHtml(r.name)}</span><span class="small">${link}</span>`;
        results.appendChild(div);
      });
    }

    async function runGithubAction(event, action, label) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const down = document.getElementById("runtimeGithubDownloadButton");
      const up = document.getElementById("runtimeGithubUploadButton");
      const text = document.getElementById("runtimeGithubText");
      try {
        if (down) down.disabled = true;
        if (up) up.disabled = true;
        if (text) text.textContent = label + " 요청 중...";
        const result = await api("/api/action", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({action, slug: ""})
        });
        if (!result.ok) {
          alert(result.message || result.error || label + "을 시작하지 못했습니다.");
        }
        await loadState();
        await loadJobHistory();
      } catch (err) {
        alert("GitHub " + label + " 버튼 오류: " + String(err));
      } finally {
        if (down) down.disabled = false;
        if (up) up.disabled = false;
      }
    }
    async function runGithubDownload(event) {
      return runGithubAction(event, "system_update", "다운로드");
    }
    async function runGithubUpload(event) {
      return runGithubAction(event, "system_upload", "업로드");
    }

    async function deleteSlug() {
      if (!selected) { alert("먼저 슬러그를 선택하세요."); return; }
      if (!confirm("정말 삭제할까요?\n'" + selected + "' 의 articles / images / output 파일이 모두 지워집니다. 되돌릴 수 없습니다.")) return;
      try {
        const result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"delete_slug", slug:selected}) });
        alert(result.ok ? (result.message || "삭제됨") : (result.message || "삭제 실패"));
        if (result.ok) { selected = ""; document.getElementById("selectedSlug").textContent = "없음"; }
      } catch (err) { alert(String(err)); }
      await loadState(); await loadSlugs(); await loadCardnews();
    }
    async function runAction(action) {
      console.log("runAction", action);
      try {
        const targetWorker = document.getElementById("targetWorker")?.value || "";
        const result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action, slug:selected, target_worker:targetWorker}) });
        if (!result.ok) {
          alert(result.message || "작업을 시작하지 못했습니다. 실행 로그를 확인해주세요.");
        }
        await loadState();
        await loadJobHistory();
      } catch (err) { alert(String(err)); }
    }
    async function deleteSlug() {
      if (!selected) { alert("먼저 슬러그를 선택하세요."); return; }
      if (!confirm("'" + selected + "' 슬러그를 삭제할까요?\n기사(주제)·카드 이미지·렌더 결과가 로컬에서 제거됩니다. 되돌릴 수 없습니다.")) return;
      try {
        const result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"delete_slug", slug:selected}) });
        alert(result.message || (result.ok ? "삭제됨" : "삭제 실패"));
        selected = "";
        await reloadLists();
        await loadState();
      } catch (err) { alert(String(err)); }
    }
    async function cancelRemoteJob() {
      if (!currentRemoteJob?.job_id) return;
      await api("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"remote_job_cancel", job_id:currentRemoteJob.job_id})});
      await loadState();
      await loadJobHistory();
    }
    async function retryRemoteJob() {
      if (!currentRemoteJob?.job_id) return;
      await api("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"remote_job_retry", job_id:currentRemoteJob.job_id})});
      await loadState();
      await loadJobHistory();
    }
    function toggleWeakPanel() {
      const panel = document.getElementById("weakPanel");
      panel.style.display = panel.style.display === "block" ? "none" : "block";
    }
    function toggleImportPanel() {
      const panel = document.getElementById("importPanel");
      panel.style.display = panel.style.display === "block" ? "none" : "block";
    }
    function toggleManage() {
      const m = document.getElementById("manageActions");
      const t = document.getElementById("manageToggle");
      const open = m.style.display === "grid";
      m.style.display = open ? "none" : "grid";
      if (t) { const s = t.querySelector("strong"); if (s) s.textContent = (open ? "＋" : "－") + " 라이브러리 · 시스템 관리"; }
    }
    async function openCardImportReview() {
      if (!selected) { alert("먼저 카드뉴스를 선택하세요."); return; }
      window.__importKind = "card";
      const panel = document.getElementById("importPanel");
      const rows = document.getElementById("importRows");
      const btn = document.getElementById("importConfirmBtn");
      panel.style.display = "block";
      btn.style.display = "none";
      rows.innerHTML = "<div class='pad small'>슬라이드 내용으로 자동 배정 중입니다...</div>";
      let result;
      try {
        result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"card_import_propose", slug:selected}) });
      } catch (err) { rows.innerHTML = "<div class='pad small'>제안 생성 실패: " + escapeHtml(String(err)) + "</div>"; return; }
      if (!result.ok) { rows.innerHTML = "<div class='pad small'>" + escapeHtml(result.message || "제안을 생성하지 못했습니다.") + "</div>"; return; }
      renderImportProposal(result.proposal || {});
    }
    async function openImportReview() {
      if (!selected) { alert("먼저 슬러그를 선택하세요."); return; }
      window.__importKind = "video";
      const panel = document.getElementById("importPanel");
      const rows = document.getElementById("importRows");
      const btn = document.getElementById("importConfirmBtn");
      panel.style.display = "block";
      btn.style.display = "none";
      rows.innerHTML = "<div class='pad small'>그림 내용을 분석해 자동 배정 중입니다...</div>";
      let result;
      try {
        result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"video_import_propose", slug:selected}) });
      } catch (err) { rows.innerHTML = "<div class='pad small'>제안 생성 실패: " + escapeHtml(String(err)) + "</div>"; return; }
      if (!result.ok) { rows.innerHTML = "<div class='pad small'>" + escapeHtml(result.message || "제안을 생성하지 못했습니다.") + "</div>"; return; }
      renderImportProposal(result.proposal || {});
    }
    function renderImportProposal(p) {
      window.__importProposal = p;
      const rows = document.getElementById("importRows");
      const btn = document.getElementById("importConfirmBtn");
      const reqs = p.requests || [];
      const assigns = p.assignments || [];
      const engineLabel = p.engine === "image-embedding" ? "그림 내용 매칭" : (p.engine === "fallback-mtime" ? "시간순 추정(모델 없음 — 꼭 확인)" : "후보 없음");
      const optionsHtml = ["<option value=''>— 사용 안 함 —</option>"].concat(
        reqs.map(r => `<option value="${escapeHtml(r.filename)}">${r.optional ? "[자동발굴] " : ""}${escapeHtml(r.filename)}${r.concept_label ? " · " + escapeHtml(r.concept_label) : ""}</option>`)
      ).join("");
      let html = `<div class='pad small'>엔진: <b>${escapeHtml(engineLabel)}</b> · 후보 ${assigns.length}장 · 요청 ${reqs.length}건</div>`;
      if (!reqs.length) {
        if ((window.__importKind || "video") === "card") {
          html += "<div class='pad small'>슬라이드 설명(prompt.md)을 읽지 못했습니다. '2. 이미지 프롬프트 보기'로 prompt.md가 있는지 확인하세요.</div>";
        } else {
          html += "<div class='pad small'>이 영상은 새로 그릴 이미지가 없습니다(누락 요청 0건). 바로 렌더하면 됩니다.</div>";
          html += "<div class='pad'><button class='btn primary' onclick='renderNowFromReview()'>이미지 없이 바로 렌더</button></div>";
        }
        rows.innerHTML = html; btn.style.display = "none"; return;
      }
      if (!assigns.length) {
        html += "<div class='pad small'>가져올 그림 후보가 없습니다. GPT 이미지를 ILLUSTRATION_DROP 또는 다운로드 폴더에 저장한 뒤 다시 누르세요.</div>";
        rows.innerHTML = html; btn.style.display = "none"; return;
      }
      assigns.forEach((a, idx) => {
        const conf = (a.confidence === null || a.confidence === undefined) ? "" : `<span class='pill ${a.confidence >= 0.30 ? "ok" : "warn"}'>신뢰도 ${(a.confidence).toFixed(2)}</span>`;
        const dedup = a.dedup
          ? (a.dedup.skip
              ? `<span class='pill warn'>기존 '${escapeHtml(a.dedup.variant)}'와 거의 동일 (${(a.dedup.score).toFixed(2)}) · 안 넣어도 자동 재사용 → 기본 '사용 안 함'</span>`
              : `<span class='pill warn'>중복 가능: ${escapeHtml(a.dedup.variant)} (${(a.dedup.score).toFixed(2)})</span>`)
          : "";
        const exact = a.exact_name ? "<span class='pill ok'>정확한 파일명</span>" : "";
        const thumb = `/api/illust-thumb?path=${encodeURIComponent(a.candidate_path)}`;
        html += `<div class='import-row' style='display:flex;gap:12px;align-items:center;padding:8px;border-bottom:1px solid #eee'>
          <img src="${thumb}" alt="" style="width:96px;height:72px;object-fit:cover;border:1px solid #ddd;border-radius:6px;background:#fafafa" onerror="this.style.opacity=0.2"/>
          <div style='flex:1;min-width:0'>
            <div class='small' style='word-break:break-all'>${escapeHtml(a.candidate_name)}</div>
            <div style='margin:4px 0'>${conf} ${exact} ${dedup}</div>
            <select id="importSel_${idx}">${optionsHtml}</select>
          </div>
        </div>`;
      });
      if ((p.unmatched_requests || []).length) {
        html += `<div class='pad small'>아직 후보가 없는 요청: ${ (p.unmatched_requests).map(escapeHtml).join(", ") }</div>`;
      }
      rows.innerHTML = html;
      assigns.forEach((a, idx) => {
        const sel = document.getElementById("importSel_" + idx);
        if (!sel) return;
        if (a.dedup && a.dedup.skip) sel.value = "";              // 거의 동일 → 기본 건너뛰기
        else if (a.proposed_filename) sel.value = a.proposed_filename;
      });
      btn.style.display = "inline-block";
    }
    async function renderNowFromReview() {
      if (!confirm("새 이미지 없이 현재 영상을 렌더 대기열에 등록합니다.")) return;
      try {
        const r = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"video_render_selected", slug:selected}) });
        alert(r.message || (r.ok ? "렌더 대기열에 등록했습니다." : "실패했습니다."));
        if (r.ok) { document.getElementById("importPanel").style.display = "none"; await loadState(); await loadJobHistory(); }
      } catch (err) { alert(String(err)); }
    }
    async function confirmImport() {
      const p = window.__importProposal || {};
      const assigns = p.assignments || [];
      const mapping = [];
      const usedFn = new Set();
      for (let idx = 0; idx < assigns.length; idx++) {
        const sel = document.getElementById("importSel_" + idx);
        const fn = sel ? sel.value : "";
        if (!fn) continue;
        if (usedFn.has(fn)) { alert("같은 파일명이 두 번 선택됐습니다: " + fn + "\n하나만 남겨주세요."); return; }
        usedFn.add(fn);
        mapping.push({ candidate_path: assigns[idx].candidate_path, filename: fn });
      }
      if (!mapping.length) { alert("최소 한 장은 파일명을 배정하세요."); return; }
      const kind = window.__importKind || "video";
      const action = kind === "card" ? "card_import_confirm" : "video_import_confirm";
      const msg = (kind === "card")
        ? ("이 매핑대로 카드 이미지 폴더에 1~5.png로 넣습니다.\n슬라이드 내용과 맞는지 확인했나요? (" + mapping.length + "장)")
        : ("이 매핑대로 라이브러리에 넣고 렌더 대기열에 등록합니다.\n파일명이 그림 내용과 맞는지 확인했나요? (" + mapping.length + "장)");
      if (!confirm(msg)) return;
      let result;
      try {
        result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action, slug:selected, mapping}) });
      } catch (err) { alert("확정 실패: " + String(err)); return; }
      alert(result.message || (result.ok ? "확정했습니다." : "실패했습니다."));
      if (result.ok) {
        document.getElementById("importPanel").style.display = "none";
        await loadState();
        await loadJobHistory();
      }
    }
    async function showWeakMappings() {
      const data = await api("/api/weak-mappings");
      const body = document.getElementById("weakRows");
      body.innerHTML = "";
      if (!data.rows || data.rows.length === 0) {
        body.innerHTML = "<tr><td colspan='5'>약한 매핑이 없습니다.</td></tr>";
      } else {
        const visualOptions = buildVisualOptions(data.visuals || {});
        data.rows.forEach((r, idx) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${r.section}<br>청크 ${r.chunk}</td>
            <td>${r.variant || "-"}</td>
            <td>${escapeHtml(r.text || "")}</td>
            <td>${escapeHtml(r.suggestion || "")}</td>
            <td>
              <select id="weakType_${idx}" onchange="fillVisualValue(${idx})">
                <option value="illust">일러스트</option>
                <option value="image">GPT 이미지</option>
                <option value="logo">로고</option>
                <option value="mascot">마스코트</option>
                <option value="none">비우기</option>
              </select>
              <input id="weakValue_${idx}" list="weakValues_${idx}" placeholder="예: penalty_refund 또는 3.png">
              <datalist id="weakValues_${idx}">${visualOptions}</datalist>
              <button class="mini-btn" onclick="saveWeakVisual(${idx}, '${escapeJs(r.section)}', ${Number(r.chunk_index) || 0})">저장</button>
            </td>`;
          body.appendChild(tr);
        });
      }
      document.getElementById("weakPanel").style.display = "block";
      window.__weakVisuals = data.visuals || {};
    }
    function buildVisualOptions(visuals) {
      const rows = [];
      ["illust","image","logo","mascot"].forEach(type => {
        (visuals[type] || []).forEach(v => rows.push(`<option value="${escapeHtml(v)}" label="${type}:${escapeHtml(v)}"></option>`));
      });
      return rows.join("");
    }
    function fillVisualValue(idx) {
      const type = document.getElementById(`weakType_${idx}`).value;
      const input = document.getElementById(`weakValue_${idx}`);
      if (type === "none") input.value = "none";
      else input.value = "";
    }
    async function saveWeakVisual(idx, section, chunkIndex) {
      const type = document.getElementById(`weakType_${idx}`).value;
      const value = document.getElementById(`weakValue_${idx}`).value.trim();
      if (!value) { alert("새 visual 값을 입력하세요."); return; }
      await api("/api/action", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          action:"update_visual",
          slug:selected,
          section,
          chunk_index:chunkIndex,
          visual_type:type,
          visual_value:value
        })
      });
      alert("저장했습니다. 필요하면 선택 영상만 렌더를 다시 실행하세요.");
      await showWeakMappings();
    }
    async function showChunks() {
      try {
        if (!selected) { alert("먼저 슬러그를 선택하세요."); return; }
        const data = await api("/api/chunks?slug=" + encodeURIComponent(selected));
        const body = document.getElementById("chunkRows");
        body.innerHTML = "";
        const rows = data.rows || [];
        window.__chunkRows = rows;
        if (!rows.length) {
          body.innerHTML = "<tr><td colspan='4'>청크가 없습니다. 먼저 영상 이미지 프롬프트 준비를 실행하세요.</td></tr>";
        }
        rows.forEach((r) => {
          const tr = document.createElement("tr");
          const overrideBadge = r.override ? "<br><span class='pill ok'>편집본</span>" : "";
          const rebalanceButton = r.section_first
            ? `<button class="mini-btn" onclick="openManualSplit('${escapeJs(r.section)}')">✏ 직접 끊기</button> <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', 0, 'rebalance_section')">구간 자동 보정</button>`
            : "";
          const mergePrevDisabled = r.can_merge_prev ? "" : "disabled title='첫 청크이거나 합친 문장이 너무 깁니다.'";
          const mergeNextDisabled = r.can_merge_next ? "" : "disabled title='마지막 청크이거나 합친 문장이 너무 깁니다.'";
          const splitDisabled = r.can_split ? "" : "disabled title='안전하게 나눌 수 있을 만큼 길지 않습니다.'";
          tr.innerHTML = `<td>${escapeHtml(r.section)}<br>청크 ${Number(r.chunk) || 0}<br>${Number(r.chars) || 0}자${overrideBadge}</td>
            <td class="chunk-text">${escapeHtml(r.text || "")}</td>
            <td>${escapeHtml(r.visual || "-")}</td>
            <td>
              ${rebalanceButton}
              <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'linebreak')">자동 줄바꿈</button>
              <button class="mini-btn" ${mergePrevDisabled} onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'merge_prev')">앞과 합치기</button>
              <button class="mini-btn" ${mergeNextDisabled} onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'merge_next')">뒤와 합치기</button>
              <button class="mini-btn" ${splitDisabled} onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'split_auto')">자동 둘로 나누기</button>
            </td>`;
          body.appendChild(tr);
        });
        document.getElementById("chunkPanel").style.display = "block";
      } catch (err) {
        alert("청크 목록을 불러오지 못했습니다.\n" + String(err));
      }
    }
    function toggleChunkPanel() {
      const panel = document.getElementById("chunkPanel");
      panel.style.display = panel.style.display === "block" ? "none" : "block";
    }
    function openManualSplit(section) {
      const rows = (window.__chunkRows || []).filter(r => r.section === section);
      const text = rows.map(r => String(r.text || "").replace(/\s+/g, " ").trim()).join("\n");
      const box = document.getElementById("manualSplitBox");
      document.getElementById("manualSplitSection").textContent = section;
      document.getElementById("manualSplitText").value = text;
      box.dataset.section = section;
      box.style.display = "block";
      box.scrollIntoView({ block: "nearest" });
    }
    function cancelManualSplit() { document.getElementById("manualSplitBox").style.display = "none"; }
    async function applyManualSplit() {
      const box = document.getElementById("manualSplitBox");
      const section = box.dataset.section || "";
      const text = document.getElementById("manualSplitText").value;
      try {
        const r = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action:"set_section_chunks", slug:selected, section, text}) });
        if (!r.ok) { alert(r.message || "적용하지 못했습니다."); return; }
        box.style.display = "none";
        alert("끊기를 적용했습니다. 다음 렌더부터 반영됩니다.");
        await showChunks();
      } catch (err) { alert("적용 실패: " + String(err)); }
    }
    async function adjustChunk(section, chunkIndex, op) {
      const message = document.getElementById("chunkMessage");
      try {
        if (message) message.textContent = "청크를 저장하는 중입니다.";
        const result = await api("/api/action", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ action:"adjust_chunk", slug:selected, section, chunk_index:chunkIndex, op })
        });
        if (!result.ok) {
          alert(result.message || "청크 조정에 실패했습니다.");
          if (message) message.textContent = result.message || "청크 조정에 실패했습니다.";
          return;
        }
        await showChunks();
        if (message) message.textContent = "저장했습니다. 다음 렌더부터 자동으로 반영됩니다.";
      } catch (err) {
        if (message) message.textContent = "저장하지 못했습니다.";
        alert("청크 조정 실패\n" + String(err));
      }
    }
    async function copyLog() {
      const el = document.getElementById("log");
      const text = el ? el.innerText : "";
      if (!text.trim()) { alert("복사할 로그가 없습니다."); return; }
      try {
        await navigator.clipboard.writeText(text);
        alert("실행 로그를 전체 복사했습니다.");
      } catch (e) {
        const t = document.createElement("textarea");
        t.value = text; document.body.appendChild(t); t.select();
        try { document.execCommand("copy"); alert("실행 로그를 전체 복사했습니다."); }
        finally { t.remove(); }
      }
    }
    function renderProgress(log) {
      if (!log) return "";
      let p = "";
      const lines = String(log).split("\n");
      for (const ln of lines) {
        let m;
        if (m = ln.match(/----- Step (\d+\/\d+)[:：]?\s*(.*?)-----/)) p = "단계 " + m[1] + (m[2] && m[2].trim() ? " · " + m[2].trim() : "");
        else if (m = ln.match(/\[render\]\s*(\d+)%/)) p = "프레임 렌더 " + m[1] + "%";
        else if (ln.indexOf("frame=") >= 0 && (m = ln.match(/frame=\s*(\d+)/)) && /speed=\s*([\d.]+x)/.test(ln)) p = "인코딩 " + m[1] + "프레임 (" + ln.match(/speed=\s*([\d.]+x)/)[1] + ")";
        else if (ln.indexOf("[CLAIMED]") >= 0) p = "워커 배정됨";
        else if (ln.indexOf("[DOWNLOAD]") >= 0) p = "준비 중";
        else if (ln.indexOf("[UPLOAD]") >= 0 || ln.indexOf("[LOCAL]") >= 0) p = "결과 정리 중";
        else if (ln.indexOf("[OK] Final MP4") >= 0 || ln.indexOf("DONE.") >= 0) p = "마무리 중";
      }
      return p;
    }
    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function escapeJs(s) {
      return String(s).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    }
    function openCardPrompt() {
      if (!selected) { alert("카드뉴스를 먼저 선택하세요."); return; }
      window.open("/card-prompt/" + encodeURIComponent(selected), "_blank");
    }
    reloadLists(); loadState(); loadJobHistory(); setInterval(loadState, 1500); setInterval(loadJobHistory, 5000); setInterval(loadCardnews, 10000);
  </script>
</body>
</html>"""


def main() -> int:
    if not SHORTS.exists():
        print(f"[ERROR] shorts folder missing: {SHORTS}")
        return 1
    host = os.environ.get("PHONESPOT_PANEL_HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, PORT), Handler)
    start_local_worker()
    # 5-1: 임베딩 캐시 백그라운드 워밍 - 첫 버튼2/렌더가 라이브러리 전체를 임베딩하느라
    # 기다리지 않도록 미리 캐시를 채운다. 실패해도 무해(폴백).
    try:
        subprocess.Popen(
            [sys.executable, str(SCRIPTS / "codex_warm_embeddings.py")],
            cwd=str(SHORTS),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass
    url = f"http://localhost:{PORT}/"
    print("=" * 60)
    print(" 폰스팟 통합 제작 패널")
    print("=" * 60)
    print(f"프로젝트: {ROOT}")
    print(f"주소    : {url}")
    print("카드뉴스 기능: 후보/프롬프트/이미지 폴더/렌더/결과/영상 넘기기")
    print("창을 닫으면 패널이 종료됩니다.")
    if os.environ.get("PHONESPOT_PANEL_NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        stop_local_worker()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
