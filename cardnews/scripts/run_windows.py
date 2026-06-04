#!/usr/bin/env python3
"""Windows 런처 (v5 - JSON 기반 + 자동 slug)"""
import sys, os, shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent

# SLUG 결정 우선순위: SLUG env > CLI 인자 (번호 prefix) > 최근 JSON
SLUG = os.environ.get('SLUG')
if not SLUG and len(sys.argv) > 1:
    arg = sys.argv[1].strip()
    # 번호 prefix 매칭 (예: "003" -> articles/003_*.json)
    articles_dir = BASE / 'articles'
    matches = sorted(articles_dir.glob(f'{arg}_*.json'))
    if matches:
        SLUG = matches[0].stem
        print(f"[arg-match] '{arg}' -> {SLUG}", flush=True)
    else:
        print(f"ERROR: no article matching '{arg}_*.json'", file=sys.stderr)
        sys.exit(1)
if not SLUG:
    # === Select mode: 미완성 슬러그 목록 보여주고 사장님 선택 ===
    articles_dir = BASE / 'articles'
    output_dir = BASE / 'output'

    def _is_done(_slug):
        # 강화: 18 jpg + captions.md + 각 jpg > 30KB
        _o = output_dir / _slug
        if not _o.exists():
            return False
        _jpgs = list(_o.rglob('card_*.jpg'))
        if len(_jpgs) < 18:
            return False
        if not (_o / 'captions.md').exists():
            return False
        # 작은 jpg = 렌더 실패 잔재
        _small = [p for p in _jpgs if p.stat().st_size < 30 * 1024]
        if _small:
            return False
        return True

    def _img_count(_slug):
        _img = BASE / 'images' / _slug
        if not _img.exists():
            return 0
        return len([p for p in _img.glob('*.png')
                    if not (p.name.startswith('card_') or p.name.startswith('logo_'))])

    if not articles_dir.exists():
        print("ERROR: articles/ folder not found.", file=sys.stderr)
        sys.exit(1)

    all_jsons = sorted(articles_dir.glob('*.json'))
    all_slugs = [jf.stem for jf in all_jsons]
    if not all_slugs:
        print("No articles/*.json found. Nothing to render.")
        sys.exit(0)

    print("=" * 60)
    print(f"Slugs in articles/ ({len(all_slugs)} total):")
    print("=" * 60)
    for i, _s in enumerate(all_slugs, 1):
        _n = _img_count(_s)
        if _is_done(_s):
            _flag = '[DONE]    '
        elif _n >= 5:
            _flag = '[READY]   '
        else:
            _flag = f'[img {_n}/5]'
        print(f"  {i:2d}. {_flag} {_s}")
    print("=" * 60)
    print("Note: [DONE] slugs can still be re-rendered (overwrites output).")

    try:
        _choice = input("\nEnter number or prefix (e.g. 003): ").strip()
    except EOFError:
        print("ERROR: stdin not available (use 'run_pngs.bat <NNN>' instead)", file=sys.stderr)
        sys.exit(1)

    if _choice.isdigit() and 1 <= int(_choice) <= len(all_slugs):
        SLUG = all_slugs[int(_choice) - 1]
    else:
        _matches = [s for s in all_slugs if s.startswith(_choice + '_') or s == _choice]
        if len(_matches) == 1:
            SLUG = _matches[0]
        elif len(_matches) > 1:
            print(f"ERROR: ambiguous prefix '{_choice}' matches {len(_matches)} slugs", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"ERROR: no slug matching '{_choice}'", file=sys.stderr)
            sys.exit(1)
    print(f"[selected] {SLUG}", flush=True)

if not SLUG:
    print("ERROR: articles/<slug>.json file not found.", file=sys.stderr)
    sys.exit(1)

OUT = BASE / 'output' / SLUG
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# 렌더 전 강제 검사 (★ 코덱스 피드백 2026-05-31)
# ============================================================
_pre_issues = []
# 1. 이미지 5장 존재
_img_dir = BASE / 'images' / SLUG
if not _img_dir.exists():
    _pre_issues.append(f"images/{SLUG}/ folder missing")
else:
    _ext = ('png', 'jpg', 'jpeg', 'webp')
    _imgs = []
    for _e in _ext:
        for _p in _img_dir.glob(f'*.{_e}'):
            if _p.name.startswith(('card_', 'logo_')) or _p.name == 'cover.png':
                continue
            _imgs.append(_p)
    # card_*.png가 이미 있으면 그것도 카운트 (auto-rename 결과 보존)
    _card_imgs = [p for p in _img_dir.glob('card_*.png') if p.stem in ('card_1','card_2','card_3','card_4','card_5')]
    if len(_imgs) < 5 and len(_card_imgs) < 5:
        _pre_issues.append(f"images/{SLUG}/: only {len(_imgs)} source + {len(_card_imgs)} card_*.png (need 5)")

# 2. articles JSON에 captions_md 필드
import json as _json_pre
_article_pre = BASE / 'articles' / f'{SLUG}.json'
if not _article_pre.exists():
    _pre_issues.append(f"articles/{SLUG}.json missing")
else:
    try:
        _data_pre = _json_pre.loads(_article_pre.read_text(encoding='utf-8'))
        if not _data_pre.get('captions_md', '').strip():
            _pre_issues.append(f"articles/{SLUG}.json: captions_md field empty")
        if not _data_pre.get('cards'):
            _pre_issues.append(f"articles/{SLUG}.json: cards field empty")
    except Exception as _e_pre:
        _pre_issues.append(f"articles/{SLUG}.json parse failed: {_e_pre}")

if _pre_issues:
    print("=" * 60)
    print("[pre-render check FAILED]")
    for _i in _pre_issues:
        print(f"  - {_i}")
    print("=" * 60)
    sys.exit(1)

RENDERER = SCRIPT_DIR / 'cardnews_renderer_v2.py'
src = RENDERER.read_text(encoding='utf-8')
src = src.replace("Path('/mnt/user-data/outputs/cardnews_tool')", "Path(r'" + str(BASE) + "')")
src = src.replace("Path('/mnt/user-data/outputs/iphone18_spec_downgrade_v2')", "Path(r'" + str(OUT) + "')")

print("=" * 60)
print("phonespot cardnews renderer (v5)")
print(f"BASE: {BASE}")
print(f"SLUG: {SLUG}")
print(f"OUT : {OUT}")
print("=" * 60)

# Playwright + Chromium 자동 설치 (첫 실행 시에만 실제 다운로드)
import subprocess as _sp
def _ensure_pkg(name, install_name=None):
    try:
        __import__(name)
    except ImportError:
        print(f"[info] Installing {install_name or name}...")
        _sp.run([sys.executable, '-m', 'pip', 'install', '--quiet', install_name or name], check=False)

_ensure_pkg('playwright')

# Chromium 다운로드 확인 (없으면 설치)
_chromium_check = _sp.run(
    [sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
    capture_output=True, text=True
)
if 'install' in _chromium_check.stdout.lower() or 'download' in _chromium_check.stdout.lower():
    print("[info] Downloading Chromium (~130MB, first run only)...")
    _sp.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
else:
    print("[info] Chromium ready")

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ['SLUG'] = SLUG

exec_globals = {'__name__': '__main__', '__file__': str(RENDERER)}
exec(compile(src, str(RENDERER), 'exec'), exec_globals)

# Summary
imgs = sorted(list(OUT.rglob('card_*.jpg')) + list(OUT.rglob('card_*.png')))
print("\n" + "=" * 60)
print(f"Images: {len(imgs)}")
total_kb = sum(p.stat().st_size for p in imgs) // 1024
print(f"Total size: {total_kb // 1024} MB ({total_kb} KB)")
print("=" * 60)

# ============================================================
# Auto verification (missing captions / empty cards / prior-article leak)
# ============================================================
print("\n[verify] start")
issues = []

# 1. 18 cards generated + size > 30KB
expected_cards = 18  # 3 sizes x 6 cards
if len(imgs) != expected_cards:
    issues.append(f"missing cards -- got {len(imgs)}/{expected_cards}")
small_cards = [p for p in imgs if p.stat().st_size < 30 * 1024]
if small_cards:
    issues.append(f"undersized cards (<30KB) -- {len(small_cards)}: {[p.name for p in small_cards[:3]]}")

# 2. captions.md exists + size > 1KB
captions_path = OUT / 'captions.md'
if not captions_path.exists():
    issues.append("captions.md missing")
elif captions_path.stat().st_size < 1024:
    issues.append(f"captions.md too small (<1KB) -- {captions_path.stat().st_size}B")

# 3. captions.md contains current SLUG title keyword
import json as _json
article_json_path = BASE / 'articles' / f'{SLUG}.json'
if article_json_path.exists() and captions_path.exists():
    try:
        article_data = _json.loads(article_json_path.read_text(encoding='utf-8'))
        title_keyword = article_data.get('title', '').strip()
        if title_keyword:
            captions_text = captions_path.read_text(encoding='utf-8')
            # at least one title token (>=2 chars) must appear in captions
            title_tokens = [t for t in title_keyword.split() if len(t) >= 2]
            hit = any(tok in captions_text for tok in title_tokens)
            if not hit:
                issues.append(f"caption/article mismatch -- title token not in captions.md (possible CAPTIONS var swap miss)")
    except Exception as e:
        issues.append(f"article meta verify failed: {e}")

# 4. prior-article leak (개선: 전체 슬러그명 또는 슬러그의 distinct 토픽 토큰만 검사)
# 옛 룰은 '2026', 'iOS', '아이폰' 같은 일반 단어로 거짓 양성 폭증 → strict 매칭으로 변경
if captions_path.exists() and (BASE / 'articles').exists():
    captions_text = captions_path.read_text(encoding='utf-8')
    other_articles = [p for p in (BASE / 'articles').glob('*.json') if p.stem != SLUG]
    # 일반 토큰 제외 리스트
    _generic = {'2026', '2025', '2024', 'iOS', '아이폰', '갤럭시', '애플', '삼성', 'AI', '폰',
                '/', '+', '·', '&', 'vs', 'VS', 'A', 'B', 'C', '/'}
    for other in other_articles:
        try:
            other_data = _json.loads(other.read_text(encoding='utf-8'))
            other_slug = other.stem
            # 1차: 슬러그명 전체 매칭 (가장 strict)
            if other_slug in captions_text:
                issues.append(f"prior-article leak -- slug '{other_slug}' literal in captions.md")
                continue
            # 2차: title에서 distinct 토큰 (4자 이상 + 일반어 제외)
            other_title = other_data.get('title', '').strip()
            other_tokens = [t for t in other_title.split() if len(t) >= 4 and t not in _generic]
            # 그 중 다른 슬러그 title에 없는 unique 토큰만
            for tok in other_tokens:
                if tok in captions_text and tok not in _data_pre.get('title', ''):
                    issues.append(f"prior-article leak -- token '{tok}' from '{other_slug}' in captions.md")
                    break
        except Exception:
            pass

# Result
if issues:
    print("[verify ! issues found]")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("[verify OK] 18 cards + captions OK, no prior-article leak")
print("=" * 60)

# === 검증 실패 시 종료 코드 1 (★ 자동화/배치용) ===
_critical_issues = [i for i in issues if any(k in i for k in ('missing', 'too small', 'undersized', 'mismatch'))]
if _critical_issues:
    sys.exit(1)

# ============================================================
# 백업 파일 자동 정리 (최근 5개만 유지)
# ============================================================
backup_files = sorted(SCRIPT_DIR.glob('cardnews_renderer_v2.py.backup_*'),
                     key=lambda p: p.stat().st_mtime, reverse=True)
if len(backup_files) > 5:
    to_delete = backup_files[5:]
    print(f"\n[backup cleanup] deleting {len(to_delete)} old backups:")
    for p in to_delete:
        try:
            p.unlink()
            print(f"  - {p.name}")
        except Exception as e:
            print(f"  - {p.name} delete failed: {e}")
elif backup_files:
    print(f"\n[backup] {len(backup_files)} backups kept (max 5)")
