from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


GENERATE_TTS = r'''"""
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
MIN_CHUNK_MS = int(os.getenv("PHONESPOT_TTS_MIN_CHUNK_MS", "900"))

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
'''


VERIFY_TTS_TIMING = r'''"""Validate runtime-only TTS pronunciation and chunk timing metadata."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "public" / "shorts_script.json"
MANIFEST = ROOT / "public" / "audio" / "tts_manifest.json"


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    if not SCRIPT.exists() or not MANIFEST.exists():
        message = "[WARN] TTS timing metadata missing; generate TTS first."
        print(message)
        return 0 if args.allow_missing else 1

    data = json.loads(SCRIPT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    for key, section in sections(data):
        chunks = [str(value).strip() for value in section.get("caption_chunks", []) or [] if str(value).strip()]
        weights = section.get("tts_chunk_weights", []) or []
        timing = section.get("_tts_timing", {}) or {}
        if chunks and len(weights) != len(chunks):
            errors.append(f"{key}: timing weight count {len(weights)} != chunk count {len(chunks)}")
            continue
        if any(float(value) <= 0 for value in weights):
            errors.append(f"{key}: timing weight must be positive")
        if timing.get("mode") == "character_weight_fallback":
            warnings.append(f"{key}: WordBoundary unavailable; character-weight fallback active")
        for idx, value in enumerate(weights, 1):
            if float(value) < 600:
                warnings.append(f"{key}.chunk[{idx}]: short visible window {float(value):.0f}ms")

    print()
    print("----- TTS timing check -----")
    print(f"Manifest : {MANIFEST}")
    print(f"Jobs     : {len(manifest.get('jobs', []))}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] pronunciation copy and chunk timing metadata passed.")
    print("----------------------------")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


DEFAULT_DICTIONARY = {
    "version": 1,
    "description": "Applied only to the spoken TTS copy. Screen captions and authored narration remain unchanged.",
    "entries": [
        {"match": "WWDC", "spoken": "더블유 더블유 디 씨"},
        {"match": "iOS", "spoken": "아이 오 에스"},
        {"match": "NFC", "spoken": "엔 에프 씨"},
        {"match": "RCS", "spoken": "알 씨 에스"},
        {"match": "OIS", "spoken": "오 아이 에스"},
        {"match": "USB-C", "spoken": "유 에스 비 씨"},
        {"match": "Gemini", "spoken": "제미나이"},
        {"match": "Siri", "spoken": "시리"},
        {"match": "SKT", "spoken": "에스 케이 티"},
        {"match": "KT", "spoken": "케이 티"},
        {"match": "LGU+", "spoken": "엘지 유플러스"},
        {"match": "IP68", "spoken": "아이 피 육십팔"},
        {"match": "IP67", "spoken": "아이 피 육십칠"},
        {"match": "mAh", "spoken": "밀리암페어아워"},
        {"match": "AI", "spoken": "에이 아이"},
        {"match": "5G", "spoken": "파이브 지"},
        {"match": "LTE", "spoken": "엘 티 이"},
    ],
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_tts_timing_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[skip] {label} already installed")
        return text
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {label}")
    print(f"[patch] {label}")
    return text.replace(old, new, 1)


def patch_chunk_util() -> None:
    path = SHORTS / "src" / "components" / "casual" / "chunkUtil.ts"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "export function getChunkWindows(chunks: string[], durFrames: number) {\n"
        "  const clean = chunks && chunks.length ? chunks : [\"\"];\n"
        "  const weights = clean.map((chunk) => Math.max(1, countChars(chunk)));",
        "export function getChunkWindows(chunks: string[], durFrames: number, timingWeights?: number[]) {\n"
        "  const clean = chunks && chunks.length ? chunks : [\"\"];\n"
        "  const hasTimingWeights =\n"
        "    timingWeights?.length === clean.length && timingWeights.every((value) => Number.isFinite(value) && value > 0);\n"
        "  const weights = hasTimingWeights\n"
        "    ? timingWeights!.map((value) => Math.max(1, value))\n"
        "    : clean.map((chunk) => Math.max(1, countChars(chunk)));",
        "chunkUtil weighted windows",
    )
    text = replace_once(
        text,
        "export function getChunkWindow(chunks: string[], idx: number, durFrames: number) {\n"
        "  const windows = getChunkWindows(chunks, durFrames);",
        "export function getChunkWindow(chunks: string[], idx: number, durFrames: number, timingWeights?: number[]) {\n"
        "  const windows = getChunkWindows(chunks, durFrames, timingWeights);",
        "chunkUtil getChunkWindow timing",
    )
    text = replace_once(
        text,
        "export function chunkIndexFromList(chunks: string[], frame: number, durFrames: number) {\n"
        "  const windows = getChunkWindows(chunks, durFrames);",
        "export function chunkIndexFromList(chunks: string[], frame: number, durFrames: number, timingWeights?: number[]) {\n"
        "  const windows = getChunkWindows(chunks, durFrames, timingWeights);",
        "chunkUtil chunkIndex timing",
    )
    if text != original:
        backup(path)
        write_text(path, text)


def patch_casual_caption() -> None:
    path = SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "  emphasisWords?: string[];\n  durFrames: number;",
        "  emphasisWords?: string[];\n  timingWeights?: number[];\n  durFrames: number;",
        "CasualCaption prop",
    )
    text = replace_once(
        text,
        "  emphasisWords = [],\n  durFrames,",
        "  emphasisWords = [],\n  timingWeights,\n  durFrames,",
        "CasualCaption destructure",
    )
    text = replace_once(
        text,
        "  const idx = chunkIndexFromList(list, frame, durFrames);",
        "  const idx = chunkIndexFromList(list, frame, durFrames, timingWeights);",
        "CasualCaption weighted index",
    )
    if text != original:
        backup(path)
        write_text(path, text)


def patch_casual_card() -> None:
    path = SHORTS / "src" / "components" / "casual" / "CasualCard.tsx"
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_once(
        text,
        "  display_chunks?: string[];\n  chunk_visuals?: ChunkVisual[];",
        "  display_chunks?: string[];\n  tts_chunk_weights?: number[];\n  chunk_visuals?: ChunkVisual[];",
        "CasualCard runtime timing field",
    )
    text = replace_once(
        text,
        "  const chunkIdx = chunkIndexFromList(data.caption_chunks, frame, durFrames);\n"
        "  const chunkWindow = getChunkWindow(data.caption_chunks, chunkIdx, durFrames);",
        "  const chunkIdx = chunkIndexFromList(data.caption_chunks, frame, durFrames, data.tts_chunk_weights);\n"
        "  const chunkWindow = getChunkWindow(data.caption_chunks, chunkIdx, durFrames, data.tts_chunk_weights);",
        "CasualCard weighted visual timing",
    )
    text = replace_once(
        text,
        "        emphasisWords={data.caption_emphasis}\n        durFrames={durFrames}",
        "        emphasisWords={data.caption_emphasis}\n        timingWeights={data.tts_chunk_weights}\n        durFrames={durFrames}",
        "CasualCard caption timing",
    )
    if text != original:
        backup(path)
        write_text(path, text)


def patch_runner() -> None:
    path = SHORTS / "run_codex_casual.bat"
    text = path.read_text(encoding="utf-8")
    original = text
    verify_block = (
        "python scripts\\generate_tts.py\n"
        "if errorlevel 1 goto :fail\n"
        "python scripts\\verify_tts_timing.py\n"
        "if errorlevel 1 goto :fail"
    )
    old = "python scripts\\generate_tts.py\nif errorlevel 1 goto :fail"
    if "python scripts\\verify_tts_timing.py" in text:
        print("[skip] runner already verifies TTS timing")
    elif old in text:
        text = text.replace(old, verify_block, 1)
        print("[patch] runner TTS timing verification")
    else:
        raise RuntimeError("runner patch anchor missing")
    if text != original:
        backup(path)
        write_text(path, text)


def merge_dictionary() -> None:
    path = SHORTS / "config" / "tts_pronunciation.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"version": 1, "description": DEFAULT_DICTIONARY["description"], "entries": []}
    existing = {str(entry.get("match")) for entry in data.get("entries", [])}
    added = 0
    for entry in DEFAULT_DICTIONARY["entries"]:
        if entry["match"] not in existing:
            data.setdefault("entries", []).append(entry)
            added += 1
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"[done] pronunciation dictionary merged: +{added}, total={len(data.get('entries', []))}")


def append_guide() -> None:
    path = SHORTS / "codex" / "CODEX_BASELINE.md"
    marker = "## TTS pronunciation and timing layer"
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        text = "# PhoneSpot Codex baseline\n"
    if marker in text:
        print("[skip] baseline guide already documents TTS layer")
        return
    text += (
        "\n\n## TTS pronunciation and timing layer\n\n"
        "- `config/tts_pronunciation.json` changes the spoken copy only. Authored narration and screen captions remain unchanged.\n"
        "- `generate_tts.py` saves edge-tts WordBoundary metadata and runtime-only `tts_chunk_weights` in `public/shorts_script.json`.\n"
        "- Casual captions and visuals use the same optional timing weights. Missing metadata falls back to the previous character-weight logic.\n"
        "- `verify_tts_timing.py` runs after TTS generation and blocks malformed timing data before rendering.\n"
    )
    write_text(path, text)


def install_desk_buttons() -> None:
    helper = Path(__file__).with_name("INSTALL_CODEX_TTS_DESK_BUTTONS.py")
    if not helper.exists():
        print("[WARN] desk button helper missing; skip desk refresh")
        return
    subprocess.run([sys.executable, str(helper)], check=True)


def run_checks() -> None:
    py_compile.compile(str(SHORTS / "scripts" / "generate_tts.py"), doraise=True)
    py_compile.compile(str(SHORTS / "scripts" / "verify_tts_timing.py"), doraise=True)
    subprocess.run(
        [sys.executable, str(SHORTS / "scripts" / "verify_tts_timing.py"), "--allow-missing"],
        cwd=SHORTS,
        check=True,
    )
    if os.environ.get("PHONESPOT_SKIP_TSC") == "1":
        print("[skip] TypeScript check disabled by PHONESPOT_SKIP_TSC=1")
        return
    subprocess.run(["npx.cmd", "tsc", "--noEmit"], cwd=SHORTS, check=True)
    print("[OK] Python and TypeScript checks passed")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - TTS Pronunciation + Timing Layer")
    print("============================================================")
    print(f"Root: {ROOT}")
    if not SHORTS.exists():
        raise RuntimeError(f"shorts folder not found: {SHORTS}")

    generate_path = SHORTS / "scripts" / "generate_tts.py"
    backup(generate_path)
    write_text(generate_path, GENERATE_TTS)
    write_text(SHORTS / "scripts" / "verify_tts_timing.py", VERIFY_TTS_TIMING)
    merge_dictionary()
    patch_chunk_util()
    patch_casual_caption()
    patch_casual_card()
    patch_runner()
    append_guide()
    install_desk_buttons()
    run_checks()
    print()
    print("[DONE] TTS pronunciation and timing layer installed.")
    print("Next: render one sample with run_codex_casual.bat and listen before accepting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
