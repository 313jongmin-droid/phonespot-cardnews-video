# -*- coding: utf-8 -*-
from __future__ import annotations

import hmac
import html
import json
import os
import re
import secrets
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
PANEL_VERSION = "phonespot-web-v60"
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,160}$")
REMOTE_QUEUE = RemoteQueue(ROOT)
LOCAL_HISTORY_PATH = DESK / "TEMP" / "local_job_history.json"
LOCAL_WORKER_PROCESS: subprocess.Popen | None = None
LOCAL_WORKER_STREAMS: list = []
# 서버가 pythonw(무콘솔)로 돌면 자식 콘솔 프로세스가 새 창을 띄운다 → 모든 subprocess에 적용.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _console_python() -> str:
    # 서버가 pythonw.exe(무콘솔)로 돌면 PY_EXE=pythonw → 자식 stdio 캡처 불안정.
    # 캡처가 필요한 자식은 옆의 python.exe(콘솔형)로 실행하고 무창은 CREATE_NO_WINDOW로 처리.
    import sys as _s
    from pathlib import Path as _P
    exe = _P(_s.executable)
    if __import__("os").name == "nt" and exe.name.lower() == "pythonw.exe":
        cand = exe.with_name("python.exe")
        if cand.exists():
            return str(cand)
    return _s.executable


PY_EXE = _console_python()
_GH_LAST_ATTEMPT = 0.0  # github_status: 실패해도 60s에 한 번만 재시도(매 폴링 스폰 방지)

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


def proposal_candidate_paths() -> set:
    """현재 가져오기 제안(IMPORT/CARD_IMPORT_PROPOSAL.json)의 후보 이미지 경로(소문자, resolve)."""
    out: set = set()
    for name in ("IMPORT_PROPOSAL.json", "CARD_IMPORT_PROPOSAL.json"):
        try:
            data = json.loads((DESK / name).read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in (data.get("assignments") or []):
            path = (item or {}).get("candidate_path")
            if isinstance(path, str) and path:
                try:
                    out.add(str(Path(path).resolve()).lower())
                except OSError:
                    pass
    return out


def prune_logs(max_files: int = 40, max_age_days: int = 14) -> int:
    """패널/워커 실행 로그 자동 정리(실행마다 새 파일 쌓이던 것): 기간 초과 삭제 + 종류별 최신 max_files개만 유지."""
    removed = 0
    cutoff = time.time() - max_age_days * 86400
    for folder, pattern in ((DESK / "TEMP" / "panel" / "panel_logs", "panel_*.log"),
                            (DESK / "TEMP" / "worker" / "logs", "worker_*.log")):
        if not folder.exists():
            continue
        files = []
        for f in folder.glob(pattern):
            try:
                files.append((f.stat().st_mtime, f))
            except OSError:
                pass
        files.sort(key=lambda t: t[0], reverse=True)
        for idx, (mtime, f) in enumerate(files):
            if idx >= max_files or mtime < cutoff:
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass  # 현재 실행 중인 로그(열려 있음)는 윈도우에서 삭제 불가 → 건너뜀
    return removed


def _pid_alive(pid: int) -> bool:
    """프로세스 생존 확인(부작용 없음).
    ★ 윈도우에서 os.kill(pid, 0)은 생존확인이 아니라 TerminateProcess(강제 종료)다(파이썬 문서:
      CTRL_C/CTRL_BREAK 외 시그널은 무조건 종료). 과거 이 코드가 고아 워커·PID 재할당된 무관 프로세스를 죽였다."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.GetExitCodeProcess.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # POSIX에서만 생존확인 의미
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _local_worker_online() -> bool:
    worker = REMOTE_QUEUE.workers().get(socket.gethostname()) or {}
    return bool(worker.get("online"))


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
            old_pid = int(pid_file.read_text(encoding="ascii").split()[0])
        except (OSError, ValueError, IndexError):
            old_pid = 0
        # 기존(고아) 워커가 살아있고 패널에 온라인 등록돼 있을 때만 재사용.
        # 그 외(PID가 다른 프로그램에 재할당 등)는 절대 건드리지 않고 새 워커를 띄운다.
        if old_pid and _pid_alive(old_pid) and _local_worker_online():
            return
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
        [PY_EXE, str(worker_script)],
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
    # 윈도우 terminate()=TerminateProcess라 워커의 atexit 정리가 안 돈다 → pid 파일은 서버가 직접 지운다.
    if LOCAL_WORKER_PROCESS is not None:
        try:
            (DESK / "TEMP" / "worker" / "local_worker.pid").unlink(missing_ok=True)
        except OSError:
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
                process_env["PYTHONUNBUFFERED"] = "1"
                process_env["GIT_TERMINAL_PROMPT"] = "0"
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    creationflags=NO_WINDOW,
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
                final_log = JOB["log"]
            update_local_history(job_id, {
                "status": "done" if exit_code == 0 else "failed",
                "finished_at": datetime.fromtimestamp(ended).isoformat(timespec="seconds"),
                "exit_code": exit_code,
                "message": "완료" if exit_code == 0 else f"종료 코드 {exit_code}",
                "log": final_log[-40000:],
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
        creationflags=NO_WINDOW,
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
        # 제목은 SNS 캡션 제목과 동일한 한글 title. 목록엔 첫 구절(/ 앞)만 깔끔하게. (2026-07-09)
        return (data.get("title", "") or "").split("/")[0].strip()
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
    return (-1, slug)  # 무번호(레거시·테스트)는 맨 아래로 — reverse=True에서 최신 번호 슬러그가 위 (2026-06-23)


def get_cardnews_rows() -> list[dict]:
    names: set[str] = set()
    for root in (CARD_OUTPUT, CARD_IMAGES):
        if root.exists():
            names.update(p.name for p in root.iterdir() if p.is_dir())
    if CARD_ARTICLES.exists():
        names.update(p.stem for p in CARD_ARTICLES.glob("*.json"))
    rows = [card_row(name) for name in names if SAFE_SLUG.match(name)]
    rows.sort(key=slug_sort_key, reverse=True)  # 최신(높은 번호) 위로 + [:80] 캡이 최신 80 보존
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
        global _GH_LAST_ATTEMPT
        now = time.time()
        file_fresh = status_file.exists() and (now - status_file.stat().st_mtime <= 60)
        attempt_recent = (now - _GH_LAST_ATTEMPT) < 60
        if (not file_fresh) and (not attempt_recent) and script.exists():
            _GH_LAST_ATTEMPT = now
            subprocess.run(
                [PY_EXE, str(script)],
                cwd=str(ROOT),
                creationflags=NO_WINDOW,
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
    # 같은 출처만 허용. (과거 *.googleusercontent.com 허용 = 아무나 만든 Apps Script 웹앱이 패널 액션을
    #  실행할 수 있던 구멍. Apps Script 쪽에 패널 호출 코드 없음 확인 후 제거, 2026-10.)
    return origin in {f"http://{host}", f"https://{host}"}


PANEL_TOKEN_PATH = DESK / "TEMP" / "panel" / "panel_token.txt"
_ALLOWED_HOSTS_CACHE: dict = {"at": 0.0, "hosts": set()}


def panel_token() -> str:
    """다른 기기(LAN) 접속용 토큰. 최초 1회 생성, TEMP(git 비추적)에 보관."""
    try:
        token = PANEL_TOKEN_PATH.read_text(encoding="ascii").strip()
        if len(token) >= 20:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(24)
    PANEL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PANEL_TOKEN_PATH.write_text(token, encoding="ascii")
    return token


def local_ipv4s() -> list[str]:
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            addr = str(info[4][0])
            if ":" not in addr:
                ips.add(addr)
    except OSError:
        pass
    try:  # 기본 경로 인터페이스 IP(실제 전송 없음, 라우팅 조회만)
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("10.255.255.255", 1))
            ips.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def allowed_hosts() -> set:
    now = time.time()
    if _ALLOWED_HOSTS_CACHE["hosts"] and now - _ALLOWED_HOSTS_CACHE["at"] < 60:
        return _ALLOWED_HOSTS_CACHE["hosts"]
    hosts = {"localhost", "127.0.0.1", "::1"}
    name = socket.gethostname().lower()
    hosts.update({name, name.split(".")[0]})
    try:
        hosts.add(socket.getfqdn().lower())
    except OSError:
        pass
    hosts.update(local_ipv4s())
    extra = os.environ.get("PHONESPOT_PANEL_ALLOWED_HOSTS", "")
    hosts.update(h.strip().lower() for h in extra.split(",") if h.strip())
    _ALLOWED_HOSTS_CACHE.update({"at": now, "hosts": hosts})
    return hosts


def request_host(handler: BaseHTTPRequestHandler) -> str:
    raw = (handler.headers.get("Host") or "").strip().lower()
    if raw.startswith("["):
        return raw[1:raw.find("]")] if "]" in raw else raw
    return raw.rsplit(":", 1)[0] if raw.count(":") == 1 else raw


def is_local_client(handler: BaseHTTPRequestHandler) -> bool:
    ip = str(handler.client_address[0] or "")
    if ip == "::1" or ip.startswith("127.") or ip.startswith("::ffff:127."):
        return True
    return ip.replace("::ffff:", "") in allowed_hosts()  # 같은 PC가 자기 LAN IP로 접속한 경우


def request_token(handler: BaseHTTPRequestHandler) -> str:
    token = (handler.headers.get("X-Panel-Token") or "").strip()
    if token:
        return token
    for part in (handler.headers.get("Cookie") or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == "panel_token":
            return value.strip()
    return (urllib.parse.parse_qs(urlparse(handler.path).query).get("t") or [""])[0]


def has_valid_token(handler: BaseHTTPRequestHandler) -> bool:
    token = request_token(handler)
    return bool(token) and hmac.compare_digest(token.encode(), panel_token().encode())


def access_denied_reason(handler: BaseHTTPRequestHandler, path: str) -> str:
    """접근 제어(빈 문자열 = 허용).
    - /api/health: 항상 허용(런처 헬스체크).
    - 유효 토큰(헤더/쿠키/?t=)이면 허용.
    - Host가 이 PC 이름·IP가 아니면 차단 = DNS 리바인딩(남의 도메인으로 127.0.0.1 접근) 방어.
    - /api/worker/*: Host만 맞으면 허용(원격 워커 호환).
    - 그 외: 같은 PC 접속만 토큰 없이 허용. 다른 기기는 토큰 필요("다른 기기 접속 링크")."""
    if path == "/api/health":
        return ""
    if has_valid_token(handler):
        return ""
    if request_host(handler) not in allowed_hosts():
        return "host not allowed"
    if path.startswith("/api/worker/"):
        return ""
    if is_local_client(handler):
        return ""
    return "token required"


def deny_response(handler: BaseHTTPRequestHandler, reason: str, path: str) -> None:
    if path.startswith("/api/"):
        json_response(handler, {"ok": False, "error": f"forbidden: {reason}"}, 403)
        return
    page = ("<!doctype html><html><head><meta charset='utf-8'><title>접근 제한</title></head>"
            "<body style='font-family:Arial,sans-serif;margin:32px;line-height:1.6'>"
            "<h2>폰스팟 패널 — 접근 제한</h2>"
            "<p>이 패널은 패널이 켜진 PC에서는 그대로 열립니다. 다른 기기(폰·다른 PC)에서 열려면 "
            "패널 PC 화면 상단의 <b>[다른 기기 접속 링크]</b>를 복사해 그 주소로 접속하세요(한 번 접속하면 저장됨).</p>"
            f"<p style='color:#888'>사유: {html.escape(reason)}</p></body></html>")
    html_response(handler, page, 403)


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
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    handler.send_header("Pragma", "no-cache")
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
    if length > 2 * 1024 * 1024:
        raise RuntimeError("요청 본문이 너무 큽니다(2MB 초과).")
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
            creationflags=NO_WINDOW,
        )
    target = f"http://localhost:8080/slug/{slug}" if slug else "http://localhost:8080/"
    webbrowser.open(target)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_OPTIONS(self) -> None:
        reason = access_denied_reason(self, urlparse(self.path).path)
        if reason:
            deny_response(self, reason, "/api/")
            return
        self.send_response(204)
        cors_headers(self)
        self.end_headers()

    def do_GET(self) -> None:
        # 과거엔 GET에 예외처리가 없어 RuntimeError 시 응답 없이 연결만 끊겼다(클라이언트는 원인 모름).
        try:
            self._handle_get()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:  # noqa: BLE001
            try:
                json_response(self, {"ok": False, "error": str(exc)}, 500)
            except Exception:
                pass

    def _handle_get(self) -> None:
        parsed = urlparse(self.path)
        reason = access_denied_reason(self, parsed.path)
        if reason:
            deny_response(self, reason, parsed.path)
            return
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
                    # 다운로드 폴더는 개인 파일이 섞여 있으므로 '현재 가져오기 제안의 후보'만 노출
                    if root == DOWNLOADS and str(target).lower() not in proposal_candidate_paths():
                        allowed = False
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
            if (urllib.parse.parse_qs(parsed.query).get("t") or [""])[0] and has_valid_token(self):
                self.send_response(302)  # 다른 기기: 토큰을 쿠키로 저장하고 주소창에서 토큰 제거
                self.send_header("Set-Cookie", f"panel_token={panel_token()}; Path=/; Max-Age=31536000; SameSite=Strict; HttpOnly")
                self.send_header("Location", "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            page = load_index_html()
            if is_local_client(self):  # 같은 PC에서 연 화면에만 다른 기기 접속 링크 제공
                links = ",".join(f"http://{ip}:{PORT}/?t={panel_token()}" for ip in local_ipv4s())
                page = page.replace("</head>", f'<meta name="panel-lan-links" content="{html.escape(links)}">\n</head>', 1)
            html_response(self, page)
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
            job = dict(select_panel_job(local_job, remote_job) or {})
            # 상태 폴링(1.5s)엔 로그 꼬리만: 진행률 파싱용. 전체/긴 꼬리는 펼칠 때 /api/job_log 로.
            if job.get("log"):
                job["log"] = str(job["log"])[-4000:]
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
                [PY_EXE, str(SCRIPTS / "codex_preflight_check.py"), slug, "--json"],
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                creationflags=NO_WINDOW,
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
        if parsed.path == "/api/job_log":
            query = urllib.parse.parse_qs(parsed.query)
            job_id = (query.get("id") or [""])[0]
            try:
                tail = max(0, int((query.get("tail") or ["0"])[0]))
            except ValueError:
                tail = 0
            log = REMOTE_QUEUE.job_log(job_id, tail or None)  # 원격: 잡별 로그 파일(전체)
            if log is None:
                with STATE_LOCK:
                    log = JOB.get("log") if (job_id and JOB.get("job_id") == job_id) else None  # 로컬 실행 중/직전
                if log is None:
                    log = next((j.get("log") or "" for j in read_local_history() if j.get("id") == job_id), "")
                if tail and len(log) > tail:
                    log = log[-tail:]
            json_response(self, {"ok": True, "log": log})
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
            reason = access_denied_reason(self, parsed.path)
            if reason:
                deny_response(self, reason, parsed.path)
                return
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
                             [[PY_EXE, str(SCRIPTS / "codex_library_sync.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "라이브러리 동기화 실행 — 실행 로그에서 가져옴/올림 개수를 확인하세요."})
                return
            if action == "library_dedup":
                # 라이브러리 근접중복 '리포트만'(읽기전용, 안전). 실제 정리는 bat --apply.
                ok = run_job("라이브러리 중복 점검(리포트)",
                             [[PY_EXE, str(SCRIPTS / "codex_library_dedup.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "중복 점검 완료 — 실행 로그와 codex/library_dedup_report.md 확인."})
                return
            if action == "library_backup":
                # 라이브러리(로컬+허브) 타임스탬프 스냅샷 백업(회전보관). 결과는 실행 로그에.
                ok = run_job("라이브러리 백업 스냅샷",
                             [[PY_EXE, str(SCRIPTS / "codex_library_backup.py")]], SHORTS)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True, "message": "라이브러리 백업 완료 — 실행 로그에서 위치/개수를 확인하세요."})
                return
            if action == "producer_check":
                # 이 PC가 카드뉴스 생성 + 영상 렌더를 모두 독립으로 할 수 있는지 자원 점검. 결과는 실행 로그에.
                ok = run_job("환경 점검(풀-생산기 자원)",
                             [[PY_EXE, str(SCRIPTS / "codex_producer_check.py")]], SHORTS)
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
            if action in ("video_prepare", "card_to_video"):
                slug = validate_slug(slug)
                commands = [
                    [PY_EXE, str(SCRIPTS / "codex_prepare_illustrations.py"), slug],
                    [PY_EXE, str(SCRIPTS / "codex_clean_latest_prompt.py"), slug],
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
                try:
                    proc = subprocess.run(
                        [PY_EXE, str(SCRIPTS / "codex_import_propose.py"), slug_now],
                        cwd=str(SHORTS), text=True, encoding="utf-8", errors="replace",
                        capture_output=True, timeout=120, creationflags=NO_WINDOW,
                    )
                except subprocess.TimeoutExpired:
                    json_response(self, {"ok": False, "message": "제안 생성 시간초과(120s). CLIP 모델 로드/다운로드가 지연됐을 수 있습니다. 부사수 PC에서 실행하거나 SETUP_EMBED 후 재시도하세요."})
                    return
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
                try:
                    proc = subprocess.run(
                        [PY_EXE, str(SCRIPTS / "cardnews_import_propose.py"), slug_now],
                        cwd=str(SHORTS), text=True, encoding="utf-8", errors="replace",
                        capture_output=True, timeout=120, creationflags=NO_WINDOW,
                    )
                except subprocess.TimeoutExpired:
                    json_response(self, {"ok": False, "message": "제안 생성 시간초과(120s). CLIP 모델 로드/다운로드가 지연됐을 수 있습니다. 부사수 PC에서 실행하거나 SETUP_EMBED 후 재시도하세요."})
                    return
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
            if action == "cover_render":
                slug = validate_slug(slug)
                job = REMOTE_QUEUE.enqueue("cover_render", slug, str(data.get("target_worker") or ""))
                json_response(self, {"ok": True, "queued": True, "job": job,
                                     "message": "커버만 다시 만들기 대기열 등록: " + slug + " (전체 재렌더 없음)"})
                return
            if action == "promo_list":
                try:
                    out = subprocess.run([PY_EXE, "scripts/promo_list.py"], cwd=str(SHORTS),
                                         capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
                    items = []
                    for line in (out.stdout or "").splitlines():
                        m = re.match(r"^\s*(\d{3})\s+(\S+)\s+(.+?)\s+\[(\w+)\]\s*$", line)
                        if m:
                            items.append({"nn": m.group(1), "label": m.group(2),
                                          "title": m.group(3).strip(), "preset": m.group(4)})
                    json_response(self, {"ok": True, "items": items})
                except Exception as exc:
                    json_response(self, {"ok": False, "items": [], "message": str(exc)})
                return
            if action == "promo_render":
                nn = str(data.get("nn") or "").strip()
                label = str(data.get("label") or "").strip()
                preset = (str(data.get("preset") or "").strip() or "showcase")
                if not nn or not label:
                    json_response(self, {"ok": False, "message": "스크립트를 선택하세요."})
                    return
                slug_now = nn + "_" + label + "_" + preset
                job = REMOTE_QUEUE.enqueue("promo_render", slug_now, str(data.get("target_worker") or ""))
                json_response(self, {"ok": True, "queued": True, "job": job,
                                     "message": "타이포 렌더 대기열 등록: " + nn + " [" + preset + "]"})
                return
            if action == "promo_generate":
                # 주제 -> promo_generate.py 로 신규 MD 자동 작성 + md2json -> 바로 promo_render 큐.
                # (promo task 소유 generator 호출. 패널은 호출+렌더 연결만 — HANDOFF §4 알림 대상.)
                slug_req = str(data.get("slug") or "").strip()
                title = str(data.get("title") or slug_req).strip()
                preset = str(data.get("preset") or "").strip()
                if not slug_req:
                    json_response(self, {"ok": False, "message": "주제를 선택하세요."})
                    return
                try:
                    cmd = [PY_EXE, "scripts/promo_generate.py", title, "--slug", slug_req]
                    if preset:
                        cmd += ["--preset", preset]
                    gen = subprocess.run(cmd, cwd=str(SHORTS), capture_output=True, text=True, timeout=90, creationflags=NO_WINDOW)
                    okline = ""
                    for ln in (gen.stdout or "").splitlines():
                        if ln.startswith("OK "):
                            okline = ln.strip()
                    if not okline:
                        tail = ((gen.stderr or "") + (gen.stdout or ""))[-200:]
                        json_response(self, {"ok": False, "message": "생성 실패: " + tail})
                        return
                    _, g_nn, g_label, g_preset = okline.split()
                    slug_now = g_nn + "_" + g_label + "_" + g_preset
                    job = REMOTE_QUEUE.enqueue("promo_render", slug_now, str(data.get("target_worker") or ""))
                    json_response(self, {"ok": True, "queued": True, "job": job,
                                         "nnn": g_nn, "label": g_label, "preset": g_preset,
                                         "message": "자동 생성+렌더 등록: " + g_nn + "_" + g_label + " [" + g_preset + "]"})
                except Exception as exc:
                    json_response(self, {"ok": False, "message": "생성 오류: " + str(exc)})
                return
            if action == "style_request":
                slug_req = str(data.get("slug") or "").strip()
                track = str(data.get("track") or "").strip()
                if not slug_req or track not in ("typo", "ai"):
                    json_response(self, {"ok": False, "message": "주제와 트랙을 선택하세요."})
                    return
                reqdir = ROOT / "_state"
                reqdir.mkdir(parents=True, exist_ok=True)
                rec = {"ts": int(time.time()), "slug": slug_req, "track": track, "status": "pending"}
                with open(reqdir / "style_requests.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                json_response(self, {"ok": True, "message": "요청 등록: " + slug_req + " -> " + track})
                return
            if action == "style_pending":
                fp = ROOT / "_state" / "style_requests.jsonl"
                items = []
                if fp.exists():
                    for line in fp.read_text(encoding="utf-8").splitlines()[-40:]:
                        try:
                            items.append(json.loads(line))
                        except Exception:
                            pass
                json_response(self, {"ok": True, "items": items})
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
            if action == "open_results":
                safe_open(DESK / "RESULTS")
                json_response(self, {"ok": True})
                return
            if action == "open_illustrations":
                safe_open(DESK / "ILLUSTRATION_DROP")
                json_response(self, {"ok": True})
                return
            if action == "work_queue_refresh":
                ok = run_job("작업대장 새로고침", [[PY_EXE, str(SCRIPTS / "codex_work_queue.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "panel_update_restart":
                ps1 = Path(__file__).resolve().parent / "start_hidden.ps1"
                if not ps1.exists():
                    json_response(self, {"ok": False, "message": "start_hidden.ps1을 찾을 수 없습니다."})
                    return
                # DETACHED_PROCESS(0x8) | CREATE_NEW_PROCESS_GROUP(0x200): 재기동 런처가
                # 서버(자기 자신) 종료 후에도 살아남아야 하므로 완전 분리 실행.
                flags = 0x00000008 | 0x00000200
                try:
                    subprocess.Popen(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                         "-File", str(ps1), "-UpdateRestart"],
                        cwd=str(DESK),
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=flags, close_fds=True,
                    )
                    receiver = (DESK / "TEMP" / "panel" / "auto_update.on").exists()
                    json_response(self, {"ok": True, "message": ("최신 코드를 받고(수신 PC) 패널을 재시작합니다." if receiver else "패널을 재시작합니다(이 PC는 push 전용이라 pull 없이 재시작만).") + " 잠시 후 자동 새로고침됩니다."})
                except Exception as exc:  # noqa: BLE001
                    json_response(self, {"ok": False, "message": f"재시작 실행 실패: {exc}"})
                return
            if action == "system_upload":
                ok = run_job("시스템 업로드: GitHub commit/push", [[PY_EXE, str(DESK / "MAINTENANCE" / "codex_github_upload.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "system_update":
                ok = run_job("시스템 업데이트: GitHub pull", [[PY_EXE, str(DESK / "MAINTENANCE" / "codex_github_update.py")]], ROOT)
                if not ok:
                    json_response(self, {"ok": False, "busy": True, "message": "이미 다른 작업이 실행 중입니다. 현재 작업이 끝난 뒤 다시 눌러주세요."})
                else:
                    json_response(self, {"ok": True})
                return
            if action == "open_card_images":
                slug = validate_slug(slug)
                (CARD_IMAGES / slug).mkdir(parents=True, exist_ok=True)
                safe_open(CARD_IMAGES / slug)
                json_response(self, {"ok": True})
                return
            if action == "open_card_result":
                slug = validate_slug(slug)
                safe_open_existing(CARD_OUTPUT / slug)
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


STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_PATH = STATIC_DIR / "index.html"


def load_index_html() -> str:
    # 화면(HTML/CSS/JS) 정본 = dashboard/static/index.html. 요청마다 디스크에서 읽어 서빙한다.
    # → UI만 바꾸면 브라우저 새로고침으로 반영(재기동·PANEL_VERSION bump 불필요).
    # → server.py 거대 raw string 편집 시 파일 꼬리 truncation 사고 원천 차단.
    return INDEX_PATH.read_text(encoding="utf-8")


def main() -> int:
    if not SHORTS.exists():
        print(f"[ERROR] shorts folder missing: {SHORTS}")
        return 1
    host = os.environ.get("PHONESPOT_PANEL_HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, PORT), Handler)
    try:
        prune_logs()
    except Exception:
        pass
    start_local_worker()
    # 5-1: 임베딩 캐시 백그라운드 워밍 - 첫 버튼2/렌더가 라이브러리 전체를 임베딩하느라
    # 기다리지 않도록 미리 캐시를 채운다. 실패해도 무해(폴백).
    try:
        subprocess.Popen(
            [PY_EXE, str(SCRIPTS / "codex_warm_embeddings.py")],
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
        REMOTE_QUEUE.flush()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
