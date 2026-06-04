# -*- coding: utf-8 -*-
"""Install the metadata-only three-channel publish package layer."""
from __future__ import annotations

import os
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RUNNER = SHORTS / "run_codex_casual.bat"
DESK_README = DESK / "README.txt"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


PUBLISH_SCRIPT = r'''# -*- coding: utf-8 -*-
"""Create a copy-ready three-channel publishing packet for one Codex short.

V1 is deliberately metadata-only:
- never modifies the rendered MP4
- never rewrites captions.md
- keeps the existing flat upload_codex files
- uses hard links for the package master when possible to avoid disk waste
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS_OUTPUT = ROOT / "cardnews" / "output"
OUT_CODEX = SHORTS / "out_codex"
UPLOAD = ROOT / "upload_codex"
PACKAGES = UPLOAD / "PUBLISH_PACKAGES"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sections_from_captions(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip().strip("-").strip()
    return sections


def clean_youtube_description(value: str) -> str:
    """Remove long-form-only timestamps from the Shorts upload copy."""
    if not value:
        return ""
    value = re.sub(
        r"(?ms)^▶\s*타임스탬프\s*$.*?(?=^▶\s*|\Z)",
        "",
        value,
    )
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    if "#Shorts" not in value and "#shorts" not in value:
        value = value.rstrip() + "\n\n#Shorts"
    return value


def clean_title(value: str, fallback: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if not value:
        value = fallback
    return value[:100].rstrip()


def script_data(slug: str) -> dict:
    path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def preferred_title(slug: str, data: dict) -> str:
    return clean_title(
        str(data.get("video_title") or data.get("title_short") or data.get("title") or ""),
        slug.replace("_", " "),
    )


def link_or_copy(src: Path, dst: Path) -> str:
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def source_line(path: Path) -> str:
    if not path.exists():
        return f"- missing: {path}"
    modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    return f"- {path} | modified={modified} | bytes={path.stat().st_size}"


def package_for(video: Path, slug: str, date_text: str | None = None) -> Path:
    if not video.exists():
        raise FileNotFoundError(f"video missing: {video}")

    date_text = date_text or datetime.now().strftime("%Y%m%d")
    package = PACKAGES / f"{date_text}_{slug}"
    package.mkdir(parents=True, exist_ok=True)

    captions_path = CARDNEWS_OUTPUT / slug / "captions.md"
    script_path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    captions = read_text(captions_path)
    sections = sections_from_captions(captions)
    data = script_data(slug)
    title = preferred_title(slug, data)

    instagram = sections.get("3") or captions
    youtube_description = clean_youtube_description(sections.get("4") or captions)
    tiktok = sections.get("5") or instagram
    youtube = f"[TITLE]\n{title}\n\n[DESCRIPTION]\n{youtube_description}"

    master = package / "video_master_9x16.mp4"
    master_mode = link_or_copy(video, master)

    write_text(package / "youtube_title.txt", title)
    write_text(package / "youtube_description.txt", youtube_description)
    write_text(package / "youtube.txt", youtube)
    write_text(package / "instagram.txt", instagram)
    write_text(package / "tiktok.txt", tiktok)
    write_text(
        package / "publish_checklist.txt",
        """PhoneSpot Codex publish checklist

[Common]
- Watch the final MP4 once before upload.
- Confirm the first two seconds and the fixed CTA.
- Confirm source text, dates, and numbers.

[YouTube Shorts]
- Upload video_master_9x16.mp4.
- Copy youtube_title.txt and youtube_description.txt.
- Select a readable frame in the YouTube mobile app if needed.

[Instagram Reels]
- Upload video_master_9x16.mp4.
- Copy instagram.txt.
- V1 has no separate cover export yet. Select a readable frame manually.

[TikTok]
- Upload video_master_9x16.mp4.
- Copy tiktok.txt.
- Select a readable frame manually.
""",
    )
    write_text(
        package / "cover_frame_guide.txt",
        """Cover export is intentionally deferred in V1.

Use a readable frame from the rendered video when publishing.
The next optional experiment can add:
1. a dedicated 1080x1920 master cover
2. an Instagram 420x654 cover crop
3. an embedded selectable cover frame near the beginning of the video
""",
    )
    write_text(
        package / "README_FIRST.txt",
        """PhoneSpot Codex three-channel publish package V1

Start here:
1. Open video_master_9x16.mp4 and review it.
2. Open the text file for the channel you are uploading to.
3. Follow publish_checklist.txt.

This V1 package does not modify the rendered video.
""",
    )

    illustration_md = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.md"
    illustration_json = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.json"
    for source in (captions_path, script_path, illustration_md, illustration_json):
        if source.exists():
            shutil.copy2(source, package / source.name)

    manifest = "\n".join(
        [
            "PhoneSpot Codex source manifest",
            f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
            f"- slug: {slug}",
            f"- package: {package}",
            f"- video_sha256: {sha256(master)}",
            f"- master_mode: {master_mode}",
            "",
            "[Sources]",
            source_line(video),
            source_line(captions_path),
            source_line(script_path),
            source_line(illustration_md),
            source_line(illustration_json),
        ]
    )
    write_text(package / "source_manifest.txt", manifest)
    write_json(
        package / "publish.json",
        {
            "version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "slug": slug,
            "title": title,
            "master_video": "video_master_9x16.mp4",
            "master_mode": master_mode,
            "master_video_sha256": sha256(master),
            "channels": {
                "youtube_shorts": {
                    "video": "video_master_9x16.mp4",
                    "title": "youtube_title.txt",
                    "description": "youtube_description.txt",
                },
                "instagram_reels": {
                    "video": "video_master_9x16.mp4",
                    "caption": "instagram.txt",
                },
                "tiktok": {
                    "video": "video_master_9x16.mp4",
                    "caption": "tiktok.txt",
                },
            },
            "cover": {
                "status": "manual-frame-selection-v1",
                "guide": "cover_frame_guide.txt",
            },
        },
    )
    print(f"[publish-package] package: {package}")
    print(f"[publish-package] master: {master.name} ({master_mode})")
    print("[publish-package] channels: youtube-shorts, instagram-reels, tiktok")
    return package


def latest_video() -> Path | None:
    candidates = [
        path
        for path in OUT_CODEX.glob("*_codex_remotion*.mp4")
        if "_raw" not in path.parts and "_raw" not in path.name
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def infer_slug(video: Path) -> str:
    name = video.stem
    match = re.match(r"(.+)_\d{8}_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    raise ValueError(f"could not infer slug from: {video.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("date", nargs="?")
    parser.add_argument("--latest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.latest:
        video = latest_video()
        if not video:
            print("[ERROR] No Codex Remotion output found.")
            return 1
        slug = args.slug or infer_slug(video)
        package_for(video, slug)
        return 0
    if not args.video or not args.slug:
        print("[ERROR] Usage: publish_codex_package.py VIDEO SLUG [YYYYMMDD]")
        print("        publish_codex_package.py --latest")
        return 1
    package_for(Path(args.video), args.slug, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


BUTTON_13 = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0..\shorts"
python scripts\publish_codex_package.py --latest
if errorlevel 1 (
  echo.
  echo [ERROR] Publish package refresh failed.
  pause
  exit /b 1
)
echo.
echo [OK] Latest publish package refreshed.
pause
'''


BUTTON_14 = r'''@echo off
chcp 65001 > nul
if not exist "%~dp0..\upload_codex\PUBLISH_PACKAGES" mkdir "%~dp0..\upload_codex\PUBLISH_PACKAGES"
start "" "%~dp0..\upload_codex\PUBLISH_PACKAGES"
'''


RUNNER_BLOCK = r'''
echo.
echo ----- Publish package V1: YouTube + Instagram + TikTok -----
python scripts\publish_codex_package.py "!OUTFILE!" "!SLUG!" "!DATE!"
if errorlevel 1 (
    echo  [WARN] Publish package generation failed. Flat MP4 remains available.
)
'''


README_APPEND = r'''

Three-channel publish package V1:
13. Run 13_REFRESH_LATEST_PUBLISH_PACKAGE.bat to rebuild the package for the latest Codex MP4.
14. Run 14_OPEN_PUBLISH_PACKAGES.bat to open copy-ready YouTube, Instagram, and TikTok files.
Normal renders also build the package automatically.
V1 does not modify the rendered MP4 or generate a cover image.
'''


BASELINE_APPEND = r'''

## Three-channel publish package V1

- A successful Codex render also creates `upload_codex/PUBLISH_PACKAGES/YYYYMMDD_<slug>/`.
- V1 never modifies the rendered MP4.
- One 1080x1920 H.264 master is shared by YouTube Shorts, Instagram Reels, and TikTok.
- Platform copy is separated into `youtube.txt`, `instagram.txt`, and `tiktok.txt`.
- YouTube long-form timestamp blocks are removed from the Shorts upload copy.
- Cover generation is deferred to a separate experiment.
- Desk buttons 13 and 14 refresh or open packages.
'''


def backup(path: Path, label: str = "publish_v1") -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_{label}_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def install_script() -> None:
    target = SCRIPTS / "publish_codex_package.py"
    if target.exists() and target.read_text(encoding="utf-8", errors="replace") == PUBLISH_SCRIPT.rstrip() + "\n":
        print("[skip] publish script already installed")
        return
    backup(target)
    write(target, PUBLISH_SCRIPT)
    py_compile.compile(str(target), doraise=True)


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8", errors="replace")
    if "Publish package V1: YouTube + Instagram + TikTok" in text:
        print("[skip] runner already builds publish package V1")
        return
    anchor = "\necho.\necho ============================================================\necho  DONE. Result: !OUTFILE!"
    if anchor not in text:
        raise RuntimeError("runner patch anchor missing")
    backup(RUNNER)
    text = text.replace(anchor, RUNNER_BLOCK.rstrip() + anchor, 1)
    write(RUNNER, text)


def install_buttons() -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    write(DESK / "13_REFRESH_LATEST_PUBLISH_PACKAGE.bat", BUTTON_13)
    write(DESK / "14_OPEN_PUBLISH_PACKAGES.bat", BUTTON_14)


def append_once(path: Path, marker: str, value: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if marker in text:
        print(f"[skip] already documented: {path}")
        return
    backup(path)
    write(path, text.rstrip() + "\n" + value.strip() + "\n")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Publish Package V1")
    print(" YouTube Shorts + Instagram Reels + TikTok")
    print("============================================================")
    if RUNNER.exists() and "DONE. Result folder: !RESULTDIR!" in RUNNER.read_text(encoding="utf-8", errors="replace"):
        print("[skip] Single-folder result package V2 is active.")
        print("[info] V1 is deprecated and will not overwrite the V2 layout.")
        return 0
    if not RUNNER.exists():
        raise RuntimeError(f"runner missing: {RUNNER}")
    install_script()
    patch_runner()
    install_buttons()
    append_once(DESK_README, "Three-channel publish package V1:", README_APPEND)
    append_once(BASELINE, "## Three-channel publish package V1", BASELINE_APPEND)
    print("[OK] Publish package V1 installed.")
    print(f"[desk] {DESK / '13_REFRESH_LATEST_PUBLISH_PACKAGE.bat'}")
    print(f"[desk] {DESK / '14_OPEN_PUBLISH_PACKAGES.bat'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
