# -*- coding: utf-8 -*-
"""Install an illustration tag DB and recent-use ranking layer for Codex shorts."""
from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


DB_MODULE = r'''# -*- coding: utf-8 -*-
"""Illustration metadata and recent-use ranking for PhoneSpot Codex shorts."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"
CONFIG_DIR = SHORTS / "config"
CODEX_DIR = SHORTS / "codex"
DB_PATH = CONFIG_DIR / "illustration_tag_db.json"
HISTORY_PATH = CODEX_DIR / "illustration_usage_history.json"
REPORT_PATH = CODEX_DIR / "ILLUSTRATION_TAG_DB.md"


SEED = {
    "aluminum_label": {"tags": ["materials", "hardware"], "keywords": ["알루미늄", "소재", "합금"]},
    "appliance": {"tags": ["hardware", "device"], "keywords": ["전자제품", "노트북", "콘솔", "가전"]},
    "battery_charge_range": {"tags": ["battery", "charging", "tips"], "keywords": ["20~80", "충전 범위", "과충전"]},
    "battery_health_check": {"tags": ["battery", "health", "tips"], "keywords": ["배터리 건강", "배터리 상태", "교체 시기", "최대 용량"]},
    "battery_overheat": {"tags": ["battery", "heat", "warning"], "keywords": ["고온", "과열", "발열", "충전 중 게임"]},
    "biometric": {"tags": ["security", "privacy", "authentication"], "keywords": ["생체", "얼굴", "지문", "인증"]},
    "chart_down": {"tags": ["price", "data", "decrease"], "keywords": ["감소", "하락", "줄어", "낮아"]},
    "chart_up": {"tags": ["price", "data", "increase"], "keywords": ["증가", "상승", "급등", "오르"]},
    "chatbot": {"tags": ["ai", "assistant", "software"], "keywords": ["챗봇", "AI 비서", "대화형", "시리"]},
    "clock": {"tags": ["time", "tips"], "keywords": ["시간", "기간", "주기", "수명"]},
    "cloud_backup": {"tags": ["security", "privacy", "cloud"], "keywords": ["클라우드", "백업", "복원"]},
    "final_update": {"tags": ["software", "update"], "keywords": ["업데이트", "베타", "버전", "공개"]},
    "foldable": {"tags": ["hardware", "foldable"], "keywords": ["폴더블", "폴드", "플립"]},
    "forecast": {"tags": ["news", "forecast"], "keywords": ["전망", "예상", "가능성", "예정"]},
    "gemini": {"tags": ["ai", "assistant", "google"], "keywords": ["제미나이", "Gemini", "구글 AI"]},
    "gift_prohibit": {"tags": ["price", "security", "warning"], "keywords": ["결제 제거", "결제 차단", "카드 제거"]},
    "gift_voucher": {"tags": ["price", "subsidy", "purchase"], "keywords": ["지원금", "할인", "혜택", "구매"]},
    "handshake": {"tags": ["policy", "access", "partnership"], "keywords": ["협력", "상호운용", "개방", "동등"]},
    "heat_release": {"tags": ["battery", "heat", "hardware"], "keywords": ["발열", "열 특성", "열 처리", "방열"]},
    "liquid_titanium": {"tags": ["materials", "hardware"], "keywords": ["액체 금속", "티타늄", "합금"]},
    "lock": {"tags": ["security", "privacy", "lock"], "keywords": ["잠금", "보안", "도난", "접근 제한"]},
    "logout": {"tags": ["security", "privacy", "account"], "keywords": ["로그아웃", "계정 제거"]},
    "market_cap": {"tags": ["price", "data", "market"], "keywords": ["시가총액", "주가", "매출", "실적"]},
    "meeting_room": {"tags": ["policy", "news", "strategy"], "keywords": ["회의", "전략", "검토", "집행위"]},
    "memory_chip": {"tags": ["ai", "hardware", "chip"], "keywords": ["메모리", "램", "RAM", "칩", "반도체"]},
    "microphone": {"tags": ["news", "quote"], "keywords": ["발언", "인터뷰", "팁스터", "기자"]},
    "newspaper": {"tags": ["news", "source"], "keywords": ["보도", "매체", "외신", "기사"]},
    "nfc_pay": {"tags": ["payment", "nfc", "access"], "keywords": ["NFC", "비접촉", "결제", "단말기"]},
    "nfc_open_access": {"tags": ["payment", "nfc", "access"], "keywords": ["NFC 개방", "상호운용", "경쟁 서비스"]},
    "ondevice_ai_chip": {"tags": ["ai", "hardware", "privacy"], "keywords": ["온디바이스", "기기 내", "자체 칩", "클라우드를 거치지"]},
    "optimized_charging": {"tags": ["battery", "charging", "tips"], "keywords": ["최적화 충전", "배터리 보호", "적응형 보호"]},
    "password": {"tags": ["security", "privacy", "authentication"], "keywords": ["비밀번호", "암호", "계정"]},
    "price_hike": {"tags": ["price", "increase"], "keywords": ["가격 인상", "인상 폭", "비싸", "가격 조정"]},
    "device_price_rise": {"tags": ["price", "increase", "device"], "keywords": ["가격 인상", "비싸질", "인상 폭", "가격 조정"]},
    "prohibit": {"tags": ["security", "warning", "restriction"], "keywords": ["금지", "차단", "제한", "주의"]},
    "repair_privacy": {"tags": ["security", "privacy", "repair"], "keywords": ["수리", "사생활", "개인정보", "보안 폴더"]},
    "reset": {"tags": ["security", "privacy", "software"], "keywords": ["초기화", "복원", "리셋"]},
    "samsung_ai": {"tags": ["ai", "assistant", "software"], "keywords": ["AI", "인공지능", "AI 앱", "AI 기능"]},
    "shield": {"tags": ["security", "privacy", "protection"], "keywords": ["보호", "보안", "차단", "방어"]},
    "smartphone": {"tags": ["device", "purchase", "cta"], "keywords": ["휴대폰", "스마트폰", "구매", "상담"]},
    "stock_chart": {"tags": ["price", "data", "market"], "keywords": ["목표주가", "주식", "증시", "매출"]},
    "store": {"tags": ["store", "purchase", "cta"], "keywords": ["매장", "방문", "상담", "점검"]},
    "theft_auto_lock": {"tags": ["security", "privacy", "theft"], "keywords": ["도난", "강제 탈취", "자동 잠금"]},
    "ti_decrease": {"tags": ["materials", "hardware", "decrease"], "keywords": ["티타늄", "사용을 줄", "감소"]},
    "warning": {"tags": ["security", "warning"], "keywords": ["경고", "위험", "주의", "악성"]},
}


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_words(values: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def library_variants() -> list[str]:
    if not ILLUST_DIR.exists():
        return []
    return sorted(path.stem for path in ILLUST_DIR.glob("*.png"))


def load_db(sync: bool = True) -> dict:
    db = read_json(
        DB_PATH,
        {
            "version": 1,
            "policy": "Tag reusable illustrations and prefer less recently used semantic matches.",
            "illustrations": {},
        },
    )
    illustrations = db.setdefault("illustrations", {})
    changed = False
    available_variants = set(library_variants())
    for variant in sorted(available_variants | set(SEED)):
        entry = illustrations.setdefault(variant, {})
        seed = SEED.get(variant, {})
        available = variant in available_variants
        existing_tags = [tag for tag in entry.get("tags", []) if tag != "library"]
        tags = clean_words([*existing_tags, *seed.get("tags", []), *(["library"] if available else [])])
        keywords = clean_words([*entry.get("keywords", []), *seed.get("keywords", [])])
        if entry.get("tags") != tags or entry.get("keywords") != keywords:
            entry["tags"] = tags
            entry["keywords"] = keywords
            changed = True
        if "note" not in entry:
            entry["note"] = "Reusable editorial illustration."
            changed = True
        if entry.get("available") != available:
            entry["available"] = available
            changed = True
    db["updated_at"] = now_text()
    if sync and (changed or not DB_PATH.exists()):
        write_json(DB_PATH, db)
    return db


def load_history() -> dict:
    return read_json(HISTORY_PATH, {"version": 1, "videos": {}})


def history_stats(history: dict | None = None) -> dict[str, dict]:
    history = history or load_history()
    stats: dict[str, dict] = {}
    for slug, video in (history.get("videos", {}) or {}).items():
        used_at = str(video.get("used_at", ""))
        for variant in video.get("illustrations", []) or []:
            item = stats.setdefault(str(variant), {"count": 0, "last_used_at": "", "last_slug": ""})
            item["count"] += 1
            if used_at >= item["last_used_at"]:
                item["last_used_at"] = used_at
                item["last_slug"] = slug
    return stats


def semantic_score(text: str, entry: dict) -> int:
    value = str(text or "").lower()
    score = 0
    for keyword in entry.get("keywords", []) or []:
        if str(keyword).lower() in value:
            score += 12
    for tag in entry.get("tags", []) or []:
        if str(tag).lower() in value:
            score += 3
    return score


def rank_variants(
    text: str,
    section_name: str = "",
    fallback: Iterable[str] = (),
    exclude: Iterable[str] = (),
    available_only: bool = True,
) -> list[str]:
    db = load_db()
    history = load_history()
    stats = history_stats(history)
    recent_slugs = sorted(
        (history.get("videos", {}) or {}).items(),
        key=lambda item: str(item[1].get("used_at", "")),
        reverse=True,
    )[:6]
    recent_penalties: dict[str, int] = {}
    for index, (_, video) in enumerate(recent_slugs):
        penalty = max(3, 18 - index * 3)
        for variant in video.get("illustrations", []) or []:
            recent_penalties[str(variant)] = max(recent_penalties.get(str(variant), 0), penalty)
    available = set(library_variants())
    fallback_order = {variant: idx for idx, variant in enumerate(clean_words(fallback))}
    blocked = set(exclude)
    rows = []
    for variant, entry in (db.get("illustrations", {}) or {}).items():
        if variant in blocked:
            continue
        if available_only and variant not in available:
            continue
        sem = semantic_score(text, entry)
        if variant in fallback_order:
            sem += max(1, 9 - fallback_order[variant])
        if section_name == "cta" and "cta" in entry.get("tags", []):
            sem += 10
        if sem <= 0:
            continue
        stat = stats.get(variant, {})
        use_count = int(stat.get("count", 0))
        recent_penalty = recent_penalties.get(variant, 0)
        rows.append(
            (
                -(sem * 10 - use_count * 5 - recent_penalty),
                use_count,
                str(stat.get("last_used_at", "")),
                variant,
            )
        )
    rows.sort()
    return [row[-1] for row in rows]


def record_usage_snapshot(data: dict, slug: str, source: str) -> None:
    illustrations = []
    for section in [data.get("hook", {}), *(data.get("facts", []) or []), data.get("cta", {})]:
        for visual in section.get("chunk_visuals", []) or []:
            if isinstance(visual, dict) and visual.get("type") == "illust" and visual.get("value"):
                illustrations.append(str(visual["value"]))
    history = load_history()
    history.setdefault("videos", {})[slug] = {
        "used_at": now_text(),
        "source": source,
        "illustrations": clean_words(illustrations),
    }
    history["updated_at"] = now_text()
    write_json(HISTORY_PATH, history)
    write_report()


def mark_requests(slug: str, requests: list[dict]) -> None:
    history = load_history()
    history.setdefault("requests", {})[slug] = {
        "updated_at": now_text(),
        "variants": [str(item.get("variant", "")) for item in requests if item.get("variant")],
    }
    history["updated_at"] = now_text()
    write_json(HISTORY_PATH, history)
    write_report()


def variant_tags(variant: str) -> list[str]:
    db = load_db()
    return list((db.get("illustrations", {}).get(variant, {}) or {}).get("tags", []) or [])


def write_report() -> None:
    db = load_db()
    history = load_history()
    stats = history_stats(history)
    lines = [
        "# Codex Illustration Tag DB",
        "",
        "자동 추천은 본문 의미와 태그를 먼저 보고, 최근 사용 횟수가 적은 일러스트를 우선합니다.",
        "수동으로 다듬은 `chunk_visuals`는 변경하지 않습니다.",
        "",
        "| illustration | tags | use count | last slug |",
        "|---|---|---:|---|",
    ]
    for variant in sorted(db.get("illustrations", {})):
        entry = db["illustrations"][variant]
        stat = stats.get(variant, {})
        lines.append(
            f"| `{variant}` | {', '.join(entry.get('tags', []))} | "
            f"{stat.get('count', 0)} | {stat.get('last_slug', '')} |"
        )
    lines.extend(["", "## Recent videos", ""])
    videos = sorted(
        (history.get("videos", {}) or {}).items(),
        key=lambda item: str(item[1].get("used_at", "")),
        reverse=True,
    )[:12]
    if not videos:
        lines.append("- 아직 기록된 영상이 없습니다.")
    for slug, item in videos:
        used = ", ".join(item.get("illustrations", []) or []) or "-"
        lines.append(f"- `{slug}`: {used}")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_db() -> None:
    load_db(sync=True)
    if not HISTORY_PATH.exists():
        write_json(HISTORY_PATH, {"version": 1, "videos": {}, "requests": {}, "updated_at": now_text()})
    write_report()


if __name__ == "__main__":
    ensure_db()
    print(f"[illustration_db] db: {DB_PATH}")
    print(f"[illustration_db] history: {HISTORY_PATH}")
    print(f"[illustration_db] report: {REPORT_PATH}")
'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_illustration_db_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[skip] {label} already installed")
        return text
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {label}")
    print(f"[patch] {label}")
    return text.replace(old, new, 1)


def patch_enhancer() -> None:
    path = SCRIPTS / "codex_enhance_script.py"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "from pathlib import Path\n",
        "from pathlib import Path\n\nfrom codex_illustration_db import rank_variants, record_usage_snapshot\n",
        "enhancer DB import",
    )
    text = replace_once(
        text,
        "    return list(dict.fromkeys(found))\n",
        "    fallback = list(dict.fromkeys(found))\n"
        "    ranked = rank_variants(text, section_name=section_name, fallback=fallback)\n"
        "    return ranked or fallback\n",
        "enhancer semantic recent-use ranking",
    )
    text = replace_once(
        text,
        '    data["_codex_common_quality_note"] = (\n'
        '        "Global 001-999 rule: captions.md narration is TTS-only; "\n'
        '        "screen chunks and curated visuals are preserved unless invalid."\n'
        "    )\n",
        '    data["_codex_common_quality_note"] = (\n'
        '        "Global 001-999 rule: captions.md narration is TTS-only; "\n'
        '        "screen chunks and curated visuals are preserved unless invalid."\n'
        "    )\n"
        '    record_usage_snapshot(data, slug, source="codex_enhance")\n',
        "enhancer usage snapshot",
    )
    if text != original:
        backup(path)
        write(path, text)


def patch_apply_uploaded() -> None:
    path = SCRIPTS / "codex_apply_uploaded_illustrations.py"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "from pathlib import Path\n",
        "from pathlib import Path\n\nfrom codex_illustration_db import record_usage_snapshot\n",
        "uploaded illustration DB import",
    )
    text = replace_once(
        text,
        '        print(f"[illustration_apply] applied: {len(applied)}")\n',
        '        record_usage_snapshot(data, slug, source="uploaded_illustrations")\n'
        '        print(f"[illustration_apply] applied: {len(applied)}")\n',
        "uploaded illustration usage snapshot",
    )
    if text != original:
        backup(path)
        write(path, text)


def patch_scout() -> None:
    path = SCRIPTS / "codex_illustration_scout.py"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "from pathlib import Path\n",
        "from pathlib import Path\n\nfrom codex_illustration_db import ensure_db, mark_requests, variant_tags, write_report\n",
        "scout DB import",
    )
    text = replace_once(
        text,
        "    slug = sys.argv[1]\n",
        "    slug = sys.argv[1]\n    ensure_db()\n",
        "scout DB sync",
    )
    text = replace_once(
        text,
        '                    "reason": rule["reason"],\n',
        '                    "reason": rule["reason"],\n'
        '                    "tags": variant_tags(variant),\n',
        "scout request tags",
    )
    text = replace_once(
        text,
        '    md_path.write_text("\\n".join(lines), encoding="utf-8")\n\n'
        '    print(f"[illustration_scout] report: {md_path}")\n',
        '    md_path.write_text("\\n".join(lines), encoding="utf-8")\n'
        "    mark_requests(slug, requests)\n"
        "    write_report()\n\n"
        '    print(f"[illustration_scout] report: {md_path}")\n',
        "scout request history",
    )
    if text != original:
        backup(path)
        write(path, text)


def install_desk_buttons() -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    write(
        DESK / "11_OPEN_ILLUSTRATION_TAG_DB.bat",
        '@echo off\nchcp 65001 > nul\nstart "" notepad "%~dp0..\\shorts\\codex\\ILLUSTRATION_TAG_DB.md"\n',
    )
    write(
        DESK / "12_REFRESH_ILLUSTRATION_TAG_DB.bat",
        '@echo off\nchcp 65001 > nul\ncd /d "%~dp0..\\shorts"\npython scripts\\codex_illustration_db.py\npause\n',
    )
    readme = DESK / "README.txt"
    text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    marker = "Illustration tag DB controls:"
    if marker not in text:
        text += (
            "\n\nIllustration tag DB controls:\n"
            "11. Run 11_OPEN_ILLUSTRATION_TAG_DB.bat to inspect tags and recent use.\n"
            "12. Run 12_REFRESH_ILLUSTRATION_TAG_DB.bat after adding or renaming library PNG files.\n"
            "Automatic ranking prefers semantic matches that were used less recently.\n"
            "Manual chunk_visuals mappings remain untouched.\n"
        )
        write(readme, text.lstrip())


def append_guide() -> None:
    path = SHORTS / "codex" / "CODEX_BASELINE.md"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "# PhoneSpot Codex baseline\n"
    marker = "## Illustration tag DB and recent-use memory"
    if marker in text:
        print("[skip] baseline guide already documents illustration DB")
        return
    text += (
        "\n\n## Illustration tag DB and recent-use memory\n\n"
        "- `config/illustration_tag_db.json` stores reusable illustration tags and keywords.\n"
        "- `codex/illustration_usage_history.json` stores one idempotent snapshot per slug.\n"
        "- Automatic mapping ranks semantic matches and reduces recently repeated illustrations.\n"
        "- Manual `chunk_visuals` mappings remain authoritative.\n"
        "- Use desk buttons 11 and 12 to inspect or refresh the DB.\n"
    )
    write(path, text)


def run_checks() -> None:
    for name in (
        "codex_illustration_db.py",
        "codex_enhance_script.py",
        "codex_apply_uploaded_illustrations.py",
        "codex_illustration_scout.py",
    ):
        py_compile.compile(str(SCRIPTS / name), doraise=True)
    subprocess.run([sys.executable, str(SCRIPTS / "codex_illustration_db.py")], cwd=SHORTS, check=True)
    print("[OK] illustration DB Python checks passed")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Illustration Tag DB + Recent Use")
    print("============================================================")
    if not SHORTS.exists():
        raise RuntimeError(f"shorts folder missing: {SHORTS}")
    write(SCRIPTS / "codex_illustration_db.py", DB_MODULE)
    patch_enhancer()
    patch_apply_uploaded()
    patch_scout()
    install_desk_buttons()
    append_guide()
    run_checks()
    print()
    print("[DONE] Illustration tag DB and recent-use ranking installed.")
    print("[NEXT] Open CODEX_VIDEO_DESK and use button 11 to inspect the DB report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
