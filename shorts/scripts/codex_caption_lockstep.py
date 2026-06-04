# -*- coding: utf-8 -*-
"""Build readable Korean display chunks directly from each TTS narration."""
from __future__ import annotations

import re
from typing import Callable


MIN_UNITS = 9
TARGET_UNITS = 16
MAX_UNITS = 22
ABSOLUTE_MAX_UNITS = 26

SENTENCE_END_RE = re.compile(r"[.!?。！？][\"'”’)]*$")
COMMA_END_RE = re.compile(r"[,;:][\"'”’)]*$")
CONNECTIVE_END_RE = re.compile(
    r"(?:고|며|면서|면|다면|지만|는데|으며|라며|하고|하거나|되며|되어|해서|하며|때문에|반면|이후|전후|경우)[,;:]?$"
)
DEPENDENT_NEXT_RE = re.compile(
    r"^(?:원|원으로|원을|원에|만원|억원|조원|달러|유로|개|건|명|배|퍼센트|%|년|월|일|시간|분|초|GB|TB|MB|기가|테라|와트|W|mAh)(?:[은는이가을를에도으로]*)$",
    re.I,
)
COHESIVE_NEXT_RE = re.compile(
    r"^(?:[A-Z][A-Z0-9+.-]{1,}|[0-9][0-9A-Za-z+.,/-]*|마시|하시|않|못|되|있|없|같|위한|통해|대해|위해|부터|까지|및|또는|모바일)",
    re.I,
)
NO_BREAK_AFTER_RE = re.compile(r"^(?:약|최대|최소|총|한|두|세|몇|바로|직접|한\s*번|두\s*번|세\s*번|번)$")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def units(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def compare_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", clean_text(text), flags=re.UNICODE).lower()


def strip_display_periods(text: str) -> str:
    return re.sub(r"\.(?=(?:[\"'”’)]*)?(?:\s|$))", "", clean_text(text))



# CODEX_CAPTION_COMPILER_V2
# Protect high-value Korean bundles before selecting a display chunk boundary.
NUMBERISH_END_RE = re.compile(r"\d+(?:[,.]\d+)?(?:\ub9cc|\uc5b5|\uc870)?$")
DEPENDENT_BUNDLE_RE = re.compile(
    r"^(?:\uc6d0(?:\ub300)?|\ub9cc\uc6d0|\uc5b5\uc6d0|\uc870\uc6d0|\ub2ec\ub7ec|\uc720\ub85c|\uac1c|\uac74|\uba85|\ubc30|%|GB|TB|MB|W|mAh)"
    r"(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c\uc5d0\uc11c\uae4c\uc9c0\ubd80\ud130]*)$",
    re.I,
)
LAW_HEAD_RE = re.compile(r"(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uace0\uc2dc|\uc870\ub840|\uaddc\uce59)$")
LAW_ARTICLE_RE = re.compile(r"^\uc81c?\d+\uc870(?:\uc758\d+)?(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c\uc5d0\uc11c]*)?$")
PRODUCT_HEAD_RE = re.compile(r"^(?:\uc544\uc774\ud3f0|\uac24\ub7ed\uc2dc|\ud53d\uc140|\uc544\uc774\ud328\ub4dc|\uac24\ub7ed\uc2dc\ud0ed|\uac24\ub7ed\uc2dc\ud3f4\ub4dc|\uac24\ub7ed\uc2dc\ud50c\ub9bd)$", re.I)
PRODUCT_MODEL_RE = re.compile(r"^(?:[A-Z]?\d+[A-Za-z+.-]*|S\d+|Z\d+)$", re.I)
MODEL_NUMBER_RE = re.compile(r"^(?:[A-Z]?\d+[A-Za-z+.-]*|S\d+|Z\d+)$", re.I)
MODEL_SUFFIX_RE = re.compile(r"^(?:\ud504\ub85c|\ud50c\ub7ec\uc2a4|\uc6b8\ud2b8\ub77c|\uc5d0\uc5b4|FE|\ud3f4\ub4dc|\ud50c\ub9bd)(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c]*)?$", re.I)


def compact_token(token: str) -> str:
    return re.sub(r"[\s,.;:!?\u3002\uff01\uff1f\"'\u201d\u2019()]+", "", str(token or ""))


def forbidden_boundary(token: str, next_token: str) -> bool:
    current = compact_token(token)
    following = compact_token(next_token)
    if not current or not following:
        return False
    if NUMBERISH_END_RE.search(current) and DEPENDENT_BUNDLE_RE.search(following):
        return True
    if LAW_HEAD_RE.search(current) and LAW_ARTICLE_RE.search(following):
        return True
    if PRODUCT_HEAD_RE.search(current) and PRODUCT_MODEL_RE.search(following):
        return True
    if MODEL_NUMBER_RE.search(current) and MODEL_SUFFIX_RE.search(following):
        return True
    return False


def boundary_score(token: str, next_token: str, current_units: int, remaining_units: int) -> int:
    distance = abs(TARGET_UNITS - current_units)
    score = 100 - distance
    sentence_end = bool(SENTENCE_END_RE.search(token))
    if sentence_end:
        score += 1000
    elif COMMA_END_RE.search(token):
        score += 500
    elif CONNECTIVE_END_RE.search(token):
        score += 280
    if remaining_units and remaining_units < MIN_UNITS:
        score -= 700
    if not sentence_end and next_token and (DEPENDENT_NEXT_RE.search(next_token) or COHESIVE_NEXT_RE.search(next_token)):
        score -= 900
    if NO_BREAK_AFTER_RE.search(token):
        score -= 900
    if forbidden_boundary(token, next_token):
        score -= 4000
    return score


def choose_break(tokens: list[str], start: int) -> int:
    total = len(tokens)
    candidates: list[tuple[int, int]] = []
    consumed = ""
    for end in range(start + 1, total + 1):
        consumed = " ".join(tokens[start:end])
        current_units = units(consumed)
        if current_units > ABSOLUTE_MAX_UNITS:
            break
        remaining = " ".join(tokens[end:])
        remaining_units = units(remaining)
        if current_units >= MIN_UNITS or end == total:
            next_token = tokens[end] if end < total else ""
            candidates.append((boundary_score(tokens[end - 1], next_token, current_units, remaining_units), end))
        if current_units >= MAX_UNITS:
            break
    if not candidates:
        return min(total, start + 1)
    return max(candidates, key=lambda item: (item[0], item[1]))[1]


def merge_short_chunks(chunks: list[str]) -> list[str]:
    output: list[str] = []
    for chunk in chunks:
        chunk = clean_text(chunk)
        if not chunk:
            continue
        if output and units(chunk) < MIN_UNITS and units(output[-1] + " " + chunk) <= ABSOLUTE_MAX_UNITS:
            output[-1] = clean_text(output[-1] + " " + chunk)
        else:
            output.append(chunk)
    if len(output) >= 2 and units(output[0]) < MIN_UNITS and units(output[0] + " " + output[1]) <= ABSOLUTE_MAX_UNITS:
        output[:2] = [clean_text(output[0] + " " + output[1])]
    return output


def split_tts_caption(text: str) -> list[str]:
    narration = clean_text(text)
    if not narration:
        return []
    tokens = narration.split()
    chunks: list[str] = []
    cursor = 0
    while cursor < len(tokens):
        end = choose_break(tokens, cursor)
        chunks.append(clean_text(" ".join(tokens[cursor:end])))
        cursor = end
    chunks = merge_short_chunks(chunks)
    if compare_text(" ".join(chunks)) != compare_text(narration):
        raise ValueError("caption splitter changed narration content")
    return chunks


def sync_section_to_tts(section: dict) -> None:
    narration = clean_text(section.get("tts", ""))
    if not narration:
        return
    chunks = split_tts_caption(narration)
    section["caption_chunks"] = chunks
    section["display_chunks"] = [strip_display_periods(chunk) for chunk in chunks]
    section["_codex_caption_lockstep"] = {
        "version": 2,
        "compiler": "korean_caption_compiler_v2",
        "policy": "display chunks are an ordered, lossless semantic partition of section TTS",
        "chunk_count": len(chunks),
    }


def validate_section_lockstep(section_name: str, section: dict, no_space_len: Callable[[str], int]) -> list[str]:
    errors: list[str] = []
    narration = clean_text(section.get("tts", ""))
    chunks = [clean_text(value) for value in section.get("caption_chunks", []) or [] if clean_text(value)]
    display = [clean_text(value) for value in section.get("display_chunks", []) or [] if clean_text(value)]
    if narration and compare_text(" ".join(chunks)) != compare_text(narration):
        errors.append(f"{section_name}: caption chunks do not match TTS narration")
    if chunks and compare_text(" ".join(display)) != compare_text(" ".join(chunks)):
        errors.append(f"{section_name}: display chunks do not match caption chunks")
    if len(chunks) != len(display):
        errors.append(f"{section_name}: caption/display count mismatch {len(chunks)} != {len(display)}")
    for idx, chunk in enumerate(chunks, 1):
        length = no_space_len(chunk)
        if length > ABSOLUTE_MAX_UNITS:
            errors.append(f"{section_name}.caption_chunks[{idx}]: too long ({length} > {ABSOLUTE_MAX_UNITS})")
        if len(chunks) > 1 and length < 4:
            errors.append(f"{section_name}.caption_chunks[{idx}]: orphan short chunk ({length})")

    for idx in range(len(chunks) - 1):
        left = chunks[idx].split()[-1] if chunks[idx].split() else ""
        right = chunks[idx + 1].split()[0] if chunks[idx + 1].split() else ""
        if forbidden_boundary(left, right):
            errors.append(f"{section_name}.caption_chunks[{idx + 1}:{idx + 3}]: protected phrase was split")
    return errors
