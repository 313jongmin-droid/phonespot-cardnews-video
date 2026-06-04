# -*- coding: utf-8 -*-
"""Disable inferred inline caption highlights without touching brand accents."""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
CASUAL_CAPTION = SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx"
STATIC_SUBTITLE = SHORTS / "src" / "components" / "StaticSubtitle.tsx"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


CASUAL_OLD = '''              color: seg.emph ? "#F74B0B" : "#1A1A1A",
              backgroundColor: seg.emph ? "rgba(247,75,11,0.10)" : "transparent",
              borderRadius: seg.emph ? 10 : 0,
              padding: seg.emph ? "0 6px" : 0,'''

CASUAL_NEW = '''              color: "#1A1A1A",
              backgroundColor: "transparent",
              borderRadius: 0,
              padding: 0,'''

STATIC_OLD = '''                color: emph ? "#FFD24A" : "#FFFFFF",'''
STATIC_NEW = '''                color: "#FFFFFF",'''


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def backup(path: Path, label: str) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_{label}_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    current = read(path)
    if marker in current:
        print(f"[skip] already documented: {path.name}")
        return
    write(path, current.rstrip() + "\n\n" + body.strip() + "\n")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    if not path.exists():
        print(f"[skip] optional file not found: {path}")
        return
    text = read(path)
    if new in text:
        print(f"[skip] already current: {path}")
        return
    if old not in text:
        raise RuntimeError(f"{label} patch anchor missing: {path}")
    backup(path, "caption_highlight_off")
    write(path, text.replace(old, new, 1))


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - Disable Inline Caption Highlights")
    print("=" * 60)
    replace_once(CASUAL_CAPTION, CASUAL_OLD, CASUAL_NEW, "casual caption")
    replace_once(STATIC_SUBTITLE, STATIC_OLD, STATIC_NEW, "static subtitle")
    append_once(
        BASELINE,
        "## Caption display color contract",
        """## Caption display color contract
- Screen-caption text uses one readable text color only.
- Do not infer or render orange or yellow inline caption highlights.
- Orange remains available for structural brand accents, CTA elements, and infographics.""",
    )
    append_once(
        MEMORY,
        "## 36. Inline caption highlights are disabled",
        """## 36. Inline caption highlights are disabled
- Inferred inline caption highlighting looked like an error when keyword matching was inaccurate.
- Keep screen-caption text uniform. Do not restore automatic orange or yellow word coloring.
- Keep PhoneSpot orange for structural brand accents, CTA elements, and infographics.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-02 - Inline caption highlights disabled",
        """## 2026-06-02 - Inline caption highlights disabled
- Disabled inferred orange highlights in the active Casual Remotion captions.
- Disabled legacy yellow inline subtitle highlights as a fallback safeguard.
- Preserved PhoneSpot orange in brand accents, CTA elements, and infographics.""",
    )
    if (SHORTS / "tsconfig.json").exists():
        subprocess.run(["cmd", "/c", "npx tsc --noEmit"], cwd=SHORTS, check=True)
    print("[OK] Inline caption highlights are disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
