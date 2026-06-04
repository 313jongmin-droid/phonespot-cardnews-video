# -*- coding: utf-8 -*-
"""Create one copy-ready result folder for a Codex short.

V2 keeps exactly one active MP4 per render result folder.
The MP4 filename matches its parent folder:
  CODEX_VIDEO_DESK/RESULTS/<render-key>/<render-key>.mp4

Channel copy, checklist, source notes, and optional illustration requests are
written beside the MP4. The rendered MP4 is never re-encoded by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS_OUTPUT = ROOT / "cardnews" / "output"
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RESULTS = DESK / "RESULTS"


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
    if not value:
        return ""
    value = re.sub(r"(?ms)^▶\s*타임스탬프\s*$.*?(?=^▶\s*|\Z)", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    if "#Shorts" not in value and "#shorts" not in value:
        value = value.rstrip() + "\n\n#Shorts"
    return value


def clean_title(value: str, fallback: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip() or fallback
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


def source_line(path: Path) -> str:
    if not path.exists():
        return f"- missing: {path}"
    modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    return f"- {path} | modified={modified} | bytes={path.stat().st_size}"


def link_or_copy(src: Path, dst: Path) -> str:
    if src.resolve() == dst.resolve():
        return "in-place"
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def result_video_path(package: Path) -> Path:
    return package / f"{package.name}.mp4"


def is_result_master(video: Path) -> bool:
    try:
        return video.parent.parent.resolve() == RESULTS.resolve() and video == result_video_path(video.parent)
    except OSError:
        return False


def unique_package(slug: str, date_text: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    key = f"{date_text}_{slug}_codex_remotion"
    package = RESULTS / key
    if not result_video_path(package).exists():
        return package
    return RESULTS / f"{key}_{datetime.now().strftime('%H%M%S')}"


def package_for(video: Path, slug: str, date_text: str | None = None) -> Path:
    video = video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"video missing: {video}")

    date_text = date_text or datetime.now().strftime("%Y%m%d")
    package = video.parent if is_result_master(video) else unique_package(slug, date_text)
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
    master = result_video_path(package)
    master_mode = link_or_copy(video, master)

    for obsolete in (
        "youtube_title.txt",
        "youtube_description.txt",
        "youtube.txt",
        "instagram.txt",
        "tiktok.txt",
        "publish_checklist.txt",
        "README_FIRST.txt",
    ):
        path = package / obsolete
        if path.exists():
            path.unlink()

    write_text(
        package / "UPLOAD_COPY.txt",
        f"""폰스팟 SNS 업로드 문구

사용 순서
1. 결과 폴더와 이름이 같은 MP4를 한 번 확인합니다.
2. 업로드할 채널 구역만 복사합니다.
3. 첫 2초, 날짜, 숫자, 고정 CTA를 확인합니다.

============================================================
YOUTUBE SHORTS
============================================================

[제목]
{title}

[설명]
{youtube_description}

============================================================
INSTAGRAM REELS
============================================================

{instagram}

============================================================
TIKTOK
============================================================

{tiktok}
""",
    )

    illustration_md = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.md"
    illustration_json = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.json"
    for source in (captions_path, script_path, illustration_md, illustration_json):
        if source.exists():
            shutil.copy2(source, package / source.name)

    write_text(
        package / "source_manifest.txt",
        "\n".join(
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
        ),
    )
    write_json(
        package / "publish.json",
        {
            "version": 2,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "slug": slug,
            "title": title,
            "master_video": master.name,
            "upload_copy": "UPLOAD_COPY.txt",
            "master_mode": master_mode,
            "master_video_sha256": sha256(master),
            "channels": {
                "youtube_shorts": {
                    "video": master.name,
                    "copy_source": "UPLOAD_COPY.txt#YOUTUBE SHORTS",
                },
                "instagram_reels": {"video": master.name, "copy_source": "UPLOAD_COPY.txt#INSTAGRAM REELS"},
                "tiktok": {"video": master.name, "copy_source": "UPLOAD_COPY.txt#TIKTOK"},
            },
        },
    )
    print(f"[result-package-v2] folder: {package}")
    print(f"[result-package-v2] master: {master.name} ({master_mode})")
    return package


def latest_video() -> Path | None:
    current = [
        path
        for path in RESULTS.glob("*/*.mp4")
        if path == result_video_path(path.parent)
    ]
    if current:
        return max(current, key=lambda path: path.stat().st_mtime)
    return None


def infer_slug(video: Path) -> str:
    if video.parent.parent.resolve() == RESULTS.resolve():
        name = video.parent.name
    else:
        name = video.stem
    match = re.match(r"\d{8}_(.+)_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    match = re.match(r"(.+)_\d{8}_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    raise ValueError(f"could not infer slug from: {video}")


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
            print("[ERROR] No Codex Remotion result found.")
            return 1
        package_for(video, args.slug or infer_slug(video))
        return 0
    if not args.video or not args.slug:
        print("[ERROR] Usage: publish_codex_package.py VIDEO SLUG [YYYYMMDD]")
        print("        publish_codex_package.py --latest")
        return 1
    package_for(Path(args.video), args.slug, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
