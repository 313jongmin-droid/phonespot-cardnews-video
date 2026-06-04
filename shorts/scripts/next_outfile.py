"""중복 회피 출력 파일명 생성.

사용:
    python scripts/next_outfile.py <slug> <date> <track>
출력 (파일명만, 경로 없음):
    첫 빌드:   <slug>_<date>_<track>.mp4
    중복 시:   <slug>_<date>_<track>_1.mp4, _2, _3 ...

배치 파일에서:
    for /f "delims=" %%F in ('python scripts\next_outfile.py !SLUG! %DATE% casual') do set "OUTFILE=out\%%F"
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if len(sys.argv) < 4:
    print("Usage: python scripts/next_outfile.py <slug> <date> <track>", file=sys.stderr)
    sys.exit(1)

slug, date, track = sys.argv[1], sys.argv[2], sys.argv[3]
project_root = Path(__file__).parent.parent
out_dir = project_root / "out"
out_dir.mkdir(parents=True, exist_ok=True)

base = f"{slug}_{date}_{track}"
candidate = f"{base}.mp4"
i = 1
while (out_dir / candidate).exists():
    candidate = f"{base}_{i}.mp4"
    i += 1

print(candidate)
