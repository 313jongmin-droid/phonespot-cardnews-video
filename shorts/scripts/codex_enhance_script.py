# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from codex_illustration_db import rank_variants, record_usage_snapshot
from codex_caption_lockstep import sync_section_to_tts, validate_section_lockstep


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS = ROOT / "cardnews"


VIDEO_NARRATION_RE = re.compile(r"영상\s*나레이션")
INTRO_RE = re.compile(r"인트로|후크|HOOK", re.I)
BODY_RE = re.compile(r"본문|FACT", re.I)
CTA_RE = re.compile(r"매장\s*안내|CTA|안내", re.I)

SOURCE_WORDS = ["보도", "외신", "매체", "팁스터", "기자", "ZDNet", "9to5Mac", "블룸버그", "맥루머스"]
BAD_PHRASES = [
    "에 따르면에 따르면",
    "와 관련해와 관련해",
    "반면와 관련해",
    "기기에서와 관련해",
    "기종별와 관련해",
    "기준으로기준으로",
    "입니다입니다",
    "합니다합니다",
    "됩니다입니다",
    "습니다입니다",
]

# PhoneSpot CTA is a channel-level contract, not article copy.
FIXED_CTA_CHUNKS = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]
FIXED_CTA_TTS = "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."

# Runtime caption handling is intentionally conservative. Caption chunks are
# authored Korean. Never invent a predicate or connective suffix here.
MALFORMED_KOREAN_PATTERNS = [
    re.compile(r"(?:다|니다)(?:입니다|합니다|됩니다|습니다)(?=[.!?,]|$)"),
    re.compile(r"(?:입니다|합니다|됩니다|습니다){2,}"),
    re.compile(r"(?:에 따르면){2,}"),
    re.compile(r"(?:와 관련해){2,}"),
]

CASUAL_REPLACEMENTS = [
    ("작동해요", "작동합니다"),
    ("작동돼요", "작동됩니다"),
    ("가능해요", "가능합니다"),
    ("해드릴게요", "도와드립니다"),
    ("알려드릴게요", "안내해드립니다"),
    ("터치키", "터치 키"),
    ("비번", "비밀번호"),
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def no_space_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def normalize_tts(text: str) -> str:
    out = clean_text(text)
    for old, new in CASUAL_REPLACEMENTS:
        out = out.replace(old, new)
    return clean_text(out)


def strip_markdown(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^\s*[-*]\s*", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    return line.strip()


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [clean_text(p) for p in parts if clean_text(p)] or [text]


def parse_captions_narration(slug: str) -> dict[str, object] | None:
    path = CARDNEWS / "output" / slug / "captions.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if VIDEO_NARRATION_RE.search(line):
            start = idx + 1
            break
    if start is None:
        return None

    buckets = {"intro": [], "body": [], "cta": []}
    current: str | None = None
    for raw in lines[start:]:
        line = raw.strip()
        if line.startswith("---"):
            break
        heading = strip_markdown(line)
        if raw.lstrip().startswith("#"):
            if INTRO_RE.search(heading):
                current = "intro"
                continue
            if BODY_RE.search(heading):
                current = "body"
                continue
            if CTA_RE.search(heading):
                current = "cta"
                continue
            if current and re.match(r"^\d+\.", heading):
                break
        if not line:
            if current:
                buckets[current].append("")
            continue
        if current:
            cleaned = strip_markdown(raw)
            if cleaned:
                buckets[current].append(cleaned)

    intro = clean_text(" ".join(x for x in buckets["intro"] if x))
    cta = clean_text(" ".join(x for x in buckets["cta"] if x))
    body_paragraphs: list[str] = []
    cur: list[str] = []
    for item in buckets["body"]:
        if item == "":
            if cur:
                body_paragraphs.append(clean_text(" ".join(cur)))
                cur = []
            continue
        cur.append(item)
    if cur:
        body_paragraphs.append(clean_text(" ".join(cur)))
    body_paragraphs = [p for p in body_paragraphs if p]
    if not intro and not body_paragraphs and not cta:
        return None
    return {"intro": intro, "body": body_paragraphs, "cta": cta, "path": str(path)}


def distribute_body_to_facts(paragraphs: list[str], fact_count: int) -> list[str]:
    if fact_count <= 0:
        return []
    if not paragraphs:
        return ["" for _ in range(fact_count)]
    if len(paragraphs) == fact_count:
        return paragraphs
    if len(paragraphs) > fact_count:
        return paragraphs[: fact_count - 1] + [clean_text(" ".join(paragraphs[fact_count - 1 :]))]
    expanded = paragraphs[:]
    while len(expanded) < fact_count:
        longest = max(range(len(expanded)), key=lambda i: len(expanded[i]))
        sentences = split_sentences(expanded[longest])
        if len(sentences) <= 1:
            expanded.append("")
            continue
        mid = max(1, len(sentences) // 2)
        expanded[longest] = clean_text(" ".join(sentences[:mid]))
        expanded.insert(longest + 1, clean_text(" ".join(sentences[mid:])))
    return expanded[:fact_count]


def section_list(data: dict) -> list[tuple[str, dict]]:
    return [("hook", data.get("hook", {}))] + [
        (f"fact_{idx + 1}", fact) for idx, fact in enumerate(data.get("facts", []) or [])
    ] + [("cta", data.get("cta", {}))]


def section_texts(section: dict) -> list[str]:
    return [clean_text(x) for x in section.get("caption_chunks", []) or [] if clean_text(x)]


def malformed_korean_reason(text: str) -> str | None:
    value = clean_text(text)
    for bad in BAD_PHRASES:
        if bad in value:
            return f"duplicated phrase: {bad}"
    for pattern in MALFORMED_KOREAN_PATTERNS:
        match = pattern.search(value)
        if match:
            return f"duplicated Korean ending: {match.group(0)}"
    return None


def needs_display_repair(section: dict) -> bool:
    chunks = section_texts(section)
    display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
    if not chunks:
        return False
    if len(display) != len(chunks):
        return True
    if any(malformed_korean_reason(item) for item in display):
        return True
    # A prior runtime pass used to turn complete source sentences into comma
    # fragments. Restore those from the authored caption chunks.
    for source, shown in zip(chunks, display):
        if re.search(r"[.!?。！？]$", source) and shown.rstrip().endswith(","):
            return True
    if any(no_space_len(x) > 42 for x in display):
        return True
    return False


def make_display_sentence(chunk: str, idx: int, total: int) -> str:
    # Kept as a public helper for compatibility with earlier patches.
    # Do not append guessed Korean particles or endings at runtime.
    return normalize_tts(chunk)


def repair_display(section: dict) -> None:
    chunks = section_texts(section)
    if not chunks:
        return
    section["display_chunks"] = [make_display_sentence(chunk, idx, len(chunks)) for idx, chunk in enumerate(chunks)]


def enforce_fixed_cta(data: dict) -> None:
    cta = data.setdefault("cta", {})
    cta["tts"] = FIXED_CTA_TTS
    cta["caption_body"] = list(FIXED_CTA_CHUNKS)
    cta["caption_emphasis"] = [FIXED_CTA_CHUNKS[1]]
    cta["headline_lines"] = [
        {"text": FIXED_CTA_CHUNKS[0]},
        {"text": FIXED_CTA_CHUNKS[1], "accent": True},
    ]
    cta["caption_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["display_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["chunk_visuals"] = [
        {"type": "illust", "value": "smartphone"},
        {"type": "logo", "value": None},
    ]
    cta["_codex_fixed_cta"] = True
    cta["_codex_narration_source"] = "fixed_cta_contract"


def validate_korean_contract(data: dict) -> None:
    errors = []
    for section_name, section in section_list(data):
        chunks = section_texts(section)
        display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
        if chunks and len(display) != len(chunks):
            errors.append(f"{section_name}: caption/display count mismatch {len(chunks)} != {len(display)}")
        errors.extend(validate_section_lockstep(section_name, section, no_space_len))
        for field_name, values in (("caption_chunks", chunks), ("display_chunks", display)):
            for idx, item in enumerate(values, 1):
                reason = malformed_korean_reason(item)
                if reason:
                    errors.append(f"{section_name}.{field_name}[{idx}]: {reason}: {item}")
        for idx, (source, shown) in enumerate(zip(chunks, display), 1):
            if re.search(r"[.!?。！？]$", source) and shown.rstrip().endswith(","):
                errors.append(f"{section_name}.display_chunks[{idx}]: complete sentence became comma fragment: {shown}")
        formal_endings = []
        for item in display:
            match = re.search(r"(합니다|입니다|됩니다|했습니다|있습니다|없습니다)[.!?。！？]?$", item)
            formal_endings.append(match.group(1) if match else None)
        for idx in range(max(0, len(formal_endings) - 2)):
            run = formal_endings[idx : idx + 3]
            if run[0] and len(set(run)) == 1:
                errors.append(
                    f"{section_name}.display_chunks[{idx + 1}:{idx + 3}]: "
                    f"robotic repeated ending `{run[0]}`; author a contextual Korean flow"
                )
    cta = data.get("cta", {})
    if cta.get("tts") != FIXED_CTA_TTS:
        errors.append("cta.tts: fixed CTA contract changed")
    if cta.get("caption_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.caption_chunks: fixed CTA contract changed")
    if cta.get("display_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.display_chunks: fixed CTA contract changed")
    cta_visuals = cta.get("chunk_visuals", []) or []
    if len(cta_visuals) != 2 or cta_visuals[-1].get("type") != "logo":
        errors.append("cta.chunk_visuals: fixed CTA must end with the PhoneSpot logo")
    validate_unique_source_images(data)
    if errors:
        raise ValueError("Korean caption contract failed\n- " + "\n- ".join(errors))


def visual_key(visual: dict) -> str:
    return f"{visual.get('type')}:{visual.get('value')}"


def list_source_images(slug: str) -> list[str]:
    img_dir = CARDNEWS / "images" / slug
    values = []
    if img_dir.exists():
        for path in sorted(img_dir.glob("*.png")):
            if re.match(r"^\d+\.png$", path.name):
                values.append(path.name)
    return values


def list_illustrations() -> list[str]:
    illust_dir = ROOT / "shorts" / "public" / "assets" / "illustrations"
    if not illust_dir.exists():
        return []
    return sorted(path.stem for path in illust_dir.glob("*.png"))


def rebalance_visuals(visuals: list[dict], count: int) -> list[dict]:
    if count <= 0:
        return []
    visuals = [dict(v) for v in visuals if isinstance(v, dict)]
    if not visuals:
        return []
    if len(visuals) == count:
        return visuals
    if len(visuals) > count:
        if count == 1:
            non_image = [v for v in visuals if v.get("type") != "image"]
            return [non_image[0] if non_image else visuals[0]]
        picked = [visuals[0]]
        middle = visuals[1:-1]
        middle = sorted(middle, key=lambda v: 0 if v.get("type") != "image" else 1)
        picked.extend(middle[: max(0, count - 2)])
        picked.append(visuals[-1])
        return picked[:count]
    return visuals + [dict(visuals[-1]) for _ in range(count - len(visuals))]


def replace_duplicates(section: dict, slug: str, is_cta: bool = False) -> None:
    visuals = [dict(v) for v in section.get("chunk_visuals", []) or []]
    if not visuals:
        return
    source_images = list_source_images(slug)
    illustrations = list_illustrations()
    used = set()
    img_i = 0
    ill_i = 0
    out = []
    for idx, visual in enumerate(visuals):
        key = visual_key(visual)
        if key not in used:
            used.add(key)
            out.append(visual)
            continue
        replacement = None
        while img_i < len(source_images):
            cand = {"type": "image", "value": source_images[img_i]}
            img_i += 1
            if visual_key(cand) not in used:
                replacement = cand
                break
        if replacement is None:
            while ill_i < len(illustrations):
                cand = {"type": "illust", "value": illustrations[ill_i]}
                ill_i += 1
                if visual_key(cand) not in used:
                    replacement = cand
                    break
        if replacement is None:
            replacement = visual
        used.add(visual_key(replacement))
        out.append(replacement)
    if is_cta and out and not any(v.get("type") == "logo" for v in out):
        out[-1] = {"type": "logo", "value": None}
    section["chunk_visuals"] = out



# Automatic illustration balance for newly generated scripts.
# Hand-curated visual maps are left untouched. The goal is to inherit the
# established 001/002 visual rhythm without hard-coding any slug.
ILLUSTRATION_RULES = [
    (("고온", "발열", "뜨거", "열 환경"), ("heat_release", "warning")),
    (("배터리", "충전", "수명", "사이클"), ("clock", "shield", "chart_down", "smartphone")),
    (("보안", "잠금", "도난", "비밀번호", "생체"), ("lock", "shield", "biometric", "password", "warning")),
    (("가격", "인상", "지원금", "유로", "달러", "만원"), ("price_hike", "chart_up", "gift_voucher", "market_cap")),
    (("AI", "인공지능", "제미나이", "시리", "챗봇"), ("chatbot", "memory_chip", "samsung_ai", "gemini")),
    (("업데이트", "베타", "버전", "공개", "출시"), ("final_update", "forecast", "calendar")),
    (("보도", "매체", "외신", "기자", "팁스터"), ("newspaper", "microphone")),
    (("폴더블", "폴드", "플립"), ("foldable",)),
    (("매장", "상담", "구매", "방문", "점검"), ("store", "smartphone", "gift_voucher")),
]


def _section_visual_text(section: dict, idx: int) -> str:
    chunks = section_texts(section)
    display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
    parts = []
    if idx < len(chunks):
        parts.append(chunks[idx])
    if idx < len(display):
        parts.append(display[idx])
    parts.extend(
        [
            clean_text(section.get("topic", "")),
            clean_text(section.get("tts", "")),
        ]
    )
    return " ".join(parts)


def _illustration_candidates(text: str, section_name: str) -> list[str]:
    found = []
    for keywords, variants in ILLUSTRATION_RULES:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            found.extend(variants)
    if section_name == "cta":
        found.extend(("store", "smartphone", "gift_voucher"))
    fallback = list(dict.fromkeys(found))
    ranked = rank_variants(text, section_name=section_name, fallback=fallback)
    return ranked or fallback


def auto_balance_illustrations(data: dict, slug: str) -> bool:
    if not data.get("_auto_generated"):
        return False

    sections = section_list(data)
    # Restored/manual mappings are already curated. Preserve them exactly.
    if any(section.get("_codex_visuals_restored_from") for _, section in sections):
        return False
    if any(section.get("_codex_manual_visuals") for _, section in sections):
        return False

    all_visuals = [
        visual
        for _, section in sections
        for visual in (section.get("chunk_visuals", []) or [])
        if isinstance(visual, dict)
    ]
    # This pass is an automatic fallback for plain image-only scripts.
    # If illustrations already exist, do not second-guess the existing map.
    if any(visual.get("type") == "illust" for visual in all_visuals):
        return False

    available = set(list_illustrations())
    used = {visual_key(visual) for visual in all_visuals}
    additions = []

    for section_name, section in sections:
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        chunks = section_texts(section)
        if not visuals or not chunks:
            continue

        replace_indexes = list(range(len(visuals)))
        if section_name == "hook":
            # Keep the first hook image as the visual anchor.
            replace_indexes = [idx for idx in replace_indexes if idx > 0]
        if section_name == "cta":
            # Keep the closing logo intact.
            replace_indexes = [idx for idx in replace_indexes if visuals[idx].get("type") != "logo"]

        replacement = None
        for idx in replace_indexes:
            if visuals[idx].get("type") not in {"image", "mascot"}:
                continue
            text = _section_visual_text(section, idx)
            for variant in _illustration_candidates(text, section_name):
                key = f"illust:{variant}"
                if variant in available and key not in used:
                    replacement = (idx, variant)
                    break
            if replacement:
                break

        if replacement is None:
            continue
        idx, variant = replacement
        visuals[idx] = {"type": "illust", "value": variant}
        used.add(f"illust:{variant}")
        section["chunk_visuals"] = visuals
        additions.append({"section": section_name, "chunk": idx + 1, "variant": variant})

    if additions:
        data["_codex_auto_illustration_balance"] = {
            "version": 1,
            "policy": "auto-generated image-only scripts: semantic illustration, max one per section",
            "additions": additions,
        }
        print(f"[codex_enhance] illustration balance: {len(additions)} added")
        for item in additions:
            print(f"  - {item['section']} chunk {item['chunk']}: illust:{item['variant']}")
        return True
    return False

def enforce_unique_source_images(data: dict, slug: str) -> bool:
    """Use each non-illustration image at most once across the whole video."""
    source_images = list_source_images(slug)
    illustrations = list_illustrations()
    sections = section_list(data)
    used_images = set()
    used_visuals = {
        visual_key(visual)
        for _, section in sections
        for visual in (section.get("chunk_visuals", []) or [])
        if isinstance(visual, dict) and visual.get("type") != "image"
    }
    replacements = []

    for section_name, section in sections:
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not visuals:
            continue
        for idx, visual in enumerate(visuals):
            if visual.get("type") != "image":
                continue
            value = str(visual.get("value") or "")
            if value and value not in used_images:
                used_images.add(value)
                continue

            replacement = None
            context = _section_visual_text(section, idx)
            for variant in _illustration_candidates(context, section_name):
                key = f"illust:{variant}"
                if variant in illustrations and key not in used_visuals:
                    replacement = {"type": "illust", "value": variant}
                    break

            if replacement is None:
                for image in source_images:
                    if image not in used_images:
                        replacement = {"type": "image", "value": image}
                        break

            if replacement is None:
                for variant in illustrations:
                    key = f"illust:{variant}"
                    if key not in used_visuals:
                        replacement = {"type": "illust", "value": variant}
                        break

            if replacement is None:
                continue

            visuals[idx] = replacement
            if replacement.get("type") == "image":
                used_images.add(str(replacement.get("value") or ""))
            else:
                used_visuals.add(visual_key(replacement))
            replacements.append(
                {
                    "section": section_name,
                    "chunk": idx + 1,
                    "from": visual,
                    "to": replacement,
                }
            )
        section["chunk_visuals"] = visuals

    if replacements:
        data["_codex_unique_source_images"] = {
            "version": 1,
            "policy": "non-illustration image visuals are used at most once across one video",
            "replacements": replacements,
        }
        print(f"[codex_enhance] unique source images: {len(replacements)} replaced")
    return bool(replacements)


def validate_unique_source_images(data: dict) -> None:
    seen = {}
    errors = []
    for section_name, section in section_list(data):
        for idx, visual in enumerate(section.get("chunk_visuals", []) or [], 1):
            if not isinstance(visual, dict) or visual.get("type") != "image":
                continue
            value = str(visual.get("value") or "")
            if not value:
                errors.append(f"{section_name}.chunk_visuals[{idx}]: empty image value")
                continue
            if value in seen:
                errors.append(
                    f"{section_name}.chunk_visuals[{idx}]: duplicated image `{value}`; "
                    f"first used at {seen[value]}"
                )
            else:
                seen[value] = f"{section_name}.chunk_visuals[{idx}]"
    if errors:
        raise ValueError("Source image once contract failed\n- " + "\n- ".join(errors))


def ensure_visual_contract(section: dict, slug: str, name: str) -> None:
    chunks = section_texts(section)
    visuals = [dict(v) for v in section.get("chunk_visuals", []) or []]
    if chunks and len(visuals) != len(chunks):
        visuals = rebalance_visuals(visuals, len(chunks))
    if name == "hook" and visuals and not any(v.get("type") == "image" for v in visuals):
        images = list_source_images(slug)
        if images:
            visuals[0] = {"type": "image", "value": images[0]}
    if name == "cta" and chunks:
        if not visuals:
            visuals = [{"type": "logo", "value": None} for _ in chunks]
        elif not any(v.get("type") == "logo" for v in visuals):
            visuals[-1] = {"type": "logo", "value": None}
    section["chunk_visuals"] = visuals
    replace_duplicates(section, slug, is_cta=(name == "cta"))


def apply_narration_tts_only(data: dict, slug: str) -> bool:
    parsed = parse_captions_narration(slug)
    if not parsed:
        return False
    if parsed.get("intro"):
        data.get("hook", {})["tts"] = normalize_tts(str(parsed["intro"]))
        data.get("hook", {})["_codex_narration_source"] = "captions.md#intro"
    facts = data.get("facts", []) or []
    distributed = distribute_body_to_facts(list(parsed.get("body") or []), len(facts))
    for fact, narration in zip(facts, distributed):
        if narration:
            fact["tts"] = normalize_tts(narration)
            fact["_codex_narration_source"] = "captions.md#body"
    if parsed.get("cta"):
        data.get("cta", {})["tts"] = normalize_tts(str(parsed["cta"]))
        data.get("cta", {})["_codex_narration_source"] = "captions.md#cta"
    data["_codex_uses_captions_md_narration"] = True
    data["_codex_captions_md_narration_path"] = parsed.get("path")
    data["_codex_narration_policy"] = "tts_only_chunks_visuals_preserved"
    return True


def fallback_tts(section: dict) -> None:
    if section.get("tts"):
        section["tts"] = normalize_tts(section["tts"])
    elif section_texts(section):
        section["tts"] = normalize_tts(" ".join(section_texts(section)))


def enhance(data: dict, slug: str) -> None:
    used_narration = apply_narration_tts_only(data, slug)
    for name, section in section_list(data):
        fallback_tts(section)
        sync_section_to_tts(section)
        if needs_display_repair(section):
            repair_display(section)
        elif not section.get("display_chunks") and section_texts(section):
            repair_display(section)
        ensure_visual_contract(section, slug, name)
        section["_codex_contextual_narrative"] = True
        section["_codex_sync_mode"] = "global999_tts_caption_lockstep"
    auto_balance_illustrations(data, slug)
    enforce_unique_source_images(data, slug)
    enforce_fixed_cta(data)
    validate_korean_contract(data)
    data["_codex_global_999_quality"] = True
    data["_codex_common_quality_logic"] = True
    data["_codex_sync_quality_logic"] = True
    data["_codex_captions_narration_priority"] = bool(used_narration)
    data["_codex_common_quality_note"] = (
        "Global 001-999 rule: screen chunks are rebuilt as an ordered, lossless partition "
        "of captions.md narration; curated visuals are rebalanced without discarding quality rules."
    )
    record_usage_snapshot(data, slug, source="codex_enhance")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_enhance_script.py <slug>")
        return 2
    slug = sys.argv[1]
    path = CARDNEWS / "output" / slug / "shorts_script.json"
    if not path.exists():
        print(f"[codex_enhance] skip, not found: {path}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    enhance(data, slug)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[codex_enhance] OK global999: {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
