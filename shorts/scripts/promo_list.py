import glob, os, re, json
pat = re.compile(r"^(\d{3})_(.+)\.json$")
items = []
for f in glob.glob("promo/*.json"):
    m = pat.match(os.path.basename(f))
    if m: items.append((m.group(1), m.group(2), f))
items.sort()
if not items: print("  (promo/ 에 NNN_*.json 없음)")
for nn, label, f in items:
    try: d = json.load(open(f, encoding="utf-8"))
    except Exception: d = {}
    print(f"  {nn}  {label:<16}  {d.get('title_short',label)}   [{d.get('preset','showcase')}]")
