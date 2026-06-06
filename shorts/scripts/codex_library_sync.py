# -*- coding: utf-8 -*-
"""
일러스트 라이브러리 공유 동기화 (옵트인)

각 PC 가 완전 독립으로 돌아가되, 원할 때만 이걸 실행해 일러스트 라이브러리를
공유 허브(공유폴더/드라이브/USB/네트워크)와 양방향으로 합친다.
이게 있어야 PC 마다 같은 그림을 또 그리지 않고, 라이브러리가 함께 쌓여
"생성 → 0 수렴" 목표가 전체적으로 성립한다.

동기화 대상:
  - shorts/public/assets/illustrations/*.png   (그림 자산)
  - shorts/config/illustration_tag_db.json     (태그/키워드/개념)

원칙:
  - 양방향 '추가 병합'(비파괴): 같은 파일명이 양쪽에 있으면 건드리지 않는다.
    새 파일명만 서로 복사한다. 기존 그림을 덮어쓰지 않는다(안전 최우선).
  - 태그 DB 는 항목 합집합으로 병합(키워드/태그 union), 양쪽에 같은 내용으로 기록.
  - 임베딩 캐시(image_embed_cache 등)는 동기화하지 않는다 — 각 PC 에서 자동 재생성됨.
  - 허브 파일이 드라이브 부분동기화로 NUL 깨졌을 수 있어 '관대 로더'로 읽는다.

허브 경로 지정(둘 중 하나):
  - 환경변수 PHONESPOT_LIBRARY_SHARE
  - 파일 shorts/config/library_share_path.txt  (한 줄에 경로)

사용:
  python scripts/codex_library_sync.py            # 동기화 실행
  python scripts/codex_library_sync.py --dry-run  # 미리보기(복사 안 함)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import codex_illustration_db as dbm  # 정식 경로 재사용(ILLUST_DIR, DB_PATH)

ILLUST_DIR = dbm.ILLUST_DIR
DB_PATH = dbm.DB_PATH
CONFIG_DIR = dbm.CONFIG_DIR
SHARE_HINT_FILE = CONFIG_DIR / "library_share_path.txt"
ALLOWED = {".png"}


def resolve_share() -> Path | None:
    raw = os.environ.get("PHONESPOT_LIBRARY_SHARE", "").strip()
    if not raw and SHARE_HINT_FILE.exists():
        raw = SHARE_HINT_FILE.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not raw:
        return None
    return Path(raw)


def load_json_lenient(path: Path) -> dict:
    """NUL/꼬리 쓰레기(드라이브 부분동기화)가 붙어도 첫 JSON 객체를 복원."""
    if not path.exists():
        return {}
    try:
        raw = path.read_bytes()
    except OSError:
        return {}
    txt = raw.decode("utf-8-sig", errors="replace").replace("\x00", " ")
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        try:
            obj, _ = json.JSONDecoder().raw_decode(txt.lstrip())
            return obj
        except (json.JSONDecodeError, ValueError):
            return {}


def write_json_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def copy_new_pngs(src_dir: Path, dst_dir: Path, dry: bool) -> list[str]:
    """src 에만 있는 png 를 dst 로 복사(추가 병합, 비파괴)."""
    copied = []
    if not src_dir.exists():
        return copied
    dst_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in dst_dir.glob("*.png")}
    for p in sorted(src_dir.glob("*.png")):
        if not p.is_file() or p.name in existing:
            continue
        if p.stat().st_size < 1000:
            continue
        copied.append(p.name)
        if not dry:
            shutil.copy2(p, dst_dir / p.name)
    return copied


def _union_list(a, b) -> list[str]:
    seen, out = set(), []
    for v in list(a or []) + list(b or []):
        s = str(v).strip()
        if s and s != "library" and s not in seen:  # 'library'/available 는 각 PC가 재계산
            seen.add(s)
            out.append(s)
    return out


def merge_tag_db(local: dict, hub: dict) -> dict:
    li = (local.get("illustrations") or {})
    hi = (hub.get("illustrations") or {})
    merged_ill: dict[str, dict] = {}
    for variant in sorted(set(li) | set(hi)):
        a = li.get(variant) or {}
        b = hi.get(variant) or {}
        entry = {}
        entry["tags"] = _union_list(a.get("tags"), b.get("tags"))
        entry["keywords"] = _union_list(a.get("keywords"), b.get("keywords"))
        # 스칼라/기타 필드: 비어있지 않은 쪽 우선, 그 외 필드도 보존
        for key in set(a) | set(b):
            if key in ("tags", "keywords", "available"):
                continue
            av, bv = a.get(key), b.get(key)
            entry[key] = av if (av not in (None, "", [], {})) else bv
        merged_ill[variant] = entry
    out = dict(local) if local else {}
    out.setdefault("version", hub.get("version", 1))
    out.setdefault("policy", hub.get("policy", ""))
    out["illustrations"] = merged_ill
    out["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    share = resolve_share()
    if share is None:
        print("[lib_sync] 공유 허브 경로가 없습니다.")
        print("  - 환경변수 PHONESPOT_LIBRARY_SHARE=<공유폴더경로>  또는")
        print(f"  - 파일에 경로 한 줄: {SHARE_HINT_FILE}")
        return 2
    if not share.exists():
        try:
            share.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[lib_sync] 공유 경로에 접근 불가: {share} ({exc})")
            return 2

    hub_ill = share / "illustrations"
    hub_db = share / "illustration_tag_db.json"

    print(f"[lib_sync] {'(dry-run) ' if dry else ''}허브: {share}")
    pulled = copy_new_pngs(hub_ill, ILLUST_DIR, dry)       # 허브 -> 로컬
    pushed = copy_new_pngs(ILLUST_DIR, hub_ill, dry)       # 로컬 -> 허브
    print(f"[lib_sync] 그림 가져옴(pull): {len(pulled)}, 올림(push): {len(pushed)}")
    if pulled:
        print("  pulled:", ", ".join(pulled[:12]) + (" ..." if len(pulled) > 12 else ""))
    if pushed:
        print("  pushed:", ", ".join(pushed[:12]) + (" ..." if len(pushed) > 12 else ""))

    local_db = load_json_lenient(DB_PATH)
    hubdb = load_json_lenient(hub_db)
    merged = merge_tag_db(local_db, hubdb)
    before = len((local_db.get("illustrations") or {}))
    after = len(merged.get("illustrations") or {})
    print(f"[lib_sync] 태그DB 항목: {before} -> {after} (병합)")
    if not dry:
        write_json_atomic(DB_PATH, merged)
        write_json_atomic(hub_db, merged)

    print("[lib_sync] 완료." + (" (dry-run, 실제 복사 안 함)" if dry else ""))
    print("  * 새로 받은 그림의 임베딩 지문은 다음 렌더/버튼1에서 자동 생성됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
