# -*- coding: utf-8 -*-
"""
import 제안기 (패널 검수용)

GPT 로 그린 그림들을 다운로드한 뒤, "어느 그림이 어느 요청인지"를 사람이
일일이 눈으로 맞추지 않도록, 그림 내용(CLIP)으로 자동 배정을 '제안'한다.
파일을 옮기지는 않는다 — 제안만 IMPORT_PROPOSAL.json 으로 쓴다.
패널이 이 제안을 썸네일/신뢰도와 함께 보여주고, 사람이 패널 안에서 확정한다.

매칭 기준: 파일명이 아니라 "그림이 실제로 무엇을 그렸는가" ↔ "요청이 무엇을
원하는가(개념 텍스트)" 의 교차모달 코사인. 그래서 잘못된 이름으로 라이브러리가
오염되는 걸 사람이 확정 단계에서 막을 수 있다.

폴백: codex_image_embed 가 사용 불가하면(모델 미설치) engine="fallback-mtime"
      으로 기존처럼 다운로드 시간순(zip) 매핑을 제안한다. 패널에서 고치면 된다.

사용:
    python scripts/codex_import_propose.py [slug]
출력:
    CODEX_VIDEO_DESK/IMPORT_PROPOSAL.json  (성공/폴백 모두 항상 기록, 종료코드 0)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import codex_image_embed as ie

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"
DOWNLOADS = Path.home() / "Downloads"
DROP = DESK / "ILLUSTRATION_DROP"
ILLUST = SHORTS / "public" / "assets" / "illustrations"
PROPOSAL_PATH = DESK / "IMPORT_PROPOSAL.json"
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}
MIN_SIZE = 10_000

DEDUP_WARN = 0.90   # 후보가 기존 라이브러리 그림과 이만큼 비슷하면 "중복 가능" 경고
DEDUP_SKIP = 0.95   # 이만큼 비슷하면 "사실상 동일" → 기본 '사용 안 함'(기존 그림 재사용) 제안
# 주의: 이미지-이미지 코사인 스케일. PC에서 실제 중복쌍을 보며 조절.


def concept_text(item: dict) -> str:
    """요청이 원하는 그림을 의미적으로 대표하는 텍스트(이미지와 교차매칭용)."""
    variant = str(item.get("variant") or "")
    parts = [str(item.get("concept_label") or ""), variant.replace("_", " ")]
    parts += [str(k) for k in (item.get("keywords") or [])]
    parts += [str(t) for t in (item.get("tags") or [])]
    src = str(item.get("source_text") or "").strip()
    if src:
        parts.append(src[:160])
    return " ".join(p for p in parts if p).strip()


def load_payload() -> tuple[str, dict, float]:
    slug_path = DESK / "LATEST_SLUG.txt"
    report_path = DESK / "LATEST_PROMPT.json"
    if not report_path.exists():
        raise SystemExit("[ERROR] LATEST_PROMPT.json 이 없습니다. 먼저 '1. 영상용 프롬프트 준비'.")
    slug = slug_path.read_text(encoding="utf-8").strip() if slug_path.exists() else ""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    threshold = report_path.stat().st_mtime - 2
    return slug, payload, threshold


def pending_requests(payload: dict) -> list[dict]:
    """검수에서 그림을 배정할 수 있는 누락 요청 목록.
    자동발굴(concept_scout)도 사람이 그렸으면 배정할 수 있게 포함하되 optional 로 표시한다.
    (렌더를 막지는 않는다 - 그건 codex_import_downloads.py 가 따로 처리.)
    필수 요청을 먼저, 선택(자동발굴) 요청을 뒤에 둔다."""
    mandatory: list[dict] = []
    optional: list[dict] = []
    for item in payload.get("requests", []) or []:
        fn = item.get("filename")
        if not fn or (ILLUST / fn).exists():
            continue
        row = dict(item)
        if item.get("source") == "concept_scout":
            row["optional"] = True
            optional.append(row)
        else:
            row["optional"] = False
            mandatory.append(row)
    return mandatory + optional


def gather_candidates(threshold: float, exclude: set[Path]) -> list[Path]:
    cands: list[Path] = []
    for folder in (DROP, DOWNLOADS):
        if not folder.exists():
            continue
        for p in folder.iterdir():
            if not p.is_file() or p.suffix.lower() not in ALLOWED:
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size < MIN_SIZE or st.st_mtime < threshold or p in exclude:
                continue
            cands.append(p)
    return sorted(cands, key=lambda p: p.stat().st_mtime)


def greedy_assign(scores: dict[tuple[int, int], float], n_c: int, n_r: int) -> dict[int, int]:
    """후보 i -> 요청 j 전역 최대값 우선 배정(1:1)."""
    cells = sorted(scores.items(), key=lambda kv: -kv[1])
    used_c, used_r = set(), set()
    out: dict[int, int] = {}
    for (ci, rj), _ in cells:
        if ci in used_c or rj in used_r:
            continue
        out[ci] = rj
        used_c.add(ci)
        used_r.add(rj)
        if len(used_r) >= n_r or len(used_c) >= n_c:
            break
    return out


def build_proposal(slug: str, requests: list[dict], candidates: list[Path],
                   exact: dict[str, Path]) -> dict:
    req_view = [{
        "filename": r.get("filename"),
        "variant": r.get("variant"),
        "section": r.get("section", ""),
        "chunk_index": int(r.get("chunk_index", 0)),
        "concept_label": r.get("concept_label") or "",
        "optional": bool(r.get("optional")),
        "concept_text": concept_text(r),
    } for r in requests]

    assignments: list[dict] = []
    # 1) ILLUSTRATION_DROP 에 요청 파일명 그대로 들어온 건 신뢰도 1.0 으로 확정 제안
    for fn, path in exact.items():
        assignments.append({
            "candidate_path": str(path),
            "candidate_name": path.name,
            "proposed_filename": fn,
            "confidence": 1.0,
            "exact_name": True,
            "alternatives": [],
            "dedup": None,
        })

    use_embed = ie.available() and bool(candidates)
    engine = "image-embedding" if use_embed else ("fallback-mtime" if candidates else "none")

    if use_embed:
        lib_index = ie.library_image_index()
        cand_vecs = ie.embed_images(candidates)
        req_texts = [concept_text(r) for r in requests]
        txt_mat = ie.embed_texts(req_texts) if requests else None
        # 점수 행렬
        scores: dict[tuple[int, int], float] = {}
        ordered_cands = [c for c in candidates if str(c) in cand_vecs]
        for ci, c in enumerate(ordered_cands):
            cv = cand_vecs[str(c)]
            if txt_mat is not None:
                for rj in range(len(requests)):
                    scores[(ci, rj)] = ie.cosine(cv, txt_mat[rj])
        assign = greedy_assign(scores, len(ordered_cands), len(requests)) if requests else {}
        for ci, c in enumerate(ordered_cands):
            cv = cand_vecs[str(c)]
            rj = assign.get(ci)
            alts = sorted(
                ((requests[k].get("filename"), scores.get((ci, k), 0.0)) for k in range(len(requests))),
                key=lambda kv: -kv[1],
            )[:3]
            dv, ds = ie.nearest_library_image(cv, lib_index)
            dedup = None
            if ds >= DEDUP_WARN:
                dedup = {"variant": dv, "score": round(ds, 4), "skip": ds >= DEDUP_SKIP}
            assignments.append({
                "candidate_path": str(c),
                "candidate_name": c.name,
                "proposed_filename": requests[rj].get("filename") if rj is not None else None,
                "confidence": round(scores.get((ci, rj), 0.0), 4) if rj is not None else None,
                "exact_name": False,
                "alternatives": [{"filename": fn, "score": round(s, 4)} for fn, s in alts],
                "dedup": dedup,
            })
    else:
        # 폴백: 시간순 zip 매핑 제안(기존 동작과 동일), 신뢰도 없음
        for ci, c in enumerate(candidates):
            rj = ci if ci < len(requests) else None
            assignments.append({
                "candidate_path": str(c),
                "candidate_name": c.name,
                "proposed_filename": requests[rj].get("filename") if rj is not None else None,
                "confidence": None,
                "exact_name": False,
                "alternatives": [],
                "dedup": None,
            })

    assigned_fns = {a["proposed_filename"] for a in assignments if a["proposed_filename"]}
    unmatched = [r.get("filename") for r in requests if r.get("filename") not in assigned_fns]

    return {
        "slug": slug,
        "engine": engine,
        "generated_at": time.time(),
        "requests": req_view,
        "assignments": assignments,
        "unmatched_requests": unmatched,
    }


def main() -> int:
    slug_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        slug, payload, threshold = load_payload()
    except SystemExit as exc:
        print(exc)
        return 0
    slug = slug or slug_arg
    requests = pending_requests(payload)

    # 정확한 파일명으로 DROP 에 미리 들어온 것
    exact: dict[str, Path] = {}
    for r in requests:
        fn = r.get("filename")
        p = DROP / fn if fn else None
        if p and p.exists() and p.is_file() and p.stat().st_size >= MIN_SIZE:
            exact[fn] = p
    exclude = set(exact.values())
    remaining = [r for r in requests if r.get("filename") not in exact]
    candidates = gather_candidates(threshold, exclude)

    proposal = build_proposal(slug, remaining, candidates, exact)
    # 요약 출력
    print(f"[propose] slug={slug} engine={proposal['engine']}")
    print(f"[propose] pending={len(requests)} exact={len(exact)} candidates={len(candidates)}")
    for a in proposal["assignments"]:
        conf = "" if a["confidence"] is None else f" ({a['confidence']:.2f})"
        dd = " [중복가능]" if a.get("dedup") else ""
        print(f"  {a['candidate_name']} -> {a['proposed_filename']}{conf}{dd}")
    if proposal["unmatched_requests"]:
        print(f"[propose] 후보 부족: {proposal['unmatched_requests']}")

    try:
        PROPOSAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROPOSAL_PATH.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[propose] 기록: {PROPOSAL_PATH}")
    except OSError as exc:
        print(f"[ERROR] 제안 파일 기록 실패: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
