#!/usr/bin/env python3
"""Chrome 자동화로 ChatGPT 이미지 생성 (단계 3).

사장님 Chrome 프로필(Profile 1)을 사용해 ChatGPT 로그인 세션 그대로 활용.
1 카드뉴스 = 1 새 채팅 — 채팅 안에서 5장 프롬프트 차례로 입력 + 이미지 다운로드.

사용:
  py scripts\\chrome_chatgpt.py --slug <slug>
    → articles/<slug>.json의 image_prompts 읽어서 images/<slug>/1.png~5.png 생성

  py scripts\\chrome_chatgpt.py --test
    → 로그인 상태만 빠르게 검증 (이미지 생성 안 함)

실패 케이스:
  - Chrome 프로필 잠금: 시작 전 chrome.exe 강제 종료 (taskkill)
  - ChatGPT 로그아웃: 텔레그램 알림 후 exit 1
  - 이미지 생성 타임아웃(3분): 해당 1장만 skip
  - 입력/송신 셀렉터 변경: 텔레그램 에러 알림
"""
import sys
import json
import time
import subprocess
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # automation/scripts/ -> root
CARDNEWS = PROJECT_ROOT / "cardnews"
ARTICLES = CARDNEWS / "articles"
IMAGES = CARDNEWS / "images"

# ===== Chrome / Profile =====
# Chrome 보안 정책상 기본 User Data 폴더는 자동화 차단됨.
# 자동화 전용 별도 폴더를 사용. 첫 실행 시 사장님이 ChatGPT 1회 로그인 필요.
CHROME_USER_DATA_DIR = r"C:\Users\di898\AppData\Local\phonespot_chrome_auto"
CHROME_PROFILE_NAME = "Default"  # 자동화 폴더 안의 Default 사용
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ===== Timeouts =====
PAGE_LOAD_TIMEOUT = 30      # 페이지 로드 대기 (s)
IMAGE_GEN_TIMEOUT = 180     # 이미지 1장 생성 최대 대기 (s) = 3분
POLL_INTERVAL = 5           # 이미지 polling 간격 (s)
SEND_WAIT = 2               # 프롬프트 송신 후 안정 대기 (s)
INPUT_TYPE_DELAY = 10       # 키 입력 사이 ms

# ===== Telegram =====
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from telegram_notify import send as tg
except Exception as e:
    def tg(msg):
        print(f"[tg unavailable: {e}] {msg}")
        return False


def kill_chrome():
    """Profile 잠금 해제 — 모든 chrome.exe 강제 종료 (Windows 한정)."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "chrome.exe"],
            capture_output=True, timeout=10
        )
        time.sleep(2)
    except Exception:
        pass


def fix_chrome_exit_type():
    """이전 강제 종료로 인한 '페이지 복구' 다이얼로그 방지.

    Preferences 파일의 exit_type을 Normal로 설정 + exited_cleanly true.
    이렇게 하면 Chrome이 다음 시작 시 비정상 종료로 인식하지 않음.
    """
    prefs_file = Path(CHROME_USER_DATA_DIR) / CHROME_PROFILE_NAME / "Preferences"
    if not prefs_file.exists():
        return
    try:
        raw = prefs_file.read_text(encoding="utf-8")
        prefs = json.loads(raw)
        if "profile" not in prefs or not isinstance(prefs["profile"], dict):
            prefs["profile"] = {}
        changed = False
        if prefs["profile"].get("exit_type") != "Normal":
            prefs["profile"]["exit_type"] = "Normal"
            changed = True
        if not prefs["profile"].get("exited_cleanly", False):
            prefs["profile"]["exited_cleanly"] = True
            changed = True
        if changed:
            prefs_file.write_text(json.dumps(prefs, ensure_ascii=False),
                                  encoding="utf-8")
    except Exception as e:
        print(f"[warn] Preferences 수정 실패: {e}")


def load_prompts(slug: str) -> list:
    """articles/<slug>.json에서 image_prompts 추출.

    1순위: 'image_prompts' 필드 (list of str)
    2순위: 'cards'에서 headline+body로 폴백 생성
    """
    jf = ARTICLES / f"{slug}.json"
    if not jf.exists():
        raise FileNotFoundError(f"articles/{slug}.json 없음")
    data = json.loads(jf.read_text(encoding="utf-8"))

    if isinstance(data.get("image_prompts"), list) and data["image_prompts"]:
        return data["image_prompts"][:5]

    # Fallback: cards에서 자동 생성
    cards = data.get("cards", [])[:5]
    if len(cards) < 5:
        raise ValueError(
            f"articles/{slug}.json에 image_prompts 없음 + cards {len(cards)}개 (5개 필요)"
        )
    common = (
        "1080x1080, photorealistic editorial. Bright airy mood, "
        "light cream / warm white / pale beige background. "
        "No black background, no dramatic spotlight. "
        "No text on screens, no brand logos, no real human faces. "
        "Numbers/dates blurred. Phonespot orange #F74B0B accent if subtle."
    )
    prompts = []
    for i, c in enumerate(cards, 1):
        head = (
            c.get("headline", "")
            .replace('<span class="hl">', "")
            .replace("</span>", "")
            .replace("\n", " ")
        )
        body = c.get("body", "")
        prompts.append(f"■ {i}.png — {head}\n{common}\n\n{body}")
    return prompts


def download_image(url: str, dst: Path) -> int:
    """이미지 URL → 파일 저장. 바이트 수 반환."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://chatgpt.com/",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    dst.write_bytes(data)
    return len(data)


def is_chatgpt_image_url(src: str) -> bool:
    """ChatGPT가 생성한 이미지 URL 판별 (DALL-E / files.openai / sandbox)."""
    if not src or not src.startswith("http"):
        return False
    markers = [
        "oaiusercontent",
        "files.openai.com",
        "sandbox.openai",
        "dalleprodsec",
        "blob.core.windows",  # 일부 케이스
    ]
    return any(m in src for m in markers)


def wait_for_new_image(page, baseline_count: int) -> str:
    """이미지가 baseline_count 보다 늘어날 때까지 polling. 마지막 ChatGPT 생성 이미지 URL 반환."""
    start = time.time()
    while time.time() - start < IMAGE_GEN_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        imgs = page.locator("img").all()
        if len(imgs) <= baseline_count:
            continue
        # 새로 생긴 이미지 중 ChatGPT URL인 마지막 것 찾기
        for img in reversed(imgs):
            try:
                src = img.get_attribute("src") or ""
                if is_chatgpt_image_url(src):
                    return src
            except Exception:
                continue
    return ""


def open_chatgpt(p):
    """Playwright로 Chrome 열고 ChatGPT 새 채팅 페이지로 이동. (context, page) 반환."""
    context = p.chromium.launch_persistent_context(
        user_data_dir=CHROME_USER_DATA_DIR,
        executable_path=CHROME_EXE,
        channel="chrome",
        headless=False,
        args=[
            f"--profile-directory={CHROME_PROFILE_NAME}",
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--restore-last-session=false",
            "--disable-infobars",
        ],
        timeout=PAGE_LOAD_TIMEOUT * 1000,
    )
    page = context.new_page()
    page.goto("https://chatgpt.com/", wait_until="domcontentloaded",
              timeout=PAGE_LOAD_TIMEOUT * 1000)
    time.sleep(3)
    return context, page


def verify_login(page) -> bool:
    """로그인 상태 확인. 입력창 셀렉터 존재 여부로 판별."""
    if "login" in page.url or "auth" in page.url:
        return False
    # 입력창이 보이면 로그인 상태
    try:
        page.wait_for_selector(
            '#prompt-textarea, [contenteditable="true"][data-id]',
            timeout=10000,
        )
        return True
    except Exception:
        return False


def send_prompt(page, prompt: str):
    """입력창에 prompt 타이핑 후 Enter."""
    sel = '#prompt-textarea, [contenteditable="true"][data-id]'
    page.wait_for_selector(sel, timeout=15000)
    page.click(sel)
    # ChatGPT 입력창은 contenteditable이라 keyboard.type 사용
    # 너무 긴 텍스트는 paste처럼 처리 (clipboard 우회)
    page.keyboard.type(prompt[:4000], delay=INPUT_TYPE_DELAY)
    time.sleep(1)
    page.keyboard.press("Enter")
    time.sleep(SEND_WAIT)


def generate_for_slug(slug: str) -> dict:
    """슬러그 1건 처리. {ok: int, fail: int, errors: [...]} 반환."""
    from playwright.sync_api import sync_playwright

    prompts = load_prompts(slug)
    out_dir = IMAGES / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    tg(f"🎨 [{slug}] Chrome 시작 (프롬프트 {len(prompts)}개)")
    kill_chrome()
    fix_chrome_exit_type()

    result = {"ok": 0, "fail": 0, "errors": []}

    with sync_playwright() as p:
        context, page = open_chatgpt(p)

        if not verify_login(page):
            tg(f"❌ [{slug}] ChatGPT 로그아웃 — 재로그인 필요")
            context.close()
            raise RuntimeError("ChatGPT not logged in")

        # 1 카드뉴스 = 1 새 채팅 (현재 페이지가 새 채팅 상태)
        baseline_imgs = len(page.locator("img").all())

        for i, prompt in enumerate(prompts, 1):
            dst = out_dir / f"{i}.png"
            if dst.exists() and dst.stat().st_size > 10000:
                tg(f"⏭ [{slug}] {i}/{len(prompts)} 이미 존재 — 건너뜀")
                result["ok"] += 1
                baseline_imgs = len(page.locator("img").all())
                continue
            try:
                tg(f"🎨 [{slug}] {i}/{len(prompts)} 입력")
                send_prompt(page, prompt)
                url = wait_for_new_image(page, baseline_imgs)
                if not url:
                    tg(f"⚠ [{slug}] {i}/{len(prompts)} 타임아웃 (3분)")
                    result["fail"] += 1
                    result["errors"].append(f"{i}:timeout")
                    continue
                size = download_image(url, dst)
                tg(f"✓ [{slug}] {i}/{len(prompts)} 저장 ({size//1024} KB)")
                result["ok"] += 1
                baseline_imgs = len(page.locator("img").all())
            except Exception as e:
                tg(f"⚠ [{slug}] {i}/{len(prompts)} 에러: {str(e)[:200]}")
                result["fail"] += 1
                result["errors"].append(f"{i}:{type(e).__name__}")
                continue

        context.close()

    tg(f"🎨 [{slug}] 완료 — OK {result['ok']} / FAIL {result['fail']}")
    return result


def test_login_only():
    """이미지 생성 없이 로그인 상태만 확인."""
    from playwright.sync_api import sync_playwright
    tg("🧪 ChatGPT 로그인 검증 시작")
    kill_chrome()
    fix_chrome_exit_type()
    with sync_playwright() as p:
        context, page = open_chatgpt(p)
        ok = verify_login(page)
        context.close()
    if ok:
        tg("✅ ChatGPT 로그인 OK — 자동화 준비됨")
        return 0
    else:
        tg("❌ ChatGPT 로그아웃 — Chrome에서 재로그인 필요")
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]

    if cmd == "--test":
        sys.exit(test_login_only())

    if cmd == "--slug" and len(sys.argv) >= 3:
        slug = sys.argv[2]
        try:
            r = generate_for_slug(slug)
            sys.exit(0 if r["fail"] == 0 else 2)
        except Exception as e:
            tg(f"❌ [{slug}] 치명적 에러: {str(e)[:200]}")
            raise

    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
