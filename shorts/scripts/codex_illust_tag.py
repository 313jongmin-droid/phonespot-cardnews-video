# -*- coding: utf-8 -*-
"""
일러스트 자동태깅 (2026-07-10) — 라이브러리 그림에 gemini vision으로 한글 키워드를 붙여 재사용성 확보.

기존 illustration_tag_db.json 의 약한 키워드(청크 문구 조각)를 그림 실제내용 기반 키워드로 보강하고,
cpt_*(개념아트)도 gemini가 실제 그림을 확인한 것이므로 img_verified=true 로 표시 → 매처 재사용 허용.

흐름: public/assets/illustrations/*.png -> gemini vision -> DB keywords 병합(union) + img_verified.
      캐시: 파일 mtime 기록, 변경 없으면 스킵. 속도제한(1.5s 딜레이 + 429 백오프).

사용:  python scripts/codex_illust_tag.py          # 신규/미검증만
       python scripts/codex_illust_tag.py --force   # 전체 재태깅
       python scripts/codex_illust_tag.py --limit 30  # 이번 실행 최대 N장(대량 라이브 분할)
키:    _secrets/gemini_key.txt (없으면 스킵 — 기존 키워드 매칭만, 비파괴)
"""
from __future__ import annotations
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
ILLUST = REPO / "shorts" / "public" / "assets" / "illustrations"
DB_PATH = REPO / "shorts" / "config" / "illustration_tag_db.json"
KEY_FILE = REPO / "_secrets" / "gemini_key.txt"
MODEL = os.environ.get("PHONESPOT_GEMINI_VISION_MODEL", "gemini-2.5-flash")

PROMPT = (
    "이 이미지는 카드뉴스 영상에 쓰는 일러스트(벡터/3D 스타일)다. 이 그림이 나타내는 개념·소재를 "
    "한글 키워드로 뽑아라.\n포함: 사물·기기(휴대폰/배터리/카메라/폴더블/충전기 등), 행동·상황"
    "(충전/비교/경고/상승/하락/개봉/보호), 추상개념(보안/가격/지원금/업데이트/성능).\n"
    "규칙: 카드뉴스 자막에 나올 법한 일반 한글 단어. 그림에 없는 건 넣지 마라. "
    "5~10개, 콤마(,)로만. 설명·문장 없이 키워드만."
)


def _load_key() -> str:
    try:
        k = KEY_FILE.read_text(encoding="utf-8").strip()
        return k if k.startswith("AIza") else ""
    except Exception:
        return ""


def _tag(key: str, path: Path) -> list[str]:
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return []
    payload = {"contents": [{"parts": [
        {"text": PROMPT},
        {"inline_data": {"mime_type": "image/png", "data": b64}},
    ]}]}
    url = ("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL
           + ":generateContent?key=" + key)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < 2:
                time.sleep(6 * (attempt + 1)); continue
            print(f"    [illust-tag] 실패 {path.name}: {exc}"); return []
        except Exception as exc:
            print(f"    [illust-tag] 실패 {path.name}: {exc}"); return []
    else:
        return []
    out, seen = [], set()
    for w in text.replace("\n", ",").split(","):
        w = w.strip().strip("-·•*").strip()
        if w and w not in seen and len(w) <= 12:
            seen.add(w); out.append(w)
    return out[:10]


def main() -> int:
    force = "--force" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception: limit = None
    if not ILLUST.exists():
        print(f"[illust-tag] illustrations 폴더 없음: {ILLUST}"); return 0
    key = _load_key()
    try:
        db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        db = {"version": 1, "illustrations": {}}
    ills = db.setdefault("illustrations", {})
    files = sorted(p for p in ILLUST.glob("*.png"))
    if not key:
        print(f"[illust-tag] gemini 키 없음 → 스킵(기존 키워드 매칭만). 일러스트 {len(files)}장"); return 0
    tagged = 0
    for p in files:
        variant = p.stem
        mt = round(p.stat().st_mtime, 1)
        entry = ills.setdefault(variant, {"tags": [], "keywords": [], "note": "", "available": True})
        if entry.get("img_verified") and not force and abs(float(entry.get("_img_mtime", 0)) - mt) < 1:
            continue  # 이미 vision 태깅됨(캐시)
        kws = _tag(key, p)
        if kws:
            merged = list(dict.fromkeys(list(entry.get("keywords") or []) + kws))  # union, 순서보존
            entry["keywords"] = merged
            entry["available"] = True
            entry["img_verified"] = True       # gemini가 실제 그림 확인 → 매처 재사용 허용(cpt_ 포함)
            entry["_img_mtime"] = mt
            tagged += 1
            print(f"    [illust-tag] {variant} += {', '.join(kws)}")
        time.sleep(1.5)  # RPM 제한(429) 예방
        if limit and tagged >= limit:
            print(f"    [illust-tag] --limit {limit} 도달 — 나머지는 다음 실행"); break
    db["updated_at"] = int(time.time())
    tmp = DB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"[illust-tag] vision 태깅 {tagged}장 / 전체 {len(files)}장 -> {DB_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
