# -*- coding: utf-8 -*-
"""
PhoneSpot 그림(이미지) 내용 임베딩 엔진 (무료 로컬 CLIP)

목적: 일러스트 재사용/배정을 "파일명/태그"가 아니라 "그림이 실제로 무엇을
      그렸는가(픽셀 내용)"로 판단한다. 그래서 파일명이 틀려도 라이브러리가
      오염되지 않고, 내용으로 올바른 그림을 찾는다.

핵심: jina-clip-v1 은 이미지와 텍스트를 같은 768차원 공간에 임베딩하고
      다국어(한국어 포함)를 지원한다 → 한국어 청크 텍스트 ↔ 그림 교차매칭이 된다.
        - 이미지:  fastembed.ImageEmbedding("jinaai/jina-clip-v1")
        - 텍스트:  fastembed.TextEmbedding("jinaai/jina-clip-v1")

원칙(codex_illust_embed.py 와 동일):
- 무료 로컬 모델만 사용(ONNX/CPU). 모델이 없거나 로드 실패하면 available()=False 로
  graceful 폴백한다. 즉 이 모듈 때문에 파이프라인이 깨지지 않는다.
- 라이브러리 그림 지문은 디스크에 캐시한다(파일 mtime/size 가 바뀌면 자동 무효화).
- 태그 DB(illustration_tag_db.json)는 건드리지 않는다. 지문은 별도 캐시에 둔다.

설치(각 PC 1회, 온라인 필요):
    pip install fastembed numpy pillow
    (SETUP_EMBED.bat 가 첫 실행 시 모델을 받아둔다. 이후 오프라인 동작)

self-test:
    python scripts/codex_image_embed.py selftest
    python scripts/codex_image_embed.py check      # 사용 가능하면 종료코드 0, 아니면 1
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Callable, Iterable

try:
    import numpy as np
except Exception:  # numpy 미설치 시에도 폴백으로 동작
    np = None

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"
CODEX_DIR = SHORTS / "codex"
CACHE_PATH = CODEX_DIR / "image_embed_cache.json"

# 이미지/텍스트가 같은 공간에 들어가는 다국어 CLIP
MODEL_NAME = os.getenv("PHONESPOT_CLIP_MODEL", "jinaai/jina-clip-v1")

# 모델 로드(첫 다운로드 포함) 최대 대기 초. 초과하면 '사용 불가'로 보고 폴백시킨다.
# 캐시된 PC(부사수)는 수 초 내 로드 → 영향 없음. 모델 없는 PC(로컬)는 빨리 폴백 → 패널 무한대기/Failed to fetch 방지.
_LOAD_TIMEOUT = float(os.getenv("PHONESPOT_CLIP_LOAD_TIMEOUT", "25"))
# HuggingFace 다운로드 자체에도 타임아웃(멈춘 연결이 try/except로 떨어지게).
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "15")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "10")


def _call_with_timeout(fn: "Callable[[], object]", seconds: float):
    """fn()을 별도 스레드로 돌려 seconds 안에 끝나면 결과, 아니면 None.
    멈춘 모델 다운로드(예외 아님)도 None으로 떨어뜨려 폴백을 강제한다.
    초과 시 스레드는 daemon이라 프로세스 종료와 함께 정리됨."""
    import threading

    box: dict = {}

    def _run():
        try:
            box["v"] = fn()
        except Exception:
            box["v"] = None

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        return None
    return box.get("v")

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}

# 테스트 주입용 오버라이드: paths(list[str]) -> ndarray, texts(list[str]) -> ndarray
_img_override: Callable[[list[str]], "np.ndarray"] | None = None
_txt_override: Callable[[list[str]], "np.ndarray"] | None = None
_img_cache_fn: Callable[[list[str]], "np.ndarray"] | None = None
_txt_cache_fn: Callable[[list[str]], "np.ndarray"] | None = None
_img_loaded = False
_txt_loaded = False


# --------------------------------------------------------------------------- #
# 임베더 로딩
# --------------------------------------------------------------------------- #
def _load_image_embedder() -> Callable[[list[str]], "np.ndarray"] | None:
    def _build():
        from fastembed import ImageEmbedding  # type: ignore

        model = ImageEmbedding(model_name=MODEL_NAME)

        def _fn(paths: list[str]) -> "np.ndarray":
            return np.array(list(model.embed(list(paths))), dtype=np.float32)

        return _fn

    # 모델 생성(첫 다운로드 포함)이 _LOAD_TIMEOUT 초 넘으면 None → 폴백.
    return _call_with_timeout(_build, _LOAD_TIMEOUT)


def _load_text_embedder() -> Callable[[list[str]], "np.ndarray"] | None:
    def _build():
        from fastembed import TextEmbedding  # type: ignore

        model = TextEmbedding(model_name=MODEL_NAME)

        def _fn(texts: list[str]) -> "np.ndarray":
            return np.array(list(model.embed(list(texts))), dtype=np.float32)

        return _fn

    return _call_with_timeout(_build, _LOAD_TIMEOUT)


def set_image_embedder(fn: Callable[[list[str]], "np.ndarray"] | None) -> None:
    global _img_override, _img_loaded, _img_cache_fn
    _img_override = fn
    _img_loaded = False
    _img_cache_fn = None


def set_text_embedder(fn: Callable[[list[str]], "np.ndarray"] | None) -> None:
    global _txt_override, _txt_loaded, _txt_cache_fn
    _txt_override = fn
    _txt_loaded = False
    _txt_cache_fn = None


def _image_embedder() -> Callable[[list[str]], "np.ndarray"] | None:
    global _img_loaded, _img_cache_fn
    if _img_override is not None:
        return _img_override
    if not _img_loaded:
        _img_cache_fn = _load_image_embedder()
        _img_loaded = True
    return _img_cache_fn


def _text_embedder() -> Callable[[list[str]], "np.ndarray"] | None:
    global _txt_loaded, _txt_cache_fn
    if _txt_override is not None:
        return _txt_override
    if not _txt_loaded:
        _txt_cache_fn = _load_text_embedder()
        _txt_loaded = True
    return _txt_cache_fn


def available() -> bool:
    """그림 임베딩 + 텍스트 교차매칭이 실제로 가능한지(둘 다 로드 성공)."""
    return np is not None and _image_embedder() is not None and _text_embedder() is not None


# --------------------------------------------------------------------------- #
# 임베딩 + 코사인
# --------------------------------------------------------------------------- #
def _normalize(mat: "np.ndarray") -> "np.ndarray":
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def cosine(a: "np.ndarray", b: "np.ndarray") -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


def embed_texts(texts: Iterable[str]) -> "np.ndarray | None":
    """텍스트들을 L2 정규화 행렬로(이미지와 같은 공간). 모델 없으면 None."""
    fn = _text_embedder()
    if fn is None or np is None:
        return None
    items = [str(t or "") for t in texts]
    if not items:
        return np.zeros((0, 1), dtype=np.float32)
    vecs = np.asarray(fn(items), dtype=np.float32)
    if vecs.ndim == 1:
        vecs = vecs.reshape(1, -1)
    return _normalize(vecs)


def embed_images(paths: Iterable[Path | str]) -> "dict[str, np.ndarray]":
    """그림 파일들을 임베딩. {abs_path: 정규화 벡터}. 모델 없으면 빈 dict.
    읽기 실패한 파일은 결과에서 빠진다(개별 폴백)."""
    fn = _image_embedder()
    if fn is None or np is None:
        return {}
    items = [str(Path(p)) for p in paths]
    if not items:
        return {}
    out: dict[str, "np.ndarray"] = {}
    try:
        vecs = np.asarray(fn(items), dtype=np.float32)
        if vecs.ndim == 1:
            vecs = vecs.reshape(1, -1)
        vecs = _normalize(vecs)
        for path, vec in zip(items, vecs):
            out[path] = vec
        return out
    except Exception:
        # 배치 실패 시 1장씩 재시도(깨진 파일 1장이 전체를 막지 않게)
        for path in items:
            try:
                v = np.asarray(fn([path]), dtype=np.float32)
                if v.ndim == 1:
                    v = v.reshape(1, -1)
                out[path] = _normalize(v)[0]
            except Exception:
                continue
        return out


# --------------------------------------------------------------------------- #
# 라이브러리 그림 지문 인덱스 (파일 mtime/size 기준 캐시)
# --------------------------------------------------------------------------- #
def _sig(path: Path) -> str:
    st = path.stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"model": MODEL_NAME, "items": {}}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if data.get("model") != MODEL_NAME:
            return {"model": MODEL_NAME, "items": {}}
        data.setdefault("items", {})
        return data
    except Exception:
        return {"model": MODEL_NAME, "items": {}}


def _save_cache(cache: dict) -> None:
    try:
        CODEX_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # 캐시는 보조 기능


def library_image_index(available_only: bool = True) -> "dict[str, np.ndarray]":
    """{variant: 그림 벡터}. 라이브러리 PNG 를 임베딩(캐시 사용, 변경분만 재계산).
    모델 없으면 빈 dict → 호출부는 폴백한다.
    available_only 는 인터페이스 호환용(현재 모든 파일이 라이브러리)."""
    if not available() or not ILLUST_DIR.exists():
        return {}
    files = sorted(p for p in ILLUST_DIR.glob("*.png") if p.is_file())
    cache = _load_cache()
    items = cache.setdefault("items", {})
    index: dict[str, "np.ndarray"] = {}
    to_embed: list[Path] = []
    for path in files:
        variant = path.stem
        try:
            sig = _sig(path)
        except OSError:
            continue
        cached = items.get(variant)
        if cached and cached.get("sig") == sig and cached.get("vec"):
            index[variant] = np.asarray(cached["vec"], dtype=np.float32)
        else:
            to_embed.append(path)
    if to_embed:
        embedded = embed_images(to_embed)
        for path in to_embed:
            vec = embedded.get(str(path))
            if vec is None:
                continue
            variant = path.stem
            index[variant] = vec
            try:
                items[variant] = {"sig": _sig(path), "vec": vec.tolist()}
            except OSError:
                pass
        # 사라진 파일 정리
        live = {p.stem for p in files}
        for variant in list(items.keys()):
            if variant not in live:
                items.pop(variant, None)
        _save_cache(cache)
    return index


# --------------------------------------------------------------------------- #
# 공개 매칭 API
# --------------------------------------------------------------------------- #
def rank_for_text(
    query: str,
    index: "dict[str, np.ndarray] | None" = None,
    exclude: Iterable[str] = (),
    top_k: int | None = None,
) -> "list[tuple[str, float]]":
    """질의 텍스트에 그림 내용이 가까운 [(variant, cosine)] 내림차순.
    모델/인덱스 없으면 빈 리스트(호출부가 폴백)."""
    if index is None:
        index = library_image_index()
    if not index:
        return []
    qv = embed_texts([query])
    if qv is None or qv.shape[0] == 0:
        return []
    qv = qv[0]
    exclude = set(exclude)
    rows = [(v, cosine(qv, vec)) for v, vec in index.items() if v not in exclude]
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows[:top_k] if top_k else rows


def best_for_text(query: str, index: "dict[str, np.ndarray] | None" = None) -> "tuple[str, float]":
    rows = rank_for_text(query, index=index, top_k=1)
    return rows[0] if rows else ("", 0.0)


def nearest_library_image(vec: "np.ndarray", index: "dict[str, np.ndarray] | None" = None) -> "tuple[str, float]":
    """주어진 그림 벡터와 가장 비슷한 기존 라이브러리 그림(중복 감지용)."""
    if index is None:
        index = library_image_index()
    best_v, best_s = "", 0.0
    for variant, lib_vec in index.items():
        s = cosine(vec, lib_vec)
        if s > best_s:
            best_v, best_s = variant, s
    return best_v, best_s


# --------------------------------------------------------------------------- #
# self-test CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    print(f"[image_embed] 모델: {MODEL_NAME}")
    print(f"[image_embed] 사용 가능: {available()}  (False면 텍스트/lexical 폴백)")
    if arg == "check":
        return 0 if available() else 1
    if arg != "selftest":
        print("usage: python scripts/codex_image_embed.py selftest|check")
        return 0
    index = library_image_index()
    print(f"[image_embed] 라이브러리 그림 지문: {len(index)}장")
    if not index:
        return 0
    for q in [
        "두 스마트폰 사이로 사진과 연락처를 옮기는 장면",
        "수상한 링크가 있는 피싱 문자 경고",
        "요금제 가격을 비교하는 그림",
    ]:
        print(f"\n질의: {q}")
        for variant, score in rank_for_text(q, index=index, top_k=5):
            print(f"  {score:.3f}  {variant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
