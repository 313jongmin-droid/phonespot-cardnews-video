# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from codex_illustration_db import load_db, library_variants, record_usage_snapshot, semantic_score
import codex_illust_embed as ce
import codex_image_embed as ie  # image-content (CLIP) matching


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
CARD_IMAGES = CARDNEWS / "images"
CARD_OUTPUT = CARDNEWS / "output"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"

# Thresholds lowered so a genuine single strong-keyword illustration match is
# used instead of falling through to a random library pick. See:
#   MAINTENANCE/CODEX_SYNC_AND_VISUAL_MATCH_FIX_GUIDE.md
MIN_IMAGE_SCORE = 16
MIN_ILLUST_SCORE = 12

# Topic-neutral editorial illustrations that are never "wrong" on a phone/IT
# news short. Used as filler when nothing matches, instead of random library art.
# ★ 진짜 중립(phone/device 일반)만. 이전엔 newspaper/shield/microphone/meeting_room/forecast
#   가 들어있었는데 이것들은 속보/보안/팟캐스트/회의/예측이라는 '특정 의미'를 그려서
#   폴백으로 쓰면 '무관 그림'으로 보였다(예: 출시일에 shield, 칩에 newspaper). 제외.
#   라이브러리에 없는 항목은 pick_neutral 이 자동으로 건너뛴다. env 로 조절 가능.
NEUTRAL_FILLERS = [v.strip() for v in os.getenv(
    "PHONESPOT_NEUTRAL_FILLERS",
    "smartphone,phone_setup_ready,phone_settings_toggle,device_os_requirement,device_data_transfer",
).split(",") if v.strip()]

# 임베딩(의미) 모드 임계: 코사인 0~1 스케일. 모델 없으면 위 lexical 임계 사용.
# 필요하면 이 두 값만 조절(올리면 더 엄격, 무관 매칭↓ / 내리면 더 관대). env 로도 조절.
EMBED_MIN_IMAGE = float(os.getenv("PHONESPOT_EMBED_MIN_IMAGE", "0.42"))
# ★ 0.42 는 너무 관대해 먼 그림이 통과했다(예: 출시일→shield, 슬림화→ti_decrease,
#   엑시노스→aluminum_label). 0.48 로 올려 약한 매칭은 중립 필러로 떨어지게 한다.
#   "무관 그림 < 중립 그림" 원칙. PC 재렌더로 검증 후 PHONESPOT_EMBED_MIN_ILLUST 로 미세조정.
EMBED_MIN_ILLUST = float(os.getenv("PHONESPOT_EMBED_MIN_ILLUST", "0.48"))

# 그림 "내용"(CLIP) 매칭 임계: 청크 텍스트 ↔ 라이브러리 그림 픽셀의 교차모달 코사인.
# 이름/태그가 아니라 실제 그림이 무엇을 그렸는지로 재사용 → 파일명이 틀려도 안전.
# 주의: 교차모달 코사인은 텍스트끼리(MiniLM)보다 절대값이 낮다. 보수적으로 시작하고
# PC 에서 렌더 결과를 보며 PHONESPOT_IMG_MATCH_MIN 으로 조절(올리면 엄격/내리면 관대).
# 이 신호는 '확신 있는 텍스트 매칭이 없을 때, 중립 필러 대신' 쓰는 보조 신호다.
# 즉 잘 맞던 매칭을 덮어쓰지 않으므로 기존 품질을 떨어뜨리지 않는다.
EMBED_MIN_ILLUST_IMG = float(os.getenv("PHONESPOT_IMG_MATCH_MIN", "0.28"))

# ★ 내용이 잘못 그려진 라이브러리 그림 차단목록. 텍스트/태그 임베딩엔 맞아도 실제 그림이
#   주제와 다른 것들(예: cpt_496029c6 = '온디바이스 AI' 개념인데 보이스피싱 장면). 매칭/폴백/
#   내용매칭 어디서도 선택 안 됨. 라이브러리 그림 자체는 PC 에서 교체/삭제 권장. env 로 확장.
ILLUST_BLOCKLIST = set(
    v.strip() for v in os.getenv("PHONESPOT_ILLUST_BLOCKLIST", "cpt_496029c6").split(",") if v.strip()
)


ALIASES = {
    "일정": ["일정", "날짜", "달력", "캘린더", "키노트", "행사", "공개", "출시", "사전예약", "예약", "7월", "8월", "6월"],
    "폴드": ["폴드", "폴더블", "fold", "foldable", "와이드", "펼친", "내부 화면"],
    "플립": ["플립", "flip", "외부 화면", "외부 디스플레이", "커버 화면", "닫은 상태"],
    "워치": ["워치", "watch", "건강", "측정", "센서", "심박", "헬스"],
    "카메라": ["카메라", "렌즈", "촬영", "사진", "줌", "망원", "초광각", "HDR", "셔터", "필터", "속도"],
    "보안": ["보안", "잠금", "개인정보", "도난", "차단", "보호", "인증", "비밀번호"],
    "AI": ["AI", "인공지능", "제미나이", "Gemini", "시리", "챗봇", "온디바이스", "모델"],
    "가격": ["가격", "요금", "지원금", "할인", "혜택", "인상", "하락", "유로", "만원", "달러"],
    "배터리": ["배터리", "충전", "발열", "방열", "전력", "용량"],
    "이전": ["백업", "복원", "이전", "전송", "클라우드", "데이터"],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def words(text: str) -> set[str]:
    text = clean(text).lower()
    raw = re.findall(r"[가-힣A-Za-z0-9]+", text)
    out = {w for w in raw if len(w) >= 2}
    for key, values in ALIASES.items():
        if any(v.lower() in text for v in values):
            out.add(key.lower())
    return out


def phrase_bonus(a: str, b: str) -> int:
    a_low = a.lower()
    b_low = b.lower()
    score = 0
    for key, values in ALIASES.items():
        hit_a = any(v.lower() in a_low for v in values)
        hit_b = any(v.lower() in b_low for v in values)
        if hit_a and hit_b:
            score += 10
    for token in ("폴드8", "폴드 8", "플립8", "플립 8", "워치9", "워치 9", "2배", "HDR", "NFC", "WWDC"):
        if token.lower() in a_low and token.lower() in b_low:
            score += 16
    return score


def parse_prompt_md(slug: str) -> dict[str, str]:
    prompt = CARD_IMAGES / slug / "prompt.md"
    if not prompt.exists():
        return {}
    text = prompt.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r"(?:^|\n)\s*[—-]+\s*(\d+\.png)\s*[—-]+\s*(.*?)\n(.*?)(?=\n\s*[—-]+\s*\d+\.png\s*[—-]+|\Z)",
        re.S,
    )
    out: dict[str, str] = {}
    for name, title, body in pattern.findall(text):
        out[name.strip()] = clean(f"{title} {body}")
    return out


def list_images(slug: str) -> list[str]:
    root = CARD_IMAGES / slug
    if not root.exists():
        return []
    return sorted(p.name for p in root.glob("*.png") if re.fullmatch(r"\d+\.png", p.name))


def image_score(context: str, description: str) -> int:
    if not description:
        return 0
    overlap = words(context) & words(description)
    return len(overlap) * 8 + phrase_bonus(context, description)


def image_candidates(slug: str, context: str, used_images: set[str], prompt_map: dict[str, str]) -> list[tuple[int, str, str]]:
    rows = []
    for image in list_images(slug):
        if image in used_images:
            continue
        desc = prompt_map.get(image, "")
        score = image_score(context, desc)
        rows.append((score, image, desc))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def illustration_candidates(context: str, used_visuals: set[str]) -> list[tuple[int, str]]:
    db = load_db()
    available = set(library_variants())
    rows = []
    for variant, entry in (db.get("illustrations", {}) or {}).items():
        if variant not in available:
            continue
        if variant in ILLUST_BLOCKLIST:
            continue
        key = f"illust:{variant}"
        if key in used_visuals:
            continue
        score = semantic_score(context, entry)
        if score > 0:
            rows.append((score, variant))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def pick_neutral(used_visuals: set[str]) -> str:
    """Return a topic-neutral filler illustration that actually exists in the
    library, preferring one not yet used in this video. Empty string if none."""
    available = set(library_variants())
    for variant in NEUTRAL_FILLERS:
        if variant in available and f"illust:{variant}" not in used_visuals:
            return variant
    for variant in NEUTRAL_FILLERS:
        if variant in available:
            return variant
    return ""


def section_items(data: dict) -> list[tuple[str, dict]]:
    return [("hook", data.get("hook", {})), *[(f"fact_{i}", fact) for i, fact in enumerate(data.get("facts", []) or [], 1)], ("cta", data.get("cta", {}))]


def section_chunks(section: dict) -> list[str]:
    return [clean(x) for x in (section.get("display_chunks") or section.get("caption_chunks") or []) if clean(x)]


def headline_text(section: dict) -> str:
    parts = []
    for line in section.get("headline_lines", []) or []:
        if isinstance(line, dict):
            parts.append(clean(line.get("text")))
        else:
            parts.append(clean(line))
    parts.append(clean(section.get("caption_body")))
    return " ".join(parts)


def context_for(section: dict, idx: int) -> str:
    chunks = section_chunks(section)
    nearby = []
    for pos in (idx - 1, idx, idx + 1):
        if 0 <= pos < len(chunks):
            nearby.append(chunks[pos])
    nearby.append(headline_text(section))
    nearby.append(clean(section.get("topic")))
    return " ".join(nearby)


def visual_key(visual: dict) -> str:
    return f"{visual.get('type')}:{visual.get('value')}"


def _image_desc_embeddings(prompt_map: dict) -> dict:
    if not ce.available() or not prompt_map:
        return {}
    names = list(prompt_map.keys())
    vecs = ce.embed([prompt_map[n] for n in names])
    if vecs is None:
        return {}
    return {n: vecs[i] for i, n in enumerate(names)}


def _embed_image_candidates(slug, cvec, used_images, prompt_map, desc_emb):
    rows = []
    for image in list_images(slug):
        if image in used_images:
            continue
        vec = desc_emb.get(image)
        score = ce.cosine(cvec, vec) if (cvec is not None and vec is not None) else 0.0
        rows.append((round(float(score), 3), image, prompt_map.get(image, "")))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def _embed_illust_candidates(cvec, lib_index, used_visuals):
    rows = []
    for variant, vec in lib_index.items():
        if variant in ILLUST_BLOCKLIST:
            continue
        if f"illust:{variant}" in used_visuals:
            continue
        score = ce.cosine(cvec, vec) if cvec is not None else 0.0
        rows.append((round(float(score), 3), variant))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


def _imgcontent_best(context, img_index, used_visuals):
    """청크 텍스트 ↔ 라이브러리 그림 '내용'(CLIP)으로 가장 가까운 (score, variant).
    이름/태그가 아니라 실제 그림 픽셀 기준 → 파일명이 틀려도 올바른 그림을 찾는다."""
    if not img_index:
        return (0.0, "")
    rows = ie.rank_for_text(context, index=img_index)
    for variant, score in rows:
        if variant in ILLUST_BLOCKLIST:
            continue
        if f"illust:{variant}" in used_visuals:
            continue
        return (round(float(score), 3), variant)
    return (0.0, "")


def semantic_match(data: dict, slug: str) -> bool:
    if data.get("_codex_manual_visuals"):
        print("[semantic_visual] manual visuals: skip")
        return False

    prompt_map = parse_prompt_md(slug)
    if not prompt_map:
        print("[semantic_visual] prompt.md image descriptions missing: skip")
        return False

    used_images: set[str] = set()
    used_visuals: set[str] = set()
    changes = []
    weak = []

    # 3단계: 임베딩(의미) 매칭. 모델 없으면 lexical 폴백(min_img/min_ill 자동 전환).
    use_embed = ce.available()
    min_img = EMBED_MIN_IMAGE if use_embed else MIN_IMAGE_SCORE
    min_ill = EMBED_MIN_ILLUST if use_embed else MIN_ILLUST_SCORE
    desc_emb = _image_desc_embeddings(prompt_map) if use_embed else {}
    lib_index = ce.build_index(available_only=True) if use_embed else {}
    # 그림 내용(CLIP) 인덱스: 있으면 확신 매칭이 없을 때 중립 필러 대신 내용으로 채운다.
    img_index = ie.library_image_index() if ie.available() else {}
    img_engine = f", image-content={len(img_index)}장(min={EMBED_MIN_ILLUST_IMG})" if img_index else ""
    print(f"[semantic_visual] engine={'embedding' if use_embed else 'lexical'} (min_img={min_img}, min_ill={min_ill}){img_engine}")

    for section_name, section in section_items(data):
        chunks = section_chunks(section)
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not chunks or not visuals:
            continue
        if len(visuals) < len(chunks):
            visuals.extend([dict(visuals[-1])] * (len(chunks) - len(visuals)))
        if len(visuals) > len(chunks):
            visuals = visuals[: len(chunks)]

        for idx, current in enumerate(visuals):
            if current.get("type") == "logo":
                used_visuals.add(visual_key(current))
                continue
            if section_name == "cta":
                # CTA is a fixed conversion surface; keep existing CTA illustration/logo contract.
                used_visuals.add(visual_key(current))
                continue

            context = context_for(section, idx)
            if use_embed:
                cvec_mat = ce.embed([context])
                cvec = cvec_mat[0] if (cvec_mat is not None and len(cvec_mat)) else None
                imgs = _embed_image_candidates(slug, cvec, used_images, prompt_map, desc_emb)
                ills = _embed_illust_candidates(cvec, lib_index, used_visuals)
            else:
                imgs = image_candidates(slug, context, used_images, prompt_map)
                ills = illustration_candidates(context, used_visuals)
            best_img = imgs[0] if imgs else (0, "", "")
            best_ill = ills[0] if ills else (0, "")

            chosen = None
            reason = ""
            if best_img[0] >= min_img and best_img[0] >= best_ill[0]:
                chosen = {"type": "image", "value": best_img[1]}
                reason = f"image score {best_img[0]}: {best_img[2][:80]}"
            elif best_ill[0] >= min_ill:
                chosen = {"type": "illust", "value": best_ill[1]}
                reason = f"illust score {best_ill[0]}"
            elif current.get("type") == "image" and current.get("value") not in used_images:
                # Source images are generated for THIS article, so an on-topic
                # source image beats any weak library guess.
                chosen = current
                reason = "kept source image (no semantic match)"
            elif current.get("type") == "mascot" and visual_key(current) not in used_visuals:
                # Mascots are emotion poses, not topical art - safe to keep.
                chosen = current
                reason = "kept mascot (no semantic match)"
            elif imgs:
                # Any unused source image is still on-topic by construction.
                chosen = {"type": "image", "value": best_img[1]}
                reason = f"unused source image (no semantic match, img score {best_img[0]})"
            else:
                # No source image left and no confident TEXT match. Before falling
                # back to a topic-neutral filler, try matching by the actual picture
                # CONTENT (CLIP). This reuses the right library art even if its
                # filename/tags are wrong - and only fires when text matching gave
                # up, so it never overrides a good match (no regression risk).
                img_best = _imgcontent_best(context, img_index, used_visuals)
                if img_best[0] >= EMBED_MIN_ILLUST_IMG and img_best[1]:
                    chosen = {"type": "illust", "value": img_best[1]}
                    reason = f"image-content match {img_best[0]}"
                else:
                    # Use a topic-neutral filler instead of a random library
                    # illustration - that fallback was what put battery/foldable
                    # art on unrelated scripts.
                    neutral = pick_neutral(used_visuals)
                    if neutral:
                        chosen = {"type": "illust", "value": neutral}
                        reason = "neutral filler (no semantic match)"
                    else:
                        chosen = current
                        reason = "kept current (no neutral available)"

            if chosen.get("type") == "image":
                used_images.add(str(chosen.get("value") or ""))
            if chosen.get("type") in {"illust", "image", "mascot"}:
                used_visuals.add(visual_key(chosen))

            if chosen != current:
                changes.append({
                    "section": section_name,
                    "chunk": idx + 1,
                    "from": current,
                    "to": chosen,
                    "context": context[:120],
                    "reason": reason,
                })
            if (best_img[0] < min_img and best_ill[0] < min_ill and section_name != "cta"):
                weak.append({
                    "section": section_name,
                    "chunk": idx + 1,
                    "current": chosen,
                    "context": context[:160],
                    "best_image_score": best_img[0],
                    "best_illust_score": best_ill[0],
                })

            visuals[idx] = chosen

        section["chunk_visuals"] = visuals

    if changes or weak:
        data["_codex_semantic_visual_match"] = {
            "version": 1,
            "policy": "Match chunks to GPT source images using prompt.md descriptions, then fallback to tagged reusable illustrations.",
            "changes": changes,
            "weak": weak,
        }
        report_path = CARD_OUTPUT / slug / "codex_semantic_visual_match_report.md"
        lines = [
            f"# Semantic Visual Match Report: {slug}",
            "",
            "청크 문맥과 `images/<slug>/prompt.md`의 1~5.png 설명을 비교해 이미지/일러스트를 재배치했습니다.",
            "",
            "## 변경",
        ]
        if not changes:
            lines.append("- 변경 없음")
        for item in changes:
            lines.append(
                f"- {item['section']} C{item['chunk']}: "
                f"`{visual_key(item['from'])}` -> `{visual_key(item['to'])}` ({item['reason']})"
            )
        lines.extend(["", "## 약한 매칭"])
        if not weak:
            lines.append("- 없음")
        for item in weak:
            lines.append(
                f"- {item['section']} C{item['chunk']}: `{visual_key(item['current'])}` "
                f"(image={item['best_image_score']}, illust={item['best_illust_score']}) / {item['context']}"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[semantic_visual] changes={len(changes)}, weak={len(weak)}")
        print(f"[semantic_visual] report: {report_path}")
        if changes:
            record_usage_snapshot(data, slug, source="semantic_visual_match")
        return bool(changes)
    print("[semantic_visual] no changes")
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_semantic_visual_match.py <slug>")
        return 2
    slug = sys.argv[1].strip()
    path = CARD_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[semantic_visual] missing: {path}")
        return 1
    data = read_json(path)
    changed = semantic_match(data, slug)
    if changed:
        write_json(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
