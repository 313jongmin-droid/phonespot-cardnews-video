"""
Generate TTS audio for public/shorts_script.json using edge-tts.

Codex TTS quality layer:
- Keeps authored narration unchanged in shorts_script.json.
- Applies an editable pronunciation dictionary only to the spoken copy.
- Saves edge-tts WordBoundary metadata.
- Adds optional chunk timing weights to the runtime public JSON.
- Cleans stale audio from older scripts before rendering.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import edge_tts
except ImportError:
    print("[ERROR] edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

VOICE = os.getenv("PHONESPOT_TTS_VOICE", "ko-KR-SunHiNeural")
RATE = os.getenv("PHONESPOT_TTS_RATE", "+42%")
VOLUME = os.getenv("PHONESPOT_TTS_VOLUME", "+0%")
PITCH = os.getenv("PHONESPOT_TTS_PITCH", "+0Hz")
LOUDNORM = os.getenv("PHONESPOT_TTS_LOUDNORM", "1") != "0"
MIN_CHUNK_MS = int(os.getenv("PHONESPOT_TTS_MIN_CHUNK_MS", "1100"))

project_root = Path(__file__).parent.parent
script_path = project_root / "public" / "shorts_script.json"
audio_dir = project_root / "public" / "audio"
config_path = project_root / "config" / "tts_pronunciation.json"
manifest_path = audio_dir / "tts_manifest.json"
audio_dir.mkdir(parents=True, exist_ok=True)


def find_ffmpeg() -> str | None:
    candidates = [
        project_root / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe",
        shutil.which("ffmpeg"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def normalize_audio(path: Path) -> None:
    if not LOUDNORM:
        return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("           WARN ffmpeg not found; skip loudness normalize")
        return
    tmp = path.with_suffix(".raw.mp3")
    path.replace(tmp)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(tmp),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar",
        "48000",
        "-b:a",
        "192k",
        str(path),
    ]
    try:
        subprocess.run(cmd, check=True)
        tmp.unlink(missing_ok=True)
    except Exception as exc:
        print(f"           WARN loudness normalize failed: {exc}")
        if path.exists():
            path.unlink(missing_ok=True)
        tmp.replace(path)


def load_dictionary() -> list[dict[str, Any]]:
    if not config_path.exists():
        return []
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return [entry for entry in data.get("entries", []) if entry.get("enabled", True)]


def apply_pronunciation(text: str, entries: list[dict[str, Any]]) -> tuple[str, list[str]]:
    spoken = text
    applied: list[str] = []
    for entry in entries:
        match = str(entry.get("match", ""))
        replacement = str(entry.get("spoken", ""))
        if not match or not replacement:
            continue
        if entry.get("regex"):
            flags = re.IGNORECASE if entry.get("ignore_case") else 0
            updated, count = re.subn(match, replacement, spoken, flags=flags)
        elif entry.get("ignore_case"):
            updated, count = re.subn(re.escape(match), replacement, spoken, flags=re.IGNORECASE)
        else:
            count = spoken.count(match)
            updated = spoken.replace(match, replacement)
        if count:
            applied.append(match)
            spoken = updated
    return spoken, applied


def load_word_boundaries(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") != "WordBoundary":
            continue
        offset_ms = max(0.0, float(item.get("offset", 0)) / 10000.0)
        duration_ms = max(0.0, float(item.get("duration", 0)) / 10000.0)
        items.append(
            {
                "offset_ms": round(offset_ms, 2),
                "duration_ms": round(duration_ms, 2),
                "text": str(item.get("text", "")),
            }
        )
    return items


def text_weight(value: str) -> int:
    return max(1, len(re.sub(r"\s+", "", value or "")))


def build_chunk_timing(chunks: list[str], boundaries: list[dict[str, Any]]) -> dict[str, Any]:
    safe_chunks = [str(chunk).strip() for chunk in chunks if str(chunk).strip()] or [""]
    fallback_weights = [text_weight(chunk) for chunk in safe_chunks]
    if not boundaries:
        return {
            "mode": "character_weight_fallback",
            "weights": fallback_weights,
            "windows": [],
            "boundary_count": 0,
        }

    total_ms = max(
        float(item["offset_ms"]) + float(item["duration_ms"])
        for item in boundaries
    )
    if len(safe_chunks) == 1 or total_ms <= 0:
        return {
            "mode": "word_boundary_snap",
            "weights": [max(1.0, total_ms)],
            "windows": [{"start_ms": 0.0, "end_ms": round(total_ms, 2), "duration_ms": round(total_ms, 2)}],
            "boundary_count": len(boundaries),
        }

    cumulative_weights: list[int] = []
    running = 0
    for weight in fallback_weights:
        running += weight
        cumulative_weights.append(running)
    total_weight = cumulative_weights[-1] or 1

    offsets = sorted({float(item["offset_ms"]) for item in boundaries if float(item["offset_ms"]) > 0})
    min_ms = MIN_CHUNK_MS if total_ms >= len(safe_chunks) * MIN_CHUNK_MS else max(300, int(total_ms / len(safe_chunks) * 0.58))
    cuts = [0.0]

    for idx in range(len(safe_chunks) - 1):
        target = total_ms * cumulative_weights[idx] / total_weight
        remaining_chunks = len(safe_chunks) - idx - 1
        low = cuts[-1] + min_ms
        high = total_ms - remaining_chunks * min_ms
        allowed = [value for value in offsets if low <= value <= high]
        if allowed:
            chosen = min(allowed, key=lambda value: abs(value - target))
        else:
            chosen = max(cuts[-1] + 1.0, min(target, total_ms - remaining_chunks))
        cuts.append(chosen)
    cuts.append(total_ms)

    windows: list[dict[str, float]] = []
    weights: list[float] = []
    for start, end in zip(cuts, cuts[1:]):
        duration = max(1.0, end - start)
        windows.append(
            {
                "start_ms": round(start, 2),
                "end_ms": round(end, 2),
                "duration_ms": round(duration, 2),
            }
        )
        weights.append(round(duration, 2))
    return {
        "mode": "word_boundary_snap",
        "weights": weights,
        "windows": windows,
        "boundary_count": len(boundaries),
        "min_chunk_ms": min_ms,
    }


def section_jobs(script: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    jobs: list[tuple[str, dict[str, Any]]] = [("hook", script["hook"])]
    for idx, fact in enumerate(script.get("facts", []), 1):
        jobs.append((f"fact_{idx}", fact))
    jobs.append(("cta", script["cta"]))
    return jobs


def clean_stale_audio(valid_keys: set[str]) -> None:
    removed: list[str] = []
    for path in audio_dir.glob("*.mp3"):
        if path.stem not in valid_keys:
            removed.append(path.name)
            path.unlink(missing_ok=True)
    for path in audio_dir.glob("*.metadata.jsonl"):
        if path.name.removesuffix(".metadata.jsonl") not in valid_keys:
            path.unlink(missing_ok=True)
    if removed:
        print(f"Removed stale audio: {', '.join(sorted(removed))}")


if not script_path.exists():
    print("[ERROR] shorts_script.json not found. Run copy_assets.py first.")
    sys.exit(1)

script = json.loads(script_path.read_text(encoding="utf-8"))
entries = load_dictionary()
jobs = section_jobs(script)
clean_stale_audio({key for key, _ in jobs})


async def gen_one(key: str, section: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    original = str(section.get("tts", "")).strip()
    spoken, applied = apply_pronunciation(original, entries)
    out = audio_dir / f"{key}.mp3"
    metadata = audio_dir / f"{key}.metadata.jsonl"
    metadata.unlink(missing_ok=True)

    try:
        comm = edge_tts.Communicate(
            spoken,
            voice=VOICE,
            rate=RATE,
            volume=VOLUME,
            pitch=PITCH,
            boundary="WordBoundary",
        )
    except TypeError:
        # Older edge-tts versions still render normally. Metadata falls back.
        comm = edge_tts.Communicate(spoken, voice=VOICE, rate=RATE, volume=VOLUME, pitch=PITCH)
    await comm.save(str(out), str(metadata))
    normalize_audio(out)

    boundaries = load_word_boundaries(metadata)
    timing = build_chunk_timing(section.get("caption_chunks", []) or [], boundaries)
    section["tts_chunk_weights"] = timing["weights"]
    section["_tts_timing"] = {
        key: value
        for key, value in timing.items()
        if key != "weights"
    }
    return out, {
        "key": key,
        "original_tts": original,
        "spoken_tts": spoken,
        "dictionary_applied": applied,
        "timing": timing,
    }


async def main() -> None:
    print(f"Voice: {VOICE}")
    print(f"Rate : {RATE}")
    print(f"Pitch: {PITCH}")
    print(f"Loudness normalize: {'on' if LOUDNORM else 'off'}")
    print(f"Pronunciation dictionary: {len(entries)} entries")
    print(f"Output: {audio_dir}")
    print(f"Jobs: {len(jobs)}")
    print()

    manifest: dict[str, Any] = {
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "loudness_normalize": LOUDNORM,
        "pronunciation_dictionary": str(config_path),
        "jobs": [],
    }
    for idx, (key, section) in enumerate(jobs, 1):
        original = str(section.get("tts", ""))
        preview = original[:36].replace("\n", " ")
        print(f"[{idx}/{len(jobs)}] {key:8} ({preview}...)")
        try:
            out, report = await gen_one(key, section)
            manifest["jobs"].append(report)
            size = out.stat().st_size
            timing = report["timing"]
            applied = ", ".join(report["dictionary_applied"]) or "-"
            print(f"           OK  {size:,} bytes | {timing['mode']} | dict: {applied}")
        except Exception as exc:
            print(f"           FAIL {exc}")
            sys.exit(1)

    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nDone. {len(jobs)} mp3 files saved to {audio_dir}")
    print(f"Timing manifest: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
