"""슬러그 목록 - 수정한 날짜 기준 역순 정렬 (최신 먼저).

출력 형식:
   N.  YYYY.MM.DD  [OK]  slug_name
   - YYYY.MM.DD: output/<slug>/ 폴더의 mtime (윈도우 탐색기 '수정한 날짜')
   - [OK]: articles에 cards[] 있고 images/<slug>/에 .png 있음 (자동 생성 가능)
   - [SC]: shorts_script.json 손폴리시본 + 이미지 있음 (빌드 가능, articles 깨져도 무관)
   - [--]: 빌드 자원 부족
"""
import json
import sys
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/
output_dir = cardnews_root / "output"
articles_dir = cardnews_root / "articles"
images_dir = cardnews_root / "images"

if not output_dir.exists():
    sys.exit(0)

# mtime 기준 역순 정렬 (최신 먼저)
slug_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
slug_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

for i, d in enumerate(slug_dirs, 1):
    slug = d.name
    mtime = datetime.datetime.fromtimestamp(d.stat().st_mtime)
    date_str = mtime.strftime("%Y.%m.%d")
    has_script = (d / "shorts_script.json").exists()
    cards_ok = False
    aj = articles_dir / f"{slug}.json"
    if aj.exists():
        try:
            j = json.load(open(aj, encoding="utf-8"))
            cards = j.get("cards")
            cards_ok = isinstance(cards, list) and len(cards) >= 2
        except Exception:
            pass
    img_ok = False
    img_subdir = images_dir / slug
    if img_subdir.exists():
        img_ok = any(p.suffix.lower() == ".png" for p in img_subdir.iterdir())
    if cards_ok and img_ok:
        flag = "[OK]"
    elif has_script and img_ok:
        flag = "[SC]"
    else:
        flag = "[--]"
    print(f"  {i:>3}.  {date_str}  {flag}  {slug}")
