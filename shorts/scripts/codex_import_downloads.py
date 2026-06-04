# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
DOWNLOADS = Path.home() / "Downloads"
DROP = DESK / "ILLUSTRATION_DROP"
ILLUST = SHORTS / "public" / "assets" / "illustrations"
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}


def run(script: str, *args: str) -> None:
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *args])
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    slug_path = DESK / "LATEST_SLUG.txt"
    report_path = DESK / "LATEST_PROMPT.json"
    if not slug_path.exists() or not report_path.exists():
        print("[ERROR] Run 01_PREPARE_GPT_PROMPTS.bat first.")
        return 2
    slug = slug_path.read_text(encoding="utf-8").strip()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    requests = [
        item for item in payload.get("requests", [])
        if item.get("filename") and not (ILLUST / item["filename"]).exists()
    ]
    if not requests:
        print("[OK] No missing requested illustration. Render can start.")
        return 0

    threshold = report_path.stat().st_mtime - 2

    selected = []
    remaining = []
    for request in requests:
        exact = DROP / request["filename"]
        if exact.exists() and exact.is_file() and exact.stat().st_size >= 10_000:
            selected.append(exact)
        else:
            remaining.append(request)

    candidates = []
    for folder in (DROP, DOWNLOADS):
        if not folder.exists():
            continue
        candidates.extend(
            item for item in folder.iterdir()
            if item.is_file()
            and item.suffix.lower() in ALLOWED
            and item.stat().st_size >= 10_000
            and item.stat().st_mtime >= threshold
            and item not in selected
        )
    candidates = sorted(candidates, key=lambda item: item.stat().st_mtime)

    if len(candidates) < len(remaining):
        print(f"[ERROR] Need {len(requests)} requested images, found {len(selected) + len(candidates)}.")
        print(f"[INFO] Exact files found in ILLUSTRATION_DROP: {len(selected)}")
        print(f"[INFO] Recent files found in ILLUSTRATION_DROP/Downloads: {len(candidates)}")
        print("[NEXT] Put GPT Plus images in CODEX_VIDEO_DESK\\ILLUSTRATION_DROP or Downloads, then retry.")
        print("[TIP] If you want to render without new images, use 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.")
        return 3

    selected = selected + candidates[-len(remaining):]
    print("")
    print(f"Slug: {slug}")
    print("Import mapping:")
    for source, request in zip(selected, requests):
        print(f"  {source.name}")
        print(f"    -> {request['filename']}")
    print("")
    answer = input("Import these files and continue? [Y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("[STOP] Nothing imported.")
        return 4

    ILLUST.mkdir(parents=True, exist_ok=True)
    for source, request in zip(selected, requests):
        target = ILLUST / request["filename"]
        shutil.copy2(source, target)
        print(f"[COPY] {target.name}")

    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_refresh_workbench.py", slug)
    print("")
    print("[OK] Downloads imported and mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
