"""shorts_script.json 자동 검증.

검사 항목 (영구 차단):
1. video_title 잘림 의심 (날짜 슬래시 분리 버그)
2. chunk_visuals image/illust 파일 실제 존재
3. stat number 8자 이하
4. compare left/right value 12자 이하
5. caption_emphasis 매칭 시뮬레이션
6. chunk_visuals 길이 == caption_chunks 길이
7. unique 검증 (한 영상 내 같은 visual 2회 금지)
8. BAD_PHRASES 검출 (2026-05-29 추가) — codex_enhance generic repair 가 만드는 어색 패턴
   - "입니다입니다", "줄어듭니다입니다" 같은 종결어미 중복
   - "에 따르면에 따르면" 같은 절 반복
9. display_chunks 길이 == caption_chunks 길이 (있을 때만)

사용: python scripts/validate_polish.py [slug]
종료 코드: 0=OK, 1=경고, 2=치명적 에러
"""
import json
import re
import sys
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
illust_dir = project_root / "public" / "assets" / "illustrations"
logos_dir = project_root / "logos"

STAT_NUMBER_MAX = 8
COMPARE_VALUE_MAX = 12

# codex_enhance generic repair 가 만들어내는 어색 패턴 — 빌드 차단
BAD_PHRASES = [
    "입니다입니다",
    "합니다합니다",
    "줍니다입니다",
    "있습니다입니다",
    "됩니다입니다",
    "줄어듭니다입니다",
    "에 따르면에 따르면",
    "와 관련해와 관련해",
    "반면와 관련해",
    "기준으로기준으로",
    "이고이고",
    "이며이며",
]


def validate_slug(slug):
    sp = output_dir / slug / "shorts_script.json"
    if not sp.exists():
        return [], [f"shorts_script.json not found"]

    j = json.load(open(sp, encoding="utf-8"))
    warnings = []
    errors = []

    # === 0) video_title 잘림 의심 ===
    vt = j.get("video_title", "")
    if re.search(r"\s\d{1,2}$", vt) or vt.startswith("/"):
        art_p = articles_dir / f"{slug}.json"
        try:
            art = json.load(open(art_p, encoding="utf-8"))
            full_title = art.get("title", "")
            proper = full_title.split(" / ")[0].strip()
            if proper != vt and proper.startswith(vt.rstrip()):
                warnings.append(f"video_title likely truncated: '{vt}' (full: '{proper}')")
        except Exception:
            warnings.append(f"video_title suspicious ending (digit): '{vt}'")

    all_secs = [j.get("hook", {})] + j.get("facts", []) + [j.get("cta", {})]
    seen_visuals = set()

    for si, sec in enumerate(all_secs):
        chunks = sec.get("caption_chunks", [])
        visuals = sec.get("chunk_visuals", [])
        display_chunks = sec.get("display_chunks", [])
        tts = sec.get("tts", "")
        sec_label = ["HOOK", *[f"FACT{i}" for i in range(1, len(j.get('facts',[]))+1)], "CTA"][si]

        # 1) 길이 매칭
        if len(chunks) != len(visuals):
            errors.append(f"{sec_label}: chunks({len(chunks)}) != visuals({len(visuals)})")

        # 1-b) display_chunks 길이 매칭 (있을 때만)
        if display_chunks and len(display_chunks) != len(chunks):
            errors.append(f"{sec_label}: display_chunks({len(display_chunks)}) != caption_chunks({len(chunks)})")

        # 1-c) BAD_PHRASES 검출 — codex_enhance 결함 차단
        fields_to_check = [("tts", tts)]
        for i, c in enumerate(display_chunks):
            fields_to_check.append((f"display_chunks[{i}]", c))
        for i, c in enumerate(chunks):
            fields_to_check.append((f"caption_chunks[{i}]", c))
        for field_name, field_val in fields_to_check:
            if not field_val:
                continue
            for bad in BAD_PHRASES:
                if bad in field_val:
                    sample = field_val if len(field_val) <= 60 else field_val[:60] + "..."
                    errors.append(f"{sec_label}.{field_name}: BAD_PHRASE '{bad}' in '{sample}'")

        # 2) 각 visual 검증
        for k, cv in enumerate(visuals):
            t = cv.get("type")
            v = cv.get("value")
            tag = f"{sec_label} C{k+1}"

            # unique 검증
            if t in ("image", "illust", "mascot"):
                key = f"{t}:{v}"
                if key in seen_visuals:
                    warnings.append(f"{tag}: duplicate {key}")
                seen_visuals.add(key)

            # image 파일 존재
            if t == "image":
                if not v:
                    errors.append(f"{tag}: image value empty")
                    continue
                if "/" in v:
                    p = project_root / "public" / "assets" / v
                    if not p.exists():
                        if v.startswith("logos/"):
                            real = logos_dir / v.split("/")[-1]
                            if not real.exists():
                                errors.append(f"{tag}: logo file missing {v}")
                        else:
                            errors.append(f"{tag}: image file missing {v}")
                else:
                    p = images_dir / slug / v
                    if not p.exists():
                        errors.append(f"{tag}: GPT image missing {v}")

            # illust 검증
            elif t == "illust":
                if not v:
                    errors.append(f"{tag}: illust value empty")
                    continue
                p = illust_dir / f"{v}.png"
                if not p.exists():
                    errors.append(f"{tag}: illust PNG missing {v}.png")

            # stat 검증
            elif t == "stat":
                num = (cv.get("value") or {}).get("number", "")
                if len(num) > STAT_NUMBER_MAX:
                    warnings.append(f"{tag}: stat number too long ({len(num)} chars > {STAT_NUMBER_MAX}): '{num}'")

            # compare 검증
            elif t == "compare":
                left_v = (cv.get("value") or {}).get("left", {}).get("value", "")
                right_v = (cv.get("value") or {}).get("right", {}).get("value", "")
                if len(left_v) > COMPARE_VALUE_MAX:
                    warnings.append(f"{tag}: compare.left.value too long ({len(left_v)} chars): '{left_v}'")
                if len(right_v) > COMPARE_VALUE_MAX:
                    warnings.append(f"{tag}: compare.right.value too long ({len(right_v)} chars): '{right_v}'")

        # 3) caption_emphasis 매칭 (자동 강조 안전망 작동 여부)
        emph_list = sec.get("caption_emphasis", [])
        for e in emph_list:
            if not e:
                continue
            cleaned = re.sub(r"[()·\s]", "", e)
            if len(cleaned) < 2:
                continue
            matched = False
            for c in chunks:
                norm = re.sub(r"\s", "", c)
                if cleaned in norm:
                    matched = True
                    break
            if not matched:
                # 자동 패턴 fallback
                auto_re = re.compile(r"\d+(?:[,.]?\d+)*\s*(?:만원|억|조|유로|달러|%|개|명|년)|iOS\s*\d+|Z\s*폴드\s*\d+|Z\s*플립\s*\d+|S\s*\d{2}")
                has_auto = any(auto_re.search(c) for c in chunks)
                if not has_auto:
                    warnings.append(f"{sec_label}: emphasis '{e}' not in chunks (no auto pattern)")

    return warnings, errors


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    if not targets:
        targets = [d.name for d in output_dir.iterdir() if d.is_dir() and (d / "shorts_script.json").exists()]

    total_warnings = 0
    total_errors = 0
    for slug in targets:
        warnings, errors = validate_slug(slug)
        if not warnings and not errors:
            print(f"[OK]   {slug}")
        else:
            print(f"[CHK]  {slug}")
            for e in errors:
                print(f"  ERROR : {e}")
                total_errors += 1
            for w in warnings:
                print(f"  WARN  : {w}")
                total_warnings += 1

    print()
    print(f"=== TOTAL: {total_errors} errors, {total_warnings} warnings ===")
    if total_errors > 0:
        sys.exit(2)
    elif total_warnings > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
