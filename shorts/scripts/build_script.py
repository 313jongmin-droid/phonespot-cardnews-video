"""
카드뉴스 articles/<slug>.json -> 영상용 shorts_script.json 자동 변환 어댑터.

사용:
    python scripts/build_script.py <slug>
이미 shorts_script.json 이 있으면 덮어쓰지 않음 (수동으로 다듬은 내용 보존).
강제 재생성: python scripts/build_script.py <slug> --force
"""
import json
import hashlib
import re
import shutil as _sh
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if len(sys.argv) < 2:
    print("Usage: python scripts/build_script.py <slug> [--force]")
    sys.exit(1)

slug = sys.argv[1]
force = "--force" in sys.argv

project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/

article_path = cardnews_root / "articles" / f"{slug}.json"
out_path = cardnews_root / "output" / slug / "shorts_script.json"


def _is_outdated(p):
    """구 스키마 감지. 재생성 트리거:
    1) opening / caption_chunks / chunk_visuals 키 누락
    2) background_image / chunk_visuals.value 에 card_*.png (카드뉴스 파생본)
    3) _auto_generated=True 인데 mascot 청크 0개 (구버전 마스코트 누락)
       단, _v2 마커가 있으면 mascot 줄인 새 로직 적용본이라 skip
    손폴리시본(_auto_generated 없거나 False)은 보존.
    """
    try:
        j = json.load(open(p, encoding="utf-8"))
    except Exception:
        return True
    if "opening" not in j:
        return True

    def _check_sec(sec):
        if "caption_chunks" not in sec or "chunk_visuals" not in sec:
            return True
        bg = sec.get("background_image", "")
        if isinstance(bg, str) and bg.startswith("card_"):
            return True
        for cv in sec.get("chunk_visuals", []):
            if cv.get("type") == "image" and str(cv.get("value", "")).startswith("card_"):
                return True
        return False

    if _check_sec(j.get("hook", {})):
        return True
    if _check_sec(j.get("cta", {})):
        return True
    for f in j.get("facts", []):
        if _check_sec(f):
            return True

    # 자동생성본인데 _v2 마커 없으면 outdated (이미지 순환·마스코트 감소 신로직 적용)
    if j.get("_auto_generated") and not j.get("_chunk_logic_v2"):
        return True
    return False


def _source_hash_of(a):
    """기사 본문(cards body+headline) 해시. 본문 바뀌면 값이 달라져 재빌드 트리거."""
    parts = []
    for c in a.get("cards", []):
        parts.append(str(c.get("body", "")))
        parts.append(str(c.get("headline", "")))
    return hashlib.sha1("\u241f".join(parts).encode("utf-8")).hexdigest()


def _article_source_hash(art_path):
    try:
        return _source_hash_of(json.load(open(art_path, encoding="utf-8")))
    except Exception:
        return ""


if out_path.exists() and not force:
    cur_hash = _article_source_hash(article_path)
    try:
        stored_hash = str(json.load(open(out_path, encoding="utf-8")).get("_source_hash") or "")
    except Exception:
        stored_hash = ""
    content_changed = bool(cur_hash) and cur_hash != stored_hash
    if _is_outdated(out_path) or content_changed:
        reason = "본문 변경 감지" if content_changed else "구 스키마"
        print(f"[REBUILD] 기존 shorts_script.json {reason} - 자동 재생성: {out_path}")
        bak = out_path.with_suffix(".json.bak")
        try:
            _sh.copy(out_path, bak)
            print(f"          (백업: {bak.name})")
        except Exception:
            pass
    else:
        print(f"[SKIP] shorts_script.json already exists (본문 동일): {out_path}")
        print("       (use --force to regenerate)")
        sys.exit(0)

if not article_path.exists():
    print(f"[ERROR] article not found: {article_path}")
    sys.exit(1)

art = json.load(open(article_path, encoding="utf-8"))
cards = art.get("cards", [])
if len(cards) < 2:
    print(f"[ERROR] article has no cards[]: {slug}")
    sys.exit(1)


def parse_headline(hl_raw):
    emph = re.findall(r'<span class="hl">(.*?)</span>', hl_raw)
    clean = re.sub(r'</?span[^>]*>', '', hl_raw)
    lines = [l.strip() for l in clean.split("\n") if l.strip()]
    return lines, emph


img_dir = cardnews_root / "images" / slug


ILLUST_PLACEHOLDER = "smartphone"  # 카드이미지 없을 때 청크 placeholder(렌더 semantic match가 실제 일러스트로 교체)


def pick_images(n):
    """GPT 원본 PNG. card_*.png 제외. 우선순위: {N}.png > gpt_{N}.png.
    카드이미지가 없으면 막지 않고 빈 배경을 반환한다(영상=일러스트 전용 모드).
    실제 화면 비주얼은 렌더 단계 codex_semantic_visual_match 가 일러스트로 채운다."""
    for pat in ("{}.png", "gpt_{}.png"):
        available = [img_dir / pat.format(i) for i in range(1, 20)]
        existing = [p.name for p in available if p.exists()]
        if existing:
            result = []
            for i in range(n):
                result.append(existing[i] if i < len(existing) else existing[-1])
            return result
    print(f"[info] images/{slug}/ 에 GPT 카드이미지 없음 → 일러스트 전용 모드(배경 비움, 렌더가 일러스트로 채움).")
    return [""] * n


def collect_all_images():
    """슬러그 전체 이미지 풀 (시퀀스 내 순환용)"""
    pool = []
    for pat in ("{}.png", "gpt_{}.png"):
        for i in range(1, 20):
            p = img_dir / pat.format(i)
            if p.exists() and p.name not in pool:
                pool.append(p.name)
    return pool


n_cards = len(cards)
images = pick_images(n_cards)
image_pool = collect_all_images()

title = art.get("title", slug)
# " / " (공백 양쪽) 만 분리 — 날짜 "6/8" 처럼 공백 없는 슬래시는 보존
video_title = title.split(" / ")[0].strip()

src_line = art.get("source_line", "").replace("출처:", "").strip()
src_short = src_line.split("·")[0].strip() if src_line else ""


def split_caption(text, max_chars=24):
    """한글 문법 단위 분할: 문장끝 > 절끝 > 어절. 2자 이하 짧은 어절 다음과 묶음."""
    text = text.replace("\n", " ").strip()
    if not text:
        return []

    def _n(s):
        return len(s.replace(" ", ""))

    def _word_chunks(s):
        words = s.split()
        tokens = []
        i = 0
        while i < len(words):
            cur = words[i]
            while _n(cur) <= 2 and i + 1 < len(words):
                i += 1
                cur = cur + " " + words[i]
            tokens.append(cur)
            i += 1
        out, c = [], ""
        for t in tokens:
            merged = (c + " " + t).strip() if c else t
            if _n(merged) > max_chars and c:
                out.append(c)
                c = t
            else:
                c = merged
        if c:
            out.append(c)
        return out

    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    for sent in sentences:
        if _n(sent) <= max_chars:
            chunks.append(sent)
            continue
        clauses = re.split(r"(?<=[,;])\s+", sent)
        clauses = [c.strip() for c in clauses if c.strip()]
        for cl in clauses:
            if _n(cl) <= max_chars:
                chunks.append(cl)
            else:
                chunks.extend(_word_chunks(cl))
    return chunks


MASCOT_EMOTIONS = ["surprised", "satisfied", "suspicious", "smirk", "serious", "wink"]


def build_chunk_visuals(chunks, idx, pool):
    """청크별 시각화. v2 로직 - 화면 전환량 증가 + 마스코트 빈도 절반.
    - 한 시퀀스 내 청크마다 이미지 순환 (pool 에서 idx+k 인덱스)
    - 짝수 idx 시퀀스 (0, 2, 4) + 청크 2개 이상이면 마지막을 mascot으로 교체
    - 나머지는 image 만 (마스코트 없음)
    """
    n = len(chunks)
    if n == 0:
        return []
    visuals = []
    if pool:
        pool_n = len(pool)
        for k in range(n):
            img = pool[(idx + k) % pool_n]
            visuals.append({"type": "image", "value": img})
    else:
        # 카드이미지 없음 → 일러스트 placeholder. 렌더의 semantic match 가 실제 일러스트로 교체.
        for k in range(n):
            visuals.append({"type": "illust", "value": ILLUST_PLACEHOLDER})
    # 마스코트: 짝수 시퀀스만 + 청크 2개 이상
    if n >= 2 and idx % 2 == 0:
        emotion = MASCOT_EMOTIONS[idx % len(MASCOT_EMOTIONS)]
        visuals[-1] = {"type": "mascot", "value": emotion}
    return visuals


def seq_from_card(card, idx, is_cta=False):
    lines, emph = parse_headline(card.get("headline", ""))
    body = card.get("body", "").strip()
    chunks = split_caption(body)
    d = {
        "tts": body,
        "caption_body": lines[:2] if len(lines) >= 2 else (lines + [""])[:2],
        "caption_emphasis": emph,
        "headline_lines": [
            {"text": lines[0] if lines else ""},
            {"text": lines[1] if len(lines) > 1 else "", "accent": True},
        ],
        "meta": card.get("source", src_short),
        "topic": "뉴스",
        "background_image": images[idx],
        "caption_chunks": chunks,
        "chunk_visuals": build_chunk_visuals(chunks, idx, image_pool),
        "stat": {"label": "", "value": "", "note": ""},
    }
    if is_cta:
        d["kakao"] = "@휴대폰성지폰스팟"
        d["location"] = "내 손 안의 성지찾기, 폰스팟"
        d["litt"] = "litt.ly/phonespot"
    return d


hook = seq_from_card(cards[0], 0)
cta = seq_from_card(cards[-1], n_cards - 1, is_cta=True)
facts = []
for i in range(1, n_cards - 1):
    f = seq_from_card(cards[i], i)
    f["id"] = f"fact_{i}"
    facts.append(f)

script = {
    "slug": slug,
    "title_short": video_title,
    "video_title": video_title,
    "publication_date": art.get("publication_date", ""),
    "sources": src_line,
    "channel_name": "휴대폰성지 폰스팟",
    "channel_tagline": "휴대폰성지 IT 브리핑",
    "opening": {"line1": "휴대폰성지 IT 브리핑", "line2": video_title},
    "hook": hook,
    "facts": facts,
    "cta": cta,
    "_auto_generated": True,
    "_chunk_logic_v2": True,
    "_source_hash": _source_hash_of(art),
    "_note": "build_script.py 자동 생성 (v2 로직): 시퀀스 내 이미지 순환 + 마스코트 짝수 시퀀스만.",
}

out_path.parent.mkdir(parents=True, exist_ok=True)
json.dump(script, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[OK] shorts_script.json 자동 생성: {out_path}")
print(f"     시퀀스: hook + fact {len(facts)} + cta = {len(facts)+2}")
print(f"     이미지 풀: {image_pool}")
