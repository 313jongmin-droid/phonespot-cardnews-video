# -*- coding: utf-8 -*-
"""Keep the desk illustration library and Remotion render cache in sync."""
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DESK = ROOT / "CODEX_VIDEO_DESK"
LIBRARY = DESK / "ILLUSTRATION_DROP"
CACHE = ROOT / "shorts" / "public" / "assets" / "illustrations"


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def copy_tree_missing(source: Path, target: Path) -> int:
    copied = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        output = target / relative
        if output.exists():
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, output)
        copied += 1
    return copied


def copy_tree_refresh(source: Path, target: Path) -> int:
    copied = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.stat().st_size == item.stat().st_size and output.stat().st_mtime_ns == item.stat().st_mtime_ns:
            continue
        shutil.copy2(item, output)
        copied += 1
    return copied


def main() -> int:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if CACHE.resolve() == LIBRARY.resolve():
            print("[illustrations] Remotion path already points to desk library.")
            return 0
    except OSError:
        pass
    recovered = copy_tree_missing(CACHE, LIBRARY)
    refreshed = copy_tree_refresh(LIBRARY, CACHE)
    print(f"[illustrations] desk library: {LIBRARY}")
    print(f"[illustrations] recovered={recovered}, cache-updated={refreshed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
