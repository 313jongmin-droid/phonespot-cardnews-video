# -*- coding: utf-8 -*-
"""
일러스트 라이브러리 백업/스냅샷

라이브러리(=가장 중요한 자산)를 타임스탬프 스냅샷으로 보관한다. 실수 삭제,
중복정리(--apply) 사고, 드라이브 부분동기화 NUL 손상에 대한 안전망.

대상:
  - 로컬: shorts/public/assets/illustrations/*.png + shorts/config/illustration_tag_db.json
          + shorts/codex/illustration_usage_history.json
  - 허브(설정돼 있으면): <hub>/illustrations/*.png + <hub>/illustration_tag_db.json

보관 위치(저장소 밖, 깃/동기화에 안 휩쓸리게):
  - 환경변수 PHONESPOT_LIBRARY_BACKUP, 없으면  <repo부모>/phonespot_library_backups
회전 보관: 최근 PHONESPOT_LIBRARY_BACKUP_KEEP(기본 10)개만 유지, 오래된 건 삭제.

무결성: 0바이트/NUL 손상 의심 파일을 경고로 표시(스냅샷은 그대로 떠서 타임라인 유지).

사용:
  python scripts/codex_library_backup.py
복원: 스냅샷 폴더의 illustrations/*.png 와 json 을 원위치로 복사하면 됩니다(수동).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import codex_illustration_db as dbm

ROOT = dbm.ROOT
ILLUST_DIR = dbm.ILLUST_DIR
DB_PATH = dbm.DB_PATH
HISTORY_PATH = dbm.HISTORY_PATH
CONFIG_DIR = dbm.CONFIG_DIR
SHARE_HINT_FILE = CONFIG_DIR / "library_share_path.txt"

BACKUP_ROOT = Path(os.environ.get("PHONESPOT_LIBRARY_BACKUP", "").strip()
                   or (ROOT.parent / "phonespot_library_backups"))
KEEP = int(os.environ.get("PHONESPOT_LIBRARY_BACKUP_KEEP", "10") or "10")


def resolve_share() -> Path | None:
    raw = os.environ.get("PHONESPOT_LIBRARY_SHARE", "").strip()
    if not raw and SHARE_HINT_FILE.exists():
        raw = SHARE_HINT_FILE.read_text(encoding="utf-8-sig", errors="replace").strip()
    return Path(raw) if raw else None


def suspect(path: Path) -> str:
    """손상 의심이면 사유 문자열, 정상이면 빈 문자열."""
    try:
        size = path.stat().st_size
    except OSError:
        return "stat 실패"
    if size == 0:
        return "0바이트"
    if path.suffix.lower() == ".json":
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                return "NUL 포함(부분동기화 의심)"
            json.loads(raw.decode("utf-8-sig", errors="replace"))
        except json.JSONDecodeError:
            return "JSON 파싱 실패"
        except OSError:
            return "읽기 실패"
    elif size < 200:
        return "너무 작음(손상 의심)"
    return ""


def snapshot(label: str, illust_dir: Path, files: list[Path]) -> dict:
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_ROOT / label / f"snapshot_{ts}"
    (dest / "illustrations").mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    n_png = 0
    if illust_dir and illust_dir.exists():
        for p in sorted(illust_dir.glob("*.png")):
            if not p.is_file():
                continue
            why = suspect(p)
            if why:
                warnings.append(f"{p.name}: {why}")
            shutil.copy2(p, dest / "illustrations" / p.name)
            n_png += 1
    n_meta = 0
    for f in files:
        if f and f.exists():
            why = suspect(f)
            if why:
                warnings.append(f"{f.name}: {why}")
            shutil.copy2(f, dest / f.name)
            n_meta += 1
    (dest / "manifest.json").write_text(json.dumps({
        "label": label, "created_at": ts, "png": n_png, "meta_files": n_meta,
        "warnings": warnings,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dest": dest, "png": n_png, "meta": n_meta, "warnings": warnings}


def rotate(label: str, keep: int) -> int:
    base = BACKUP_ROOT / label
    if not base.exists():
        return 0
    snaps = sorted([d for d in base.iterdir() if d.is_dir() and d.name.startswith("snapshot_")])
    removed = 0
    for d in snaps[:-keep] if keep > 0 else []:
        try:
            shutil.rmtree(d)
            removed += 1
        except OSError:
            pass
    return removed


def main() -> int:
    try:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[backup] 백업 위치 생성 불가: {BACKUP_ROOT} ({exc})")
        return 2
    print(f"[backup] 보관 위치: {BACKUP_ROOT} (최근 {KEEP}개 유지)")

    results = []
    # 1) 로컬
    res = snapshot("local", ILLUST_DIR, [DB_PATH, HISTORY_PATH])
    rot = rotate("local", KEEP)
    results.append(("local", res, rot))

    # 2) 허브(설정 시)
    hub = resolve_share()
    if hub and hub.exists():
        res_h = snapshot("hub", hub / "illustrations", [hub / "illustration_tag_db.json"])
        rot_h = rotate("hub", KEEP)
        results.append(("hub", res_h, rot_h))

    for label, res, rot in results:
        print(f"[backup] {label}: 그림 {res['png']}장 + 메타 {res['meta']}개 -> {res['dest'].name} (오래된 {rot}개 정리)")
        for w in res["warnings"]:
            print(f"   [경고] {label} 손상 의심: {w}")
    print("[backup] 완료. 복원은 스냅샷 폴더의 파일을 원위치로 복사하면 됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
