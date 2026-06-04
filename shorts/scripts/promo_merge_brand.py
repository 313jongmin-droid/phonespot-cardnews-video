"""promo: public/shorts_script.json 의 빈 브랜드 값(채널/카카오/litt/위치)을 promo/_brand.json 으로 채움."""
import json, pathlib
root = pathlib.Path(__file__).parent.parent
brand = json.load(open(root / "promo" / "_brand.json", encoding="utf-8"))
sp = root / "public" / "shorts_script.json"
d = json.load(open(sp, encoding="utf-8"))
if not d.get("channel_name"): d["channel_name"] = brand.get("channel_name")
if not d.get("channel_tagline"): d["channel_tagline"] = brand.get("channel_tagline")
cta = d.setdefault("cta", {})
for k in ("kakao", "litt", "location"):
    if not cta.get(k): cta[k] = brand.get(k)
json.dump(d, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("[brand] merged channel/kakao/litt/location")
