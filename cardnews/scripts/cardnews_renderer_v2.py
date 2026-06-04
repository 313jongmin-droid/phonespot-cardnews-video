#!/usr/bin/env python3
"""원UI 8.5 정식 배포 시작 카드뉴스 (v5)
- 흰 배경 + 검정 텍스트 + 오렌지 강조
- 카드 1: 매거진 스타일 (cover 풀스크린 + 좌측 텍스트)
- 폰트: Pretendard 9종 OTF 로컬 다운로드 + file:// 로 직접 로드
- 카드 2~6: h2 좌측 오렌지 바, 1~2문장 기사체 본문
- 폰스팟 로고: 누끼 (logo_cutout_*.png), 가운데, 2배
"""
import subprocess, shutil, urllib.request, re, os
from pathlib import Path

BASE = Path('/mnt/user-data/outputs/cardnews_tool')
OUT = Path('/mnt/user-data/outputs/iphone18_spec_downgrade_v2')
OUT.mkdir(parents=True, exist_ok=True)

# SLUG 자동 결정: 환경변수(run_windows.py가 설정) 우선, 없으면 articles/ 최근 JSON.
# ★ 이미지 폴더 경로를 SLUG에서 파생 — 하드코딩 금지 (옛 기사 폴더 재사용 사고 차단)
SLUG = os.environ.get('SLUG', '')
if not SLUG:
    _ad = BASE / 'articles'
    if _ad.exists():
        _jf = sorted(_ad.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        if _jf:
            SLUG = _jf[0].stem

SLUG_IMG_DIR = BASE / 'images' / SLUG  # images/<slug>/
COVER_SRC = SLUG_IMG_DIR / 'cover.png'
LOGO_WHITE_SRC = BASE / 'images' / 'logo_cutout_white.png'
LOGO_COLOR_SRC = BASE / 'images' / 'logo_cutout_original.png'
LOGO_TRIM_SRC = BASE / 'images' / 'logo_cutout_trimmed.png'
print(f"[slug] SLUG={SLUG!r}  IMG_DIR={SLUG_IMG_DIR}")

# v8 auto-rename: 카드 1~5만 자동 매핑 (카드 6은 배경 이미지 X, 로고 사용)
def _auto_rename_cards():
    """images/<slug>/ 폴더의 비-card 이미지를 시간순으로 card_1~5.png 자동 매핑.
    카드 6은 배경 이미지 사용 안 함 (로고 사용). 따라서 GPT는 5장만 생성하면 됨."""
    existing = [p for p in SLUG_IMG_DIR.glob('card_*.png') if p.stem in ('card_1','card_2','card_3','card_4','card_5')]
    if len(existing) >= 5:
        return

    skip = {'cover.png', '.placeholder'}
    skip_prefixes = ('card_', 'logo_')
    candidates = []
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        for p in SLUG_IMG_DIR.glob(f'*.{ext}'):
            if p.name in skip:
                continue
            if any(p.name.startswith(prefix) for prefix in skip_prefixes):
                continue
            candidates.append(p)
    if len(candidates) < 5:
        print(f"[auto-rename] found {len(candidates)} candidate images (need 5). using existing card_*.png.")
        return

    # 파일명이 숫자(1~5)로 시작하면 숫자 순서로 매핑, 아니면 mtime 순서.
    # 예: 1.png 2.png 3.png ... → 그대로 card_1~5 / "1 (1).png", "3-xxx.png"도 인식
    def _lead_num(p):
        m = re.match(r'\s*(\d+)', p.stem)
        return int(m.group(1)) if m else None
    _nums = [_lead_num(p) for p in candidates]
    _use_num = (all(n is not None for n in _nums)
                and len(set(_nums)) == len(_nums))
    if _use_num:
        candidates.sort(key=_lead_num)
        print(f"[auto-rename] numeric filenames detected -> numeric order:")
    else:
        candidates.sort(key=lambda p: p.stat().st_mtime)
        print(f"[auto-rename] {len(candidates[:5])} files -> mtime order:")
    for i, src_img in enumerate(candidates[:5], 1):
        dst = SLUG_IMG_DIR / f'card_{i}.png'
        if dst.exists() and dst.stat().st_mtime > src_img.stat().st_mtime:
            print(f"  skip card_{i}.png (already up-to-date)")
            continue
        try:
            if src_img.suffix.lower() == '.png':
                shutil.copy(src_img, dst)
            else:
                from PIL import Image
                im = Image.open(src_img)
                if im.mode in ('RGBA', 'LA'):
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                elif im.mode != 'RGB':
                    im = im.convert('RGB')
                im.save(dst, 'PNG')
            print(f"  {src_img.name} → card_{i}.png")
        except Exception as e:
            print(f"  [error] {src_img.name}: {e}")

_auto_rename_cards()

for sz in ['1x1', '4x5', '9x16']:
    (OUT / sz).mkdir(exist_ok=True)
    if LOGO_WHITE_SRC.exists():
        shutil.copy(LOGO_WHITE_SRC, OUT / sz / 'logo_white.png')
    if LOGO_COLOR_SRC.exists():
        shutil.copy(LOGO_COLOR_SRC, OUT / sz / 'logo_color.png')
    if LOGO_TRIM_SRC.exists():
        shutil.copy(LOGO_TRIM_SRC, OUT / sz / 'logo_color_trimmed.png')
    if COVER_SRC.exists():
        shutil.copy(COVER_SRC, OUT / sz / 'cover.png')
    # v8 매거진 톤 — 카드 1~5 이미지만 복사 (카드 6은 로고 사용, 배경 이미지 X)
    for _i in range(1, 6):
        for _ext in ('png', 'jpg', 'jpeg'):
            _img = SLUG_IMG_DIR / f'card_{_i}.{_ext}'
            if _img.exists():
                shutil.copy(_img, OUT / sz / f'card_{_i}.png')
                break

SIZE_CONFIG = {
    '1x1':  {'w': 1080, 'h': 1080},
    '4x5':  {'w': 1080, 'h': 1350},
    '9x16': {'w': 1080, 'h': 1920},
}

FF = '"Pretendard", "Noto Sans KR", "Malgun Gothic", sans-serif'

# 폰트 로컬 임베드 (★ 코덱스 피드백 — CDN 의존 X, fonts/ woff 9종 직접 로드)
_FONTS_DIR = BASE / 'fonts'
_FONT_FACES = ""
for _fn, _w in [
    ('Pretendard-Thin.woff', 100),
    ('Pretendard-ExtraLight.woff', 200),
    ('Pretendard-Light.woff', 300),
    ('Pretendard-Regular.woff', 400),
    ('Pretendard-Medium.woff', 500),
    ('Pretendard-SemiBold.woff', 600),
    ('Pretendard-Bold.woff', 700),
    ('Pretendard-ExtraBold.woff', 800),
    ('Pretendard-Black.woff', 900),
]:
    _fp = _FONTS_DIR / _fn
    if _fp.exists():
        _url = _fp.resolve().as_uri()
        _FONT_FACES += f"@font-face {{ font-family: 'Pretendard'; src: url('{_url}') format('woff'); font-weight: {_w}; font-style: normal; font-display: swap; }}\n"

LOGO_HEIGHT = {'1x1': 128, '4x5': 144, '9x16': 176}
LOGO_BOTTOM = {'1x1': 50, '4x5': 60, '9x16': 80}
PAGE_BOTTOM = {'1x1': 70, '4x5': 80, '9x16': 100}
PAGE_RIGHT = {'1x1': 60, '4x5': 80, '9x16': 80}
PAGE_SIZE = {'1x1': 24, '4x5': 26, '9x16': 32}

GLOBAL_FONT_RESET = f"""
{_FONT_FACES}
* {{ font-family: {FF} !important; box-sizing: border-box; margin: 0; padding: 0; }}
html, body, div, span, h1, h2, h3, h4, h5, h6, p, a, b, strong, em, i, u, img {{ font-family: {FF} !important; }}
"""


# ========================================================================
# v8 매거진 통일 톤 (basicappleguy 스타일)
# ========================================================================
# 모든 카드 (1~6) 같은 레이아웃: 이미지 상단 + 검정 텍스트 영역 하단.
# articles/<slug>.json의 cards 배열에서 6개 카드 데이터 로드.
# 이미지 파일: images/<slug>/card_1.png ~ card_6.png

def render_card_magazine(size, page_num, image_filename, headline, body, source=""):
    """v8 매거진 통일 카드 — 이미지 풀스크린 + 하단 그라데이션 + 텍스트 오버레이.
    이미지는 카드 전체를 채우고, 하단 50%까지 자연스러운 검정 그라데이션이 덮어
    텍스트 가독성 확보.
    Args:
        size: '1x1' / '4x5' / '9x16'
        page_num: 1~6
        image_filename: 'card_1.png' 등
        headline: 큰 흰 헤드라인 (한 줄 또는 두 줄)
        body: 옅은 흰 본문 (3~4줄 권장)
        source: 우측 상단 작은 회색 출처
    """
    w, h = SIZE_CONFIG[size]['w'], SIZE_CONFIG[size]['h']

    if size == '1x1':
        # +2pt: head 60→62, body 26→28, source 18→20
        head_size, body_size, source_size = 62, 28, 20
        text_left = 70
        text_bottom = 75      # 70 → 75 (조금 더 위로)
        grad_ratio = 0.58     # 0.55 → 0.58 (그라데이션 살짝 더 길게)
        source_top = 50
    elif size == '4x5':
        # +2pt: head 76→78, body 32→34, source 22→24
        head_size, body_size, source_size = 78, 34, 24
        text_left = 80
        text_bottom = 95      # 90 → 95
        grad_ratio = 0.57     # 0.55 → 0.57
        source_top = 60
    else:
        # +2pt: head 104→106, body 42→44, source 30→32
        head_size, body_size, source_size = 106, 44, 32
        text_left = 90
        text_bottom = 130     # 120 → 130
        grad_ratio = 0.52     # 0.50 → 0.52
        source_top = 80

    grad_height = int(h * grad_ratio)
    fade_top = h - grad_height  # 그라데이션 시작 위치 (위에서부터)

    css = """
{GLOBAL_FONT_RESET}
html, body {{ background: #000000; -webkit-font-smoothing: antialiased; font-family: {FF} !important; }}
.card {{ width: {w}px; height: {h}px; position: relative; overflow: hidden; background: #000000; font-family: {FF} !important; }}
.bg-img {{
  position: absolute; top: 0; left: 0; width: {w}px; height: {h}px;
  object-fit: cover; object-position: center; z-index: 1;
}}
.fade {{
  position: absolute; left: 0; right: 0;
  top: {fade_top}px; height: {grad_height}px;
  background-image: linear-gradient(
    to bottom,
    rgba(0,0,0,0) 0%,
    rgba(0,0,0,0.15) 18%,
    rgba(0,0,0,0.45) 42%,
    rgba(0,0,0,0.78) 70%,
    rgba(0,0,0,0.95) 100%
  );
  z-index: 2;
}}
.card6-bg {{
  position: absolute; top: 0; left: 0; width: {w}px; height: {h}px;
  background: #FFFFFF;
  z-index: 1;
}}
/* 카드 6 전용 텍스트 색상 반전 (흰 배경) */
.card6-mode .fade {{ display: none; }}
.card6-mode .headline {{ color: #1A1A1A !important; text-shadow: none !important; }}
.card6-mode .body {{ color: rgba(26,26,26,0.78) !important; text-shadow: none !important; }}
.card6-mode .source {{ color: rgba(26,26,26,0.55) !important; text-shadow: none !important; }}
.card6-mode .page-ind {{ color: rgba(26,26,26,0.4) !important; }}
.card6-mode .headline .hl, .card6-mode .body .hl {{ color: #F74B0B !important; }}
.card6-logo-area {{
  position: absolute; top: 0; left: 0; width: {w}px; height: {fade_top_for_logo}px;
  display: flex; align-items: center; justify-content: center;
  z-index: 3;
}}
.text-area {{
  position: absolute;
  left: {text_left}px; right: {text_left}px;
  bottom: {text_bottom}px;
  z-index: 5;
  font-family: {FF} !important;
}}
.headline {{
  font-family: {FF} !important;
  font-size: {head_size}px; font-weight: 900;
  line-height: 1.14;
  color: #FFFFFF !important;
  letter-spacing: -2.5px;
  margin-bottom: 26px;
  text-shadow: 0 2px 16px rgba(0,0,0,0.5);
}}
.headline .hl, .body .hl {{
  color: #F74B0B !important;
}}
.body {{
  font-family: {FF} !important;
  font-size: {body_size}px; font-weight: 500;
  line-height: 1.62;
  color: rgba(255,255,255,0.9) !important;
  letter-spacing: -0.3px;
  text-shadow: 0 1px 8px rgba(0,0,0,0.4);
}}
.source {{
  position: absolute;
  top: {source_top}px; right: {text_left}px;
  font-family: {FF} !important;
  font-size: {source_size}px; font-weight: 500;
  color: rgba(255,255,255,0.65) !important;
  letter-spacing: -0.2px;
  text-shadow: 0 1px 6px rgba(0,0,0,0.4);
  z-index: 10;
}}
.page-ind {{
  position: absolute;
  bottom: {pbot}px; right: {pright}px;
  font-family: {FF} !important;
  color: rgba(255,255,255,0.45) !important;
  font-weight: 500;
  font-size: {psize}px;
  letter-spacing: 0.5px;
  z-index: 10;
}}
""".format(
    GLOBAL_FONT_RESET=GLOBAL_FONT_RESET, FF=FF,
    w=w, h=h, grad_height=grad_height, fade_top=fade_top,
    fade_top_for_logo=fade_top + int(grad_height * 0.3),
    text_left=text_left, text_bottom=text_bottom,
    head_size=head_size, body_size=body_size, source_size=source_size,
    source_top=source_top,
    pbot=PAGE_BOTTOM[size], pright=PAGE_RIGHT[size], psize=PAGE_SIZE[size]
)
    # 카드 6은 배경 이미지 X — 다크 그라데이션 배경 + 중앙 큰 폰스팟 로고
    if page_num == 6:
        if size == '1x1':
            big_logo_h = 200
        elif size == '4x5':
            big_logo_h = 260
        else:
            big_logo_h = 360
        # 카드 6 전용 HTML — 이미지 영역에 로고를 배치
        bg_image_html = f'<div class="card6-bg"></div><div class="card6-logo-area"><img src="logo_color_trimmed.png" alt="Phonespot" style="height: {big_logo_h}px; display: block;"></div>'
        logo_html = ''
    else:
        bg_image_html = f'<img class="bg-img" src="{image_filename}" alt="">'
        logo_html = ''

    return """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>{css}</style></head><body>
<div class="{card_class}">
  {bg_image_html}
  <div class="fade"></div>
  <div class="source">{source}</div>
  <div class="text-area">
    {logo_html}
    <div class="headline">{headline}</div>
    <div class="body">{body}</div>
  </div>
  <div class="page-ind">{page_num} / 6</div>
</div></body></html>""".format(
    css=css, bg_image_html=bg_image_html, source=source,
    logo_html=logo_html,
    card_class='card card6-mode' if page_num == 6 else 'card',
    headline=headline.replace('\n', '<br>'),
    body=body.replace('\n', '<br>'),
    page_num=page_num
)


# articles/<slug>.json의 cards 배열 로드 (v8 매거진 모드)
def _load_cards_data():
    """articles/<slug>.json의 cards 필드 로드. 없으면 None 반환 (legacy 모드)."""
    import json as _json
    import os as _os
    _slug = _os.environ.get('SLUG', '')
    if not _slug:
        _articles_dir = BASE / 'articles'
        if _articles_dir.exists():
            _json_files = sorted(_articles_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
            if _json_files:
                _slug = _json_files[0].stem
    _article_path = BASE / 'articles' / f'{_slug}.json'
    if _article_path.exists():
        try:
            _data = _json.loads(_article_path.read_text(encoding='utf-8'))
            return _data.get('cards', None), _data.get('source_line', '')
        except Exception:
            return None, ''
    return None, ''


CARDS_DATA, SOURCE_LINE = _load_cards_data()
USE_MAGAZINE_MODE = CARDS_DATA is not None and len(CARDS_DATA) == 6


# ========== 메인 렌더 (v9 — 매거진 모드 강제) ==========
# articles/<slug>.json의 cards 필드 6개 데이터로 렌더링.
# cards 필드 없으면 에러로 명시 (legacy 모드 폐기).

if not USE_MAGAZINE_MODE:
    raise RuntimeError(
        f"\n[에러] articles/<slug>.json에 cards 배열(6개)이 없습니다.\n"
        f"v9 매거진 모드는 cards 필수입니다.\n"
        f"슬러그 폴더: {COVER_SRC.parent.name}\n"
        f"예시 구조:\n"
        f"  {{\n"
        f"    \"slug\": \"...\",\n"
        f"    \"cards\": [\n"
        f"      {{\"image\": \"card_1.png\", \"headline\": \"...\", \"body\": \"...\", \"source\": \"...\"}},\n"
        f"      ... (6개)\n"
        f"    ],\n"
        f"    \"captions_md\": \"...\"\n"
        f"  }}"
    )

# JSON 스키마 검증
_required_card_fields = ('headline', 'body')
for _i, _card in enumerate(CARDS_DATA, 1):
    _missing = [f for f in _required_card_fields if not _card.get(f)]
    if _missing:
        raise RuntimeError(f"[error] card {_i} missing required fields: {_missing}")

print(f"[v9 magazine mode] {len(CARDS_DATA)} cards loaded + schema OK")
def _make_renderer(i, card_data, src_line):
    return lambda size: render_card_magazine(
        size, page_num=i,
        image_filename=card_data.get('image', f'card_{i}.png'),
        headline=card_data.get('headline', ''),
        body=card_data.get('body', ''),
        source=card_data.get('source', src_line)
    )
RENDERERS = [(i+1, _make_renderer(i+1, card, SOURCE_LINE)) for i, card in enumerate(CARDS_DATA)]

# ========== Playwright 렌더링 ==========
from playwright.sync_api import sync_playwright
import time
_t0 = time.time()
with sync_playwright() as p:
    browser = p.chromium.launch()
    for size, cfg in SIZE_CONFIG.items():
        size_dir = OUT / size
        print(f"\n=== {size} ({cfg['w']}x{cfg['h']}) ===")
        ctx = browser.new_context(viewport={'width': cfg['w'], 'height': cfg['h']}, device_scale_factor=1)
        page = ctx.new_page()
        for i, render_fn in RENDERERS:
            html = render_fn(size)
            html_path = size_dir / f'card_{i}.html'
            jpg_path = size_dir / f'card_{i}.jpg'
            html_path.write_text(html, encoding='utf-8')
            page.goto('file:///' + html_path.as_posix())
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except Exception:
                pass
            page.screenshot(
                path=str(jpg_path),
                type='jpeg', quality=85,
                full_page=False,
                clip={'x': 0, 'y': 0, 'width': cfg['w'], 'height': cfg['h']}
            )
            html_path.unlink()
            print(f"  OK card_{i}.jpg")
        ctx.close()
    browser.close()
print(f"\nRender time: {time.time() - _t0:.1f}s")

# Clean up
for sz in ['1x1', '4x5', '9x16']:
    for fn in ['logo.jpg', 'logo_white.png', 'logo_color.png', 'cover.png']:
        p = OUT / sz / fn
        if p.exists():
            p.unlink()


# ========== JPG size summary ==========
print("\n=== JPG result ===")
total_kb = 0
count = 0
for jpg in sorted(OUT.rglob('card_*.jpg')):
    sz_kb = jpg.stat().st_size // 1024
    total_kb += sz_kb
    count += 1
print(f"  {count} files / {total_kb} KB total ({total_kb//1024} MB)")

# 기존 PNG 정리 (이전 실행 잔재)
for png in OUT.rglob('card_*.png'):
    try:
        png.unlink()
    except Exception:
        pass

# ========== captions.md (articles/<slug>.json에서 읽음) ==========
# JSON 단일 소스: 캡션 컨텐츠는 articles/<slug>.json의 "captions_md" 필드에 통째 저장.
# 이로써 renderer 코드 수정 없이 캡션만 변경 가능 + 캡션 누락 사고 구조적 차단.
import json as _json
import os as _os
SLUG = _os.environ.get('SLUG', '')
if not SLUG:
    # SLUG 환경변수 없으면 articles/ 가장 최근 JSON에서 추출
    _articles_dir = BASE / 'articles'
    if _articles_dir.exists():
        _json_files = sorted(_articles_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        if _json_files:
            SLUG = _json_files[0].stem

_article_path = BASE / 'articles' / f'{SLUG}.json'
if _article_path.exists():
    try:
        _article_data = _json.loads(_article_path.read_text(encoding='utf-8'))
        CAPTIONS = _article_data.get('captions_md', '')
        NARRATION = _article_data.get('narration_md', '')
        if CAPTIONS:
            # token replacement: {LITTLY}, {PRECON_URL}
            LITTLY = "litt.ly/phonespot"
            PRECON_URL = "https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1"
            CAPTIONS = CAPTIONS.replace('{LITTLY}', LITTLY).replace('{PRECON_URL}', PRECON_URL)
            # append narration_md as channel 6 (video task baseline)
            if NARRATION:
                if not CAPTIONS.endswith('\n'):
                    CAPTIONS += '\n'
                CAPTIONS += '\n---\n\n## 6. 영상 나레이션 (뉴스 방송 톤 / edge-tts RATE+50% 기준)\n\n' + NARRATION
                _narr_note = f" + narration_md ({len(NARRATION.replace(chr(10), '').replace(' ', ''))} chars)"
            else:
                _narr_note = " (no narration_md field)"
            (OUT / 'captions.md').write_text(CAPTIONS, encoding='utf-8')
            print(f"\nOK captions.md (loaded from articles/{SLUG}.json){_narr_note}")
        else:
            print(f"\n[warn] articles/{SLUG}.json has no 'captions_md' field -- captions.md skipped")
    except Exception as _e:
        print(f"\n[error] article JSON load failed: {_e}")
else:
    print(f"\n[error] articles/{SLUG}.json not found -- captions.md skipped")
