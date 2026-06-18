import glob, os, re, json, sys
pat = re.compile(r"^(\d{3})_(.+)\.md$")
FACT_IDS = ["problem", "solution", "trust", "fact4", "fact5", "fact6"]
def strip_bullet(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in "-*" and s[1] == " ":
        return s[2:].strip()
    return s
def getv(s, key):
    if s.startswith(key):
        v = s.split(":", 1)[1].strip()
        return v
    return None
def realval(v):
    return None if (v is None or v == "" or v.startswith("(")) else v
def build(md, nn, label):
    cur = None; meta = {"preset": "showcase", "title": label, "hook_pattern": ""}; opening = {}; secs = {}; order = []
    for raw in open(md, encoding="utf-8"):
        s = raw.strip()
        if s.startswith("## "):
            cur = s[3:].strip()
            if cur != "오프닝" and cur not in secs:
                secs[cur] = {}; order.append(cur)
            continue
        c = strip_bullet(s)
        if cur is None:
            v = getv(c, "preset");  meta["preset"] = v if v else meta["preset"]
            v = getv(c, "title");   meta["title"] = v if v else meta["title"]
            v = getv(c, "후킹");    meta["hook_pattern"] = v if realval(v) else meta["hook_pattern"]
        elif cur == "오프닝":
            for k in ("line1", "line2"):
                v = getv(c, k);  opening[k] = v if v is not None else opening.get(k, "")
            v = getv(c, "스타일")
            if realval(v): opening["style"] = v
            v = getv(c, "효과음")
            if realval(v): opening["sfx"] = v
        else:
            t = secs[cur]
            v = getv(c, "화면")
            if v is not None: t["caption_chunks"] = [x.strip() for x in v.split("|") if x.strip()]
            v = getv(c, "나레이션")
            if v is not None: t["tts"] = v
            v = getv(c, "스타일")
            if realval(v): t["style"] = v
            v = getv(c, "효과음")
            if realval(v): t["sfx"] = v
    facts_keys = [k for k in order if k.startswith("팩트")]
    facts = []
    for i, k in enumerate(facts_keys):
        fc = {"id": FACT_IDS[i] if i < len(FACT_IDS) else f"fact{i+1}"}
        fc.update(secs[k]); facts.append(fc)
    cta = secs.get("CTA", {})
    cta.setdefault("kakao", ""); cta.setdefault("litt", ""); cta.setdefault("location", "")
    d = {"slug": f"{nn}_{label}", "title_short": meta["title"], "video_title": meta["title"],
         "preset": meta["preset"], "hook_pattern": meta.get("hook_pattern",""), "channel_name": "", "channel_tagline": "", "publication_date": "2026.05.29",
         "opening": {"line1": opening.get("line1", ""), "line2": opening.get("line2", "")},
         "hook": secs.get("훅", {}), "facts": facts, "cta": cta}
    for k in ("style", "sfx"):
        if k in opening: d["opening"][k] = opening[k]
    return d
def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    n = 0
    for md in sorted(glob.glob("promo/review/*.md")):
        m = pat.match(os.path.basename(md))
        if not m: continue
        nn, label = m.group(1), m.group(2)
        if want and want.isdigit() and int(want) != int(nn): continue
        d = build(md, nn, label)
        json.dump(d, open(f"promo/{nn}_{label}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        n += 1
    print(f"{n}개 JSON 재구성(MD 기준)")

# import 시에는 build()만 노출하고, 직접 실행할 때만 전체 재생성(JSON 덮어쓰기)한다.
if __name__ == "__main__":
    main()
