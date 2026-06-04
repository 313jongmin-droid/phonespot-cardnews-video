"""list_slugs.py 와 동일 정렬 기준 (mtime 역순) - N번째 슬러그명 출력."""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if len(sys.argv) < 2:
    sys.exit(2)

try:
    n = int(sys.argv[1])
except ValueError:
    sys.exit(2)

project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/
output_dir = cardnews_root / "output"

if not output_dir.exists():
    sys.exit(3)

slug_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
slug_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

if n < 1 or n > len(slug_dirs):
    sys.exit(4)

print(slug_dirs[n - 1].name)
