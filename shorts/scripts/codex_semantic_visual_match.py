# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from codex_illustration_db import load_db, library_variants, record_usage_snapshot, semantic_score


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
CARD_IMAGES = CARDNEWS / "images"
CARD_OUTPUT = CARDNEWS / "output"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"

MIN_IMAGE_SCORE = 18
MIN_ILLUST_SCORE = 14


ALIASES = {
    "일정": ["일정", "날짜", "달력", "캘린더", "키노트", "행사", "공개", "출시", "사전예약", "예약", "7월", "8월", "6월"],
    "폴드": ["폴드", "폴더블", "fold", "foldable", "와이드", "펼친", "내부 화면"],
    "플립": ["플립", "flip", "외부 화면", "외부 디스플레이", "커버 화면", "닫은 상태"],
    "워치": ["워치", "watch", "건강", "측정", "센서", "심박", "헬스"],
    "카메라": ["카메라", "렌즈", "촬영", "사진", "줌", "망원", "초광각", "HDR", "셔터", "필터", "속도"],
    "보안": ["보안", "잠금", "개인정보", "도난", "차단", "보호", "인증", "비밀번호"],
    "AI": ["AI", "인공지능", "제미나이", "Gemini", "시리", "챗봇", "온디바이스", "모델"],
    "가격": ["가격", "요금", "지원금", "할인", "혜택", "인상", "하락", "유로", "만원", "달러"],
    "배터리": ["배터리", "충전", "발열", "방열", "전력", "용량"],
    "이전": ["백업", "복원", "이전", "전송", "클라우드", "데이터"],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def words(text: str) -> set[str]:
    text = clean(text).lower()
    raw = re.findall(r"[가-힣A-Za-z0-9]+", text)
    out = {w for w in raw if len(w) >= 2}
    for key, values in ALIASES.items():
        if any(v.lower() in text for v in values):
            out.add(key.lower())
    return out


def phrase_bonus(a: str, b: str) -> int:
    a_low = a.lower()
    b_low = b.lower()
    score = 0
    for key, values in ALIASES.items():
        hit_a = any(v.lower() in a_low for v in values)
        hit_b = any(v.lower() in b_low for v in values)
        if hit_a and hit_b:
            score += 10
    for token in ("폴드8", "폴드 8", "플립8", "플립 8", "워치9", "워치 9", "2배", "HDR", "NFC", "WWDC"):
        if token.lower() in a_low and token.lower() in b_low:
            score += 16
    return score


def parse_prompt_md(slug: str) -> dict[str, str]:
    prompt = CARD_IMAGES / slug / "prompt.md"
    if not prompt.exists():
        return {}
    text = prompt.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r"(?:^|\n)\s*[—-]+\s*(\d+\.png)\s*[—-]+\s*(.*?)\n(.*?)(?=\n\s*[—-]+\s*\d+\.png\s*[—-]+|\Z)",
        re.S,
    )
    out: dict[str, str] = {}
    for name, title, body in pattern.findall(text):
        out[name.strip()] = clean(f"{title} {body}")
    return out


def list_images(slug: str) -> list[str]:
    root = CARD_IMAGES / slug
    if not root.exists():
        return []
    return sorted(p.name for p in root.glob("*.png") if re.fullmatch(r"\d+\.png", p.name))


def image_score(context: str, description: str) -> int:
    if not description:
        return 0
    overlap = words(context) & words(description)
    return len(overlap) * 8 + phrase_bonus(context, description)


def image_candidates(slug: str, context: str, used_images: set[str], prompt_map: dict[str, str]) -> list[tuple[int, str, str]]:
    rows = []
    for image in list_images(slug):
        if image in used_images:
            continue
        desc = prompt_map.get(image, "")
        score = image_score(context, desc)
        rows.append((score, image, desc))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def illustration_candidates(context: str, used_visuals: set[str]) -> list[tuple[int, str]]:
    db = load_db()
    available = set(library_variants())
    rows = []
    for variant, entry in (db.get("illustrations", {}) or {}).items():
        if variant not in available:
            continue
        key = f"illust:{variant}"
        if key in used_visuals:
            continue
        score = semantic_score(context, entry)
        if score > 0:
            rows.append((score, variant))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def section_items(data: dict) -> list[tuple[str, dict]]:
    return [("hook", data.get("hook", {})), *[(f"fact_{i}", fact) for i, fact in enumerate(data.get("facts", []) or [], 1)], ("cta", data.get("cta", {}))]


def section_chunks(section: dict) -> list[str]:
    return [clean(x) for x in (section.get("display_chunks") or section.get("caption_chunks") or []) if clean(x)]


def headline_text(section: dict) -> str:
    parts = []
    for line in section.get("headline_lines", []) or []:
        if isinstance(line, dict):
            parts.append(clean(line.get("text")))
        else:
            parts.append(clean(line))
    parts.append(clean(section.get("caption_body")))
    return " ".join(parts)


def context_for(section: dict, idx: int) -> str:
    chunks = section_chunks(section)
    nearby = []
    for pos in (idx - 1, idx, idx + 1):
        if 0 <= pos < len(chunks):
            nearby.append(chunks[pos])
    nearby.append(headline_text(section))
    nearby.append(clean(section.get("topic")))
    return " ".join(nearby)


def visual_key(visual: dict) -> str:
    return f"{visual.get('type')}:{visual.get('value')}"


def semantic_match(data: dict, slug: str) -> bool:
    if data.get("_codex_manual_visuals"):
        print("[semantic_visual] manual visuals: skip")
        return False

    prompt_map = parse_prompt_md(slug)
    if not prompt_map:
        print("[semantic_visual] prompt.md image descriptions missing: skip")
        return False

    used_images: set[str] = set()
    used_visuals: set[str] = set()
    changes = []
    weak = []

    for section_name, section in section_items(data):
        chunks = section_chunks(section)
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not chunks or not visuals:
            continue
        if len(visuals) < len(chunks):
            visuals.extend([dict(visuals[-1])] * (len(chunks) - len(visuals)))
        if len(visuals) > len(chunks):
            visuals = visuals[: len(chunks)]

        for idx, current in enumerate(visuals):
            if current.get("type") == "logo":
                used_visuals.add(visual_key(current))
                continue
            if section_name == "cta":
                # CTA is a fixed conversion surface; keep existing CTA illustration/logo contract.
                used_visuals.add(visual_key(current))
                continue

            context = context_for(section, idx)
            imgs = image_candidates(slug, context, used_images, prompt_map)
            ills = illustration_candidates(context, used_visuals)
            best_img = imgs[0] if imgs else (0, "", "")
            best_ill = ills[0] if ills else (0, "")

            chosen = None
            reason = ""
            if best_img[0] >= MIN_IMAGE_SCORE and best_img[0] >= best_ill[0]:
                chosen = {"type": "image", "value": best_img[1]}
                reason = f"image score {best_img[0]}: {best_img[2][:80]}"
            elif best_ill[0] >= MIN_ILLUST_SCORE:
                chosen = {"type": "illust", "value": best_ill[1]}
                reason = f"illust score {best_ill[0]}"
            elif current.get("type") == "image" and current.get("value") not in used_images:
                chosen = current
                reason = "kept existing image"
            elif current.get("type") in {"illust", "mascot", "stat", "compare"} and visual_key(current) not in used_visuals:
                chosen = current
                reason = "kept existing non-image"
            elif imgs:
                chosen = {"type": "image", "value": best_img[1]}
                reason = f"fallback image score {best_img[0]}"
            elif ills:
                chosen = {"type": "illust", "value": best_ill[1]}
                reason = f"fallback illust score {best_ill[0]}"
            else:
                chosen = current
                reason = "no candidate"

            if chosen.get("type") == "image":
                used_images.add(str(chosen.get("value") or ""))
            if chosen.get("type") in {"illust", "image", "mascot"}:
                used_visuals.add(visual_key(chosen))

            if chosen != current:
                changes.append({
                    "section": section_name,
                    "chunk": idx + 1,
                    "from": current,
                    "to": chosen,
                    "context": context[:120],
                    "reason": reason,
                })
            if (best_img[0] < MIN_IMAGE_SCORE and best_ill[0] < MIN_ILLUST_SCORE and section_name != "cta"):
                weak.append({
                    "section": section_name,
                    "chunk": idx + 1,
                    "current": chosen,
                    "context": context[:160],
                    "best_image_score": best_img[0],
                    "best_illust_score": best_ill[0],
                })

            visuals[idx] = chosen

        section["chunk_visuals"] = visuals

    if changes or weak:
        data["_codex_semantic_visual_match"] = {
            "version": 1,
            "policy": "Match chunks to GPT source images using prompt.md descriptions, then fallback to tagged reusable illustrations.",
            "changes": changes,
            "weak": weak,
        }
        report_path = CARD_OUTPUT / slug / "codex_semantic_visual_match_report.md"
        lines = [
            f"# Semantic Visual Match Report: {slug}",
            "",
            "청크 문맥과 `images/<slug>/prompt.md`의 1~5.png 설명을 비교해 이미지/일러스트를 재배치했습니다.",
            "",
            "## 변경",
        ]
        if not changes:
            lines.append("- 변경 없음")
        for item in changes:
            lines.append(
                f"- {item['section']} C{item['chunk']}: "
                f"`{visual_key(item['from'])}` -> `{visual_key(item['to'])}` ({item['reason']})"
            )
        lines.extend(["", "## 약한 매칭"])
        if not weak:
            lines.append("- 없음")
        for item in weak:
            lines.append(
                f"- {item['section']} C{item['chunk']}: `{visual_key(item['current'])}` "
                f"(image={item['best_image_score']}, illust={item['best_illust_score']}) / {item['context']}"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[semantic_visual] changes={len(changes)}, weak={len(weak)}")
        print(f"[semantic_visual] report: {report_path}")
        if changes:
            record_usage_snapshot(data, slug, source="semantic_visual_match")
        return bool(changes)
    print("[semantic_visual] no changes")
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_semantic_visual_match.py <slug>")
        return 2
    slug = sys.argv[1].strip()
    path = CARD_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[semantic_visual] missing: {path}")
        return 1
    data = read_json(path)
    changed = semantic_match(data, slug)
    if changed:
        write_json(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
