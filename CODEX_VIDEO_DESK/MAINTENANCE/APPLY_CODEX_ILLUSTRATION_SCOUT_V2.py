# -*- coding: utf-8 -*-
"""Install Illustration Scout V2 without changing the accepted renderer."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
SCOUT = SHORTS / "scripts" / "codex_illustration_scout.py"
DB = SHORTS / "scripts" / "codex_illustration_db.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LABEL = f"bak_illustration_scout_v2_{STAMP}"


SCOUT_V2 = r'''# -*- coding: utf-8 -*-
"""Suggest reusable GPT Plus illustrations when the current visual map is weak.

CODEX_ILLUSTRATION_SCOUT_V2
- Grow a reusable editorial library instead of requesting article-specific art.
- Audit semantic quality gaps, not only missing predefined files.
- Limit each article to at most three new GPT Plus requests.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from codex_illustration_db import ensure_db, load_db, mark_requests, semantic_score, variant_tags, write_report


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"
MAX_REQUESTS = 3

STYLE = """\ud55c\uad6d \ud734\ub300\ud3f0\u00b7IT \ub274\uc2a4 \uc1fc\uce20\uc6a9 \uace0\ud488\uc9c8 \uc5d0\ub514\ud1a0\ub9ac\uc5bc \uc77c\ub7ec\uc2a4\ud2b8.
\ubcf8\ubb38\uc758 \ud575\uc2ec \uc758\ubbf8\ub97c \ud55c\ub208\uc5d0 \uc774\ud574\ud560 \uc218 \uc788\uac8c \ud45c\ud604\ud558\ub418, \ud55c \uae30\uc0ac\uc5d0\uc11c\ub9cc \uc4f8 \uc218 \uc788\ub294 \uc138\ubd80 \ubb18\uc0ac\ub294 \ud53c\ud558\uc138\uc694.
\ud2b9\uc815 \ube0c\ub79c\ub4dc \ub85c\uace0, \uc81c\ud488 \ubaa8\ub378\uba85, \ub0a0\uc9dc, \uac00\uaca9, \uc778\ubb3c \uc774\ub984, \ub9e4\uc7a5 \uc774\ub984, \uc6cc\ud130\ub9c8\ud06c\ub294 \ub123\uc9c0 \ub9c8\uc138\uc694.
\ub2e8\uc21c \uc544\uc774\ucf58 \ud558\ub098\uac00 \uc544\ub2c8\ub77c \uc911\uc2ec \uc624\ube0c\uc81d\ud2b8\uc640 1~2\uac1c\uc758 \ubcf4\uc870 \uc694\uc18c\ub97c \ud65c\uc6a9\ud574 \uc644\uc131\ub3c4 \uc788\uac8c \uad6c\uc131\ud558\uc138\uc694.
\uc624\ub80c\uc9c0(#F74B0B), \uac80\uc815, \ud770\uc0c9\uc744 \uc911\uc2ec\uc73c\ub85c \uc0ac\uc6a9\ud558\uace0 \ubc1d\uc740 \uc0b4\uad6c\uc0c9(#FFF1EA) \ubc30\uacbd\uc744 \uc801\uc6a9\ud558\uc138\uc694.
\uae54\ub054\ud55c \uc678\uacfd\uc120, \uc790\uc5f0\uc2a4\ub7ec\uc6b4 \uae4a\uc774\uac10, \ucda9\ubd84\ud55c \ub514\ud14c\uc77c\uc744 \uac16\ucd98 \ud604\ub300\uc801\uc778 \uc5d0\ub514\ud1a0\ub9ac\uc5bc \uc2a4\ud0c0\uc77c.
\ud654\uba74 \ube44\uc728 4:3, \ud574\uc0c1\ub3c4 1024x768 PNG."""


RULES = [
    {
        "variant": "telecom_discount_compare",
        "groups": (("\uacf5\uc2dc\uc9c0\uc6d0\uae08", "\ub2e8\ub9d0 \uac00\uaca9", "\ucd9c\uace0\uac00"), ("\uc120\ud0dd\uc57d\uc815", "\uc6d4 \uc694\uae08", "\uc694\uae08 \ud560\uc778")),
        "reason": "\ub2e8\ub9d0 \uc989\uc2dc \ud560\uc778\uacfc \uc6d4 \uc694\uae08 \ud560\uc778\uc744 \ube44\uad50\ud558\ub294 \ud1b5\uc2e0\ube44 \ucf58\ud150\uce20\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0\uc744 \uc911\uc2ec\uc73c\ub85c \uc88c\uce21\uc5d0\ub294 \ub2e8\ub9d0 \uac00\uaca9\uc774 \ud55c \ubc88\uc5d0 \ub0ae\uc544\uc9c0\ub294 \ud750\ub984, \uc6b0\uce21\uc5d0\ub294 \ub9e4\uc6d4 \uc694\uae08\uc774 \uc904\uc5b4\ub4dc\ub294 \ud750\ub984. \uc22b\uc790 \uc5c6\uc774 \ub450 \ud560\uc778 \ubc29\uc2dd\uc758 \ucc28\uc774\ub97c \uc2dc\uac01\uc801\uc73c\ub85c \ube44\uad50.",
    },
    {
        "variant": "plan_price_tier_compare",
        "groups": (("\uc694\uae08\uc81c",), ("\uace0\uac00", "\uc911\uc800\uac00", "\ubd84\uae30\uc810", "\uc6d0\ub300")),
        "reason": "\uc694\uae08\uc81c \uad6c\uac04\ubcc4 \ud61c\ud0dd \ube44\uad50\uc640 \uad6c\ub9e4 \uac00\uc774\ub4dc\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc138 \ub2e8\uacc4\ub85c \ub098\ub258 \uc694\uae08\uc81c \uad6c\uac04\uc744 \uacc4\ub2e8\uc2dd\uc73c\ub85c \ubcf4\uc5ec\uc8fc\uace0, \uad6c\uac04\ubcc4\ub85c \ub2ec\ub77c\uc9c0\ub294 \ud560\uc778 \ud750\ub984\uc744 \uac04\uacb0\ud55c \ud654\uc0b4\ud45c\uc640 \uccb4\ud06c \ud45c\uc2dc\ub85c \ud45c\ud604. \uc2e4\uc81c \uac00\uaca9 \uc22b\uc790\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "smishing_fake_link",
        "groups": (("\ubb38\uc790", "\uba54\uc2dc\uc9c0", "\ub9c1\ud06c", "URL"), ("\uc2a4\ubbf8\uc2f1", "\uc545\uc131 \uc571", "\uac00\uc9dc \ud398\uc774\uc9c0", "\ud074\ub9ad")),
        "reason": "\uc2a4\ubbf8\uc2f1, \uc545\uc131 \ub9c1\ud06c, \uac00\uc9dc \uc2e0\uccad\uc11c \uc8fc\uc758 \ucf58\ud150\uce20\uc5d0 \ubc94\uc6a9\uc73c\ub85c \uc4f8 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ubb38\uc790 \uba54\uc2dc\uc9c0\uc758 \uc758\uc2ec\uc2a4\ub7ec\uc6b4 \ub9c1\ud06c\uac00 \uac00\uc9dc \uc6f9\ud398\uc774\uc9c0\uc640 \uc545\uc131 \uc571 \uc124\uce58 \uacbd\uace0\ub85c \uc5f0\uacb0\ub418\ub294 \ud750\ub984. \uc911\uc2ec \uc2a4\ub9c8\ud2b8\ud3f0, \uc704\ud5d8 \ud45c\uc2dc, \uc9e7\uc740 \uc5f0\uacb0\uc120\uc73c\ub85c \uad6c\uc131.",
    },
    {
        "variant": "impersonation_call",
        "groups": (("\uc0ac\uce6d", "\ubcf4\uc774\uc2a4\ud53c\uc2f1", "\uc0ac\uae30\ubc94"), ("\ud1b5\ud654", "\uc804\ud654", "\uac80\ucc30", "\uacbd\ucc30", "\uae08\uac10\uc6d0")),
        "reason": "\uae30\uad00\uc0ac\uce6d\ud615 \ubcf4\uc774\uc2a4\ud53c\uc2f1\uacfc \uc704\ud5d8 \ud1b5\ud654 \uc8fc\uc758 \ub274\uc2a4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \ud1b5\ud654 \ud654\uba74 \uc8fc\ubcc0\uc5d0 \uc704\uc870\ub41c \uacf5\uacf5\uae30\uad00 \ubc30\uc9c0\uc640 \uacbd\uace0 \ud45c\uc2dc. \ud2b9\uc815 \uae30\uad00 \ub85c\uace0 \uc5c6\uc774 \uc0ac\uce6d \uc804\ud654\uc758 \uc704\ud5d8\uc744 \ubcf4\uc5ec\uc8fc\ub294 \ubc94\uc6a9 \uad6c\uc131.",
    },
    {
        "variant": "emergency_account_freeze",
        "groups": (("\uc9c0\uae09\uc815\uc9c0", "\ud658\uc218", "\uc2e0\uace0"), ("\uc1a1\uae08", "\uac70\ub798 \uc740\ud589", "112", "1332", "1\uc2dc\uac04")),
        "reason": "\uc1a1\uae08 \uc0ac\uae30 \uc9c1\ud6c4 \ub300\uc751\uacfc \uace8\ub4e0\ud0c0\uc784 \uc548\ub0b4\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc1a1\uae08 \ud654\uc0b4\ud45c\uac00 \uc740\ud589 \uacc4\uc88c \uc55e\uc5d0\uc11c \uae34\uae09 \uc815\uc9c0\ub418\ub294 \uc7a5\uba74. \uc791\uc740 \uc2dc\uacc4\uc640 \ubcf4\ud638 \ubc29\ud328\ub97c \ubcf4\uc870 \uc694\uc18c\ub85c \uc0ac\uc6a9\ud574 \ube60\ub978 \ub300\uc751\uc744 \uac15\uc870.",
    },
    {
        "variant": "fake_government_page",
        "groups": (("\uc815\ubd80", "\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uc2e0\uccad \uc548\ub0b4"), ("\uac00\uc9dc \ud398\uc774\uc9c0", "\ub611\uac19\uc774 \uc0dd\uae34", "\uc2a4\ubbf8\uc2f1")),
        "reason": "\uacf5\uacf5\uae30\uad00 \uc0ac\uce6d \uc6f9\uc0ac\uc774\ud2b8\uc640 \uac00\uc9dc \uc2e0\uccad \ud398\uc774\uc9c0 \uacbd\uace0\uc5d0 \ubc94\uc6a9\uc73c\ub85c \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc11c\ub85c \ube44\uc2b7\ud55c \ub450 \uac1c\uc758 \ubaa8\ubc14\uc77c \uc6f9\ud398\uc774\uc9c0. \ud558\ub098\ub294 \uc548\uc804 \uccb4\ud06c, \ub2e4\ub978 \ud558\ub098\ub294 \uacbd\uace0 \ud45c\uc2dc\uc640 \uc8fc\uc758 \uc0c9\uc0c1\uc73c\ub85c \uad6c\ubd84. \ud2b9\uc815 \uc815\ubd80 \ub85c\uace0\ub098 URL\uc740 \ub123\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "personal_data_leak",
        "groups": (("\uc8fc\ubbfc\ubc88\ud638", "\uacc4\uc88c", "\uc778\uc99d\ubc88\ud638", "\uac1c\uc778\uc815\ubcf4"), ("\uc720\ucd9c", "\ud0c8\ucde8", "\uc545\uc131 \uc571", "\ub178\ucd9c")),
        "reason": "\uac1c\uc778\uc815\ubcf4 \uc720\ucd9c, \uc545\uc131 \uc571, \uacc4\uc815 \ud0c8\ucde8 \ub274\uc2a4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \uc548\uc758 \uac1c\uc778\uc815\ubcf4 \uce74\ub4dc, \uacc4\uc88c, \uc778\uc99d \ucf54\ub4dc\uac00 \ubc16\uc73c\ub85c \ube60\uc838\ub098\uac00\ub824\ub294 \uc21c\uac04\uc744 \ubcf4\ud638 \ubc29\ud328\uac00 \ub9c9\ub294 \uc7a5\uba74.",
    },
    {
        "variant": "official_site_check",
        "groups": (("\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uacf5\uc2dd \ud398\uc774\uc9c0", "\uc815\ubd8024", "mygov"),),
        "reason": "\uacf5\uc2dd \uc548\ub0b4 \ucc44\ub110 \ud655\uc778\uacfc \uc758\uc2ec \ub9c1\ud06c \ud53c\ud574 \uc608\ubc29\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \ube0c\ub77c\uc6b0\uc800\uc758 \uc548\uc804\ud55c \uacf5\uc2dd \ud398\uc774\uc9c0\ub97c \uccb4\ud06c \ud45c\uc2dc\uc640 \ubcf4\ud638 \ubc29\ud328\ub85c \ud655\uc778\ud558\ub294 \uc7a5\uba74. \ud2b9\uc815 URL\uacfc \ub85c\uace0\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def section_text(section: dict) -> str:
    return clean(" ".join([section.get("topic", ""), " ".join(section.get("caption_chunks", []) or []), " ".join(section.get("display_chunks", []) or []), section.get("tts", "")]))


def chunk_text(section: dict, idx: int) -> str:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    return clean(" ".join([(chunks[idx] if idx < len(chunks) else ""), (displays[idx] if idx < len(displays) else ""), section.get("topic", "")]))


def matches(rule: dict, text: str) -> bool:
    value = text.lower()
    return all(any(keyword.lower() in value for keyword in group) for group in rule["groups"])


def find_chunk(section: dict, rule: dict) -> int:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    for idx in range(max(len(chunks), len(displays))):
        if matches(rule, chunk_text(section, idx)):
            return idx
    flattened = [keyword for group in rule["groups"] for keyword in group]
    for idx in range(max(len(chunks), len(displays))):
        value = chunk_text(section, idx).lower()
        if any(keyword.lower() in value for keyword in flattened):
            return idx
    return 0


def current_visual(section: dict, idx: int) -> dict:
    visuals = section.get("chunk_visuals", []) or []
    if 0 <= idx < len(visuals) and isinstance(visuals[idx], dict):
        return visuals[idx]
    return {}


def preserve_hook_anchor(section_name: str, section: dict, idx: int) -> int:
    visuals = section.get("chunk_visuals", []) or []
    if section_name == "hook" and idx == 0 and len(visuals) > 1:
        return 1
    return idx


def quality_gap(db: dict, section: dict, idx: int) -> tuple[int, str]:
    visual = current_visual(section, idx)
    if visual.get("type") != "illust":
        return 0, f"current visual is {visual.get('type', 'missing')}; a reusable semantic illustration can improve this slot"
    variant = str(visual.get("value") or "")
    entry = (db.get("illustrations", {}) or {}).get(variant, {})
    score = semantic_score(chunk_text(section, idx), entry)
    return score, f"current illust:{variant} semantic score={score}; replace weak fallback with a reusable semantic asset"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_illustration_scout.py <slug>")
        return 2
    slug = sys.argv[1]
    ensure_db()
    output_dir = CARDNEWS / "output" / slug
    script_path = output_dir / "shorts_script.json"
    if not script_path.exists():
        print(f"[illustration_scout_v2] skip, missing: {script_path}")
        return 0

    data = json.loads(script_path.read_text(encoding="utf-8-sig"))
    db = load_db()
    existing = {path.stem for path in ILLUST_DIR.glob("*.png")} if ILLUST_DIR.exists() else set()
    requests = []
    seen = set()
    reserved_slots = set()

    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        text = section_text(section)
        for rule in RULES:
            variant = rule["variant"]
            if variant in seen or variant in existing or not matches(rule, text):
                continue
            chunk_idx = preserve_hook_anchor(section_name, section, find_chunk(section, rule))
            slot = (section_name, chunk_idx)
            if slot in reserved_slots:
                continue
            score, gap = quality_gap(db, section, chunk_idx)
            if score >= 12:
                continue
            seen.add(variant)
            reserved_slots.add(slot)
            requests.append(
                {
                    "variant": variant,
                    "filename": f"{variant}.png",
                    "section": section_name,
                    "chunk_index": chunk_idx,
                    "reason": rule["reason"],
                    "quality_gap": gap,
                    "tags": variant_tags(variant),
                    "prompt": STYLE + "\n\n\ud575\uc2ec \ucf58\uc149\ud2b8:\n" + rule["concept"],
                    "status": "requested",
                }
            )
            if len(requests) >= MAX_REQUESTS:
                break
        if len(requests) >= MAX_REQUESTS:
            break

    payload = {
        "version": 2,
        "slug": slug,
        "policy": "suggest reusable GPT Plus assets when existing semantic coverage is weak; max three requests per video",
        "upload_dir": str(ILLUST_DIR),
        "requests": requests,
    }
    json_path = output_dir / "codex_illustration_requests.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Codex Illustration Requests V2: {slug}",
        "",
        "\ud604\uc7ac \uc2dc\uac01 \ub9e4\ud551\uc758 \ubb38\ub9e5 \ud488\uc9c8\uc744 \uac80\uc0ac\ud574, \ub2e4\ub978 \uae30\uc0ac\uc5d0\uc11c\ub3c4 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\ub294 \uc77c\ub7ec\uc2a4\ud2b8\ub9cc \ucd94\ucc9c\ud569\ub2c8\ub2e4.",
        "\uc601\uc0c1 \ud55c \ud3b8\ub2f9 \ucd5c\ub300 3\uac1c\ub9cc \uc81c\uc548\ud569\ub2c8\ub2e4.",
        "",
    ]
    if not requests:
        lines.append("\ucd94\uac00\ub85c \ub9cc\ub4e4 \ubc94\uc6a9 \uc77c\ub7ec\uc2a4\ud2b8\uac00 \uc5c6\uc2b5\ub2c8\ub2e4. \ubc14\ub85c \ub80c\ub354\ub9c1\ud574\ub3c4 \ub429\ub2c8\ub2e4.")
    for idx, item in enumerate(requests, 1):
        lines.extend(
            [
                f"## {idx}. `{item['filename']}`",
                "",
                f"- \uc801\uc6a9 \uc704\uce58: `{item['section']}` \uccad\ud06c {item['chunk_index'] + 1}",
                f"- \ucd94\ucc9c \uc774\uc720: {item['reason']}",
                f"- \uad50\uccb4 \uadfc\uac70: {item['quality_gap']}",
                "",
                "```text",
                item["prompt"],
                "```",
                "",
            ]
        )
    md_path = output_dir / "codex_illustration_requests.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    mark_requests(slug, requests)
    write_report()
    print(f"[illustration_scout_v2] report: {md_path}")
    print(f"[illustration_scout_v2] requests: {len(requests)}")
    for item in requests:
        print(f"  - {item['filename']} -> {item['section']} chunk {item['chunk_index'] + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


DB_EXTRA = r'''
    # CODEX_ILLUSTRATION_SCOUT_V2 reusable editorial growth assets.
    "telecom_discount_compare": {"tags": ["price", "subsidy", "compare", "telecom"], "keywords": ["\uacf5\uc2dc\uc9c0\uc6d0\uae08", "\uc120\ud0dd\uc57d\uc815", "\ub2e8\ub9d0 \ud560\uc778", "\uc6d4 \uc694\uae08 \ud560\uc778"]},
    "plan_price_tier_compare": {"tags": ["price", "plan", "compare", "telecom"], "keywords": ["\uc694\uae08\uc81c", "\uace0\uac00 \uc694\uae08\uc81c", "\uc911\uc800\uac00 \uc694\uae08\uc81c", "\ubd84\uae30\uc810"]},
    "smishing_fake_link": {"tags": ["security", "smishing", "warning", "link"], "keywords": ["\uc2a4\ubbf8\uc2f1", "\ubb38\uc790 \ub9c1\ud06c", "\uc545\uc131 \uc571", "\uac00\uc9dc \ud398\uc774\uc9c0"]},
    "impersonation_call": {"tags": ["security", "voice-phishing", "call", "warning"], "keywords": ["\uae30\uad00\uc0ac\uce6d", "\uc0ac\uce6d", "\ubcf4\uc774\uc2a4\ud53c\uc2f1", "\uc704\ud5d8 \ud1b5\ud654"]},
    "emergency_account_freeze": {"tags": ["security", "bank", "response", "golden-time"], "keywords": ["\uc9c0\uae09\uc815\uc9c0", "\ud658\uc218", "\uc1a1\uae08", "\uac70\ub798 \uc740\ud589"]},
    "fake_government_page": {"tags": ["security", "smishing", "government", "warning"], "keywords": ["\uac00\uc9dc \ud398\uc774\uc9c0", "\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uc815\ubd80 \uc0ac\uce6d"]},
    "personal_data_leak": {"tags": ["security", "privacy", "leak"], "keywords": ["\uac1c\uc778\uc815\ubcf4", "\uc8fc\ubbfc\ubc88\ud638", "\uacc4\uc88c", "\uc778\uc99d\ubc88\ud638", "\uc720\ucd9c"]},
    "official_site_check": {"tags": ["security", "official-site", "check"], "keywords": ["\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uacf5\uc2dd \ud398\uc774\uc9c0", "\uc815\ubd8024", "mygov"]},
'''


def backup(path: Path) -> None:
    target = path.with_name(path.name + f".{LABEL}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + body.strip() + "\n")


def patch_db() -> None:
    text = DB.read_text(encoding="utf-8")
    if "CODEX_ILLUSTRATION_SCOUT_V2 reusable editorial growth assets" in text:
        print("[skip] Illustration DB V2 seeds already installed")
        return
    anchor = "\n}\n\n\ndef now_text()"
    if anchor not in text:
        raise RuntimeError("illustration DB seed anchor missing")
    backup(DB)
    write(DB, text.replace(anchor, "\n" + DB_EXTRA.rstrip() + anchor, 1))


def typecheck() -> None:
    if os.environ.get("PHONESPOT_SKIP_TSC") == "1":
        print("[skip] TypeScript check disabled for isolated fixture")
        return
    result = subprocess.run(["cmd", "/c", "npx.cmd", "tsc", "--noEmit"], cwd=SHORTS)
    if result.returncode != 0:
        raise RuntimeError("TypeScript check failed")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Illustration Scout V2")
    print("============================================================")
    for required in (SCOUT, DB):
        if not required.exists():
            raise RuntimeError(f"required file missing: {required}")
    if "CODEX_ILLUSTRATION_SCOUT_V2" not in SCOUT.read_text(encoding="utf-8"):
        backup(SCOUT)
        write(SCOUT, SCOUT_V2)
    else:
        print("[skip] Illustration Scout V2 already installed")
    patch_db()
    py_compile.compile(str(SCOUT), doraise=True)
    py_compile.compile(str(DB), doraise=True)
    typecheck()
    append_once(
        MEMORY,
        "## 38. Illustration Scout V2",
        """## 38. Illustration Scout V2
- Scout requests are no longer limited to nine predefined missing files.
- Audit the current semantic visual quality and suggest up to three reusable GPT Plus editorial illustrations per video.
- Prefer broadly reusable concepts. Avoid article-specific dates, prices, names, and logos.
- Existing rendering, source-image-once, CTA, Korean caption, and TTS rules remain unchanged.""",
    )
    append_once(
        PATCH_LOG,
        "## Illustration Scout V2",
        f"""## Illustration Scout V2
- Applied: {STAMP}
- Scope: Scout prompts and illustration tag DB seeds only. Renderer unchanged.
- Rollback: RUN_ROLLBACK_CODEX_ILLUSTRATION_SCOUT_V2.bat
""",
    )
    print("[OK] Illustration Scout V2 installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
