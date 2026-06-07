# -*- coding: utf-8 -*-
"""Validate the exact script that Remotion will render."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from codex_chunk_overrides import validate_effective_script


ROOT = Path(__file__).resolve().parent.parent
RUNTIME_SCRIPT = ROOT / "public" / "shorts_script.json"


def main() -> int:
    if not RUNTIME_SCRIPT.exists():
        print(f"[effective_script] missing: {RUNTIME_SCRIPT}")
        return 2
    data = json.loads(RUNTIME_SCRIPT.read_text(encoding="utf-8-sig"))
    errors = validate_effective_script(data)
    if errors:
        print("[effective_script] ERROR")
        for error in errors:
            print(f"  - {error}")
        return 1
    slug = data.get("slug") or (sys.argv[1] if len(sys.argv) > 1 else "-")
    override = data.get("_codex_chunk_overrides_applied") or {}
    sections = override.get("sections") if isinstance(override, dict) else []
    suffix = f" | override: {', '.join(sections)}" if sections else ""
    print(f"[effective_script] OK: {slug}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
