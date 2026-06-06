# -*- coding: utf-8 -*-
"""
PhoneSpot 일러스트 의미 임베딩 엔진 (무료 로컬 모델)

목적: 일러스트 매칭/중복제거를 "부분 문자열 일치" 대신 "의미 유사도"로 한다.
      이 모듈은 1·2·3단계(개념 발굴형 스카우트 / 중복 제거 / 렌더 매칭 교체)가
      공통으로 쓰는 토대다.

원칙:
- 무료 로컬 모델만 사용(기본 fastembed + 다국어 MiniLM, ONNX/CPU, 한국어 지원).
- 모델이 없거나 로드 실패하면 기존 lexical 점수(codex_illustration_db.semantic_score)로
  **graceful 폴백**한다. 즉 이 모듈 때문에 파이프라인이 깨지지 않는다.
- 라이브러리 개념 임베딩은 디스크에 캐시한다(모델/텍스트가 바뀌면 자동 무효화).

설치(각 PC 1회, 온라인 필요):
    pip install fastembed numpy
    (또는 SETUP_EMBED.bat 실행. 첫 실행 시 모델 다운로드 후에는 오프라인 동작)

self-test:
    python scripts/codex_illust_embed.py selftest
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

# 같은 폴더의 일러스트 태그 DB (개념 텍스트 소스 + lexical 폴백)
import codex_illustration_db as db_mod

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CODEX_DIR = SHORTS / "codex"
CACHE_PATH = CODEX_DIR / "illust_embed_cache.json"

MODEL_NAME = os.getenv(
    "PHONESPOT_EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# 테스트에서 주입할 수 있는 임베더 오버라이드: texts -> np.ndarray (행=문장)
_embedder_override: Callable[[list[str]], np.ndarray] | None = None
_embedder_cache: Callable[[list[str]], np.ndarray] | None = None
_embedder_loaded = False


# --------------------------------------------------------------------------- #
# 임베더 로딩 (fastembed -> sentence-transformers -> None)
# --------------------------------------------------------------------------- #
def _load_embedder() -> Callable[[list[str]], np.ndarray] | None:
    # 1) fastembed (가벼움, torch 불필요)
    try:
        from fastembed import TextEmbedding  # type: ignore

        model = TextEmbedding(model_name=MODEL_NAME)

        def _fn(texts: list[str]) -> np.ndarray:
            return np.array(list(model.embed(list(texts))), dtype=np.float32)

        return _fn
    except Exception:
        pass
    # 2) sentence-transformers (있으면 사용)
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer(MODEL_NAME)

        def _fn2(texts: list[str]) -> np.ndarray:
            return np.array(model.encode(list(texts)), dtype=np.float32)

        return _fn2
    except Exception:
        pass
    return None


def set_embedder(fn: Callable[[list[str]], np.ndarray] | None) -> None:
    """테스트/대체용 임베더 주입. None이면 자동 로딩으로 되돌린다."""
    global _embedder_override, _embedder_loaded, _embedder_cache
    _embedder_override = fn
    _embedder_loaded = False
    _embedder_cache = None


def _embedder() -> Callable[[list[str]], np.ndarray] | None:
    global _embedder_loaded, _embedder_cache
    if _embedder_override is not None:
        return _embedder_override
    if not _embedder_loaded:
        _embedder_cache = _load_embedder()
        _embedder_loaded = True
    return _embedder_cache


def available() -> bool:
    """의미 임베딩이 실제로 가능한지(모델 로드 성공) 여부."""
    return _embedder() is not None


# --------------------------------------------------------------------------- #
# 임베딩 + 코사인
# --------------------------------------------------------------------------- #
def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def embed(texts: Iterable[str]) -> np.ndarray | None:
    """문장들을 L2 정규화된 벡터 행렬로. 모델 없으면 None."""
    fn = _embedder()
    if fn is None:
        return None
    items = [str(t or "") for t in texts]
    if not items:
        return np.zeros((0, 1), dtype=np.float32)
    vecs = np.asarray(fn(items), dtype=np.float32)
    if vecs.ndim == 1:
        vecs = vecs.reshape(1, -1)
    return _normalize(vecs)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


# --------------------------------------------------------------------------- #
# 개념 텍스트 + 라이브러리 인덱스(캐시)
# --------------------------------------------------------------------------- #
def concept_text(variant: str, entry: dict) -> str:
    """일러스트 1개를 의미적으로 대표하는 한국어 텍스트."""
    keywords = " ".join(str(k) for k in (entry.get("keywords") or []))
    tags = " ".join(str(t) for t in (entry.get("tags") or []))
    note = str(entry.get("note") or "")
    name = str(variant).replace("_", " ")
    return " ".join(p for p in (name, keywords, tags, note) if p).strip()


def _hash(text: str) -> str:
    return hashlib.sha1((MODEL_NAME + "\x00" + text).encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"model": MODEL_NAME, "items": {}}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if data.get("model") != MODEL_NAME:
            return {"model": MODEL_NAME, "items": {}}
        return data
    except Exception:
        return {"model": MODEL_NAME, "items": {}}


def _save_cache(cache: dict) -> None:
    try:
        CODEX_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # 캐시는 보조 기능, 실패해도 치명적이지 않음


def build_index(available_only: bool = False, db: dict | None = None) -> dict[str, np.ndarray]:
    """{variant: 벡터} 인덱스. 캐시 활용, 새 개념만 임베딩."""
    if not available():
        return {}
    db = db or db_mod.load_db()
    illus = db.get("illustrations", {}) or {}
    available_set = set(db_mod.library_variants()) if available_only else None

    cache = _load_cache()
    items = cache.setdefault("items", {})
    index: dict[str, np.ndarray] = {}
    to_embed: list[tuple[str, str]] = []  # (variant, text)

    for variant, entry in illus.items():
        if available_set is not None and variant not in available_set:
            continue
        text = concept_text(variant, entry)
        h = _hash(text)
        cached = items.get(variant)
        if cached and cached.get("hash") == h and cached.get("vec"):
            index[variant] = np.asarray(cached["vec"], dtype=np.float32)
        else:
            to_embed.append((variant, text))

    if to_embed:
        vecs = embed([t for _, t in to_embed])
        if vecs is not None:
            for (variant, text), vec in zip(to_embed, vecs):
                index[variant] = vec
                items[variant] = {"hash": _hash(text), "vec": vec.tolist()}
            _save_cache(cache)
    return index


# --------------------------------------------------------------------------- #
# 공개 API: rank / similarity / cover  (모델 없으면 lexical 폴백)
# --------------------------------------------------------------------------- #
def _lexical_rank(query: str, db: dict, available_only: bool, exclude: set[str], top_k: int | None):
    available_set = set(db_mod.library_variants()) if available_only else None
    rows = []
    for variant, entry in (db.get("illustrations", {}) or {}).items():
        if variant in exclude:
            continue
        if available_set is not None and variant not in available_set:
            continue
        score = db_mod.semantic_score(query, entry)
        if score > 0:
            rows.append((variant, float(score)))
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows[:top_k] if top_k else rows


def rank(
    query: str,
    available_only: bool = True,
    exclude: Iterable[str] = (),
    top_k: int | None = None,
    db: dict | None = None,
) -> list[tuple[str, float]]:
    """질의 텍스트에 의미적으로 가까운 일러스트 [(variant, score)] 내림차순.
    모델이 있으면 코사인(0~1), 없으면 lexical 점수로 폴백."""
    db = db or db_mod.load_db()
    exclude = set(exclude)
    if not available():
        return _lexical_rank(query, db, available_only, exclude, top_k)
    index = build_index(available_only=available_only, db=db)
    if not index:
        return _lexical_rank(query, db, available_only, exclude, top_k)
    qv = embed([query])
    if qv is None:
        return _lexical_rank(query, db, available_only, exclude, top_k)
    qv = qv[0]
    rows = [(v, cosine(qv, vec)) for v, vec in index.items() if v not in exclude]
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows[:top_k] if top_k else rows


def similarity(text_a: str, text_b: str) -> float:
    """두 텍스트 의미 유사도(0~1). 모델 없으면 토큰 자카드 근사."""
    if available():
        vecs = embed([text_a, text_b])
        if vecs is not None and vecs.shape[0] == 2:
            return max(0.0, cosine(vecs[0], vecs[1]))
    ta = set(str(text_a).lower().split())
    tb = set(str(text_b).lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def cover(concept: str, available_only: bool = False, db: dict | None = None) -> tuple[str, float]:
    """라이브러리에 이 개념이 이미 커버돼 있는지: 가장 가까운 (variant, score).
    중복 제거(2단계)에서 score가 임계 이상이면 '새로 만들지 말고 재사용'."""
    ranked = rank(concept, available_only=available_only, top_k=1, db=db)
    return ranked[0] if ranked else ("", 0.0)


# --------------------------------------------------------------------------- #
# self-test CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    print(f"[illust_embed] 모델: {MODEL_NAME}")
    print(f"[illust_embed] 임베딩 사용 가능: {available()}  (False면 lexical 폴백)")
    if arg != "selftest":
        print("usage: python scripts/codex_illust_embed.py selftest")
        return 0
    queries = [
        "송금 후 1시간 안에 거래은행에 지급정지 신청",
        "카카오톡으로 자녀를 사칭한 메신저피싱 문자",
        "새 폰으로 사진 연락처 데이터 옮기기",
        "갤럭시 언팩 키노트 공개 일정",
    ]
    for q in queries:
        print(f"\n질의: {q}")
        for variant, score in rank(q, available_only=False, top_k=5):
            print(f"  {score:.3f}  {variant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
