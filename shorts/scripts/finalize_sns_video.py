# -*- coding: utf-8 -*-
"""Finalize a Remotion-rendered MP4 into an SNS/player-compatible file.

Codex Update 01 final default:
  H.264 / yuv420p / BT.709 / AAC 192k
  Balanced target around 1.5Mbps video with a 2.2Mbps ceiling.

Why:
  The earlier 6Mbps test had little visible benefit for mostly static graphic
  shorts. This balanced preset gives a modest sharpness/bitrate lift while
  keeping file size and SNS compatibility reasonable.

Optional comparison presets remain available:
  CODEX_EXPORT_PRESET=high      -> H.264 high bitrate comparison
  CODEX_EXPORT_PRESET=h265-2x   -> H.265 comparison only
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def find_ffmpeg() -> str | None:
    candidates = [
        ROOT / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe",
        shutil.which("ffmpeg"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def common_prefix(ffmpeg: str, src: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-vf",
        "scale=1080:1920:in_range=pc:out_range=tv,format=yuv420p",
        "-color_range",
        "tv",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
    ]


def h264_balanced_args() -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-b:v",
        "1500k",
        "-maxrate",
        "2200k",
        "-bufsize",
        "4400k",
        "-preset",
        "medium",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]


def h264_high_args() -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-b:v",
        "6000k",
        "-maxrate",
        "8000k",
        "-bufsize",
        "12000k",
        "-preset",
        "medium",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]


def h265_2x_args() -> list[str]:
    return [
        "-c:v",
        "libx265",
        "-b:v",
        "2200k",
        "-minrate",
        "1800k",
        "-maxrate",
        "2600k",
        "-bufsize",
        "5200k",
        "-preset",
        "medium",
        "-tag:v",
        "hvc1",
        "-x265-params",
        "log-level=error:keyint=60:min-keyint=30:scenecut=40",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]


def export_args(preset: str) -> tuple[str, list[str]]:
    if preset in {"high", "highbitrate", "sns-high"}:
        return "H.264 HIGH comparison (target 6Mbps)", h264_high_args()
    if preset in {"h265-2x", "hevc-2x", "h265_2x"}:
        return "H.265 2X comparison (target 2.2Mbps)", h265_2x_args()
    return "H.264 BALANCED default (target 1.5Mbps, max 2.2Mbps)", h264_balanced_args()


def main() -> int:
    if len(sys.argv) < 3:
        print("[ERROR] Usage: python scripts/finalize_sns_video.py input.mp4 output.mp4")
        return 1

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    if not src.exists():
        print(f"[ERROR] Raw render not found: {src}")
        return 1

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[ERROR] FFmpeg not found. Run npm install in shorts first.")
        return 1

    preset = (os.environ.get("CODEX_EXPORT_PRESET") or "balanced").strip().lower()
    label, args = export_args(preset)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.mp4")
    if tmp.exists():
        tmp.unlink()

    cmd = common_prefix(ffmpeg, src) + args + [str(tmp)]
    print(f"[INFO] Finalizing MP4: {label}")
    subprocess.run(cmd, check=True)

    if dst.exists():
        dst.unlink()
    tmp.rename(dst)
    print(f"[OK] Final MP4: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
