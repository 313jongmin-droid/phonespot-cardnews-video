# -*- coding: utf-8 -*-
"""Block renders that violate Korean caption compiler V2 contracts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from codex_caption_lockstep import ABSOLUTE_MAX_UNITS, forbidden_boundary, units


ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "cardnews" / "output"


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts\\validate_caption_compiler_v2.py <slug>")
        return 2
    slug = sys.argv[1]
    path = OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[caption_v2] missing: {path}")
        return 2
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    for name, section in sections(data):
        chunks = [str(x or "").strip() for x in section.get("caption_chunks", []) or [] if str(x or "").strip()]
        if name != "cta":
            for idx, chunk in enumerate(chunks, 1):
                if units(chunk) > ABSOLUTE_MAX_UNITS:
                    errors.append(f"{name}.caption_chunks[{idx}]: {units(chunk)} > {ABSOLUTE_MAX_UNITS}")
        for idx in range(len(chunks) - 1):
            left = chunks[idx].split()[-1] if chunks[idx].split() else ""
            right = chunks[idx + 1].split()[0] if chunks[idx + 1].split() else ""
            if forbidden_boundary(left, right):
                errors.append(f"{name}.caption_chunks[{idx + 1}:{idx + 3}]: protected phrase split")
    if errors:
        print("[caption_v2] ERROR")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[caption_v2] OK: {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
