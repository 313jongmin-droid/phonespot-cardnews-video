# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
DOWNLOADS = Path.home() / "Downloads"
DROP = DESK / "ILLUSTRATION_DROP"
ILLUST = SHORTS / "public" / "assets" / "illustrations"
CONFIRMED_PATH = DESK / "IMPORT_CONFIRMED.json"
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}
MIN_SIZE = 10_000
CONFIRMED_MAX_AGE = 24 * 3600  # 하루 지난 확정 매핑은 무시(오염 방지)


def run(script: str, *args: str) -> None:
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *args])
    if result.returncode:
        raise SystemExit(result.returncode)


def warm_image_fingerprints() -> None:
    """새로 들어온 그림의 내용 지문을 캐시에 채운다(렌더 매칭이 내용 기준으로 동작).
    모델 없거나 실패해도 치명적이지 않다(렌더가 텍스트/lexical 로 폴백)."""
    try:
        import codex_image_embed as ie
        if ie.available():
            idx = ie.library_image_index()
            print(f"[fingerprint] 라이브러리 그림 지문 {len(idx)}장 준비")
        else:
            print("[fingerprint] 임베딩 모델 없음 - 지문 생략(렌더는 폴백 매칭)")
    except Exception as exc:  # noqa: BLE001
        print(f"[fingerprint] 생략({exc})")


def _within(path: Path, roots: tuple[Path, ...]) -> bool:
    try:
        rp = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            rp.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def load_confirmed(slug: str) -> list[dict] | None:
    """패널에서 사람이 확정한 매핑. 신선하고 slug 가 맞을 때만 사용."""
    if not CONFIRMED_PATH.exists():
        return None
    try:
        data = json.loads(CONFIRMED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if str(data.get("slug") or "") != slug:
        return None
    if time.time() - float(data.get("generated_at") or 0) > CONFIRMED_MAX_AGE:
        return None
    mapping = data.get("mapping") or []
    return mapping if isinstance(mapping, list) and mapping else None


def consume_confirmed() -> None:
    try:
        CONFIRMED_PATH.rename(CONFIRMED_PATH.with_suffix(".used.json"))
    except OSError:
        try:
            CONFIRMED_PATH.unlink()
        except OSError:
            pass


def apply_confirmed(slug: str, mapping: list[dict]) -> int:
    """패널 검수에서 확정된 정확한 매핑대로 복사한다. mtime 추측을 하지 않는다."""
    roots = (DROP, DOWNLOADS, ILLUST)
    plan: list[tuple[Path, Path]] = []
    for entry in mapping:
        fn = str(entry.get("filename") or "").strip()
        src_raw = str(entry.get("candidate_path") or "").strip()
        if not fn or not src_raw:
            continue
        if fn != Path(fn).name or Path(fn).suffix.lower() not in ALLOWED:
            print(f"[ERROR] 잘못된 대상 파일명: {fn}")
            return 2
        src = Path(src_raw)
        if not src.exists() or not src.is_file() or src.suffix.lower() not in ALLOWED:
            print(f"[ERROR] 원본 그림이 없거나 형식이 아님: {src}")
            return 2
        if src.stat().st_size < MIN_SIZE:
            print(f"[ERROR] 그림이 너무 작음: {src}")
            return 2
        if not _within(src, roots):
            print(f"[ERROR] 허용되지 않은 위치의 파일: {src}")
            return 2
        plan.append((src, ILLUST / fn))

    if not plan:
        print("[ERROR] 확정 매핑이 비어 있습니다.")
        return 2

    ILLUST.mkdir(parents=True, exist_ok=True)
    print(f"Slug: {slug}")
    print("Confirmed import mapping (사람이 패널에서 확정):")
    for src, target in plan:
        print(f"  {src.name} -> {target.name}")
    for src, target in plan:
        shutil.copy2(src, target)
        print(f"[COPY] {target.name}")

    warm_image_fingerprints()
    consume_confirmed()
    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_refresh_workbench.py", slug)
    print("")
    print("[OK] 확정 매핑대로 가져오고 매핑 완료.")
    return 0


def main() -> int:
    slug_path = DESK / "LATEST_SLUG.txt"
    report_path = DESK / "LATEST_PROMPT.json"
    if not slug_path.exists() or not report_path.exists():
        print("[ERROR] Run 01_PREPARE_GPT_PROMPTS.bat first.")
        return 2
    slug = slug_path.read_text(encoding="utf-8").strip()

    # 1) 패널에서 사람이 확정한 매핑이 있으면 그걸 정답으로 사용(이름 추측 안 함)
    confirmed = load_confirmed(slug)
    if confirmed is not None:
        return apply_confirmed(slug, confirmed)

    # 2) (폴백) 확정 매핑이 없으면 기존 동작: 최근 다운로드를 시간순으로 매핑
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    requests = [
        item for item in payload.get("requests", [])
        if item.get("filename") and not (ILLUST / item["filename"]).exists()
        # 자동 발굴 개념(cpt_*)은 '선택' 제안이라 렌더를 막지 않는다.
        and item.get("source") != "concept_scout"
    ]
    if not requests:
        print("[OK] No missing requested illustration. Render can start.")
        return 0

    threshold = report_path.stat().st_mtime - 2

    selected = []
    remaining = []
    for request in requests:
        exact = DROP / request["filename"]
        if exact.exists() and exact.is_file() and exact.stat().st_size >= MIN_SIZE:
            selected.append(exact)
        else:
            remaining.append(request)

    candidates = []
    for folder in (DROP, DOWNLOADS):
        if not folder.exists():
            continue
        candidates.extend(
            item for item in folder.iterdir()
            if item.is_file()
            and item.suffix.lower() in ALLOWED
            and item.stat().st_size >= MIN_SIZE
            and item.stat().st_mtime >= threshold
            and item not in selected
        )
    candidates = sorted(candidates, key=lambda item: item.stat().st_mtime)

    if len(candidates) < len(remaining):
        print(f"[ERROR] Need {len(requests)} requested images, found {len(selected) + len(candidates)}.")
        print(f"[INFO] Exact files found in ILLUSTRATION_DROP: {len(selected)}")
        print(f"[INFO] Recent files found in ILLUSTRATION_DROP/Downloads: {len(candidates)}")
        print("[NEXT] Put GPT Plus images in CODEX_VIDEO_DESK\\ILLUSTRATION_DROP or Downloads, then retry.")
        print("[TIP] If you want to render without new images, use 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.")
        return 3

    selected = selected + candidates[-len(remaining):]
    print("")
    print(f"Slug: {slug}")
    print("Import mapping:")
    for source, request in zip(selected, requests):
        print(f"  {source.name}")
        print(f"    -> {request['filename']}")
    print("")
    answer = input("Import these files and continue? [Y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("[STOP] Nothing imported.")
        return 4

    ILLUST.mkdir(parents=True, exist_ok=True)
    for source, request in zip(selected, requests):
        target = ILLUST / request["filename"]
        shutil.copy2(source, target)
        print(f"[COPY] {target.name}")

    warm_image_fingerprints()
    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_refresh_workbench.py", slug)
    print("")
    print("[OK] Downloads imported and mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# confirmed-mapping aware import (panel review)
