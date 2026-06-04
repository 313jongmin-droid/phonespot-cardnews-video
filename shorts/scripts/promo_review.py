import glob, os, re, json, sys
pat = re.compile(r"^(\d{3})_(.+)\.json$")
items = {}
for f in glob.glob("promo/*.json"):
    m = pat.match(os.path.basename(f))
    if m: items[m.group(1)] = (m.group(2), f)
arg = sys.argv[1] if len(sys.argv) > 1 else ""
target = None
if arg.isdigit():
    key = f"{int(arg):03d}"
    if key in items: target = items[key][1]
if not target:
    for nn,(label,f) in items.items():
        if arg and arg in label: target = f; break
if not target:
    print("사용: py scripts\\promo_review.py <번호 또는 이름>"); raise SystemExit
d = json.load(open(target, encoding="utf-8"))
def show(lbl, s):
    print(f"[{lbl}] 화면: " + " / ".join(s.get("caption_chunks", [])))
    print(f"        나레이션: {s.get('tts','')}")
print("="*60); print(os.path.basename(target), " preset:", d.get("preset","showcase")); print("="*60)
print(f"[오프닝] {d['opening']['line1']} / {d['opening']['line2']}")
show("훅", d["hook"])
for i, fc in enumerate(d["facts"], 1): show(f"팩트{i}", fc)
show("CTA", d["cta"])
