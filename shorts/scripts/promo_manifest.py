# 렌더된 promo 영상의 변주 속성을 promo/_manifest.csv 에 1행 기록.
# 목적: "어떤 훅/스타일/프리셋이 성과 좋았나" 귀속 대비 데이터 축적.
# variant_id = slug+preset+styles+music 해시(변주 식별 키). 기존 행은 자동 백필.
# usage: promo_manifest.py <outfile> <nn> <slug> <preset>
import sys, os, csv, json, datetime, hashlib
outfile = sys.argv[1] if len(sys.argv) > 1 else ""
nn      = sys.argv[2] if len(sys.argv) > 2 else ""
slug    = sys.argv[3] if len(sys.argv) > 3 else ""
preset  = sys.argv[4] if len(sys.argv) > 4 else ""

def variant_id(slug, preset, styles, music):
    key = "%s|%s|%s|%s" % (slug, preset, styles, music)
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:10]

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
styles_str = ";".join(sec_styles)
music_src  = d.get("music_src", "")
row = {
    "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "outfile": os.path.basename(outfile),
    "nn": nn, "slug": slug, "preset": preset,
    "hook_pattern": d.get("hook_pattern", ""),
    "hook_text": (opening.get("line2", "") or chunks(hook)),
    "styles": styles_str,
    "music_src": music_src,
    "music_start": d.get("music_start", ""),
    "n_facts": len(facts),
    "variant_id": variant_id(slug, preset, styles_str, music_src),
}
cols = ["ts","outfile","nn","slug","preset","hook_pattern","hook_text","styles","music_src","music_start","n_facts","variant_id"]
path = "promo/_manifest.csv"

# 기존 행 읽기 → variant_id 없는 옛 행 백필 → 새 행 추가 → 전체 재기록(헤더 마이그레이션).
rows = []
if os.path.exists(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if not r.get("variant_id"):
                r["variant_id"] = variant_id(r.get("slug",""), r.get("preset",""), r.get("styles",""), r.get("music_src",""))
            rows.append({c: r.get(c, "") for c in cols})
rows.append(row)
with open(path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print("manifest +1:", row["outfile"], "| hook:", row["hook_pattern"] or "(미지정)", "| vid:", row["variant_id"])
