"""자동 일러스트 생성 — chrome_chatgpt.py 활용 (종민님 ChatGPT Plus 구독).

흐름:
1. 누락 일러스트 감지 (output/<slug>/shorts_script.json 의 illust value - 라이브러리)
2. ILLUSTRATIONS_PROMPTS.md 에서 프롬프트 추출
3. cardnews/scripts/chrome_chatgpt.py 의 Playwright 함수 활용 → ChatGPT 자동 호출
4. public/assets/illustrations/<variant>.png 저장

사용:
  py scripts/auto_gen_illust.py           # 자동 감지 모드
  py scripts/auto_gen_illust.py newspaper # 특정 variant 강제 (테스트)
  py scripts/auto_gen_illust.py --list    # 누락 목록만 (생성 X)

조건: 종민님 PC + ChatGPT Plus 로그인된 Chrome Profile 1.
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJ = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJ.parent
CARDNEWS = REPO_ROOT / "cardnews"
ILLUST_DIR = PROJ / "public" / "assets" / "illustrations"
PROMPTS_MD = PROJ / "ILLUSTRATIONS_PROMPTS.md"

# automation/scripts 의 chrome_chatgpt 모듈 활용
sys.path.insert(0, str(REPO_ROOT / "automation" / "scripts"))


def parse_prompts():
    """ILLUSTRATIONS_PROMPTS.md 파싱 -> {variant: prompt}"""
    if not PROMPTS_MD.exists():
        return {}
    md = PROMPTS_MD.read_text(encoding="utf-8")
    pattern = re.compile(r"###\s*\d+\.\s*`(\w+)\.png`[^\n]*\n+```\s*\n(.*?)```", re.DOTALL)
    return {m.group(1): m.group(2).strip() for m in pattern.finditer(md)}


def find_missing():
    existing = set(p.stem for p in ILLUST_DIR.glob("*.png"))
    needed = set()
    output_dir = CARDNEWS / "output"
    if not output_dir.exists():
        return set(), existing
    for sp in output_dir.glob("*/shorts_script.json"):
        try:
            j = json.load(open(sp, encoding="utf-8"))
            for s in [j.get("hook", {})] + j.get("facts", []) + [j.get("cta", {})]:
                for cv in s.get("chunk_visuals", []):
                    if cv.get("type") == "illust":
                        v = cv.get("value")
                        if v:
                            needed.add(v)
        except Exception:
            continue
    return needed - existing, existing


def main():
    list_only = "--list" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    prompts_dict = parse_prompts()
    print(f"[prompts] {len(prompts_dict)} variants in ILLUSTRATIONS_PROMPTS.md")

    if args:
        targets = args
    else:
        missing, existing = find_missing()
        print(f"[lib] existing: {len(existing)} PNG")
        print(f"[missing] {len(missing)}: {sorted(missing)}")
        if not missing:
            print("[OK] 누락 일러스트 없음")
            return 0
        targets = sorted(missing)

    if list_only:
        return 0

    # 프롬프트 매칭
    jobs = []
    skip_list = []
    for v in targets:
        p = prompts_dict.get(v)
        if not p:
            skip_list.append(v)
            continue
        jobs.append((v, p))

    if skip_list:
        print(f"[SKIP] 프롬프트 사전에 없음: {skip_list}")
    if not jobs:
        print("[SKIP] 처리할 일러스트 없음")
        return 0

    print(f"[chrome_chatgpt] {len(jobs)}개 일러스트 생성")
    for v, _ in jobs:
        print(f"  - {v}")

    # chrome_chatgpt 함수 동적 import
    try:
        from chrome_chatgpt import (
            kill_chrome, fix_chrome_exit_type, open_chatgpt, verify_login,
            send_prompt, wait_for_new_image, download_image, tg
        )
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        print(f"[ERROR] chrome_chatgpt 또는 playwright import 실패: {e}")
        return 2

    tg(f"🎨 영상 일러스트 자동 생성 시작 ({len(jobs)}개)")
    kill_chrome()
    fix_chrome_exit_type()

    ok = 0
    fail = 0

    with sync_playwright() as p:
        context, page = open_chatgpt(p)
        if not verify_login(page):
            tg(f"❌ ChatGPT 로그아웃 — 재로그인 필요")
            context.close()
            return 2

        # baseline 이미지 수 (기존 채팅 안 이미지)
        baseline = len(page.locator("img").all())

        for variant, prompt in jobs:
            dst = ILLUST_DIR / f"{variant}.png"
            print(f"\n[GEN] {variant}")
            try:
                send_prompt(page, prompt)
                url = wait_for_new_image(page, baseline)
                if not url:
                    print(f"  ✗ TIMEOUT")
                    tg(f"⚠ [{variant}] 타임아웃 (3분)")
                    fail += 1
                    continue
                size = download_image(url, dst)
                print(f"  ✓ OK ({size//1024} KB)")
                tg(f"✓ [{variant}] 저장 ({size//1024} KB)")
                ok += 1
                # 다음 baseline 갱신
                baseline = len(page.locator("img").all())
            except Exception as e:
                print(f"  ✗ ERROR: {str(e)[:200]}")
                tg(f"⚠ [{variant}] 에러: {str(e)[:100]}")
                fail += 1

        context.close()

    print(f"\n=== DONE. OK={ok}, FAIL={fail} ===")
    tg(f"🎨 일러스트 자동 생성 완료 — OK {ok} / FAIL {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
