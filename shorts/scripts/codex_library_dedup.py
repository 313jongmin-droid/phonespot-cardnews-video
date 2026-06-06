# -*- coding: utf-8 -*-
"""
라이브러리 중복 정리 (canonical/dedup)

여러 PC가 같은 개념을 다른 이름으로 그려 라이브러리에 비슷한 그림이 쌓이는 걸 막는다.
CLIP 이미지-이미지 유사도로 '거의 같은' 그림을 군집화해서:
  - 기본(report): 군집을 리포트로만 보여준다(읽기전용, 안전).
  - --apply: 각 군집에서 대표(canonical) 1개만 남기고 나머지 png 삭제 + 태그DB 병합.

대표 선택 규칙: 사람이 붙인 이름(비-cpt_) 우선 → 짧은 이름 → 알파벳.
임계값: PHONESPOT_DEDUP_SIM (기본 0.92, 이미지-이미지 코사인). 높을수록 '진짜 거의 동일'만.

주의:
- --apply 는 파일을 삭제한다. 먼저 report 로 확인하고, 백업(공유 허브/깃)이 있는 상태에서.
- 임베딩 모델이 없으면 동작 불가(그림 내용 비교라 텍스트 폴백 없음) → 안내 후 종료.

사용:
  python scripts/codex_library_dedup.py            # 리포트만(읽기전용)
  python scripts/codex_library_dedup.py --apply     # 실제 정리(삭제+병합)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import codex_image_embed as ie
import codex_illustration_db as dbm

ILLUST_DIR = dbm.ILLUST_DIR
DB_PATH = dbm.DB_PATH
CODEX_DIR = dbm.CODEX_DIR
REPORT_MD = CODEX_DIR / "library_dedup_report.md"
REPORT_JSON = CODEX_DIR / "library_dedup_report.json"
SIM = float(os.getenv("PHONESPOT_DEDUP_SIM", "0.92"))


def _np():
    try:
        import numpy as np
        return np
    except Exception:
        return None


def cluster_duplicates(index: dict, threshold: float) -> list[list[str]]:
    """근접중복 군집(크기>=2)만 반환. union-find."""
    np = _np()
    variants = list(index)
    n = len(variants)
    if np is None or n < 2:
        return []
    mat = np.stack([np.asarray(index[v], dtype=np.float32) for v in variants])
    # 벡터는 이미 L2 정규화됨 → 내적이 코사인
    sim = mat @ mat.T
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        row = sim[i]
        for j in range(i + 1, n):
            if row[j] >= threshold:
                union(i, j)
    groups: dict[int, list[str]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(variants[i])
    return [sorted(g) for g in groups.values() if len(g) > 1]


def pick_canonical(members: list[str]) -> str:
    def key(v: str):
        return (v.startswith("cpt_"), len(v), v)  # 비-cpt 우선, 짧은 이름, 알파벳
    return sorted(members, key=key)[0]


def load_db_lenient() -> dict:
    try:
        raw = DB_PATH.read_bytes()
        txt = raw.decode("utf-8-sig", errors="replace").replace("\x00", " ")
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            obj, _ = json.JSONDecoder().raw_decode(txt.lstrip())
            return obj
    except Exception:
        return {}


def write_json_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_report(index: dict, clusters: list[list[str]]) -> dict:
    rows = []
    np = _np()
    for members in clusters:
        canon = pick_canonical(members)
        cv = index[canon]
        dups = []
        for m in members:
            if m == canon:
                continue
            s = float(np.dot(np.asarray(cv), np.asarray(index[m]))) if np is not None else 0.0
            dups.append({"variant": m, "sim_to_canonical": round(s, 4)})
        rows.append({"canonical": canon, "duplicates": dups})
    total_dups = sum(len(r["duplicates"]) for r in rows)
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "threshold": SIM,
        "library_count": len(index),
        "clusters": rows,
        "removable_duplicates": total_dups,
    }


def write_report(report: dict) -> None:
    write_json_atomic(REPORT_JSON, report)
    lines = [
        "# 라이브러리 중복 점검 리포트",
        "",
        f"- 생성: {report['generated_at']}",
        f"- 유사도 임계: {report['threshold']} (PHONESPOT_DEDUP_SIM)",
        f"- 라이브러리 그림: {report['library_count']}장",
        f"- 군집 수: {len(report['clusters'])}, 정리하면 줄어들 중복: {report['removable_duplicates']}장",
        "",
        "각 군집에서 '대표' 하나만 남기고 나머지를 정리할 수 있습니다(--apply).",
        "",
    ]
    for i, c in enumerate(report["clusters"], 1):
        lines.append(f"## {i}. 대표: `{c['canonical']}`")
        for d in c["duplicates"]:
            lines.append(f"   - 중복 후보 `{d['variant']}`  (유사도 {d['sim_to_canonical']})")
        lines.append("")
    CODEX_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_dedup(report: dict) -> tuple[int, int]:
    """대표만 남기고 중복 png 삭제 + 태그DB 병합. (삭제수, 병합항목수) 반환."""
    db = load_db_lenient()
    illus = db.get("illustrations") or {}
    removed = 0
    merged = 0
    for c in report["clusters"]:
        canon = c["canonical"]
        centry = illus.get(canon) or {}
        for d in c["duplicates"]:
            v = d["variant"]
            # 태그/키워드 병합
            de = illus.get(v) or {}
            for fld in ("tags", "keywords"):
                vals = list(centry.get(fld) or []) + list(de.get(fld) or [])
                seen, out = set(), []
                for x in vals:
                    x = str(x).strip()
                    if x and x != "library" and x not in seen:
                        seen.add(x); out.append(x)
                centry[fld] = out
            illus.pop(v, None)
            merged += 1
            # 파일 삭제
            png = ILLUST_DIR / f"{v}.png"
            try:
                if png.exists():
                    png.unlink()
                    removed += 1
            except OSError as exc:
                print(f"[dedup][WARN] 삭제 실패 {png.name}: {exc}")
        illus[canon] = centry
    db["illustrations"] = illus
    write_json_atomic(DB_PATH, db)
    return removed, merged


def main() -> int:
    apply = "--apply" in sys.argv
    if not ie.available():
        print("[dedup] 임베딩 모델이 없어 그림 내용 비교 불가. SETUP_EMBED 후 다시 실행.")
        return 2
    index = ie.library_image_index()
    if not index:
        print("[dedup] 라이브러리 그림이 없습니다.")
        return 0
    clusters = cluster_duplicates(index, SIM)
    report = build_report(index, clusters)
    write_report(report)
    print(f"[dedup] 라이브러리 {report['library_count']}장 / 군집 {len(clusters)} / 정리가능 중복 {report['removable_duplicates']}장 (임계 {SIM})")
    print(f"[dedup] 리포트: {REPORT_MD}")
    if not apply:
        if report["removable_duplicates"]:
            print("[dedup] 정리하려면 --apply 로 다시 실행하세요(파일 삭제됨, 먼저 백업 권장).")
        return 0
    removed, merged = apply_dedup(report)
    print(f"[dedup] 정리 완료: 삭제 {removed}장, 태그DB 병합 {merged}건.")
    print("  * 다음 렌더/버튼1에서 임베딩 지문이 갱신됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
