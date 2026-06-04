# -*- coding: utf-8 -*-
"""Fail closed when malformed Korean captions reach the Codex render boundary."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ENHANCER = ROOT / "shorts" / "scripts" / "codex_enhance_script.py"
OUTPUT = ROOT / "cardnews" / "output"


def load_enhancer():
    spec = importlib.util.spec_from_file_location("codex_enhance_script", ENHANCER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {ENHANCER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LIST_MARKER_AT_END = re.compile(r"(?:^|\s)(\d{1,2}[\)\.])\s*$")
LIST_MARKER_ONLY = re.compile(r"^\s*(\d{1,2}[\)\.])\s*$")


def validate_list_caption_layout(data: dict) -> None:
    """Allow runtime-repairable list splits and block unrecoverable orphan markers."""
    errors: list[str] = []
    repairs: list[str] = []
    sections = [("hook", data.get("hook") or {})]
    sections.extend((str(item.get("id") or f"fact_{idx + 1}"), item) for idx, item in enumerate(data.get("facts") or []))
    sections.append(("cta", data.get("cta") or {}))

    for section_name, section in sections:
        for field in ("caption_chunks", "display_chunks"):
            chunks = [str(chunk or "").strip() for chunk in (section.get(field) or [])]
            for idx, chunk in enumerate(chunks):
                match = LIST_MARKER_AT_END.search(chunk)
                if not match:
                    continue
                marker = match.group(1)
                if idx + 1 >= len(chunks) or not chunks[idx + 1].strip():
                    errors.append(f"{section_name}.{field}[{idx}]: orphan list marker `{marker}` has no following item")
                else:
                    repairs.append(f"{section_name}.{field}[{idx}] `{marker}` -> next chunk")

    if errors:
        raise ValueError("List-caption layout contract failed\n- " + "\n- ".join(errors))
    if repairs:
        print(f"[list_caption_guard] runtime repairs: {len(repairs)}")
        for repair in repairs[:8]:
            print(f"  - {repair}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_codex_korean.py <slug>")
        return 2
    slug = sys.argv[1]
    path = OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[korean_guard] missing: {path}")
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    enhancer = load_enhancer()
    try:
        validate_list_caption_layout(data)
        enhancer.validate_korean_contract(data)
    except ValueError as exc:
        print(f"[korean_guard] FAIL: {slug}")
        print(exc)
        return 2
    print(f"[korean_guard] OK: {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
