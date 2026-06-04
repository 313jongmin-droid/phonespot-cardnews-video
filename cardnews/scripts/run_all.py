#!/usr/bin/env python3
"""다중 기사 일괄 렌더링 (배치 모드).
- articles/*.json 중 images/<slug>/에 이미지 ≥5장이고 output/<slug>/이 미완성인 슬러그만 처리.
- 각 슬러그를 SLUG 환경변수에 넣고 run_windows.py를 순차 실행.
- 마지막에 슬러그별 결과 요약.
"""
import os, sys, subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
ARTICLES_DIR = BASE / 'articles'
IMAGES_DIR = BASE / 'images'
OUTPUT_DIR = BASE / 'output'
RUN_WINDOWS = SCRIPT_DIR / 'run_windows.py'

EXPECTED_CARDS = 18  # 3 사이즈 × 6장

def has_enough_images(slug: str) -> int:
    folder = IMAGES_DIR / slug
    if not folder.exists():
        return 0
    n = 0
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        for p in folder.glob(f'*.{ext}'):
            if p.name.startswith('logo_') or p.name == 'cover.png':
                continue
            n += 1
    return n

def output_card_count(slug: str) -> int:
    out = OUTPUT_DIR / slug
    if not out.exists():
        return 0
    return len(list(out.rglob('card_*.jpg')))

def is_done(slug: str) -> bool:
    # 강화: 18 jpg + captions.md + 각 jpg > 30KB (★ 코덱스 피드백)
    out = OUTPUT_DIR / slug
    if not out.exists():
        return False
    jpgs = list(out.rglob('card_*.jpg'))
    if len(jpgs) < EXPECTED_CARDS:
        return False
    if not (out / 'captions.md').exists():
        return False
    if any(p.stat().st_size < 30 * 1024 for p in jpgs):
        return False
    return True

def main():
    if not ARTICLES_DIR.exists():
        print(f"[error] articles/ folder not found")
        sys.exit(1)

    json_files = sorted(ARTICLES_DIR.glob('*.json'))
    targets, skipped = [], []
    for jf in json_files:
        slug = jf.stem
        n_img = has_enough_images(slug)
        n_out = output_card_count(slug)
        if n_img < 5:
            skipped.append((slug, f'{n_img} imgs (<5)'))
        elif is_done(slug):
            skipped.append((slug, f'already done ({n_out} cards + captions.md)'))
        else:
            targets.append(slug)

    print("=" * 60)
    print(f"phonespot cardnews -- batch runner (run_all.py)")
    print(f"JSON found  : {len(json_files)}")
    print(f"Targets     : {len(targets)}")
    print(f"Skipped     : {len(skipped)}")
    print("=" * 60)
    if skipped:
        print("[Skipped]")
        for s, r in skipped:
            print(f"  - {s}: {r}")
    if not targets:
        print("\nNo targets. Exit.")
        return
    print("\n[Targets]")
    for s in targets:
        print(f"  - {s}")

    results = []
    for i, slug in enumerate(targets, 1):
        print("\n" + "=" * 60, flush=True)
        print(f"[{i}/{len(targets)}] {slug} render start", flush=True)
        print("=" * 60, flush=True)
        env = os.environ.copy()
        env['SLUG'] = slug
        env.setdefault('PYTHONIOENCODING', 'utf-8')
        env['PYTHONUNBUFFERED'] = '1'  # 자식 stdout 즉시 flush
        # 자식 stdout/stderr를 부모 stdout으로 직접 흘려보냄 + line-buffered
        # 이전 버그: stdout 캡처 미명시 + unbuffered 미설정 → run_all_log.txt에 자식 출력 사라짐
        try:
            proc = subprocess.run(
                [sys.executable, '-u', str(RUN_WINDOWS)],
                env=env, cwd=str(BASE),
                timeout=600,  # 10분 안에 못 끝나면 강제 종료 → 다음 슬러그로
            )
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT 600s] -> next slug", flush=True)
            rc = -1
        n_out = output_card_count(slug)
        ok = rc == 0 and n_out >= EXPECTED_CARDS
        print(f"  -> returncode={rc} / output cards={n_out}", flush=True)
        results.append((slug, ok, n_out))

    print("\n" + "=" * 60)
    print("Batch summary")
    print("=" * 60)
    for slug, ok, n in results:
        flag = '[ OK ]' if ok else '[FAIL]'
        print(f"  {flag}  {slug}  ({n} cards)")
    print("=" * 60)

if __name__ == '__main__':
    main()
