# 인자=번호 -> 1건, 무인자 -> 전체.  형식: NNN|label|preset|path
import glob, os, re, json, sys
pat = re.compile(r"^(\d{3})_(.+)\.json$")
items = []
for f in glob.glob("promo/*.json"):
    m = pat.match(os.path.basename(f))
    if m: items.append((m.group(1), m.group(2), f))
items.sort()
def emit(nn, label, f):
    try: preset = json.load(open(f, encoding="utf-8")).get("preset", "showcase")
    except Exception: preset = "showcase"
    print(f"{nn}|{label}|{preset}|{f}")
if len(sys.argv) > 1:
    try: q = int(sys.argv[1])
    except Exception: print(""); raise SystemExit
    for nn, label, f in items:
        if int(nn) == q: emit(nn, label, f); break
    else: print("")
else:
    for nn, label, f in items: emit(nn, label, f)
