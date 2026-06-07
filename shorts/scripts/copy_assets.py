"""
폰스팟 뉴스 쇼츠 - 자산 복사 스크립트
- shorts_script.json (output/<slug>/) -> public/
- background_image + chunk_visuals 의 image 타입 -> public/assets/
- logos/*.png -> public/assets/logos/
- 빌드 시작 시 public/assets/ 직속 파일 자동 정리 (logos·illustrations 폴더 보존)

사용법: python scripts/copy_assets.py <slug>
"""
import json
import shutil
import sys
from pathlib import Path

from codex_chunk_overrides import write_effective_script

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if len(sys.argv) < 2:
    print("Usage: python scripts/copy_assets.py <slug>")
    sys.exit(1)

slug = sys.argv[1]
project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/


script_src = cardnews_root / "output" / slug / "shorts_script.json"
public_dir = project_root / "public"
assets_dir = public_dir / "assets"

public_dir.mkdir(parents=True, exist_ok=True)
assets_dir.mkdir(parents=True, exist_ok=True)

if not script_src.exists():
    print(f"[ERROR] shorts_script.json not found: {script_src}")
    print("Run: python scripts/build_script.py <slug> (or create manually)")
    sys.exit(1)

# [0] 정리: public/assets/ 직속 파일 삭제 (logos·illustrations 폴더는 보존)
cleaned = 0
for f in assets_dir.iterdir():
    if f.is_file():
        f.unlink()
        cleaned += 1
if cleaned:
    print(f"[0] Cleaned {cleaned} stale files in public/assets/ (folders preserved)")

print(f"[1] Copying shorts_script.json -> public/")
script, override_report = write_effective_script(
    slug,
    public_dir / "shorts_script.json",
    source_path=script_src,
)
if override_report["applied"]:
    print(f"[OVERRIDE] applied: {', '.join(override_report['sections'])}")
if override_report["legacy_sections"]:
    print(
        "[WARN] legacy chunk override without source hash: "
        + ", ".join(override_report["legacy_sections"])
        + " (next panel edit upgrades it)"
    )
print(f"    OK")

ai_image_dir = cardnews_root / "images" / slug
card_image_dir = cardnews_root / "output" / slug / "9x16"

# needed: background_image + chunk_visuals의 image 타입 value
needed = set()
all_secs = [script["hook"]] + script.get("facts", []) + [script["cta"]]
for sec in all_secs:
    bg = sec.get("background_image")
    if bg:
        needed.add(bg)
    if sec.get("background_video"):
        needed.add(sec["background_video"])
    for cv in sec.get("chunk_visuals", []):
        if cv.get("type") == "image":
            val = cv.get("value")
            if val:
                needed.add(val)
    if sec.get("source_screenshot"):
        needed.add(sec["source_screenshot"]["file"])

# logos/X.png 같은 건 별도 logos 루프에서 처리. 여기선 직속 파일만 처리
direct_needed = [n for n in needed if "/" not in n]
logos_needed = [n for n in needed if n.startswith("logos/")]

print(f"[2] Copying {len(direct_needed)} direct images -> public/assets/")
missing = []
for fname in direct_needed:
    src_ai = ai_image_dir / fname
    src_card = card_image_dir / fname
    dst_path = assets_dir / fname
    if src_ai.exists():
        shutil.copy(src_ai, dst_path)
        print(f"    [AI ]  {fname}")
    elif src_card.exists():
        shutil.copy(src_card, dst_path)
        print(f"    [CARD] {fname}")
    else:
        missing.append(fname)
        print(f"    [MISS] {fname}")

# [3] logos 복사 — chunk_visuals 에 logos/X 가 있거나 매번 전체 복사
logo_src = project_root / "logos"
if logo_src.exists():
    logo_dst = assets_dir / "logos"
    logo_dst.mkdir(parents=True, exist_ok=True)
    # 기존 logos 정리 (logos/ 안 파일 모두 삭제 후 재복사 — fresh)
    for f in logo_dst.iterdir():
        if f.is_file():
            f.unlink()
    logo_count = 0
    for lf in sorted(logo_src.glob("*.png")):
        shutil.copy(lf, logo_dst / lf.name)
        logo_count += 1
    print(f"[3] {logo_count} logos -> public/assets/logos/")

if missing:
    print(f"\n[INFO] {len(missing)} missing files:")
    for m in missing:
        print(f"   - {m}")

print(f"\nDone. public/assets/ direct={len(direct_needed)}, logos={len(logos_needed)}")
