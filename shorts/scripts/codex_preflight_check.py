# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from codex_chunk_overrides import apply_overrides, validate_effective_script


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS = ROOT / "cardnews"
CARD_OUTPUT = CARDNEWS / "output"
CARD_IMAGES = CARDNEWS / "images"
CARD_ARTICLES = CARDNEWS / "articles"
SHORTS = ROOT / "shorts"
ASSETS = SHORTS / "public" / "assets"
DESK = ROOT / "CODEX_VIDEO_DESK"


def add(items: list[dict], level: str, message: str, detail: str = "") -> None:
    items.append({"level": level, "message": message, "detail": detail})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def section_iter(data: dict):
    if isinstance(data.get("hook"), dict):
        yield "hook", data["hook"]
    for idx, fact in enumerate(data.get("facts") or [], 1):
        if isinstance(fact, dict):
            yield str(fact.get("id") or f"fact_{idx}"), fact
    if isinstance(data.get("cta"), dict):
        yield "cta", data["cta"]


def all_visuals(data: dict):
    for section_name, section in section_iter(data):
        for idx, visual in enumerate(section.get("chunk_visuals") or [], 1):
            if isinstance(visual, dict):
                yield section_name, idx, visual


def visual_label(visual: dict) -> str:
    kind = str(visual.get("type") or visual.get("kind") or "")
    if kind == "image":
        return str(visual.get("value") or visual.get("path") or visual.get("src") or visual.get("image") or "")
    if kind in {"illust", "illustration"}:
        return str(visual.get("value") or visual.get("variant") or visual.get("name") or "")
    if kind == "logo":
        return str(visual.get("name") or visual.get("path") or "logo")
    return kind or "unknown"


def check_korean_guard(slug: str, items: list[dict]) -> None:
    guard = SHORTS / "scripts" / "validate_codex_korean.py"
    if not guard.exists():
        add(items, "WARN", "한글 검증 스크립트가 없습니다.", str(guard))
        return
    result = subprocess.run(
        [sys.executable, str(guard), slug],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode == 0:
        add(items, "OK", "한글 문장/CTA 기본 검증 통과")
    else:
        add(items, "ERROR", "한글 문장/CTA 검증 실패", (result.stdout + "\n" + result.stderr).strip())


def check(slug: str) -> dict:
    items: list[dict] = []
    out = CARD_OUTPUT / slug
    img = CARD_IMAGES / slug
    article = CARD_ARTICLES / f"{slug}.json"
    script = out / "shorts_script.json"
    captions = out / "captions.md"

    if article.exists():
        add(items, "OK", "기사 JSON 있음", str(article))
    else:
        add(items, "ERROR", "기사 JSON 없음", str(article))

    image_files = sorted([p for p in img.glob("*.png") if p.name.lower() not in {"cover.png"}]) if img.exists() else []
    if len(image_files) >= 5:
        add(items, "OK", f"카드뉴스 원본 이미지 {len(image_files)}개 있음")
    else:
        add(items, "WARN", f"카드뉴스 원본 이미지 부족: {len(image_files)}/5", str(img))

    card_files = list(out.glob("card_*.jpg")) + list(out.glob("card_*.png"))
    if card_files:
        add(items, "OK", f"카드뉴스 결과 카드 {len(card_files)}개 있음")
    else:
        add(items, "WARN", "카드뉴스 결과 카드가 아직 없습니다.", str(out))

    if captions.exists():
        add(items, "OK", "captions.md 있음")
    else:
        add(items, "WARN", "captions.md 없음")

    if not script.exists():
        add(items, "ERROR", "shorts_script.json 없음. 영상 준비를 먼저 실행해야 합니다.", str(script))
        return finish(slug, items)

    try:
        data = load_json(script)
        add(items, "OK", "shorts_script.json 문법 정상")
    except Exception as exc:
        add(items, "ERROR", "shorts_script.json 문법 오류", str(exc))
        return finish(slug, items)

    try:
        override_report = apply_overrides(data, slug, strict=True)
        effective_errors = validate_effective_script(data)
        if effective_errors:
            add(items, "ERROR", "최종 렌더 청크 검증 실패", "\n".join(effective_errors))
            return finish(slug, items)
        if override_report["applied"]:
            add(
                items,
                "OK",
                "청크 편집본을 포함한 최종 렌더 스크립트 검증 통과",
                ", ".join(override_report["sections"]),
            )
        else:
            add(items, "OK", "최종 렌더 스크립트 청크 검증 통과")
    except Exception as exc:
        add(items, "ERROR", "청크 편집본을 최종 렌더 스크립트에 적용할 수 없습니다.", str(exc))
        return finish(slug, items)

    facts = data.get("facts") or []
    if isinstance(data.get("hook"), dict) and isinstance(data.get("cta"), dict) and len(facts) >= 3:
        add(items, "OK", f"영상 섹션 구조 정상: facts {len(facts)}개")
    else:
        add(items, "ERROR", "영상 섹션 구조가 부족합니다. hook/facts/cta 확인 필요")

    cta_text = " ".join(
        str(x)
        for x in [
            data.get("cta", {}).get("tts"),
            " ".join(data.get("cta", {}).get("caption_chunks") or []),
            " ".join(data.get("cta", {}).get("display_chunks") or []),
        ]
    )
    if "휴대폰 구매할 땐" in cta_text or "지원금부터 무료로" in cta_text:
        add(items, "OK", "CTA 고정 문구 확인")
    else:
        add(items, "WARN", "CTA 고정 문구가 보이지 않습니다.", cta_text[:160])

    source_images: dict[str, tuple[str, int]] = {}
    duplicates: list[str] = []
    missing_visuals: list[str] = []
    for section, idx, visual in all_visuals(data):
        kind = str(visual.get("type") or visual.get("kind") or "")
        label = visual_label(visual)
        where = f"{section} #{idx}"
        if kind == "image":
            if label:
                if label in source_images:
                    previous_section, previous_index = source_images[label]
                    if previous_section != section or previous_index != idx - 1:
                        duplicates.append(
                            f"{where}: {label} (first: {previous_section} #{previous_index})"
                        )
                source_images[label] = (section, idx)
                if not (img / label).exists() and not (out / label).exists() and not (ASSETS / label).exists():
                    missing_visuals.append(f"{where}: image {label}")
        elif kind in {"illust", "illustration"}:
            candidate = ASSETS / "illustrations" / f"{label}.png"
            drop = DESK / "ILLUSTRATION_DROP" / f"{label}.png"
            if label and not candidate.exists() and not drop.exists():
                missing_visuals.append(f"{where}: illustration {label}")
        elif kind == "logo":
            # Logo may be rendered as text or file depending on component. Warn only for explicit paths.
            pass

    if duplicates:
        add(items, "ERROR", "GPT 원본 이미지가 한 영상 안에서 중복 사용됩니다.", "\n".join(duplicates[:12]))
    else:
        add(items, "OK", "GPT 원본 이미지 1회 사용 룰 통과")

    if missing_visuals:
        add(items, "ERROR", "필요한 이미지/일러스트 파일이 없습니다.", "\n".join(missing_visuals[:20]))
    else:
        add(items, "OK", "영상 visual 파일 존재 확인")

    long_chunks: list[str] = []
    short_chunks: list[str] = []
    for section, obj in section_iter(data):
        chunks = obj.get("display_chunks") or obj.get("caption_chunks") or []
        for idx, chunk in enumerate(chunks, 1):
            text = str(chunk or "").strip()
            if len(re.sub(r"\s+", "", text)) > 26:
                long_chunks.append(f"{section} #{idx}: {text[:64]}")
            if 0 < len(text) < 6:
                short_chunks.append(f"{section} #{idx}: {text}")
    if long_chunks:
        add(items, "WARN", "화면 청크가 긴 항목이 있습니다. 줄바꿈/분할 확인 권장", "\n".join(long_chunks[:10]))
    else:
        add(items, "OK", "긴 화면 청크 없음")
    if short_chunks:
        add(items, "WARN", "너무 짧은 화면 청크가 있습니다.", "\n".join(short_chunks[:10]))

    check_korean_guard(slug, items)
    return finish(slug, items)


def finish(slug: str, items: list[dict]) -> dict:
    errors = sum(1 for item in items if item["level"] == "ERROR")
    warnings = sum(1 for item in items if item["level"] == "WARN")
    status = "ERROR" if errors else ("WARN" if warnings else "OK")
    return {"slug": slug, "status": status, "errors": errors, "warnings": warnings, "items": items}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check(args.slug)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[preflight] {result['slug']} status={result['status']} errors={result['errors']} warnings={result['warnings']}")
        for item in result["items"]:
            print(f"[{item['level']}] {item['message']}")
            if item.get("detail"):
                print(item["detail"])
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
