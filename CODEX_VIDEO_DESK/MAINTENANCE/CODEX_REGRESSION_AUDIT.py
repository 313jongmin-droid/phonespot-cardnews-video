# -*- coding: utf-8 -*-
"""Audit current PhoneSpot Codex shorts scripts without rewriting them."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
OUTPUT = ROOT / "cardnews" / "output"
ILLUST = ROOT / "shorts" / "public" / "assets" / "illustrations"
FIXED_CTA = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]
MALFORMED = (
    "입니다입니다",
    "합니다합니다",
    "됩니다됩니다",
    "줄어듭니다입니다",
    "한다고 합니다합니다",
)


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", str(text or "")))


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for index, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{index}", fact
    yield "cta", data.get("cta", {})


def latest_slugs(limit: int, all_slugs: bool) -> list[str]:
    rows = []
    for path in OUTPUT.iterdir() if OUTPUT.exists() else []:
        if path.is_dir() and (path / "shorts_script.json").exists():
            rows.append((path.stat().st_mtime, path.name))
    rows.sort(reverse=True)
    result = [slug for _, slug in rows]
    return result if all_slugs else result[:limit]


def audit_slug(slug: str) -> tuple[int, int]:
    script_path = OUTPUT / slug / "shorts_script.json"
    data = json.loads(script_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    seen_images: dict[str, str] = {}

    for section_name, section in sections(data):
        captions = [str(item).strip() for item in section.get("caption_chunks", []) or []]
        displays = [str(item).strip() for item in section.get("display_chunks", []) or []]
        visuals = [item for item in section.get("chunk_visuals", []) or [] if isinstance(item, dict)]
        if captions and len(displays) != len(captions):
            errors.append(f"{section_name}: caption/display count mismatch {len(captions)} != {len(displays)}")
        if captions and len(visuals) != len(captions):
            errors.append(f"{section_name}: caption/visual count mismatch {len(captions)} != {len(visuals)}")
        for field, values in (("caption", captions), ("display", displays)):
            for index, text in enumerate(values, 1):
                for bad in MALFORMED:
                    if bad in text.replace(" ", ""):
                        errors.append(f"{section_name}.{field}[{index}]: malformed Korean `{bad}`")
                if compact_len(text) > 46:
                    warnings.append(f"{section_name}.{field}[{index}]: long text {compact_len(text)} chars")
        for index, visual in enumerate(visuals, 1):
            visual_type = str(visual.get("type") or "")
            value = str(visual.get("value") or "")
            where = f"{section_name}.visual[{index}]"
            if visual_type == "image":
                if not value:
                    errors.append(f"{where}: empty image value")
                elif value in seen_images:
                    errors.append(f"{where}: duplicated source image `{value}`; first used at {seen_images[value]}")
                else:
                    seen_images[value] = where
            if visual_type == "illust" and value and not (ILLUST / f"{value}.png").exists():
                errors.append(f"{where}: missing illustration `{value}.png`")

    cta = data.get("cta", {})
    if cta.get("caption_chunks") != FIXED_CTA:
        errors.append("cta: fixed caption contract changed")
    if cta.get("display_chunks") != FIXED_CTA:
        errors.append("cta: fixed display contract changed")
    cta_visuals = cta.get("chunk_visuals", []) or []
    if len(cta_visuals) != 2 or not isinstance(cta_visuals[-1], dict) or cta_visuals[-1].get("type") != "logo":
        errors.append("cta: final visual must be PhoneSpot logo")

    print(f"\n### {slug}")
    for item in errors:
        print(f"[ERROR] {item}")
    for item in warnings:
        print(f"[WARN ] {item}")
    if not errors and not warnings:
        print("[OK] contract audit passed")
    return len(errors), len(warnings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    slugs = args.slugs or latest_slugs(args.limit, args.all)
    print(f"[audit] slugs: {len(slugs)}")
    errors = warnings = 0
    for slug in slugs:
        try:
            e_count, w_count = audit_slug(slug)
            errors += e_count
            warnings += w_count
        except Exception as exc:
            errors += 1
            print(f"\n### {slug}\n[ERROR] {exc}")
    print(f"\nTOTAL: errors={errors}, warnings={warnings}")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

