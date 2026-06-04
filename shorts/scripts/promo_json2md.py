import glob, os, re, json, sys
pat = re.compile(r"^(\d{3})_(.+)\.json$")
def to_md(f):
    d = json.load(open(f, encoding="utf-8"))
    m = pat.match(os.path.basename(f)); nn, label = m.group(1), m.group(2)
    L = [f"# {nn} {label}", f"- preset: {d.get('preset','showcase')}", f"- title: {d.get('title_short','')}", "",
         "## 오프닝", f"- line1: {d['opening']['line1']}", f"- line2: {d['opening']['line2']}",
         f"- 스타일: {d['opening'].get('style','(프리셋 기본)')}", f"- 효과음: {d['opening'].get('sfx','(자동)')}"]
    def sec(name, s, iscta=False):
        L.extend(["", f"## {name}",
                  f"- 스타일: {s.get('style','(프리셋 기본)')}",
                  f"- 효과음: {s.get('sfx','(자동: '+('ding' if iscta else 'whoosh')+')')}",
                  "- 화면: " + " | ".join(s.get("caption_chunks", [])),
                  "- 나레이션: " + s.get("tts", "")])
    sec("훅", d["hook"])
    for i, fc in enumerate(d["facts"], 1): sec(f"팩트{i}", fc)
    sec("CTA", d["cta"], True)
    L.append("")
    out = os.path.join("promo", "review", f"{nn}_{label}.md")
    open(out, "w", encoding="utf-8").write("\n".join(L)); return out
want = sys.argv[1] if len(sys.argv) > 1 else None
n = 0
for f in sorted(glob.glob("promo/*.json")):
    m = pat.match(os.path.basename(f))
    if not m: continue
    if want and want.isdigit() and int(want) != int(m.group(1)): continue
    try:
        to_md(f); n += 1
    except Exception as e:
        print("SKIP", f, e)
print(f"{n}개 MD")
