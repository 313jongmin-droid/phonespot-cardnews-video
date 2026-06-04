import glob, os, re, json
pat = re.compile(r"^(\d{3})_(.+)\.json$")
def fields(d):
    r = {"opening": [d["opening"]["line1"], d["opening"]["line2"]],
         "hook": d["hook"].get("caption_chunks", []), "hook_tts": d["hook"].get("tts","")}
    for i, fc in enumerate(d["facts"], 1):
        r[f"fact{i}"] = fc.get("caption_chunks", []); r[f"fact{i}_tts"] = fc.get("tts","")
    r["cta"] = d["cta"].get("caption_chunks", []); r["cta_tts"] = d["cta"].get("tts","")
    return r
chg = 0
for f in sorted(glob.glob("promo/*.json")):
    b = os.path.basename(f)
    if not pat.match(b): continue
    o = os.path.join("promo", "_orig", b)
    if not os.path.exists(o): continue
    a, c = fields(json.load(open(o,encoding="utf-8"))), fields(json.load(open(f,encoding="utf-8")))
    for k in a:
        if a[k] != c[k]:
            chg += 1
            print(f"[{b} · {k}]\n   원본: {a[k]}\n   수정: {c[k]}")
print(f"\n변경 필드 {chg}건" if chg else "변경 없음")
