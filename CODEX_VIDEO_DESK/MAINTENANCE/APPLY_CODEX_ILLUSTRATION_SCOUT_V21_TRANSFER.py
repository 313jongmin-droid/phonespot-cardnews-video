# -*- coding: utf-8 -*-
"""Extend Illustration Scout V2 with reusable migration assets and gap reporting."""
from __future__ import annotations

import os
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
SCOUT = SHORTS / "scripts" / "codex_illustration_scout.py"
DB = SHORTS / "scripts" / "codex_illustration_db.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LABEL = f"bak_illustration_scout_v21_{STAMP}"


RULES_INSERT = r'''
    {
        "variant": "device_data_transfer",
        "groups": (("\ub370\uc774\ud130", "\uc0ac\uc9c4", "\ub3d9\uc601\uc0c1", "\uc5f0\ub77d\ucc98", "\uba54\uc2dc\uc9c0"), ("\uc62e\uae30", "\uc774\uc804", "Smart Switch", "iCloud", "USB \ucf00\uc774\ube14")),
        "reason": "\uc2e0\uaddc \uae30\uae30 \uad50\uccb4, \uc2a4\ub9c8\ud2b8\uc704\uce58, \ud074\ub77c\uc6b0\ub4dc \uc774\uc804 \uac00\uc774\ub4dc\uc5d0 \ubc94\uc6a9\uc73c\ub85c \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ub450 \ub300\uc758 \uc2a4\ub9c8\ud2b8\ud3f0 \uc0ac\uc774\ub85c \uc0ac\uc9c4, \uc5f0\ub77d\ucc98, \uba54\uc2dc\uc9c0\ub97c \uc0c1\uc9d5\ud558\ub294 \uc791\uc740 \uce74\ub4dc\uac00 \uc548\uc804\ud558\uac8c \uc774\ub3d9\ud558\ub294 \uc7a5\uba74. \uc5f0\uacb0 \ucf00\uc774\ube14\uacfc \ud074\ub77c\uc6b0\ub4dc\ub97c \ubcf4\uc870 \uc694\uc18c\ub85c \ud45c\ud604.",
    },
    {
        "variant": "chat_backup_restore",
        "groups": (("\ub300\ud654", "\uba54\uc2e0\uc800", "\uce74\uce74\uc624\ud1a1", "\ucc44\ud305"), ("\ubc31\uc5c5", "\ubcf5\uc6d0", "\ub85c\uadf8\uc778")),
        "reason": "\uba54\uc2e0\uc800 \ub300\ud654 \ubc31\uc5c5, \ud734\ub300\ud3f0 \uad50\uccb4, \uacc4\uc815 \ubcf5\uc6d0 \uc548\ub0b4\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ucc44\ud305 \ub9d0\ud48d\uc120\uc774 \ub2f4\uae34 \uc2a4\ub9c8\ud2b8\ud3f0\uc5d0\uc11c \ud074\ub77c\uc6b0\ub4dc \ubc31\uc5c5\uc744 \uac70\uccd0 \uc0c8 \uc2a4\ub9c8\ud2b8\ud3f0\uc73c\ub85c \ubcf5\uc6d0\ub418\ub294 \ud750\ub984. \ud2b9\uc815 \uba54\uc2e0\uc800 \ub85c\uace0\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "secure_app_reregistration",
        "groups": (("\uc778\uc99d\uc11c", "\uae08\uc735 \uc571", "\uacb0\uc81c \uc218\ub2e8", "\ubaa8\ubc14\uc77c \uc2e0\ubd84\uc99d", "\uae30\uae30 \uc778\uc99d"), ("\uc7ac\ub4f1\ub85d", "\uc7ac\ubc1c\uae09", "\uc0c8 \ud3f0", "\ub85c\uadf8\uc778", "\ub2e4\uc2dc \ub4f1\ub85d")),
        "reason": "\ud3f0 \uad50\uccb4 \ud6c4 \uae08\uc735 \uc571, \uc778\uc99d\uc11c, \uacb0\uc81c\uc218\ub2e8 \uc7ac\uc124\uc815 \uc548\ub0b4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc0c8 \uc2a4\ub9c8\ud2b8\ud3f0 \ud654\uba74 \uc548\uc5d0 \uc790\ubb3c\uc1e0, \uc778\uc99d \uce74\ub4dc, \uacb0\uc81c \uce74\ub4dc\uac00 \uc21c\ucc28\uc801\uc73c\ub85c \ub2e4\uc2dc \ub4f1\ub85d\ub418\ub294 \uc7a5\uba74. \uc548\uc804\ud55c \uc7ac\uc124\uc815 \ud750\ub984\uc744 \uccb4\ud06c \ud45c\uc2dc\ub85c \ud45c\ud604.",
    },
'''


DB_INSERT = r'''
    # CODEX_ILLUSTRATION_SCOUT_V21 reusable migration assets.
    "device_data_transfer": {"tags": ["device", "migration", "backup", "tips"], "keywords": ["\ub370\uc774\ud130 \uc774\uc804", "\ub370\uc774\ud130 \uc62e\uae30", "Smart Switch", "iCloud", "USB \ucf00\uc774\ube14"]},
    "chat_backup_restore": {"tags": ["messenger", "backup", "restore", "tips"], "keywords": ["\ub300\ud654 \ubc31\uc5c5", "\ub300\ud654 \ubcf5\uc6d0", "\uba54\uc2e0\uc800", "\uce74\uce74\uc624\ud1a1"]},
    "secure_app_reregistration": {"tags": ["security", "bank", "authentication", "setup"], "keywords": ["\uc778\uc99d\uc11c", "\uae08\uc735 \uc571", "\uacb0\uc81c \uc218\ub2e8", "\uae30\uae30 \uc778\uc99d", "\uc7ac\ub4f1\ub85d"]},
'''


GAP_HELPERS = r'''

def semantic_gap_rows(db: dict, data: dict) -> list[dict]:
    rows = []
    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        visuals = section.get("chunk_visuals", []) or []
        chunks = section.get("caption_chunks", []) or section.get("display_chunks", []) or []
        for idx, visual in enumerate(visuals):
            if not isinstance(visual, dict) or visual.get("type") != "illust":
                continue
            variant = str(visual.get("value") or "")
            entry = (db.get("illustrations", {}) or {}).get(variant, {})
            score = semantic_score(chunk_text(section, idx), entry)
            if score <= 0:
                rows.append(
                    {
                        "section": section_name,
                        "chunk_index": idx,
                        "variant": variant,
                        "text": chunks[idx] if idx < len(chunks) else "",
                    }
                )
    return rows
'''


def backup(path: Path) -> None:
    target = path.with_name(path.name + f".{LABEL}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + body.strip() + "\n")


def patch_scout() -> None:
    text = SCOUT.read_text(encoding="utf-8")
    if "CODEX_ILLUSTRATION_SCOUT_V21" in text:
        print("[skip] Illustration Scout V2.1 already installed")
        return
    if "CODEX_ILLUSTRATION_SCOUT_V2" not in text:
        raise RuntimeError("Install Illustration Scout V2 first")
    backup(SCOUT)
    anchor = "\n]\n\n\ndef clean(value: str)"
    if anchor not in text:
        raise RuntimeError("Scout rule anchor missing")
    text = text.replace(anchor, RULES_INSERT + anchor, 1)
    anchor = "\ndef main() -> int:"
    if anchor not in text:
        raise RuntimeError("Scout main anchor missing")
    text = text.replace(anchor, GAP_HELPERS + anchor, 1)
    old = '''    payload = {
        "version": 2,
        "slug": slug,
        "policy": "suggest reusable GPT Plus assets when existing semantic coverage is weak; max three requests per video",
        "upload_dir": str(ILLUST_DIR),
        "requests": requests,
    }'''
    new = '''    uncovered_gaps = semantic_gap_rows(db, data)
    payload = {
        "version": 2.1,
        "slug": slug,
        "policy": "suggest reusable GPT Plus assets when existing semantic coverage is weak; max three requests per video",
        "upload_dir": str(ILLUST_DIR),
        "requests": requests,
        "uncovered_gaps": uncovered_gaps,
    }'''
    if old not in text:
        raise RuntimeError("Scout payload anchor missing")
    text = text.replace(old, new, 1)
    new = '''    if not requests:
        if uncovered_gaps:
            lines.append("\uc0c8 \ud504\ub86c\ud504\ud2b8\ub294 \uc5c6\uc9c0\ub9cc, \ubb38\ub9e5 \uc801\ud569\ub3c4\uac00 \ub0ae\uc740 \ud3f4\ubc31 \uc77c\ub7ec\uc2a4\ud2b8\uac00 \ub0a8\uc544 \uc788\uc2b5\ub2c8\ub2e4. Codex\uc5d0\uac8c \uaddc\uce59 \ud655\uc7a5\uc744 \uc694\uccad\ud558\uc138\uc694.")
        else:
            lines.append("\ucd94\uac00\ub85c \ub9cc\ub4e4 \ubc94\uc6a9 \uc77c\ub7ec\uc2a4\ud2b8\uac00 \uc5c6\uc2b5\ub2c8\ub2e4. \ubc14\ub85c \ub80c\ub354\ub9c1\ud574\ub3c4 \ub429\ub2c8\ub2e4.")'''
    start = text.find("    if not requests:\n")
    end = text.find("    for idx, item in enumerate(requests, 1):", start)
    if start < 0 or end < 0:
        raise RuntimeError("Scout empty-report anchor missing")
    text = text[:start] + new + "\n" + text[end:]
    anchor = '''    md_path = output_dir / "codex_illustration_requests.md"'''
    insert = '''    if uncovered_gaps:
        lines.extend(["", "## \ub0a8\uc544 \uc788\ub294 \ubb38\ub9e5 \ucee4\ubc84\ub9ac\uc9c0 \uacbd\uace0", ""])
        for gap in uncovered_gaps[:8]:
            lines.append(f"- `{gap['section']}` \uccad\ud06c {gap['chunk_index'] + 1}: `{gap['variant']}` -> {gap['text']}")
        lines.append("- \uc704 \ud56d\ubaa9\uc740 \ub80c\ub354\ub9c1\uc744 \ub9c9\uc9c0 \uc54a\uc9c0\ub9cc, \ubc18\ubcf5\ub418\uba74 \ubc94\uc6a9 \uc77c\ub7ec\uc2a4\ud2b8 \uaddc\uce59\uc744 \ucd94\uac00\ud574\uc57c \ud569\ub2c8\ub2e4.")

'''
    if anchor not in text:
        raise RuntimeError("Scout report anchor missing")
    text = text.replace(anchor, insert + anchor, 1)
    text = text.replace('print(f"[illustration_scout_v2] requests: {len(requests)}")', 'print(f"[illustration_scout_v21] requests: {len(requests)}, uncovered_gaps: {len(uncovered_gaps)}")', 1)
    text = text.replace('CODEX_ILLUSTRATION_SCOUT_V2\n', 'CODEX_ILLUSTRATION_SCOUT_V21\nCODEX_ILLUSTRATION_SCOUT_V2\n', 1)
    write(SCOUT, text)


def patch_db() -> None:
    text = DB.read_text(encoding="utf-8")
    if "CODEX_ILLUSTRATION_SCOUT_V21 reusable migration assets" in text:
        print("[skip] Illustration DB V2.1 seeds already installed")
        return
    anchor = "\n}\n\n\ndef now_text()"
    if anchor not in text:
        raise RuntimeError("Illustration DB seed anchor missing")
    backup(DB)
    write(DB, text.replace(anchor, "\n" + DB_INSERT.rstrip() + anchor, 1))


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Illustration Scout V2.1 Transfer Pack")
    print("============================================================")
    patch_scout()
    patch_db()
    py_compile.compile(str(SCOUT), doraise=True)
    py_compile.compile(str(DB), doraise=True)
    append_once(
        MEMORY,
        "## 39. Illustration Scout V2.1 migration pack",
        """## 39. Illustration Scout V2.1 migration pack
- Add reusable data-transfer, messenger-backup, and secure-app-reregistration illustration requests.
- If semantic fallback illustrations remain uncovered, report them instead of silently saying no new image is needed.
- Rendering remains available; uncovered gaps are quality warnings for the next library-growth pass.""",
    )
    append_once(
        PATCH_LOG,
        "## Illustration Scout V2.1 migration pack",
        f"""## Illustration Scout V2.1 migration pack
- Applied: {STAMP}
- Scope: data-transfer reusable prompts and uncovered semantic-gap report.
- Rollback: RUN_ROLLBACK_CODEX_ILLUSTRATION_SCOUT_V21_TRANSFER.bat
""",
    )
    print("[OK] Illustration Scout V2.1 transfer pack installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
