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

from codex_chunk_overrides import chunk_signature

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VOICE = os.getenv("PHONESPOT_TTS_VOICE", "ko-KR-SunHiNeural")
RATE = os.getenv("PHONESPOT_TTS_RATE", "+42%")
VOLUME = os.getenv("PHONESPOT_TTS_VOLUME", "+0%")
PITCH = os.getenv("PHONESPOT_TTS_PITCH", "+0Hz")
LOUDNORM = os.getenv("PHONESPOT_TTS_LOUDNORM", "1") != "0"

# --- 슈퍼톤(Sora) TTS + edge-tts 폴백 (2026-07-07) ---
# 엔진: auto=키+크레딧 있으면 슈퍼톤, 실패/부재 시 edge / edge=강제무료 / supertone=강제
TTS_ENGINE = os.getenv("PHONESPOT_TTS_ENGINE", "auto").lower()
def _load_supertone_key() -> str:
    k = os.getenv("SUPERTONE_API_KEY", "").strip()
    if k:
        return k
    try:
        kp = Path(__file__).resolve().parent.parent.parent / "_secrets" / "supertone_key.txt"
        if kp.exists():
            return kp.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


SUPERTONE_KEY = _load_supertone_key()
SUPERTONE_VOICE = os.getenv("PHONESPOT_SUPERTONE_VOICE", "f32a02422bd88da70fddb2")  # Sora
SUPERTONE_STYLE = os.getenv("PHONESPOT_SUPERTONE_STYLE", "friendly")
SUPERTONE_MODEL = os.getenv("PHONESPOT_SUPERTONE_MODEL", "sona_speech_1")
SUPERTONE_SPEED = float(os.getenv("PHONESPOT_SUPERTONE_SPEED", "1.4"))  # edge +42% 대응 (캐주얼 빠른 톤)
SUPERTONE_BASE = "https://supertoneapi.com/v1"


def supertone_enabled() -> bool:
    return TTS_ENGINE in ("auto", "supertone") and bool(SUPERTONE_KEY)


def synth_supertone(spoken: str, out: Path) -> bool:
    """슈퍼톤 REST로 mp3 생성. 성공 True / 실패 False(호출부에서 edge 폴백)."""
    if not SUPERTONE_KEY:
        return False
    try:
        import requests  # type: ignore
    except Exception:
        return False
    url = f"{SUPERTONE_BASE}/text-to-speech/{SUPERTONE_VOICE}"
    headers = {"x-sup-api-key": SUPERTONE_KEY, "Content-Type": "application/json"}
    body = {
        "text": spoken, "language": "ko", "model": SUPERTONE_MODEL,
        "output_format": "mp3", "style": SUPERTONE_STYLE,
        "voice_settings": {"speed": SUPERTONE_SPEED},
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code >= 400 and "style" in body:
            # style 미지원 보이스면 style 빼고 재시도
            b2 = {k: v for k, v in body.items() if k != "style"}
            r = requests.post(url, headers=headers, json=b2, timeout=60)
        r.raise_for_status()
        out.write_bytes(r.content)
        return True
    except Exception as exc:
        print(f"    [supertone] 실패 -> edge-tts 폴백: {exc}")
        return False
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


def timing_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value or ""), flags=re.UNICODE).lower()


def aligned_boundary_cuts(
    chunks: list[str],
    boundaries: list[dict[str, Any]],
    spoken: str,
    pronunciation_entries: list[dict[str, Any]],
) -> list[float]:
    usable = [item for item in boundaries if timing_text(item.get("text", ""))]
    boundary_text = "".join(timing_text(item.get("text", "")) for item in usable)
    spoken_text = timing_text(spoken)
    if boundary_text != spoken_text:
        raise RuntimeError(
            "WordBoundary text does not match spoken TTS; exact chunk timing cannot be guaranteed"
        )

    cumulative: dict[int, float] = {}
    length = 0
    for idx, item in enumerate(usable):
        length += len(timing_text(item.get("text", "")))
        if idx + 1 < len(usable):
            cumulative[length] = float(usable[idx + 1]["offset_ms"])

    cuts: list[float] = []
    for idx in range(1, len(chunks)):
        prefix = " ".join(chunks[:idx])
        spoken_prefix, _ = apply_pronunciation(prefix, pronunciation_entries)
        target = len(timing_text(spoken_prefix))
        if target not in cumulative:
            raise RuntimeError(
                f"chunk {idx} does not end on a TTS WordBoundary; adjust the chunk at a word boundary"
            )
        cuts.append(cumulative[target])
    return cuts


def build_chunk_timing(
    chunks: list[str],
    boundaries: list[dict[str, Any]],
    spoken: str = "",
    pronunciation_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    safe_chunks = [str(chunk).strip() for chunk in chunks if str(chunk).strip()] or [""]
    fallback_weights = [text_weight(chunk) for chunk in safe_chunks]
    if not boundaries:
        return {
            "mode": "character_weight_fallback",
            "weights": fallback_weights,
            "windows": [],
            "boundary_count": 0,
            "caption_signature": chunk_signature(safe_chunks),
        }

    total_ms = max(
        float(item["offset_ms"]) + float(item["duration_ms"])
        for item in boundaries
    )
    if len(safe_chunks) == 1 or total_ms <= 0:
        return {
            "mode": "word_boundary_text_align",
            "weights": [max(1.0, total_ms)],
            "windows": [{"start_ms": 0.0, "end_ms": round(total_ms, 2), "duration_ms": round(total_ms, 2)}],
            "boundary_count": len(boundaries),
            "caption_signature": chunk_signature(safe_chunks),
        }

    try:
        exact_cuts = aligned_boundary_cuts(
            safe_chunks,
            boundaries,
            spoken,
            pronunciation_entries or [],
        )
    except RuntimeError as exc:
        # 단어경계 정렬 불가(날짜·영문 등 TTS 발음 != 글자) → 빌드 실패 대신 글자수 폴백 렌더.
        # 정밀 싱크(B)는 word_boundary 모드에서만 적용; 폴백은 가독바닥 있는 근사 동기화.
        # 완전 정밀을 원하면 기사 청크에서 날짜/영문을 한글로 풀어쓰면 단어경계가 맞는다.
        print(f"    [timing] word-boundary align unavailable -> character_weight fallback ({exc})")
        return {
            "mode": "character_weight_fallback",
            "weights": fallback_weights,
            "windows": [],
            "boundary_count": len(boundaries),
            "caption_signature": chunk_signature(safe_chunks),
        }
    cuts = [0.0, *exact_cuts, total_ms]

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
        "mode": "word_boundary_text_align",
        "weights": weights,
        "windows": windows,
        "boundary_count": len(boundaries),
        "caption_signature": chunk_signature(safe_chunks),
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


def restore_matching_cache(script: dict[str, Any], jobs: list[tuple[str, dict[str, Any]]]) -> bool:
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    expected_settings = {
        "voice": VOICE,
        "rate": RATE,
        "volume": VOLUME,
        "pitch": PITCH,
        "loudness_normalize": LOUDNORM,
        "tts_engine": TTS_ENGINE,
        "supertone_voice": (SUPERTONE_VOICE if supertone_enabled() else ""),
    }
    for key, expected in expected_settings.items():
        default = "+0%" if key == "volume" else None
        if manifest.get(key, default) != expected:
            return False

    reports = {
        str(item.get("key") or ""): item
        for item in manifest.get("jobs", [])
        if item.get("key")
    }
    changed = False
    manifest_changed = False
    for key, section in jobs:
        report = reports.get(key)
        audio = audio_dir / f"{key}.mp3"
        if not report or not audio.exists() or audio.stat().st_size <= 0:
            return False
        original = str(section.get("tts", "")).strip()
        spoken, _ = apply_pronunciation(original, entries)
        if str(report.get("original_tts", "")).strip() != original:
            return False
        if str(report.get("spoken_tts", "")).strip() != spoken:
            return False
        metadata = audio_dir / f"{key}.metadata.jsonl"
        boundaries = load_word_boundaries(metadata) if metadata.exists() else []
        if report.get("engine") != "supertone" and not boundaries:
            return False
        _stored = report.get("timing") or {}
        _safe = [str(c).strip() for c in (section.get("caption_chunks", []) or []) if str(c).strip()] or [""]
        if (report.get("engine") == "supertone"
                and _stored.get("mode") == "word_boundary_text_align"
                and _stored.get("caption_signature") == chunk_signature(_safe)):
            timing = _stored  # whisper 정밀정렬 보존(캐시 재렌더에 char로 덮어쓰지 않음)
        elif report.get("engine") == "supertone":
            # 기존 char 캐시 → 캐시 오디오로 whisper 업그레이드(재synth 없음). 실패=char.
            timing = _whisper_timing(audio_dir / f"{key}.mp3",
                                     section.get("caption_chunks", []) or [], spoken) \
                or build_chunk_timing(section.get("caption_chunks", []) or [], boundaries, spoken, entries)
        else:
            timing = build_chunk_timing(
                section.get("caption_chunks", []) or [],
                boundaries,
                spoken,
                entries,
            )
        if report.get("timing") != timing:
            report["timing"] = timing
            report["caption_signature"] = timing.get("caption_signature")
            manifest_changed = True
        weights = timing.get("weights")
        if not isinstance(weights, list) or not weights:
            return False
        timing_meta = {name: value for name, value in timing.items() if name != "weights"}
        if section.get("tts_chunk_weights") != weights:
            section["tts_chunk_weights"] = weights
            changed = True
        if section.get("_tts_timing") != timing_meta:
            section["_tts_timing"] = timing_meta
            changed = True

    if changed:
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if manifest_changed:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Existing TTS cache matches this script. Reusing {len(jobs)} audio files.")
    return True


if not script_path.exists():
    print("[ERROR] shorts_script.json not found. Run copy_assets.py first.")
    sys.exit(1)

script = json.loads(script_path.read_text(encoding="utf-8"))
entries = load_dictionary()
jobs = section_jobs(script)
clean_stale_audio({key for key, _ in jobs})

if restore_matching_cache(script, jobs):
    sys.exit(0)

try:
    import edge_tts
except ImportError:
    print("[ERROR] This script needs new TTS audio, but edge-tts is not installed.")
    print("[ERROR] Run the render-worker setup once, then retry this job.")
    sys.exit(1)


_WHISPER_MODEL = None


def _whisper_words(mp3_path):
    """faster-whisper로 단어별 (정규화텍스트, 시작ms, 끝ms). 미설치/off/실패면 None → char 근사 폴백."""
    if os.getenv("PHONESPOT_WHISPER_ALIGN", "auto").lower() == "off":
        return None
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return None
    global _WHISPER_MODEL
    try:
        if _WHISPER_MODEL is None:
            _WHISPER_MODEL = WhisperModel(
                os.getenv("PHONESPOT_WHISPER_MODEL", "base"),
                device=os.getenv("PHONESPOT_WHISPER_DEVICE", "cpu"),
                compute_type=os.getenv("PHONESPOT_WHISPER_COMPUTE", "int8"),
            )
        segments, _info = _WHISPER_MODEL.transcribe(str(mp3_path), language="ko", word_timestamps=True)
        words = []
        for seg in segments:
            for w in (getattr(seg, "words", None) or []):
                t = re.sub(r"[\W_]+", "", w.word or "", flags=re.UNICODE).lower()
                if t and w.start is not None and w.end is not None:
                    words.append((t, float(w.start) * 1000.0, float(w.end) * 1000.0))
        return words or None
    except Exception as exc:
        print(f"    [whisper] 정렬 실패 -> char 근사: {exc}")
        return None


def _whisper_timing(mp3_path, chunks, spoken):
    """슈퍼톤 오디오를 whisper로 정렬 → 청크별 정밀 타이밍(word_boundary와 동일 shape). 실패=None."""
    words = _whisper_words(mp3_path)
    if not words:
        return None
    safe_chunks = [str(c).strip() for c in chunks if str(c).strip()] or [""]

    def _norm(t):
        return re.sub(r"[\W_]+", "", str(t or ""), flags=re.UNICODE).lower()

    pts = [(0, words[0][1])]
    cum = 0
    for norm_t, _st, en in words:
        cum += len(norm_t)
        pts.append((cum, en))
    w_total_chars = cum or 1
    total_ms = words[-1][2]
    chunk_norm = [_norm(c) for c in safe_chunks]
    c_total = sum(len(c) for c in chunk_norm) or 1

    def _time_at(target):
        w = target * w_total_chars / c_total  # 청크문자 → whisper문자 공간 스케일
        for i in range(1, len(pts)):
            if pts[i][0] >= w:
                (c0, t0), (c1, t1) = pts[i - 1], pts[i]
                return t1 if c1 == c0 else t0 + (t1 - t0) * (w - c0) / (c1 - c0)
        return total_ms

    cuts, acc = [], 0
    for i in range(len(chunk_norm) - 1):
        acc += len(chunk_norm[i])
        cuts.append(_time_at(acc))
    bounds = [0.0] + cuts + [total_ms]
    windows, weights = [], []
    for i in range(len(safe_chunks)):
        s2, e2 = bounds[i], bounds[i + 1]
        d = max(1.0, e2 - s2)
        windows.append({"start_ms": round(s2, 2), "end_ms": round(e2, 2), "duration_ms": round(d, 2)})
        weights.append(round(d, 2))
    print(f"    [whisper] 정밀정렬 OK ({len(words)}단어)")
    return {
        "mode": "word_boundary_text_align",
        "weights": weights,
        "windows": windows,
        "boundary_count": len(words),
        "caption_signature": chunk_signature(safe_chunks),
    }


async def gen_one(key: str, section: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    original = str(section.get("tts", "")).strip()
    spoken, applied = apply_pronunciation(original, entries)
    out = audio_dir / f"{key}.mp3"
    metadata = audio_dir / f"{key}.metadata.jsonl"
    metadata.unlink(missing_ok=True)

    engine = "edge"
    if supertone_enabled() and synth_supertone(spoken, out):
        engine = "supertone"
        normalize_audio(out)
    else:
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

    # 슈퍼톤은 WordBoundary 없음 -> whisper 정밀정렬 시도 → 실패 시 character_weight 근사
    boundaries = load_word_boundaries(metadata) if metadata.exists() else []
    timing = None
    if engine == "supertone" and not boundaries:
        timing = _whisper_timing(out, section.get("caption_chunks", []) or [], spoken)
    if timing is None:
        timing = build_chunk_timing(
            section.get("caption_chunks", []) or [],
            boundaries,
            spoken,
            entries,
        )
    section["tts_chunk_weights"] = timing["weights"]
    section["_tts_timing"] = {
        key: value
        for key, value in timing.items()
        if key != "weights"
    }
    return out, {
        "key": key,
        "engine": engine,
        "original_tts": original,
        "spoken_tts": spoken,
        "dictionary_applied": applied,
        "caption_signature": timing.get("caption_signature"),
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
        "volume": VOLUME,
        "pitch": PITCH,
        "loudness_normalize": LOUDNORM,
        "tts_engine": TTS_ENGINE,
        "supertone_voice": (SUPERTONE_VOICE if supertone_enabled() else ""),
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
            print(f"           OK  {size:,} bytes | TTS:{report.get('engine','edge')} | {timing['mode']} | dict: {applied}")
        except Exception as exc:
            print(f"           FAIL {exc}")
            sys.exit(1)

    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nDone. {len(jobs)} mp3 files saved to {audio_dir}")
    print(f"Timing manifest: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
