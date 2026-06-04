#!/usr/bin/env python3
"""야간 자동 처리 daemon (Path B).

매일 02:00 Windows Task Scheduler가 실행:
1. articles/*.json 스캔 → images/<slug>/ 폴더 있고 이미지 0장이고 output 미완성인 슬러그 찾기
2. 각 슬러그:
   - (Day 3 예정) Chrome 자동화로 ChatGPT 이미지 5장 생성 → images/<slug>/에 1.png~5.png
3. (Day 4 예정) run_all.bat 자동 실행 → 18장 × N + captions
4. 진행 상황·결과 텔레그램 알림

현재 (Day 2): 골격만. 큐 스캔 + 텔레그램 알림까지.

사장님 아침 워크플로우:
  - Cowork에서 신규 뉴스 수집 + 후보 선택
  - articles/<slug>.json 작성 (image_prompts 필드 포함)
  - images/<slug>/ 폴더 생성 (비어있는 상태로)
  - 이 daemon이 새벽 02:00에 자동 처리
"""
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # automation/scripts/ -> root
CARDNEWS = PROJECT_ROOT / "cardnews"
ARTICLES = CARDNEWS / "articles"
IMAGES = CARDNEWS / "images"
OUTPUT = CARDNEWS / "output"
RUN_ALL_BAT = CARDNEWS / "run_all.bat"

# telegram_notify를 같은 폴더에서 import
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from telegram_notify import send as tg
except Exception as e:
    def tg(msg):
        print(f"[telegram unavailable: {e}] {msg}")
        return False

EXPECTED_OUTPUT = 18  # 3 사이즈 × 6 카드


def count_images(folder: Path) -> int:
    if not folder.exists():
        return 0
    n = 0
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        if p.name.startswith("logo_") or p.name == "cover.png":
            continue
        n += 1
    return n


def count_output_cards(slug: str) -> int:
    out = OUTPUT / slug
    if not out.exists():
        return 0
    return len(list(out.rglob("card_*.jpg")))


def find_pending_slugs() -> list:
    """처리 대상 슬러그 목록.

    조건:
    - articles/<slug>.json 존재
    - images/<slug>/ 폴더 존재 (사장님이 아침에 만들어야 함)
    - 이미지 5장 미만 (이미지 생성 필요)
    - output 미완성
    """
    if not ARTICLES.exists():
        return []
    pending = []
    for jf in sorted(ARTICLES.glob("*.json")):
        slug = jf.stem
        img_dir = IMAGES / slug
        if not img_dir.exists():
            continue  # 사장님이 아침에 폴더 안 만들었음 — 건너뜀
        n_out = count_output_cards(slug)
        if n_out >= EXPECTED_OUTPUT:
            continue  # 출력 완성 — 이미 처리됨
        n_img = count_images(img_dir)
        if n_img < 5:
            pending.append(slug)  # 이미지 부족 = 신규 처리 대상
        # n_img >= 5인데 출력 미완성 = 렌더링만 필요 (Day 4 run_all.bat)
    return pending


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    pending = find_pending_slugs()

    if not pending:
        msg = f"🌙 야간 사이클 {now}\n큐 비어있음 → 사이클 스킵"
        tg(msg)
        print(f"[daemon] {msg}")
        return

    lines = [f"🌙 야간 사이클 시작 ({now})", f"대상 {len(pending)}건:"]
    for s in pending:
        lines.append(f"  • {s}")
    tg("\n".join(lines))

    print(f"[daemon] Found {len(pending)} pending: {pending}")

    # ===== Day 3 예정 =====
    # for slug in pending:
    #     image_prompts = load_prompts_from_json(slug)
    #     for i, prompt in enumerate(image_prompts, 1):
    #         tg(f"🎨 {slug} 이미지 {i}/{len(image_prompts)} 생성 중...")
    #         chrome_generate_image(prompt, IMAGES / slug / f"{i}.png")
    #     tg(f"✅ {slug} 이미지 완료")

    # ===== Day 4 예정 =====
    # tg("🎬 렌더링 시작 (run_all.bat)")
    # import subprocess
    # proc = subprocess.run([str(RUN_ALL_BAT)], cwd=str(PROJECT))
    # if proc.returncode == 0:
    #     tg(f"✔ 사이클 완료 — {len(pending)}건 × 18장 + captions 생성")
    # else:
    #     tg(f"✗ 렌더링 실패 (exit {proc.returncode}) — 로그 확인")

    tg("⚠ 이미지 생성·렌더링 단계 미구현 (Day 3·4 예정). 현재 골격만 작동.")


if __name__ == "__main__":
    main()
