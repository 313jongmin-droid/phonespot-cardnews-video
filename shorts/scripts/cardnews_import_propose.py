# -*- coding: utf-8 -*-
"""
카드뉴스 import 제안기 (패널 검수용)

카드뉴스는 슬라이드 순서대로 1.png~N.png 를 쓴다. GPT 로 그린 그림들을 다운로드한 뒤
"어느 그림이 몇 번 슬라이드인지"를 그림 내용(CLIP) ↔ 슬라이드 설명(prompt.md)으로
자동 배정 '제안'한다. 파일은 옮기지 않는다 — 제안만 CARD_IMPORT_PROPOSAL.json 으로 쓴다.
패널이 썸네일/신뢰도와 함께 보여주고, 사람이 패널 안에서 확정한다.

영상 쪽과 차이:
- 대상이 개념 파일명이 아니라 슬라이드 순번(N.png) 이다.
- 슬라이드 설명이 영어라 jina-clip 교차매칭이 더 강하다.
- 라이브러리/중복제거 개념이 없다(카드 전용 1회용). 순수 편의 기능.

폴백: codex_image_embed 가 사용 불가하면 engine="fallback-order" 로 다운로드 시간순 매핑.

사용:
    python scripts/cardnews_import_propose.py <slug>
출력:
    CODEX_VIDEO_DESK/CARD_IMPORT_PROPOSAL.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import codex_image_embed as ie

ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS = ROOT / "cardnews"
DESK = ROOT / "CODEX_VIDEO_DESK"
DOWNLOADS = Path.home() / "Downloads"
PROPOSAL_PATH = DESK / "CARD_IMPORT_PROPOSAL.json"
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}
MIN_SIZE = 10_000
RECENT_HOURS = float(os.getenv("PHONESPOT_CARD_IMPORT_HOURS", "12"))

# prompt.md 의 슬라이드 헤더: 줄 시작의 "— 1.png — 제목"  (em dash U+2014)
# 줄머리에 고정해야 "■ .../1-5.png — 5장 일괄" 같은 헤더 줄을 슬라이드로 오인하지 않는다.
SLIDE_RE = re.compile(r"(?m)^\s*[—\-]\s*(\d+)\.png\s*[—\-]\s*([^\n]*)")


def parse_slides(slug: str) -> list[dict]:
    pmd = CARDNEWS / "images" / slug / "prompt.md"
    if not pmd.exists():
        return []
    text = pmd.read_text(encoding="utf-8", errors="replace")
    matches = list(SLIDE_RE.finditer(text))
    slides = []
    for i, m in enumerate(matches):
        n = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        desc = re.sub(r"\s+", " ", text[start:end]).strip()
        slides.append({
            "n": n,
            "filename": f"{n}.png",
            "title": title,
            "concept_text": (title + " " + desc).strip(),
        })
    # 같은 N 이 중복 추출되면(예: 공통룰 안에 N.png 언급) 첫 번째만 유지
    seen = set()
    uniq = []
    for s in slides:
        if s["n"] in seen:
            continue
        seen.add(s["n"])
        uniq.append(s)
    return sorted(uniq, key=lambda s: s["n"])


def gather_candidates(slug: str) -> list[Path]:
    img_dir = CARDNEWS / "images" / slug
    cands: list[Path] = []
    threshold = time.time() - RECENT_HOURS * 3600
    # 1) 다운로드 폴더의 최근 이미지
    if DOWNLOADS.exists():
        for p in DOWNLOADS.iterdir():
            if p.is_file() and p.suffix.lower() in ALLOWED:
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size >= MIN_SIZE and st.st_mtime >= threshold:
                    cands.append(p)
    # 2) 카드 이미지 폴더에 웹업로드된 느슨한 파일(N.png / card_*.png 은 제외)
    if img_dir.exists():
        for p in img_dir.iterdir():
            if not (p.is_file() and p.suffix.lower() in ALLOWED):
                continue
            if re.fullmatch(r"\d+\.png", p.name) or p.name.startswith("card_"):
                continue
            try:
                if p.stat().st_size >= MIN_SIZE:
                    cands.append(p)
            except OSError:
                pass
    # 중복 경로 제거, 시간순
    uniq = {str(p): p for p in cands}
    return sorted(uniq.values(), key=lambda p: p.stat().st_mtime)


def greedy_assign(scores: dict, n_c: int, n_s: int) -> dict:
    cells = sorted(scores.items(), key=lambda kv: -kv[1])
    used_c, used_s, out = set(), set(), {}
    for (ci, sj), _ in cells:
        if ci in used_c or sj in used_s:
            continue
        out[ci] = sj
        used_c.add(ci)
        used_s.add(sj)
        if len(used_s) >= n_s or len(used_c) >= n_c:
            break
    return out


def build_proposal(slug: str, slides: list[dict], candidates: list[Path]) -> dict:
    req_view = [{
        "filename": s["filename"],
        "variant": s["filename"],
        "section": "card",
        "chunk_index": s["n"],
        "concept_label": s["title"],
        "optional": False,
        "concept_text": s["concept_text"],
    } for s in slides]

    use_embed = ie.available() and bool(candidates) and bool(slides)
    engine = "image-embedding" if use_embed else ("fallback-order" if candidates else "none")
    assignments: list[dict] = []

    if use_embed:
        cand_vecs = ie.embed_images(candidates)
        ordered = [c for c in candidates if str(c) in cand_vecs]
        txt = ie.embed_texts([s["concept_text"] for s in slides])
        scores = {}
        for ci, c in enumerate(ordered):
            cv = cand_vecs[str(c)]
            for sj in range(len(slides)):
                scores[(ci, sj)] = ie.cosine(cv, txt[sj])
        assign = greedy_assign(scores, len(ordered), len(slides))
        for ci, c in enumerate(ordered):
            sj = assign.get(ci)
            alts = sorted(
                ((slides[k]["filename"], scores.get((ci, k), 0.0)) for k in range(len(slides))),
                key=lambda kv: -kv[1],
            )[:3]
            assignments.append({
                "candidate_path": str(c),
                "candidate_name": c.name,
                "proposed_filename": slides[sj]["filename"] if sj is not None else None,
                "confidence": round(scores.get((ci, sj), 0.0), 4) if sj is not None else None,
                "exact_name": False,
                "alternatives": [{"filename": fn, "score": round(s, 4)} for fn, s in alts],
                "dedup": None,
            })
    else:
        for ci, c in enumerate(candidates):
            sj = ci if ci < len(slides) else None
            assignments.append({
                "candidate_path": str(c),
                "candidate_name": c.name,
                "proposed_filename": slides[sj]["filename"] if sj is not None else None,
                "confidence": None,
                "exact_name": False,
                "alternatives": [],
                "dedup": None,
            })

    assigned = {a["proposed_filename"] for a in assignments if a["proposed_filename"]}
    unmatched = [s["filename"] for s in slides if s["filename"] not in assigned]
    return {
        "slug": slug,
        "engine": engine,
        "generated_at": time.time(),
        "requests": req_view,
        "assignments": assignments,
        "unmatched_requests": unmatched,
    }


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else ""
    if not slug:
        print("[card_propose] usage: cardnews_import_propose.py <slug>")
        return 0
    slides = parse_slides(slug)
    if not slides:
        print(f"[card_propose] prompt.md 슬라이드를 못 읽었습니다: {slug}")
    candidates = gather_candidates(slug)
    proposal = build_proposal(slug, slides, candidates)
    print(f"[card_propose] slug={slug} engine={proposal['engine']} slides={len(slides)} candidates={len(candidates)}")
    for a in proposal["assignments"]:
        conf = "" if a["confidence"] is None else f" ({a['confidence']:.2f})"
        print(f"  {a['candidate_name']} -> {a['proposed_filename']}{conf}")
    try:
        PROPOSAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROPOSAL_PATH.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[card_propose] 기록: {PROPOSAL_PATH}")
    except OSError as exc:
        print(f"[ERROR] 제안 파일 기록 실패: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
