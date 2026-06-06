# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import os
import re
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
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,160}$")
REMOTE_QUEUE = RemoteQueue(ROOT)

STATE_LOCK = threading.Lock()
JOB = {
    "running": False,
    "name": "",
    "started": 0.0,
    "ended": 0.0,
    "exit_code": None,
    "log": "",
}


def append_log(text: str) -> None:
    with STATE_LOCK:
        JOB["log"] += text
        if len(JOB["log"]) > 260_000:
            JOB["log"] = JOB["log"][-260_000:]


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
    with STATE_LOCK:
        if JOB["running"]:
            return False
        JOB.update({
            "running": True,
            "name": name,
            "started": time.time(),
            "ended": 0.0,
            "exit_code": None,
            "log": f"[START] {name}\n",
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
            with STATE_LOCK:
                JOB["running"] = False
                JOB["ended"] = time.time()
                JOB["exit_code"] = exit_code
                JOB["log"] += "\n[DONE]\n" if exit_code == 0 else "\n[FAILED]\n"
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
    rows = parse_slugs(run_capture([sys.executable, str(SCRIPTS / "list_slugs.py")]))
    rows.sort(key=slug_sort_key)
    card_map = {row["slug"]: row for row in get_cardnews_rows()}
    for row in rows:
        card = card_map.get(row["slug"])
        if card:
            row["stage"] = card.get("stage", "")
            row["stageClass"] = card.get("stageClass", "")
        else:
            row["stage"] = "부분"
            row["stageClass"] = "muted"
    return rows


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
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
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
    if kind not in {"illust", "image", "logo", "mascot", "none"}:
        raise RuntimeError(f"unsupported visual type: {kind}")
    if kind == "none":
        return {"type": "none", "value": "none"}
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
        visuals.append({"type": "none", "value": "none"})
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
    path = override_path_for_slug(slug)
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return
    sections = payload.get("sections") or {}
    if not isinstance(sections, dict):
        return
    for section_name, override in sections.items():
        if not isinstance(override, dict):
            continue
        try:
            sec = get_section_obj(data, section_name)
        except Exception:
            continue
        chunks = [str(x).strip() for x in (override.get("chunks") or []) if str(x).strip()]
        if chunks:
            sec["caption_chunks"] = chunks
            sec["display_chunks"] = [strip_display_period(chunk) for chunk in chunks]
            sec["_codex_chunk_override"] = True
        visuals = override.get("visuals")
        if isinstance(visuals, list):
            sec["chunk_visuals"] = visuals
    data["_codex_chunk_overrides_applied"] = True


def strip_display_period(text: str) -> str:
    return str(text or "").strip().rstrip(".。.!?！？").strip()


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


def validate_override_section(section_name: str, sec: dict, chunks: list[str]) -> None:
    clean = [str(x).strip() for x in chunks if str(x).strip()]
    if not clean:
        raise RuntimeError("chunk list is empty")
    tts = str(sec.get("tts") or "").strip()
    if tts and compare_text(" ".join(clean)) != compare_text(tts):
        raise RuntimeError(
            f"{section_name}: chunks must preserve the TTS sentence. "
            "Use merge/split only; do not add or remove words."
        )
    for idx, chunk in enumerate(clean, 1):
        units = len(re.sub(r"\s+", "", chunk))
        if len(clean) > 1 and units < 4:
            raise RuntimeError(f"{section_name} chunk {idx}: too short")
        if units > 42:
            raise RuntimeError(f"{section_name} chunk {idx}: too long")
    forbidden_end = ("은", "는", "이", "가", "을", "를", "에", "의", "와", "과", "로", "으로")
    forbidden_start = ("은", "는", "이", "가", "을", "를", "에", "의", "와", "과", "로", "으로")
    for left, right in zip(clean, clean[1:]):
        lword = left.split()[-1] if left.split() else ""
        rword = right.split()[0] if right.split() else ""
        if lword in forbidden_end or rword in forbidden_start:
            raise RuntimeError(f"{section_name}: unnatural Korean boundary near `{lword} | {rword}`")


def save_chunk_override(slug: str, section: str, sec: dict, chunks: list[str], visuals: list[dict]) -> Path:
    validate_override_section(section, sec, chunks)
    CHUNK_OVERRIDES.mkdir(parents=True, exist_ok=True)
    path = override_path_for_slug(slug)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    else:
        payload = {"version": 1, "slug": slug, "sections": {}}
    payload.setdefault("sections", {})[section] = {
        "chunks": [str(x).strip() for x in chunks if str(x).strip()],
        "display_chunks": [strip_display_period(x) for x in chunks if str(x).strip()],
        "visuals": visuals,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "policy": "TTS text is preserved; only screen chunk boundaries are overridden.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return path


def chunk_rows_for_slug(slug: str) -> list[dict]:
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    rows = []
    for section, sec in section_names(data):
        chunks = chunk_source(sec)
        visuals = sec.get("chunk_visuals") or []
        for index, chunk in enumerate(chunks):
            visual = visuals[index] if index < len(visuals) and isinstance(visuals[index], dict) else {}
            rows.append({
                "section": section,
                "chunk_index": index,
                "chunk": index + 1,
                "text": strip_display_period(chunk),
                "visual": f"{visual.get('type', '-')}: {visual.get('value', '-')}",
                "chars": len(str(chunk).replace("\\n", "")),
                "override": bool(sec.get("_codex_chunk_override")),
            })
    return rows


def best_split_index(text: str) -> int:
    plain = " ".join(str(text or "").replace("\\n", " ").split())
    if len(plain) < 18:
        return -1
    preferred = [" 그리고 ", " 또한 ", " 다만 ", " 때문에 ", " 기준 ", " 경우 ", "이며 ", "하고 ", ", "]
    target = len(plain) // 2
    best = -1
    best_score = 10_000
    for token in preferred:
        start = 0
        while True:
            pos = plain.find(token, start)
            if pos < 0:
                break
            split = pos + len(token)
            score = abs(split - target)
            if 7 <= split <= len(plain) - 7 and score < best_score:
                best = split
                best_score = score
            start = pos + 1
    if best >= 0:
        return best
    spaces = [m.start() for m in re.finditer(r"\s+", plain)]
    if not spaces:
        return -1
    split = min(spaces, key=lambda x: abs(x - target))
    return split if 7 <= split <= len(plain) - 7 else -1


def auto_linebreak(text: str) -> str:
    plain = " ".join(str(text or "").replace("\\n", " ").split())
    if len(plain) <= 18:
        return strip_display_period(plain)
    idx = best_split_index(plain)
    if idx < 0:
        return strip_display_period(plain)
    left = plain[:idx].strip(" ,")
    right = plain[idx:].strip(" ,")
    if not left or not right:
        return strip_display_period(plain)
    return strip_display_period(left) + "\\n" + strip_display_period(right)


def adjust_chunk_boundary(slug: str, section: str, chunk_index: int, op: str) -> Path:
    path = script_path_for_slug(slug)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    apply_chunk_overrides(data, slug)
    sec = get_section_obj(data, section)
    chunks = chunk_source(sec)
    if not chunks:
        raise RuntimeError(f"{section} has no chunks")
    if not (0 <= chunk_index < len(chunks)):
        raise RuntimeError(f"chunk index out of range: {chunk_index}")
    visuals = sec.setdefault("chunk_visuals", [])
    if not isinstance(visuals, list):
        visuals = []
    visuals = [dict(v) if isinstance(v, dict) else {"type": "none", "value": "none"} for v in visuals]
    while len(visuals) < len(chunks):
        visuals.append({"type": "none", "value": "none"})

    if op == "linebreak":
        chunks[chunk_index] = auto_linebreak(chunks[chunk_index])
    elif op == "merge_prev":
        if chunk_index <= 0:
            raise RuntimeError("first chunk cannot merge previous")
        chunks[chunk_index - 1] = (chunks[chunk_index - 1].replace("\\n", " ").rstrip(" ,") + " " + chunks[chunk_index].replace("\\n", " ").lstrip()).strip()
        del chunks[chunk_index]
        if len(visuals) > chunk_index:
            del visuals[chunk_index]
    elif op == "merge_next":
        if chunk_index >= len(chunks) - 1:
            raise RuntimeError("last chunk cannot merge next")
        chunks[chunk_index] = (chunks[chunk_index].replace("\\n", " ").rstrip(" ,") + " " + chunks[chunk_index + 1].replace("\\n", " ").lstrip()).strip()
        del chunks[chunk_index + 1]
        if len(visuals) > chunk_index + 1:
            del visuals[chunk_index + 1]
    elif op == "split_auto":
        plain = " ".join(chunks[chunk_index].replace("\\n", " ").split())
        split = best_split_index(plain)
        if split < 0:
            raise RuntimeError("this chunk is too short or has no safe split point")
        left = plain[:split].strip(" ,")
        right = plain[split:].strip(" ,")
        chunks[chunk_index] = left
        chunks.insert(chunk_index + 1, right)
        visuals.insert(chunk_index + 1, {"type": "none", "value": "none"})
    elif op == "rebalance_section":
        chunks = [auto_linebreak(x) for x in chunks]
    else:
        raise RuntimeError(f"unknown chunk operation: {op}")

    while len(visuals) > len(chunks):
        visuals.pop()
    return save_chunk_override(slug, section, sec, chunks, visuals)


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
            json_response(self, {"ok": True, "service": "phonespot-panel"})
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
            if parsed.path == "/api/worker/result":
                query = urllib.parse.parse_qs(parsed.query)
                job_id = (query.get("job_id") or [""])[0]
                length = int(self.headers.get("Content-Length", "0") or "0")
                filename = self.headers.get("X-File-Name", "result.mp4")
                path = REMOTE_QUEUE.save_result(job_id, filename, self.rfile.read(length))
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
  <style>
    :root { --bg:#f5f6f8; --panel:#fff; --ink:#15181d; --muted:#667085; --line:#dde2ea; --orange:#f74b0b; --blue:#17345f; --red:#b42318; --green:#027a48; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font-family:"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif; }
    header { min-height:64px; display:flex; align-items:center; justify-content:space-between; padding:12px 24px; background:#111827; color:white; gap:16px; }
    header strong { font-size:20px; } header span { color:#cbd5e1; font-size:13px; word-break:break-all; }
    main { display:grid; grid-template-columns:400px 1fr; gap:16px; padding:16px; max-width:1540px; margin:0 auto; }
    section { background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    .head { display:flex; align-items:center; justify-content:space-between; padding:13px 15px; border-bottom:1px solid var(--line); background:#fbfcfd; gap:10px; }
    h2 { margin:0; font-size:16px; } .small { font-size:12px; color:var(--muted); }
    .pad { padding:14px 16px; }
    .tabs { display:flex; gap:8px; padding:10px; background:#fff; border-bottom:1px solid var(--line); }
    .tab { flex:1; border:1px solid var(--line); background:#fff; border-radius:7px; padding:9px; cursor:pointer; font-weight:700; }
    .tab.active { background:#fff0e8; border-color:var(--orange); color:var(--orange); }
    .list { max-height:715px; overflow:auto; }
    .row { width:100%; border:0; border-bottom:1px solid #eef1f5; background:white; text-align:left; padding:10px 12px; cursor:pointer; display:grid; gap:8px; align-items:center; font-size:13px; }
    .row.video { grid-template-columns:44px 82px 58px 92px minmax(0,1fr); }
    .row.card { grid-template-columns:44px 82px 92px minmax(0,1fr); }
    .row:hover { background:#fff7f3; } .row.active { background:#fff0e8; outline:2px solid rgba(247,75,11,.25); }
    .row-number { display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:8px; background:#0f172a; color:white; font-size:15px; font-weight:900; line-height:1; }
    .row.active .row-number { background:var(--orange); color:white; }
    .row-date,.flag { color:#334155; font-size:12px; white-space:nowrap; }
    .slug-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; font-weight:700; }
    .title-sub { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); font-size:12px; margin-top:2px; font-weight:400; }
    .flag { font-weight:700; color:var(--blue); }
    .stage-pill { display:inline-flex; align-items:center; justify-content:center; min-width:82px; padding:4px 8px; border-radius:999px; font-size:11px; font-weight:800; border:1px solid var(--line); background:#f8fafc; color:#475569; }
    .stage-pill.ok { background:#ecfdf5; border-color:#86efac; color:#166534; }
    .stage-pill.warn { background:#fff7ed; border-color:#fdba74; color:#9a3412; }
    .stage-pill.muted { background:#f1f5f9; border-color:#cbd5e1; color:#64748b; }
    .grid { display:grid; grid-template-columns:repeat(3, minmax(160px,1fr)); gap:12px; }
    .action-head { align-items:flex-start; }
    .selected-badge { min-width:360px; max-width:720px; padding:10px 14px; border:2px solid var(--orange); border-radius:10px; background:#fff7f3; color:#111827; box-shadow:0 6px 20px rgba(247,75,11,.12); }
    .selected-badge span { display:block; font-size:12px; color:#9a3412; font-weight:700; margin-bottom:4px; }
    .selected-badge b { display:block; font-size:22px; line-height:1.18; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .status-note { margin-top:8px; padding:10px 12px; background:#f8fafc; border:1px solid var(--line); border-radius:8px; line-height:1.45; }
    .btn { border:1px solid var(--line); background:white; border-radius:8px; min-height:84px; padding:12px; cursor:pointer; text-align:left; }
    .btn:hover { border-color:var(--orange); box-shadow:0 2px 12px rgba(0,0,0,.06); }
    .btn.primary { background:var(--orange); color:white; border-color:var(--orange); }
    .btn strong { display:block; font-size:15px; margin-bottom:6px; } .btn span { font-size:12px; color:inherit; opacity:.82; line-height:1.35; }
    .runtime-strip { max-width:1520px; margin:14px auto 0; padding:0 18px; display:grid; grid-template-columns:1.05fr 1.25fr .9fr .9fr; gap:10px; box-sizing:border-box; }
    .runtime-card { border:1px solid var(--line); border-radius:10px; background:white; padding:10px 12px; min-height:62px; min-width:0; }
    .runtime-card span { display:block; font-size:11px; color:#64748b; margin-bottom:5px; }
    .runtime-card b { display:block; font-size:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .runtime-card.good { border-color:#86efac; background:#f0fdf4; }
    .runtime-card.bad { border-color:#fecaca; background:#fef2f2; }
    .runtime-card.warn { border-color:#fdba74; background:#fff7ed; }
    .runtime-action { margin-top:8px; border:1px solid var(--orange); background:white; color:var(--orange); border-radius:7px; padding:5px 8px; font-size:11px; font-weight:800; cursor:pointer; }
    .runtime-action:hover { background:#fff0e8; }
    .runtime-actions { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .runtime-actions .runtime-action { margin-top:8px; }
    .runtime-select { width:100%; margin-top:7px; border:1px solid var(--line); border-radius:6px; padding:5px 7px; background:white; font-size:11px; }
    .status { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
    .metric { border:1px solid var(--line); border-radius:8px; padding:12px; background:white; min-height:76px; } .metric b { display:block; font-size:20px; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .warn { color:var(--red); } .ok { color:var(--green); }
    .log { height:390px; overflow:auto; background:#0b1020; color:#dbeafe; padding:14px; font-family:Consolas,monospace; font-size:12px; white-space:pre-wrap; }
    .results { max-height:170px; overflow:auto; font-size:13px; } .result-row { display:flex; justify-content:space-between; gap:10px; padding:7px 0; border-bottom:1px solid #eef1f5; }
    .result-row > * { min-width:0; }
    .result-row a { overflow-wrap:anywhere; word-break:break-word; }
    .preflight-panel { display:none; border-top:1px solid var(--line); background:#f8fafc; }
    .preflight-list { display:grid; gap:8px; }
    .preflight-item { border:1px solid var(--line); border-radius:8px; padding:8px 10px; background:white; font-size:13px; line-height:1.45; }
    .preflight-item.OK { border-color:#86efac; background:#f0fdf4; }
    .preflight-item.WARN { border-color:#fdba74; background:#fff7ed; }
    .preflight-item.ERROR { border-color:#fecaca; background:#fef2f2; }
    .preflight-item pre { white-space:pre-wrap; margin:6px 0 0; font-family:Consolas,monospace; font-size:12px; color:#334155; }
    .weak-panel { display:none; border-top:1px solid var(--line); background:#fffaf7; }
    .weak-table { width:100%; border-collapse:collapse; font-size:12px; }
    .weak-table th,.weak-table td { border-bottom:1px solid #f0d8ce; padding:8px; vertical-align:top; text-align:left; }
    .weak-table th { background:#fff0e8; color:#7a271a; position:sticky; top:0; }
    .weak-scroll { max-height:330px; overflow:auto; }
    .weak-table select,.weak-table input { width:100%; border:1px solid #e7b9a8; border-radius:6px; padding:6px; font-size:12px; background:white; }
    .mini-btn { border:1px solid var(--orange); color:var(--orange); background:white; border-radius:6px; padding:6px 8px; cursor:pointer; font-size:12px; margin:2px; }
    .mini-btn:hover { background:#fff0e8; }
    .chunk-panel { display:none; border-top:1px solid var(--line); background:#f8fbff; }
    .chunk-table { width:100%; border-collapse:collapse; font-size:12px; }
    .chunk-table th,.chunk-table td { border-bottom:1px solid #dbe7f5; padding:8px; vertical-align:top; text-align:left; }
    .chunk-table th { background:#edf5ff; color:#17345f; position:sticky; top:0; }
    .chunk-text { white-space:pre-wrap; line-height:1.45; }
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
  <header><div><strong>폰스팟 통합 제작 패널</strong> <span>카드뉴스 + 숏폼 영상</span></div><span id="rootText"></span></header>
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
          <button class="btn primary" onclick="runAction('video_import_render')"><strong>2. 이미지 가져오기 + 렌더</strong><span>다운로드한 GPT 이미지를 반영하고 최신 영상 작업물을 렌더합니다.</span></button>
          <button class="btn" onclick="runPreflight()"><strong>렌더 전 사전검사</strong><span>이미지, 스크립트, CTA, 한글 문장, 중복 사용을 먼저 확인합니다.</span></button>
          <button class="btn" onclick="runAction('video_render_selected')"><strong>3. 선택 영상만 렌더</strong><span>추가 이미지 없이 현재 선택한 슬러그를 다시 렌더합니다.</span></button>
          <button class="btn" onclick="window.open('/prompt','_blank')"><strong>영상 이미지 프롬프트 보기</strong><span>최신 영상용 GPT 프롬프트를 브라우저에서 엽니다.</span></button>
          <button class="btn" onclick="openIllustrationRequests()"><strong>신규 일러스트 요청서</strong><span>선택한 영상의 범용 일러스트 추천과 GPT 프롬프트를 엽니다.</span></button>
          <button class="btn" onclick="runAction('open_results')"><strong>영상 결과 폴더</strong><span>완성 MP4와 발행 패키지 폴더를 엽니다.</span></button>
          <button class="btn" onclick="runAction('system_update')"><strong>시스템 업데이트</strong><span>GitHub에서 최신 코드만 받아옵니다. 렌더 결과물은 건드리지 않습니다.</span></button>
          <button class="btn" onclick="runAction('open_illustrations')"><strong>일러스트 폴더</strong><span>재사용 일러스트 라이브러리와 드롭 폴더를 엽니다.</span></button>
          <button class="btn" onclick="chooseUpload('illustration')"><strong>일러스트 웹 업로드</strong><span>다른 PC에서도 생성한 일러스트를 드롭 폴더에 바로 올립니다.</span></button>
          <button class="btn" onclick="showChunks()"><strong>7. 청크 경계 편집</strong><span>문구 내용과 TTS는 유지하고 줄바꿈, 앞뒤 합치기, 자동 분할만 조정합니다.</span></button>
        </div>
        <div id="cardActions" class="pad grid" style="display:none">
          <button class="btn" onclick="reloadLists()"><strong>1. 후보 새로고침</strong><span>cardnews/articles, images, output 폴더를 다시 스캔합니다. 외부 뉴스 수집 실행은 아직 붙이지 않았습니다.</span></button>
          <button class="btn" onclick="runAction('telegram_card_summary')"><strong>후보 현황 텔레그램</strong><span>현재 카드뉴스 후보와 상태를 텔레그램으로 보냅니다.</span></button>
          <button class="btn primary" onclick="openCardPrompt()"><strong>2. 이미지 프롬프트 보기</strong><span>선택한 카드뉴스의 images/&lt;slug&gt;/prompt.md를 브라우저에서 확인합니다.</span></button>
          <button class="btn" onclick="runAction('open_card_images')"><strong>3. 이미지 업로드 폴더</strong><span>1.png~5.png를 넣을 카드뉴스 이미지 폴더를 엽니다.</span></button>
          <button class="btn" onclick="chooseUpload('card')"><strong>3-1. 이미지 웹 업로드</strong><span>다른 PC에서도 카드 이미지를 선택 항목에 바로 올립니다.</span></button>
          <button class="btn primary" onclick="runAction('card_render')"><strong>4. 카드뉴스 생성</strong><span>기존 카드뉴스 렌더러를 실행해 1x1, 4x5, 9x16 카드와 captions.md를 생성합니다.</span></button>
          <button class="btn" onclick="runAction('open_card_result')"><strong>5. 카드뉴스 결과 확인</strong><span>완성된 카드뉴스 output 폴더를 엽니다.</span></button>
          <button class="btn primary" onclick="runAction('card_to_video')"><strong>6. 영상으로 넘기기</strong><span>완성된 카드뉴스를 Codex 숏폼 영상 준비 단계로 넘깁니다.</span></button>
        </div>
      </section>
      <section>
        <div class="head"><h2>상태</h2><span class="small" id="jobText">대기 중</span></div>
        <div class="pad status">
          <div class="metric"><span class="small" id="metric1Label">선택 슬러그</span><b id="latestSlug">-</b></div>
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
          <div class="pad small">문장 내용과 TTS는 바꾸지 않습니다. 화면에 보이는 청크 경계와 줄바꿈만 조정합니다.</div>
          <div class="weak-scroll">
            <table class="chunk-table">
              <thead><tr><th>구간</th><th>청크 문구</th><th>visual</th><th>작업</th></tr></thead>
              <tbody id="chunkRows"></tbody>
            </table>
          </div>
        </div>
      </section>
      <section><div class="head"><h2>실행 로그</h2><span class="small">실패하면 이 로그를 복사해서 보내면 됩니다.</span></div><div id="log" class="log"></div></section>
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
        btn.innerHTML = `<span class="row-number">${item.number}</span><span class="row-date">${item.date}</span><span class="flag">[${item.flag}]</span><span class="stage-pill ${item.stageClass || "muted"}">${item.stage || "-"}</span><span class="slug-name">${item.slug}</span>`;
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
        btn.innerHTML = `<span class="row-number">${idx + 1}</span><span class="row-date">${item.date || "-"}</span><span class="stage-pill ${item.stageClass || "muted"}">${item.stage || item.status}</span><span class="slug-name">${item.slug}<span class="title-sub">${item.title || ""}</span><span class="title-sub">이미지 ${item.images}/5 · 카드 ${item.cards} · 프롬프트 ${item.prompt ? "있음" : "없음"}</span></span>`;
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
    async function loadState() {
      const data = await api("/api/state");
      lastState = data;
      document.getElementById("rootText").textContent = data.root;
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
      const runtimeJob = document.getElementById("runtimeJob");
      const runtimeJobText = document.getElementById("runtimeJobText");
      if (runtimeJobText) runtimeJobText.textContent = job.running ? `실행 중 · ${job.name}` : (job.exit_code === null ? "대기 중" : `마지막 종료 ${job.exit_code}`);
      if (runtimeJob) runtimeJob.className = `runtime-card ${job.running ? "warn" : (job.exit_code === 0 ? "good" : (job.exit_code === null ? "" : "bad"))}`;
      const cancelButton = document.getElementById("cancelJobButton");
      const retryButton = document.getElementById("retryJobButton");
      cancelButton.style.display = job.remote && job.running ? "" : "none";
      retryButton.style.display = job.remote && !job.running && job.exit_code !== 0 ? "" : "none";
      document.getElementById("jobText").textContent = job.running ? `실행 중: ${job.name}` : (job.exit_code === null ? "대기 중" : `마지막 종료 코드: ${job.exit_code}`);
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

    async function runAction(action) {
      console.log("runAction", action);
      try {
        const targetWorker = document.getElementById("targetWorker")?.value || "";
        const result = await api("/api/action", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({action, slug:selected, target_worker:targetWorker}) });
        if (!result.ok) {
          alert(result.message || "작업을 시작하지 못했습니다. 실행 로그를 확인해주세요.");
        }
        await loadState();
      } catch (err) { alert(String(err)); }
    }
    async function cancelRemoteJob() {
      if (!currentRemoteJob?.job_id) return;
      await api("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"remote_job_cancel", job_id:currentRemoteJob.job_id})});
      await loadState();
    }
    async function retryRemoteJob() {
      if (!currentRemoteJob?.job_id) return;
      await api("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"remote_job_retry", job_id:currentRemoteJob.job_id})});
      await loadState();
    }
    function toggleWeakPanel() {
      const panel = document.getElementById("weakPanel");
      panel.style.display = panel.style.display === "block" ? "none" : "block";
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
        if (!rows.length) {
          body.innerHTML = "<tr><td colspan='4'>청크가 없습니다. 먼저 영상 이미지 프롬프트 준비를 실행하세요.</td></tr>";
        }
        rows.forEach((r) => {
          const tr = document.createElement("tr");
          const overrideBadge = r.override ? "<br><span class='pill ok'>편집본</span>" : "";
          tr.innerHTML = `<td>${escapeHtml(r.section)}<br>청크 ${Number(r.chunk) || 0}<br>${Number(r.chars) || 0}자${overrideBadge}</td>
            <td class="chunk-text">${escapeHtml(r.text || "")}</td>
            <td>${escapeHtml(r.visual || "-")}</td>
            <td>
              <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'linebreak')">줄바꿈 정리</button>
              <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'merge_prev')">앞과 합치기</button>
              <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'merge_next')">뒤와 합치기</button>
              <button class="mini-btn" onclick="adjustChunk('${escapeJs(r.section)}', ${Number(r.chunk_index)||0}, 'split_auto')">자동 둘로 나누기</button>
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
    async function adjustChunk(section, chunkIndex, op) {
      try {
        const result = await api("/api/action", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ action:"adjust_chunk", slug:selected, section, chunk_index:chunkIndex, op })
        });
        if (!result.ok) {
          alert(result.message || "청크 조정에 실패했습니다.");
          return;
        }
        await showChunks();
      } catch (err) {
        alert("청크 조정 실패\n" + String(err));
      }
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
    reloadLists(); loadState(); setInterval(loadState, 1500); setInterval(loadCardnews, 10000);
  </script>
</body>
</html>"""


def main() -> int:
    if not SHORTS.exists():
        print(f"[ERROR] shorts folder missing: {SHORTS}")
        return 1
    host = os.environ.get("PHONESPOT_PANEL_HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, PORT), Handler)
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
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
