"""슬러그 목록 - articles ∪ output 기준, 수정한 날짜 역순(최신 먼저).

영상은 article(cards[])만 있으면 빌드 가능(일러스트는 라이브러리에서 자동 매칭)하므로,
카드뉴스 output 폴더가 없어도 article 만 있으면 목록에 뜬다(카드뉴스 목록과 동일한 독립 스캔).

플래그(영상 빌드 기준):
   [OK]  articles 에 cards[]>=2  → 영상 빌드 가능
   [SC]  output/<slug>/shorts_script.json 있음(article 깨져도 빌드 가능)
   [--]  자원 부족
출력: `  N.  YYYY.MM.DD  [FLAG]  slug`
"""
import json
import sys
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

project_root = Path(__file__).parent.parent      # shorts/
repo_root = project_root.parent                   # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"
output_dir = cardnews_root / "output"
articles_dir = cardnews_root / "articles"

# 슬러그 수집: output 폴더 ∪ articles json (둘 중 하나만 있어도 등재)
mtime: dict[str, float] = {}
if output_dir.exists():
    for d in output_dir.iterdir():
        if d.is_dir():
            try:
                mtime[d.name] = d.stat().st_mtime
            except OSError:
                pass
if articles_dir.exists():
    for aj in articles_dir.glob("*.json"):
        try:
            m = aj.stat().st_mtime
        except OSError:
            continue
        mtime[aj.stem] = max(mtime.get(aj.stem, 0.0), m)

if not mtime:
    sys.exit(0)


def cards_ok(slug: str) -> bool:
    aj = articles_dir / f"{slug}.json"
    if not aj.exists():
        return False
    try:
        j = json.load(open(aj, encoding="utf-8"))
        cards = j.get("cards")
        return isinstance(cards, list) and len(cards) >= 2
    except Exception:
        return False


def has_script(slug: str) -> bool:
    return (output_dir / slug / "shorts_script.json").exists()


rows = sorted(mtime.items(), key=lambda kv: kv[1], reverse=True)
for i, (slug, m) in enumerate(rows, 1):
    date_str = datetime.datetime.fromtimestamp(m).strftime("%Y.%m.%d")
    if cards_ok(slug):
        flag = "[OK]"
    elif has_script(slug):
        flag = "[SC]"
    else:
        flag = "[--]"
    print(f"  {i:>3}.  {date_str}  {flag}  {slug}")
