# review/NNN_*.md (권위) ↔ promo/NNN_*.json 정합 검사.
# MD를 md2json.build로 재구성한 결과가 커밋된 JSON과 다르면 리포트(드리프트 탐지).
# 사용: py scripts\promo_check_sync.py        -> 전체
#       py scripts\promo_check_sync.py 005    -> 한 편
# 종료코드: 0=일치, 1=드리프트 있음(CI/검증용).
import glob, os, re, json, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("promo_md2json", os.path.join(HERE, "promo_md2json.py"))
m2j = importlib.util.module_from_spec(spec)
# md2json은 __main__ 가드가 있어 import 시 build()만 노출(파일 안 씀). 이 검사는 순수 read-only.
spec.loader.exec_module(m2j)

pat = re.compile(r"^(\d{3})_(.+)\.md$")
want = sys.argv[1] if len(sys.argv) > 1 else None
drift = []
checked = 0
for md in sorted(glob.glob("promo/review/*.md")):
    b = os.path.basename(md)
    mm = pat.match(b)
    if not mm:
        continue
    nn, label = mm.group(1), mm.group(2)
    if want and want.isdigit() and int(want) != int(nn):
        continue
    jpath = f"promo/{nn}_{label}.json"
    expected = m2j.build(md, nn, label)
    checked += 1
    if not os.path.exists(jpath):
        drift.append(f"{nn}_{label}: JSON 없음 ({jpath})")
        continue
    actual = json.load(open(jpath, encoding="utf-8"))
    # 렌더 시 채워지는 휘발 필드는 비교 제외(브랜드/음악 병합 결과).
    for k in ("channel_name", "channel_tagline", "music_src", "music_start"):
        expected.pop(k, None); actual.pop(k, None)
    if isinstance(actual.get("cta"), dict):
        for k in ("kakao", "litt", "location"):
            actual["cta"].pop(k, None); expected.get("cta", {}).pop(k, None)
    if expected != actual:
        keys = sorted(set(expected) | set(actual))
        diffs = [k for k in keys if expected.get(k) != actual.get(k)]
        drift.append(f"{nn}_{label}: 불일치 필드 {diffs}")

print(f"검사 {checked}편 / 드리프트 {len(drift)}건")
for d in drift:
    print("  -", d)
if drift:
    print("→ `py scripts\\promo_md2json.py` 로 JSON 재생성하면 MD 기준으로 맞춰짐.")
sys.exit(1 if drift else 0)
