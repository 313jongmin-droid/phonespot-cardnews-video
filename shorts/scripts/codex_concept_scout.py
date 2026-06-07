# -*- coding: utf-8 -*-
"""
개념 발굴형 일러스트 스카우트 (1단계)

기존 codex_illustration_scout.py 는 13개 고정 규칙(RULES)에 걸리는 갭만 채웠다.
이 모듈은 그 한계를 넘어, 라이브러리에 마땅한 그림이 없는 청크에서
**범용 개념(concept)** 을 발굴해 신규 일러스트 요청을 만든다.

목표(가이드 참고): 콘텐츠 전용 1회용 그림이 아니라 재사용 가능한 개념을 쌓아
라이브러리만으로 수렴하게 한다. 그래서 두 가지를 지킨다.
  1) 개념 추상화 — 청크에서 날짜/금액/모델명 같은 1회용 디테일을 제거하고 일반 개념만 남긴다.
  2) 의미 중복제거 — 새 개념을 만들기 전에 codex_illust_embed.cover() 로 기존 라이브러리와
     비교해 충분히 비슷하면 새로 만들지 않고 재사용한다.

안전:
- 기존 라이브 파이프라인(codex_illustration_scout.py, codex_semantic_visual_match.py)은 건드리지 않는다.
- 임베딩 모델이 없으면 codex_illust_embed 가 lexical 로 폴백하므로 그대로 동작한다(품질만 낮아짐).
- 신규 개념은 태그 DB(illustration_tag_db.json)에 available=false 로 등록된다.
  사람이 GPT로 그려서 png 를 ILLUSTRATION_DROP / illustrations 에 넣으면 available 로 승격된다.

사용:
    python scripts/codex_concept_scout.py <slug>
    python scripts/codex_concept_scout.py <slug> --dry-run   # DB/요청 파일 기록 없이 미리보기
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import codex_illustration_db as db_mod
import codex_illust_embed as ce
import codex_semantic_visual_match as svm
import codex_illustration_scout as scout

CARD_OUTPUT = svm.CARD_OUTPUT

MAX_NEW_CONCEPTS = 5          # 영상 1편당 새로 만들 개념 상한
COVER_COSINE = 0.55           # 임베딩 사용 시: 이 이상 유사하면 "이미 커버됨"
COVER_LEXICAL = 12            # lexical 폴백 시: 이 이상이면 "이미 커버됨"

# 1회용(비범용) 토큰 제거: 숫자/날짜/금액/퍼센트/모델명/특정 브랜드 등
ONE_OFF_PATTERNS = [
    re.compile(r"\d+(?:[.,]\d+)?\s*(?:원|만원|억원|조원|달러|유로|퍼센트|%|개|건|명|배|년|월|일|시간|분|초|기가|gb|tb|mb|w|mah)", re.I),
    re.compile(r"\d+"),
    re.compile(r"(?:갤럭시|아이폰|갤럭시탭|아이패드|갤럭시폴드|갤럭시플립|픽셀)\s*[a-z0-9+.-]*", re.I),
    re.compile(r"\b(?:s\d{1,2}|z\s*폴드\s*\d+|z\s*플립\s*\d+|ios\s*\d+|one\s*ui\s*\d+)\b", re.I),
    re.compile(r"\b(?:wwdc|nfc|rcs|hdr)\s*\d*\b", re.I),
    re.compile(r"\b(?:iphone|ipad|ipados|ios|macos|android|galaxy|pixel|skt|kt|lgu|one\s*ui)\b", re.I),
    re.compile(r"(?:\uc544\uc774\ud3f0|\uc544\uc774\ud328\ub4dc|\uc5d0\uc774\ub2ff|\uc775\uc2dc\uc624)"),
]

STOPWORDS = {
    "그리고", "하지만", "그래서", "그러나", "또한", "이것", "저것", "그것", "여기", "거기",
    "오늘", "지금", "바로", "정말", "매우", "아주", "조금", "약간", "모두", "각각", "경우",
    "이번", "다음", "처음", "마지막", "관련", "위해", "통해", "대해", "기준", "확인", "필요",
    "사용", "방법", "내용", "설명", "안내", "수법", "체크", "주의", "뉴스", "기사",
    "다만", "이후", "이전", "이상", "이하", "직후", "시작", "모든", "다시", "함께",
    "같은", "매번", "무조건", "혹시", "또는", "그냥", "직접", "우선", "먼저", "결국",
    "특히", "정도", "가지", "부분", "버전", "기능", "처음부터",
}

# 한국어 조사 제거(명사 본체가 2자 이상 남을 때만)
JOSA_RE = re.compile(
    r"(?:으로서|으로써|으로|로서|로써|에서|"
    r"에게서|에게|한테서|한테|까지|부터|마저|"
    r"조차|이라도|라도|이며|이고|이랑|랑|과|와|"
    r"을|를|이|가|은|는|에|의|도|만|들)$"
)


def strip_josa(token: str) -> str:
    m = JOSA_RE.search(token)
    if m and (len(token) - len(m.group(0))) >= 2:
        return token[: m.start()]
    return token


def clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_one_off(text: str) -> str:
    """1회용 디테일(숫자/날짜/모델명 등)을 제거해 개념을 일반화한다."""
    out = " " + str(text or "") + " "
    for pat in ONE_OFF_PATTERNS:
        out = pat.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


# 한국어 서술어/종결형(개념 명사가 아님) 제외용
PREDICATE_RE = re.compile(
    r"(?:합니다|됩니다|입니다|습니다|니다|하세요|하시려면|하시기|하십시오|바랍니다|드립니다|"
    r"있고|있습니다|없습니다|가능합니다|봅니다|냅니다|줍니다|십시오|면서|으며|에서만|에서|으로)$"
)


def _is_predicate(token: str) -> bool:
    return bool(PREDICATE_RE.search(token)) and len(token) >= 3


def extract_concept(chunk: str, topic: str) -> dict:
    """청크/주제에서 재사용 가능한 개념 명사 키워드를 뽑는다.
    1회용 디테일·브랜드·한국어 서술어를 제외하고 등장 순서를 유지한다."""
    base = strip_one_off(clean(chunk) + " " + clean(topic))
    raw = re.findall(r"[가-힣]{2,}|[A-Za-z]{3,}", base)
    seen = set()
    tokens = []
    for tok in raw:
        t = strip_josa(tok.strip())
        if len(t) < 2:
            continue
        low = t.lower()
        if low in STOPWORDS or low in seen:
            continue
        if _is_predicate(t):  # 합니다/됩니다/에서만 등 서술어 제외
            continue
        seen.add(low)
        tokens.append(t)
    # 등장 순서 유지(명사가 보통 앞쪽). 길이 정렬은 서술어를 끌어올리므로 쓰지 않는다.
    keywords = tokens[:5]
    label = " ".join(keywords[:2]) if keywords else clean(topic) or "개념"
    return {"label": label, "keywords": keywords}


def concept_id(keywords: list[str]) -> str:
    """개념 키워드로 결정적 ID 생성 → 영상이 달라도 같은 개념이면 같은 ID(자연 중복제거)."""
    key = " ".join(sorted(k.lower() for k in keywords)) or "empty"
    return "cpt_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


# ── 읽기 쉬운 파일명: <영어슬러그>_<hash8>.png ──────────────────────────────
# 영어 슬러그는 '보이는 이름'일 뿐, 개념 동일성은 항상 hash8(키워드 해시)가 보장한다.
# Gemini로 번역(키 있을 때) → 실패/키없음이면 cpt_<hash8> 로 폴백(기존과 동일, 무해).
# 슬러그가 PC/실행마다 달라도 의미 중복제거(ce.cover)가 같은 개념을 재사용하므로 안전.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_GEMINI_KEY_FILE = _REPO_ROOT / "_secrets" / "gemini_key.txt"
_NAME_CACHE_FILE = _REPO_ROOT / "shorts" / "config" / "concept_name_cache.json"
_GEMINI_TEXT_MODEL = os.environ.get("PHONESPOT_GEMINI_TEXT_MODEL", "gemini-2.5-flash")


def _slugify_ascii(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:40]


def _load_name_cache() -> dict:
    try:
        return json.loads(_NAME_CACHE_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _save_name_cache(cache: dict) -> None:
    try:
        _NAME_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _NAME_CACHE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, _NAME_CACHE_FILE)
    except Exception:
        pass


def _gemini_english_slug(label: str, keywords: list[str]) -> str | None:
    """개념을 1~3단어 영문 snake_case 슬러그로 번역. 키없음/오류/타임아웃이면 None."""
    try:
        key = _GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not key.startswith("AIza"):
        return None
    prompt = (
        "Convert this Korean illustration concept into a short English filename slug. "
        "Rules: 1-3 words, lowercase, snake_case, ASCII letters only, no digits, describe "
        "the general reusable visual concept. Output ONLY the slug.\n"
        "Concept: " + (label or "") + "\nKeywords: " + ", ".join(keywords)
    )
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + _GEMINI_TEXT_MODEL + ":generateContent?key=" + key)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _slugify_ascii(text) or None
    except Exception:
        return None


def readable_variant(label: str, keywords: list[str]) -> str:
    """<영어슬러그>_<hash8> 반환. 번역 불가 시 cpt_<hash8>(기존). 캐시로 재번역/변동 최소화."""
    hash8 = concept_id(keywords)[4:]  # 'cpt_' 제거
    cache = _load_name_cache()
    slug = cache.get(hash8)
    if not slug:
        slug = _gemini_english_slug(label, keywords)
        if slug:
            cache[hash8] = slug
            _save_name_cache(cache)
    return (slug + "_" + hash8) if slug else ("cpt_" + hash8)


def cover_threshold() -> float:
    return COVER_COSINE if ce.available() else COVER_LEXICAL


def eligible_visual(visual: dict) -> bool:
    return isinstance(visual, dict) and visual.get("type") not in {"image", "logo", "mascot"}


def find_gaps(data: dict, slug: str, db: dict) -> list[dict]:
    """라이브러리에 충분히 맞는 그림이 없는 청크 목록."""
    threshold = cover_threshold()
    gaps = []
    for section_name, section in svm.section_items(data):
        if section_name == "cta":
            continue
        chunks = svm.section_chunks(section)
        visuals = section.get("chunk_visuals", []) or []
        for idx, _ in enumerate(chunks):
            if idx >= len(visuals) or not eligible_visual(visuals[idx]):
                continue
            context = svm.context_for(section, idx)
            ranked = ce.rank(context, available_only=False, top_k=1, db=db)
            best_score = ranked[0][1] if ranked else 0.0
            if best_score < threshold:
                gaps.append({
                    "section": section_name,
                    "chunk_index": idx,
                    "text": chunks[idx],
                    "context": context,
                    "best_existing": ranked[0][0] if ranked else "",
                    "best_score": round(best_score, 3),
                })
    return gaps


def existing_uncovered_gaps(slug: str) -> list[dict]:
    """기존 codex_illustration_scout.py 가 남긴 약한 매핑 목록을 갭 후보로 읽는다."""
    jpath = CARD_OUTPUT / slug / "codex_illustration_requests.json"
    if not jpath.exists():
        return []
    try:
        data = json.loads(jpath.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    out = []
    for g in (data.get("uncovered_gaps") or []):
        out.append({
            "section": g.get("section"),
            "chunk_index": int(g.get("chunk_index", 0)),
            "text": str(g.get("text", "")),
            "best_existing": str(g.get("variant", "")),
            "best_score": 0.0,
        })
    return out


def build_request(concept: dict, variant: str, gap: dict) -> dict:
    prompt = (
        scout.STYLE
        + "\n\n핵심 콘셉트(재사용 가능한 일반 개념): " + concept["label"]
        + "\n표현할 의미 키워드: " + ", ".join(concept["keywords"])
        + "\n주의: 특정 기사에서만 쓸 디테일(숫자/날짜/금액/브랜드/모델명/인물)은 절대 넣지 말 것."
    )
    return {
        "variant": variant,
        "filename": variant + ".png",
        "concept_label": concept["label"],
        "keywords": concept["keywords"],
        "section": gap["section"],
        "chunk_index": gap["chunk_index"],
        "source_text": gap["text"],
        "nearest_existing": gap["best_existing"],
        "nearest_score": gap["best_score"],
        "prompt": prompt,
        "status": "requested",
    }


def register_concept(db: dict, variant: str, concept: dict) -> None:
    """신규 개념을 태그 DB에 등록(available=false). 이후 매칭/중복제거에서 후보가 된다."""
    illus = db.setdefault("illustrations", {})
    entry = illus.setdefault(variant, {})
    entry["keywords"] = db_mod.clean_words(list(concept["keywords"]))
    tags = entry.get("tags", []) or []
    if "auto" not in tags:
        tags = tags + ["auto"]
    entry["tags"] = tags
    entry["note"] = "자동 발굴 개념: " + concept["label"]
    entry.setdefault("available", False)


def scout_concepts(slug: str, dry_run: bool = False) -> dict:
    path = CARD_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        return {"ok": False, "error": "missing: " + str(path)}

    data = svm.read_json(path)
    db = db_mod.load_db()  # SEED + 라이브러리 병합본
    gaps = find_gaps(data, slug, db)
    # 기존 일러스트 스카우트가 표시한 약한 매핑(uncovered_gaps)도 갭 소스로 포함한다.
    # lexical 모드에서 find_gaps 가 갭을 못 잡아도 이쪽에서 후보가 들어온다.
    seen_slots = {(g["section"], g["chunk_index"]) for g in gaps}
    for g in existing_uncovered_gaps(slug):
        slot = (g["section"], g["chunk_index"])
        if slot not in seen_slots:
            gaps.append(g)
            seen_slots.add(slot)

    threshold = cover_threshold()
    requests = []
    reused = []
    minted_ids = set()

    for gap in gaps:
        if len(requests) >= MAX_NEW_CONCEPTS:
            break
        concept = extract_concept(gap["text"], "")
        if not concept["keywords"]:
            continue
        variant = readable_variant(concept["label"], concept["keywords"])
        # 이미 이번 실행에서 만든 개념이면 스킵(영상 내 중복)
        if variant in minted_ids:
            continue
        # 의미 중복제거: 기존 라이브러리/이미 등록된 개념과 충분히 비슷하면 재사용
        cov_variant, cov_score = ce.cover(" ".join(concept["keywords"]), available_only=False, db=db)
        if cov_score >= threshold and cov_variant and cov_variant != variant:
            reused.append({
                "section": gap["section"], "chunk_index": gap["chunk_index"],
                "concept": concept["label"], "reused_variant": cov_variant,
                "score": round(cov_score, 3),
            })
            continue
        # 신규 개념 확정
        register_concept(db, variant, concept)
        minted_ids.add(variant)
        requests.append(build_request(concept, variant, gap))

    result = {
        "ok": True, "slug": slug, "engine": "embedding" if ce.available() else "lexical-fallback",
        "threshold": threshold, "gaps": len(gaps),
        "new_concepts": len(requests), "reused": len(reused),
        "requests": requests, "reused_detail": reused,
    }

    if not dry_run:
        if requests:
            # DB 저장(신규 개념 영구 등록) + 개념 요청 파일 출력
            db_mod.write_json(db_mod.DB_PATH, db)
            out_dir = CARD_OUTPUT / slug
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "codex_concept_requests.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "codex_concept_requests.md").write_text(render_md(result), encoding="utf-8")
        # 패널 노출: 기존 일러스트 요청 파일에 병합(개념 요청 추가/갱신, 멱등)
        try:
            merge_into_illustration_requests(slug, requests)
        except Exception as exc:
            print("[concept_scout] (참고) 요청 병합 생략:", exc)
    return result


def merge_into_illustration_requests(slug: str, requests: list) -> None:
    """개념 요청을 패널이 읽는 codex_illustration_requests.json/.md 에 멱등 병합한다.
    기존 일러스트 스카우트 요청은 보존하고, source=concept_scout 항목만 교체한다."""
    out_dir = CARD_OUTPUT / slug
    jpath = out_dir / "codex_illustration_requests.json"
    mpath = out_dir / "codex_illustration_requests.md"
    data = {}
    if jpath.exists():
        try:
            data = json.loads(jpath.read_text(encoding="utf-8-sig"))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 3)
    data.setdefault("slug", slug)
    data["uncovered_gaps"] = data.get("uncovered_gaps") or []
    base = [r for r in (data.get("requests") or [])
            if isinstance(r, dict) and r.get("source") != "concept_scout"]
    for req in requests:
        base.append({
            "variant": req["variant"],
            "filename": req["filename"],
            "section": req["section"],
            "chunk_index": req["chunk_index"],
            "reason": "자동 발굴 범용 개념: " + req["concept_label"],
            "quality_gap": "기존 최근접 " + (req["nearest_existing"] or "-") + " (" + str(req["nearest_score"]) + ")",
            "tags": ["auto", "concept"],
            "concept_label": req["concept_label"],
            "source_text": req["source_text"],
            "keywords": req["keywords"],
            "prompt": req["prompt"],
            "status": "requested",
            "source": "concept_scout",
        })
    data["requests"] = base
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    START = "<!-- CONCEPT_SCOUT_START -->"
    END = "<!-- CONCEPT_SCOUT_END -->"
    md = mpath.read_text(encoding="utf-8", errors="replace") if mpath.exists() else ""
    if START in md and END in md:
        md = md.split(START)[0].rstrip() + md.split(END, 1)[1]
    engine = "embedding" if ce.available() else "lexical-fallback"
    lines = [START, "", "## 추가 범용 일러스트 요청(개념 발굴)  [engine: " + engine + "]"]
    if not requests:
        lines.append("- 신규 개념 없음 (라이브러리가 이미 충분히 커버).")
    for i, req in enumerate(requests, 1):
        lines += [
            "",
            "### C" + str(i) + ". `" + req["filename"] + "` (" + req["concept_label"] + ")",
            "- 위치: " + req["section"] + " 청크 " + str(req["chunk_index"] + 1),
            "- 키워드: " + ", ".join(req["keywords"]),
            "",
            "```text", req["prompt"], "```",
        ]
    lines.append(END)
    block = "\n".join(lines)
    md = (md.rstrip() + "\n\n" + block + "\n") if md.strip() else (block + "\n")
    mpath.write_text(md, encoding="utf-8")


def render_md(result: dict) -> str:
    lines = [
        "# 개념 발굴 요청: " + result["slug"],
        "",
        "엔진: " + result["engine"] + " / 갭 " + str(result["gaps"]) +
        "개 / 신규개념 " + str(result["new_concepts"]) + "개 / 재사용 " + str(result["reused"]) + "개",
        "",
        "## 새로 만들 범용 개념(요청)",
    ]
    if not result["requests"]:
        lines.append("- 없음 (라이브러리가 이미 충분히 커버)")
    for i, req in enumerate(result["requests"], 1):
        lines += [
            "",
            "### " + str(i) + ". `" + req["filename"] + "`  (" + req["concept_label"] + ")",
            "- 위치: " + req["section"] + " 청크 " + str(req["chunk_index"] + 1),
            "- 키워드: " + ", ".join(req["keywords"]),
            "- 출처 청크: " + req["source_text"],
            "- 가장 가까운 기존: " + (req["nearest_existing"] or "-") + " (" + str(req["nearest_score"]) + ")",
            "",
            "```text",
            req["prompt"],
            "```",
        ]
    if result["reused_detail"]:
        lines += ["", "## 기존 개념 재사용(생성 안 함)"]
        for r in result["reused_detail"]:
            lines.append("- " + r["section"] + " C" + str(r["chunk_index"] + 1) + ": '" +
                         r["concept"] + "' → " + r["reused_variant"] + " (" + str(r["score"]) + ")")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    slugs = [a for a in args if not a.startswith("--")]
    if not slugs:
        print("usage: python scripts/codex_concept_scout.py <slug> [--dry-run]")
        return 2
    try:
        res = scout_concepts(slugs[0], dry_run=dry)
    except Exception as exc:
        print("[concept_scout] 예외로 건너뜀(파이프라인 비차단): " + str(exc))
        return 0
    if not res.get("ok"):
        print("[concept_scout] " + res.get("error", "failed"))
        return 1
    print("[concept_scout] 엔진=" + res["engine"] + " 갭=" + str(res["gaps"]) +
          " 신규개념=" + str(res["new_concepts"]) + " 재사용=" + str(res["reused"]) +
          (" (dry-run)" if dry else ""))
    for req in res["requests"]:
        print("  + " + req["filename"] + "  (" + req["concept_label"] + ")  ← " + req["source_text"][:30])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
