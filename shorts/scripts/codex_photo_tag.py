# -*- coding: utf-8 -*-
"""
실사 포토 자동 태깅 (2026-07-09) — 단말기 실제품 이미지를 파일명 안 지어도 청크에 자동 매칭되게.

흐름: photos/*.jpg|png 를 gemini vision(gemini-2.5-flash)에 보내 한글 키워드 추출
      -> shorts/config/photo_tag_db.json 저장(파일명+mtime 캐시, 신규/변경분만 호출).
매처(codex_semantic_visual_match.py)가 이 DB의 keywords 를 파일명 토큰과 함께 청크 매칭에 사용.

사용:  python scripts/codex_photo_tag.py            # 신규/변경 사진만 태깅
       python scripts/codex_photo_tag.py --force    # 전체 재태깅
키:    _secrets/gemini_key.txt (없으면 조용히 스킵 — 파일명 매칭만으로 동작, 비파괴)
"""
from __future__ import annotations
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PHOTOS = REPO / "shorts" / "public" / "assets" / "photos"
DB_PATH = REPO / "shorts" / "config" / "photo_tag_db.json"
KEY_FILE = REPO / "_secrets" / "gemini_key.txt"
MODEL = os.environ.get("PHONESPOT_GEMINI_VISION_MODEL", "gemini-2.5-flash")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

PROMPT = (
    "이 이미지는 스마트폰/휴대폰 관련 사진이다. 카드뉴스 영상의 자막(청크)과 매칭할 한글 키워드를 뽑아라.\n"
    "포함: 브랜드(애플/삼성/구글 등 보이면), 제품군(아이폰/갤럭시/폴더블/플립 등 확실할 때만), "
    "부위·특징(후면/전면/카메라/화면/디스플레이/충전/배터리/색상/케이스/워치/이어폰), '로고'인지 '실제제품'인지.\n"
    "규칙: 자막에 나올 법한 일반적인 한글 단어. 확실치 않은 모델번호(17/18 등)는 넣지 마라. "
    "5~10개, 콤마(,)로만 구분. 설명·문장 없이 키워드만 출력."
)


def _load_key() -> str:
    try:
        k = KEY_FILE.read_text(encoding="utf-8").strip()
        return k if k.startswith("AIza") else ""
    except Exception:
        return ""


def _tag_image(key: str, path: Path) -> list[str]:
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return []
    payload = {"contents": [{"parts": [
        {"text": PROMPT},
        {"inline_data": {"mime_type": MIME.get(path.suffix.lower(), "image/jpeg"), "data": b64}},
    ]}]}
    url = ("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL
           + ":generateContent?key=" + key)
    text = None
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
                time.sleep(6 * (attempt + 1))  # 속도제한/일시장애 → 백오프 후 재시도
                continue
            print(f"    [photo-tag] 실패 {path.name}: {exc}")
            return []
        except Exception as exc:
            print(f"    [photo-tag] 실패 {path.name}: {exc}")
            return []
    if text is None:
        return []
    kws = [w.strip() for w in text.replace("\n", ",").split(",")]
    seen, out = set(), []
    for w in kws:
        w = w.strip().strip("-·•*").strip()
        if w and w not in seen and len(w) <= 12:
            seen.add(w); out.append(w)
    return out[:10]


def main() -> int:
    force = "--force" in sys.argv
    if not PHOTOS.exists():
        print(f"[photo-tag] photos 폴더 없음: {PHOTOS}")
        return 0
    key = _load_key()
    try:
        db = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else {}
    except Exception:
        db = {}
    files = sorted(p for p in PHOTOS.iterdir() if p.suffix.lower() in EXTS)
    if not key:
        print(f"[photo-tag] gemini 키 없음 → 스킵(파일명 매칭만 동작). photos {len(files)}장")
        return 0
    tagged = 0
    for p in files:
        mt = round(p.stat().st_mtime, 1)
        cur = db.get(p.name)
        if cur and not force and abs(float(cur.get("mtime", 0)) - mt) < 1:
            continue  # 캐시(변경 없음)
        kws = _tag_image(key, p)
        if kws:
            db[p.name] = {"keywords": kws, "mtime": mt, "ts": int(time.time())}
            tagged += 1
            print(f"    [photo-tag] {p.name} -> {', '.join(kws)}")
        time.sleep(1.5)  # 호출 간 간격 → gemini RPM 제한(429) 예방
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"[photo-tag] 신규 태깅 {tagged}장 / 전체 {len(files)}장 / DB {len(db)}건 -> {DB_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
