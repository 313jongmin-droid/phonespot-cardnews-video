"""
Lightweight post-render quality check.
Checks compatibility first. Low bitrate is not automatically bad for static
graphic shorts because H.264 can compress them very efficiently.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def find_ffmpeg() -> str | None:
    candidates = [
        ROOT / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe",
        shutil.which("ffmpeg"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("[WARN] verify_video_quality.py requires mp4 path")
        return 0

    video = Path(sys.argv[1])
    if not video.exists():
        print(f"[WARN] video not found: {video}")
        return 0

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[WARN] ffmpeg not found; skip quality check")
        return 0

    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    text = (proc.stderr or "") + (proc.stdout or "")

    video_line = ""
    for line in text.splitlines():
        if "Video:" in line:
            video_line = line.strip()
            break

    bitrate_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", text)
    bitrate = int(bitrate_match.group(1)) if bitrate_match else None
    pix_fmt = "unknown"
    if " yuv420p" in video_line:
        pix_fmt = "yuv420p"
    elif " yuvj420p" in video_line:
        pix_fmt = "yuvj420p"

    size_mb = video.stat().st_size / (1024 * 1024)
    print()
    print("----- Quality check -----")
    print(f"File      : {video}")
    print(f"Size      : {size_mb:.1f} MB")
    if bitrate:
        print(f"Bitrate   : {bitrate} kb/s")
    print(f"Pixel fmt : {pix_fmt}")

    warnings: list[str] = []
    notes: list[str] = []

    if pix_fmt != "yuv420p":
        warnings.append("Pixel format is not yuv420p. Run SNS finalize step before upload.")

    if bitrate and bitrate < 700:
        notes.append("Low bitrate can be normal for mostly static graphic shorts. Judge visual sharpness, not bitrate alone.")
    if size_mb < 4:
        notes.append("Small file size can be normal for static screens after CRF encoding.")

    if warnings:
        for warning in warnings:
            print(f"[WARN] {warning}")
    else:
        print("[OK] SNS/player compatibility baseline passed.")

    for note in notes:
        print(f"[INFO] {note}")

    print("-------------------------")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
