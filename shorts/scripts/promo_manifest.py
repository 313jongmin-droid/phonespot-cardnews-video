# 렌더된 promo 영상의 변주 속성을 promo/_manifest.csv 에 1행 기록.
# 목적: 나중에 "어떤 훅/스타일/프리셋이 성과 좋았나" 귀속(C단계) 대비 데이터 축적.
# usage: promo_manifest.py <outfile> <nn> <slug> <preset>
import sys, os, csv, json, datetime
outfile = sys.argv[1] if len(sys.argv) > 1 else ""
nn      = sys.argv[2] if len(sys.argv) > 2 else ""
slug    = sys.argv[3] if len(sys.argv) > 3 else ""
preset  = sys.argv[4] if len(sys.argv) > 4 else ""
d = {}
try:
    d = json.load(open("public/shorts_script.json", encoding="utf-8"))
except Exception:
    pass
def chunks(x):
    c = x.get("caption_chunks") if isinstance(x, dict) else None
    return " ".join(c) if c else ""
opening = d.get("opening", {}) or {}
hook    = d.get("hook", {}) or {}
facts   = d.get("facts", []) or []
secs = [("open", opening), ("hook", hook)] + \
       [("fact%d" % (i + 1), f) for i, f in enumerate(facts)] + \
       [("cta", d.get("cta", {}) or {})]
sec_styles = ["%s:%s" % (k, o.get("style")) for k, o in secs if isinstance(o, dict) and o.get("style")]
row = {
    "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "outfile": os.path.basename(outfile),
    "nn": nn, "slug": slug, "preset": preset,
    "hook_pattern": d.get("hook_pattern", ""),
    "hook_text": (opening.get("line2", "") or chunks(hook)),
    "styles": ";".join(sec_styles),
    "music_src": d.get("music_src", ""),
    "music_start": d.get("music_start", ""),
    "n_facts": len(facts),
}
cols = ["ts","outfile","nn","slug","preset","hook_pattern","hook_text","styles","music_src","music_start","n_facts"]
path = "promo/_manifest.csv"
new = not os.path.exists(path)
with open(path, "a", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    if new: w.writeheader()
    w.writerow(row)
print("manifest +1:", row["outfile"], "| hook_pattern:", row["hook_pattern"] or "(미지정)")
