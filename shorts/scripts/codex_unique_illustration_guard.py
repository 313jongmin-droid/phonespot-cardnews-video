# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

from codex_illustration_db import library_variants, rank_variants, record_usage_snapshot

import os

# 매처(codex_semantic_visual_match)와 동일한 제외 규칙을 가드에도 적용한다.
# 가드는 '중복 일러스트를 유니크하게' 바꾸는데, 그 대체 풀에서 cpt(미검증 개념아트)·차단목록을
# 빼야 매처가 걸러낸 그림(예: cpt_496029c6 보이스피싱)이 되살아나지 않는다.
_BLOCKLIST = set(v.strip() for v in os.getenv("PHONESPOT_ILLUST_BLOCKLIST", "").split(",") if v.strip())
_EXCLUDE_CPT = os.getenv("PHONESPOT_TRUST_CONCEPT_ART", "0") == "0"
_NEUTRALS = set(v.strip() for v in os.getenv(
    "PHONESPOT_NEUTRAL_FILLERS",
    "smartphone,phone_setup_ready,phone_settings_toggle,device_os_requirement,device_data_transfer",
).split(",") if v.strip())


def _is_bad_variant(variant: str) -> bool:
    return variant in _BLOCKLIST or (_EXCLUDE_CPT and str(variant).startswith("cpt_"))


ROOT = Path(__file__).resolve().parent.parent.parent
CARD_OUTPUT = ROOT / "cardnews" / "output"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def sections(data: dict) -> list[tuple[str, dict]]:
    return [("hook", data.get("hook", {})), *[(f"fact_{i}", item) for i, item in enumerate(data.get("facts", []) or [], 1)], ("cta", data.get("cta", {}))]


def chunks(section: dict) -> list[str]:
    return [clean(x) for x in (section.get("display_chunks") or section.get("caption_chunks") or []) if clean(x)]


def headline(section: dict) -> str:
    parts = []
    for line in section.get("headline_lines", []) or []:
        if isinstance(line, dict):
            parts.append(clean(line.get("text")))
        else:
            parts.append(clean(line))
    return " ".join(parts)


def context(section: dict, index: int) -> str:
    vals = chunks(section)
    nearby = []
    for pos in (index - 1, index, index + 1):
        if 0 <= pos < len(vals):
            nearby.append(vals[pos])
    nearby.append(headline(section))
    nearby.append(clean(section.get("tts")))
    return " ".join(nearby)


def visual_key(visual: dict) -> str:
    return f"{visual.get('type')}:{visual.get('value')}"


def replace_duplicate_illustrations(data: dict, slug: str) -> bool:
    available = set(library_variants())
    used: set[str] = set()
    replacements = []
    weak = []

    for section_name, section in sections(data):
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not visuals:
            continue

        for idx, visual in enumerate(visuals):
            vtype = visual.get("type")
            if vtype == "logo":
                # Fixed CTA logo may appear as a brand surface. Do not treat it as an illustration.
                continue
            if vtype not in {"illust", "mascot"}:
                continue

            key = visual_key(visual)
            if key not in used:
                used.add(key)
                continue

            # 중립 필러(smartphone 등)는 반복 허용 — 억지로 유니크하게 바꾸면 무관/불량 그림을
            # 끌어온다(매처가 의도적으로 중립으로 둔 것). 의미 있는 일러스트 중복만 교체.
            if visual.get("type") == "illust" and str(visual.get("value")) in _NEUTRALS:
                continue

            ctx = context(section, idx)
            replacement = None
            for variant in rank_variants(ctx, section_name=section_name, exclude={item.split(":", 1)[1] for item in used if item.startswith("illust:")}):
                if _is_bad_variant(variant):
                    continue
                if variant in available:
                    replacement = {"type": "illust", "value": variant}
                    break

            if replacement is None:
                weak.append(
                    {
                        "section": section_name,
                        "chunk": idx + 1,
                        "duplicate": visual,
                        "context": ctx[:160],
                    }
                )
                continue

            visuals[idx] = replacement
            used.add(visual_key(replacement))
            replacements.append(
                {
                    "section": section_name,
                    "chunk": idx + 1,
                    "from": visual,
                    "to": replacement,
                    "context": ctx[:160],
                }
            )

        section["chunk_visuals"] = visuals

    if replacements or weak:
        data["_codex_unique_illustration_guard"] = {
            "version": 1,
            "policy": "Illustrations and mascots should not repeat inside one video. CTA logo is exempt.",
            "replacements": replacements,
            "weak": weak,
        }
        report = CARD_OUTPUT / slug / "codex_unique_illustration_guard_report.md"
        lines = [
            f"# Unique Illustration Guard Report: {slug}",
            "",
            "같은 영상 안에서 같은 일러스트/마스코트가 반복되는 것을 줄이기 위한 검사입니다.",
            "",
            "## 교체",
        ]
        if not replacements:
            lines.append("- 없음")
        for item in replacements:
            lines.append(
                f"- {item['section']} C{item['chunk']}: "
                f"`{visual_key(item['from'])}` -> `{visual_key(item['to'])}`"
            )
        lines.extend(["", "## 대체 후보 부족"])
        if not weak:
            lines.append("- 없음")
        for item in weak:
            lines.append(
                f"- {item['section']} C{item['chunk']}: `{visual_key(item['duplicate'])}` / {item['context']}"
            )
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[unique_illust] replacements={len(replacements)}, weak={len(weak)}")
        print(f"[unique_illust] report: {report}")
        if replacements:
            record_usage_snapshot(data, slug, source="unique_illustration_guard")
            return True
    else:
        print("[unique_illust] no duplicate illustration")
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_unique_illustration_guard.py <slug>")
        return 2
    slug = sys.argv[1].strip()
    path = CARD_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[unique_illust] missing: {path}")
        return 1
    data = read_json(path)
    changed = replace_duplicate_illustrations(data, slug)
    if changed:
        write_json(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
