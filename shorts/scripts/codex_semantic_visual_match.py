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

# 수동 차단목록 = 비상용 escape hatch(기본 비움, env 로만 채움). 특정 그림 1개를 위한
# 하드코딩은 하지 않는다 — 이름↔그림 불일치는 아래 '그림내용(CLIP) 검증'이 범용으로 잡는다.
ILLUST_BLOCKLIST = set(
    v.strip() for v in os.getenv("PHONESPOT_ILLUST_BLOCKLIST", "").split(",") if v.strip()
)

# ★ 미검증 개념아트(concept-scout cpt_*) 정책 (범용, 이름 하드코딩 아님).
# cpt_* 는 '개념 요청' 텍스트로 자동 생성/임포트된 아트라 텍스트/태그 임베딩엔 맞아도
# 실제 그림이 틀릴 수 있다(예: 'AI' 개념인데 보이스피싱 장면). 그림내용(CLIP) 검증이
# 활성화돼 있지 않으면 텍스트매칭에서 제외하고, 검수된 라이브러리 아트/중립으로 대체한다.
# CLIP 켜지면 content 경로에서 실제 그림으로 검증되어 다시 쓰일 수 있다. env 로 해제 가능.
EXCLUDE_UNVERIFIED_CONCEPT = os.getenv("PHONESPOT_TRUST_CONCEPT_ART", "0") == "0"
CONCEPT_PREFIX = "cpt_"
def _is_unverified_concept(variant: str) -> bool:
    return EXCLUDE_UNVERIFIED_CONCEPT and str(variant).startswith(CONCEPT_PREFIX)


# ★ 실사(제품/인물) 포토 라이브러리 — 일러스트와 별개 폴더. '사용 가능한' 실사만 한글
# 파일명으로 넣어두면(예: 갤럭시Z플립8_제품_폴더블.jpg) 파일명을 라벨로 임베딩해 매칭한다.
# 정책: 포토 1순위 + 매우 확신할 때만(>= PHOTO_MIN). 애매하면 건너뛰고 → 일러스트(기존) → 생성요청.
# PHOTO_MIN 은 텍스트 임베딩 코사인(0~1). 0.80 은 매우 엄격 → 사진이 안 뜨면 env 로 낮춰 검증.
PHOTO_DIR = SHORTS / "public" / "assets" / "photos"
PHOTO_MIN = float(os.getenv("PHONESPOT_PHOTO_MIN", "0.80"))
PHOTO_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def list_photos() -> list[str]:
    if not PHOTO_DIR.exists():
        return []
    return sorted(
        x.name for x in PHOTO_DIR.iterdir() if x.is_file() and x.suffix.lower() in PHOTO_EXTS
    )


def photo_label(fname: str) -> str:
    base = re.sub(r"\.[^.]+$", "", fname)
    return clean(base.replace("_", " ").replace("-", " "))


def build_photo_index() -> dict:
    """{filename: 벡터}. 파일명 라벨을 임베딩. 모델/폴더 없으면 {}."""
    files = list_photos()
    if not files or not ce.available():
        return {}
    vecs = ce.embed([photo_label(f) for f in files])
    if vecs is None:
        return {}
    return {files[i]: vecs[i] for i in range(len(files))}


# ─ 포토 매칭 = 임베딩이 아니라 '모델명 토큰의 실제 등장'(렉시컬). 한글 임베딩이 모델명
#   (갤럭시A vs 엑시노스 vs S25)을 구분 못 해 엉뚱한 폰이 매칭되던 문제(렌더로 확인) 때문.
#   제품 사진은 파일명에 정확한 모델명이 박혀 있으므로, 그 '구별 토큰'이 청크에 그대로 나올
#   때만 1순위 채택. 브랜드명(애플/삼성/갤럭시)은 구별토큰으로 인정(2026-07-09) → 브랜드 로고/사진이 그 브랜드 청크에 매칭(제품샷이 더 구체적이면 제품샷 우선, 로고는 순수 브랜드 청크에). 여전히 로고/제품/폰 등 진짜 흔한단어만 스톱.
#   범용(이름 하드코딩 아님). 임베딩 불필요 → 모델 미설치 PC에서도 동작.
PHOTO_STOP = set(v.strip().lower() for v in os.getenv(
    "PHONESPOT_PHOTO_STOP",
    "로고,제품,신형,최신,폰,휴대폰,스마트폰,단말,통신사,사진,이미지",  # 브랜드명(애플/삼성/갤럭시/구글/샤오미/퀄컴) 스톱 해제(2026-07-09): 렉시컬+1회사용이라 과매칭 안전, 브랜드 로고/사진이 브랜드명 청크에 붙게
).split(",") if v.strip())


def _photo_tokens(label: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[\s_\-]+", label):
        out += re.findall(r"[가-힣]+|[A-Za-z]+|[0-9]+", part)
    return out


def _is_distinctive(tok: str) -> bool:
    if tok.lower() in PHOTO_STOP:
        return False
    if re.fullmatch(r"[가-힣]+", tok):
        return len(tok) >= 2   # 플립/폴드/워치/배터리/엑시노스/스냅드래곤/알뜰폰
    if re.fullmatch(r"[A-Za-z]+", tok):
        return len(tok) >= 3   # ios/lgu (kt 2글자는 오탐 위험 → 제외)
    if re.fullmatch(r"[0-9]+", tok):
        return len(tok) >= 3   # 2600 (25 같은 짧은 숫자 제외)
    return False


def photo_lexical_score(label: str, chunk: str) -> tuple[int, int]:
    """(구별토큰 일치수, 일반토큰 일치수). 한글=부분문자열, 영문=단어경계."""
    c_low = chunk.lower()
    dist = gen = 0
    seen: set[str] = set()
    for tok in _photo_tokens(label):
        if tok in seen:
            continue
        seen.add(tok)
        if re.fullmatch(r"[A-Za-z]+", tok):
            hit = re.search(r"(?<![A-Za-z])" + re.escape(tok.lower()) + r"(?![A-Za-z])", c_low) is not None
        else:
            hit = tok in chunk
        if not hit:
            continue
        if _is_distinctive(tok):
            dist += 1
        else:
            gen += 1
    return dist, gen


# ─ 일러스트 렉시컬 키워드 매칭 (임베딩 보조). DB의 keywords가 청크에 '실제로' 여러 개
#   등장하면 결정론적으로 우선. 해시 이름(cpt/_xxxx)·헤드라인 문맥에 희석되는 임베딩 코사인의
#   불안정을 보완 — 포토를 렉시컬로 고친 것과 같은 처방. 임베딩은 키워드 약할 때의 보조로 유지.
MIN_ILLUST_KEYWORDS = int(os.getenv("PHONESPOT_MIN_ILLUST_KEYWORDS", "2"))
ILLUST_KW_STOP = set(v.strip().lower() for v in os.getenv(
    "PHONESPOT_ILLUST_KW_STOP",
    "폰,스마트폰,휴대폰,단말,기기,화면,사용,기능,제품",  # 너무 흔한 키워드는 임계 계산에서 제외
).split(",") if v.strip())


def illust_lexical_hits(keywords: list, chunk: str) -> int:
    """청크에 등장하는 '구별되는' 키워드 개수(한글=부분문자열, 영문/숫자=단어경계)."""
    c_low = chunk.lower()
    hits = 0
    seen: set = set()
    for kw in keywords:
        kw = str(kw).strip()
        if not kw or kw in seen:
            continue
        seen.add(kw)
        if len(kw) < 2 or kw.lower() in ILLUST_KW_STOP:
            continue
        if re.fullmatch(r"[A-Za-z0-9]+", kw):
            ok = re.search(r"(?<![A-Za-z0-9])" + re.escape(kw.lower()) + r"(?![A-Za-z0-9])", c_low) is not None
        else:
            ok = kw in chunk
        if ok:
            hits += 1
    return hits


def build_illust_keyword_index() -> dict:
    """{variant: [keywords]} — available 한 일러스트만. cpt 미검증/blocklist 제외(매처와 동일)."""
    db = load_db()
    out: dict = {}
    for variant, entry in (db.get("illustrations", {}) or {}).items():
        if not isinstance(entry, dict) or not entry.get("available"):
            continue
        if variant in ILLUST_BLOCKLIST or _is_unverified_concept(variant):
            continue
        kws = [str(k).strip() for k in (entry.get("keywords") or []) if str(k).strip()]
        if kws:
            out[variant] = kws
    return out


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
    # 원자적 쓰기: temp+os.replace. 렌더 중 쓰기가 끊겨도 shorts_script.json이 truncate/NUL 손상 X.
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


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
        if variant in ILLUST_BLOCKLIST or _is_unverified_concept(variant):
            continue
        key = f"illust:{variant}"
        if key in used_visuals:
            continue
        score = semantic_score(context, entry)
        if score > 0:
            rows.append((score, variant))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows


_NEUTRAL_RR = [0]  # 라운드로빈 커서(프로세스=영상 1편이라 안전)


def pick_neutral(used_visuals: set[str]) -> str:
    """토픽 중립 필러를 반환. ① 아직 안 쓴 중립 우선 ② 전부 한 번씩 쓰면 라운드로빈으로
    분산(예전엔 항상 첫 번째=smartphone 반환 → 영문/설정 청크 많은 기사에서 smartphone 11회
    쏠림). 라이브러리에 실제 존재하는 것만. 없으면 빈 문자열."""
    available = [v for v in NEUTRAL_FILLERS if v in set(library_variants())]
    if not available:
        return ""
    for variant in available:
        if f"illust:{variant}" not in used_visuals:
            return variant
    variant = available[_NEUTRAL_RR[0] % len(available)]
    _NEUTRAL_RR[0] += 1
    return variant


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
        if variant in ILLUST_BLOCKLIST or _is_unverified_concept(variant):
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
    photo_files = list_photos()
    photo_engine = f", photos={len(photo_files)}장(렉시컬 모델명 매칭)" if photo_files else ""
    # 일러스트 렉시컬 키워드 인덱스(임베딩 경로 보조). lexical 폴백 경로는 이미 word-overlap 사용.
    illust_kw_index = build_illust_keyword_index() if use_embed else {}
    illust_kw_engine = f", illust-kw={len(illust_kw_index)}개(min={MIN_ILLUST_KEYWORDS})" if illust_kw_index else ""
    print(f"[semantic_visual] engine={'embedding' if use_embed else 'lexical'} (min_img={min_img}, min_ill={min_ill}){img_engine}{photo_engine}{illust_kw_engine}")
    # 진단(무조건 기록): 이 렌더가 실제로 본 photo_files 수/경로. changes 없어 리포트가 안 나와도 남김.
    try:
        (CARD_OUTPUT / slug).mkdir(parents=True, exist_ok=True)
        (CARD_OUTPUT / slug / "_visual_engine_diag.txt").write_text(
            f"use_embed={use_embed}\nphoto_files={len(photo_files)}\nphotos={photo_files}\n"
            f"PHOTO_DIR={PHOTO_DIR}\nPHOTO_DIR_exists={PHOTO_DIR.exists()}\n"
            f"illust_kw_index={len(illust_kw_index)}\n",
            encoding="utf-8",
        )
    except Exception:
        pass

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

            # 일러스트 렉시컬 키워드 매칭(청크 자체 기준, 헤드라인 제외). 임베딩 보조.
            best_lex_ill = (0, "")
            if illust_kw_index:
                _ichunk = clean(chunks[idx]) if idx < len(chunks) else context
                for _iv, _kws in illust_kw_index.items():
                    if f"illust:{_iv}" in used_visuals:
                        continue
                    _h = illust_lexical_hits(_kws, _ichunk)
                    if _h > best_lex_ill[0]:
                        best_lex_ill = (_h, _iv)
                if best_lex_ill[1] and best_lex_ill[0] >= MIN_ILLUST_KEYWORDS:
                    print(f"[illust-kw] {section_name} c{idx+1}: {best_lex_ill[1]} hits={best_lex_ill[0]}")

            # 0순위: 실사 포토 — 렉시컬 모델명 매칭(임베딩 X, 청크 자체 기준). 구별 토큰이
            #   청크에 실제 등장할 때만. 동점이면 일반토큰 일치수로. 없으면 일러스트로 폴백.
            best_photo = (0, 0, "")  # (구별토큰수, 일반토큰수, 파일명)
            if photo_files:
                _pchunk = clean(chunks[idx]) if idx < len(chunks) else context
                for _pf in photo_files:
                    if f"image:photos/{_pf}" in used_visuals:
                        continue
                    _d, _g = photo_lexical_score(photo_label(_pf), _pchunk)
                    if _d > 0 and (_d, _g) > (best_photo[0], best_photo[1]):
                        best_photo = (_d, _g, _pf)
                if best_photo[2]:
                    print(f"[photo] {section_name} c{idx+1}: {best_photo[2]} dist={best_photo[0]} gen={best_photo[1]}")

            # ★ 범용 그림내용(CLIP) 검증용 랭킹. 텍스트/태그로 고른 일러스트라도 '실제 그림'이
            #   주제와 맞는지 같은 잣대(EMBED_MIN_ILLUST_IMG)로 확인한다. 이름 하드코딩 없이
            #   어떤 이름↔그림 불일치든(예: AI인데 사기장면, 디스플레이인데 티타늄) 거부된다.
            #   엔진/데이터 없으면 빈 리스트 → 검증 생략(기존 동작 유지, 무회귀).
            content_rows = []
            if use_embed and img_index:
                try:
                    content_rows = list(ie.rank_for_text(context, index=img_index))
                except Exception:
                    content_rows = []
            content_score = {v: s for v, s in content_rows}

            chosen = None
            reason = ""
            if best_photo[2]:
                # 실사 포토는 모델명이 청크에 실제로 박혔을 때만 뜸(구별토큰≥1) = 확신 매칭이므로
                # 일러스트보다 우선(실제 제품 > 추상 일러스트). 약한 포토 자체가 안 생겨 굶김 X.
                chosen = {"type": "image", "value": f"photos/{best_photo[2]}"}
                reason = f"photo lexical dist={best_photo[0]} gen={best_photo[1]}: {best_photo[2]}"
            elif best_img[0] >= min_img and best_img[0] >= best_ill[0]:
                chosen = {"type": "image", "value": best_img[1]}
                reason = f"image score {best_img[0]}: {best_img[2][:80]}"
            elif (
                best_lex_ill[0] >= MIN_ILLUST_KEYWORDS
                and f"illust:{best_lex_ill[1]}" not in used_visuals
            ):
                # 렉시컬 키워드 다중 일치(≥2, cpt 제외) = 작성자 확정 신호 → content-gate 면제.
                # CLIP은 '범용/추상'으로 그린 일러스트를 거부할 수 있는데, 키워드가 청크에 실제로
                # 여러 개 박혀 있으면 그게 더 신뢰할 신호다(임베딩 best_ill보다 우선). content-gate는
                # 약한 임베딩 픽(best_ill)에만 적용 → 이름↔그림 불일치는 거기서 계속 잡힌다.
                chosen = {"type": "illust", "value": best_lex_ill[1]}
                reason = f"illust lexical kw hits={best_lex_ill[0]} (content-gate 면제): {best_lex_ill[1]}"
            elif best_ill[0] >= min_ill and (
                not content_score or content_score.get(best_ill[1], 0.0) >= EMBED_MIN_ILLUST_IMG
            ):
                chosen = {"type": "illust", "value": best_ill[1]}
                reason = f"illust score {best_ill[0]} (content {content_score.get(best_ill[1], 'n/a')})"
            elif (
                current.get("type") == "image"
                and not str(current.get("value")).startswith("photos/")
                and current.get("value") not in used_images
            ):
                # Source images are generated for THIS article, so an on-topic
                # source image beats any weak library guess.
                # ★ 단 photos/ 는 제외 — 실사 포토는 '렉시컬 매처만' (재)배정한다. 이전 렌더가
                #   남긴 낡은 포토(예 임베딩 시절 갤럭시A)가 이 '유지' 분기로 되살아나면 안 됨
                #   (매처가 이번엔 dist=0으로 거부했는데 stale 값이 살아남던 버그). photos/ 면
                #   여기서 안 잡고 아래 일러스트/중립으로 떨어뜨린다.
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
                img_best = (0.0, "")
                for _v, _sc in content_rows:
                    if _v in ILLUST_BLOCKLIST or f"illust:{_v}" in used_visuals:
                        continue
                    img_best = (round(float(_sc), 3), _v)
                    break
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
