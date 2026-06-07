# -*- coding: utf-8 -*-
"""Compile and validate render-time chunk overrides."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from codex_caption_lockstep import (
    ABSOLUTE_MAX_UNITS,
    clean_text,
    compare_text,
    strip_display_periods,
    validate_section_lockstep,
)


ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "cardnews" / "output"
OVERRIDES = ROOT / "CODEX_VIDEO_DESK" / "CHUNK_OVERRIDES"
RUNTIME_SCRIPT = ROOT / "shorts" / "public" / "shorts_script.json"
SUPPORTED_VISUAL_TYPES = {
    "image",
    "illust",
    "mascot",
    "pricebar",
    "timeline",
    "stat",
    "compare",
    "calendar",
    "bankaccount",
    "logo",
}


def section_items(data: dict[str, Any]):
    if isinstance(data.get("hook"), dict):
        yield "hook", data["hook"]
    for idx, fact in enumerate(data.get("facts") or [], 1):
        if isinstance(fact, dict):
            yield f"fact_{idx}", fact
    if isinstance(data.get("cta"), dict):
        yield "cta", data["cta"]


def get_section(data: dict[str, Any], section_name: str) -> dict[str, Any] | None:
    if section_name == "hook":
        value = data.get("hook")
        return value if isinstance(value, dict) else None
    if section_name == "cta":
        value = data.get("cta")
        return value if isinstance(value, dict) else None
    if section_name.startswith("fact_"):
        try:
            index = int(section_name.split("_", 1)[1]) - 1
        except ValueError:
            return None
        facts = data.get("facts") or []
        if 0 <= index < len(facts) and isinstance(facts[index], dict):
            return facts[index]
    return None


def flatten_chunk(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\\n", " ").replace("\n", " ")).strip()


def display_chunk(text: str) -> str:
    lines = [strip_display_periods(line) for line in str(text or "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def section_tts_hash(section: dict[str, Any]) -> str:
    narration = clean_text(section.get("tts", ""))
    return hashlib.sha256(narration.encode("utf-8")).hexdigest()


def chunk_signature(chunks: list[str]) -> str:
    normalized = [flatten_chunk(chunk) for chunk in chunks if flatten_chunk(chunk)]
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_effective_section(section_name: str, section: dict[str, Any]) -> list[str]:
    errors = validate_section_lockstep(section_name, section, lambda value: len(re.sub(r"\s+", "", value)))
    chunks = [flatten_chunk(value) for value in section.get("caption_chunks", []) or [] if flatten_chunk(value)]
    display = [display_chunk(value) for value in section.get("display_chunks", []) or [] if display_chunk(value)]
    visuals = section.get("chunk_visuals") or []

    if len(visuals) != len(chunks):
        errors.append(f"{section_name}: visual/chunk count mismatch {len(visuals)} != {len(chunks)}")
    for idx, visual in enumerate(visuals, 1):
        if not isinstance(visual, dict):
            errors.append(f"{section_name}.chunk_visuals[{idx}]: visual must be an object")
            continue
        visual_type = str(visual.get("type") or "")
        if visual_type not in SUPPORTED_VISUAL_TYPES:
            errors.append(f"{section_name}.chunk_visuals[{idx}]: unsupported visual type `{visual_type or '-'}`")
        if visual_type != "logo" and visual.get("value") in (None, "", "none"):
            errors.append(f"{section_name}.chunk_visuals[{idx}]: visual value is empty")

    for idx, value in enumerate(display, 1):
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) > 3:
            errors.append(f"{section_name}.display_chunks[{idx}]: manual layout exceeds 3 lines")
        if any(len(re.sub(r"\s+", "", line)) > ABSOLUTE_MAX_UNITS for line in lines):
            errors.append(
                f"{section_name}.display_chunks[{idx}]: a manual line exceeds {ABSOLUTE_MAX_UNITS} units"
            )
    return errors


def validate_effective_script(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for section_name, section in section_items(data):
        errors.extend(validate_effective_section(section_name, section))
    return errors


def apply_overrides(
    data: dict[str, Any],
    slug: str,
    override_path: Path | None = None,
    *,
    strict: bool = True,
) -> dict[str, Any]:
    path = override_path or OVERRIDES / f"{slug}.json"
    report = {"applied": False, "path": str(path), "sections": [], "legacy_sections": []}
    if not path.exists():
        return report
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        if strict:
            raise RuntimeError(f"청크 편집 파일을 읽지 못했습니다: {exc}") from exc
        report["error"] = str(exc)
        return report

    sections = payload.get("sections") or {}
    if not isinstance(sections, dict):
        raise RuntimeError("청크 편집 파일의 sections 형식이 잘못되었습니다.")

    for section_name, override in sections.items():
        if not isinstance(override, dict):
            continue
        section = get_section(data, section_name)
        if section is None:
            raise RuntimeError(f"청크 편집 대상 구간이 원본에 없습니다: {section_name}")

        expected_hash = str(override.get("source_tts_sha256") or "")
        current_hash = section_tts_hash(section)
        if expected_hash and expected_hash != current_hash:
            raise RuntimeError(
                f"{section_name}: 원본 TTS가 편집 이후 변경되었습니다. "
                "이 구간의 청크 편집을 초기화한 뒤 다시 보정하세요."
            )
        if not expected_hash:
            report["legacy_sections"].append(section_name)

        chunks = [flatten_chunk(value) for value in override.get("chunks") or [] if flatten_chunk(value)]
        display_values = override.get("display_chunks")
        if isinstance(display_values, list) and len(display_values) == len(chunks):
            display = [display_chunk(value) for value in display_values]
        else:
            display = [display_chunk(value) for value in chunks]
        visuals = override.get("visuals")

        if chunks:
            section["caption_chunks"] = chunks
            section["display_chunks"] = display
            section["_codex_chunk_override"] = {
                "version": int(payload.get("version") or 1),
                "source_tts_sha256": current_hash,
                "chunk_signature": chunk_signature(chunks),
            }
        if isinstance(visuals, list):
            section["chunk_visuals"] = copy.deepcopy(visuals)

        section_errors = validate_effective_section(section_name, section)
        if section_errors:
            raise RuntimeError("청크 편집 검증 실패\n- " + "\n- ".join(section_errors))
        report["sections"].append(section_name)

    if report["sections"]:
        data["_codex_chunk_overrides_applied"] = {
            "version": 2,
            "path": str(path),
            "sections": report["sections"],
        }
        report["applied"] = True
    return report


def build_effective_script(
    slug: str,
    *,
    source_path: Path | None = None,
    override_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = source_path or OUTPUT / slug / "shorts_script.json"
    if not source.exists():
        raise FileNotFoundError(f"shorts_script.json not found: {source}")
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    report = apply_overrides(data, slug, override_path, strict=True)
    errors = validate_effective_script(data)
    if errors:
        raise RuntimeError("최종 렌더 스크립트 검증 실패\n- " + "\n- ".join(errors))
    data["_codex_effective_script"] = {
        "version": 2,
        "slug": slug,
        "source": str(source),
        "override_applied": bool(report["applied"]),
        "override_sections": report["sections"],
    }
    return data, report


def write_effective_script(
    slug: str,
    output_path: Path = RUNTIME_SCRIPT,
    *,
    source_path: Path | None = None,
    override_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    data, report = build_effective_script(
        slug,
        source_path=source_path,
        override_path=override_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data, report

