# promo 생성 근거 패널(읽기전용). "생성할 때 수치를 본다".
# 보여주는 것: ① 작성 스크립트 후킹 분포 ② 렌더 분포(manifest) ③ 성과 축집계(_results) ④ 다음 생성 제안(빈 칸).
# usage: py scripts\promo_plan.py [--gate 5000]
import csv, os, sys, glob, re, collections

GATE = 5000
if "--gate" in sys.argv:
    try: GATE = int(sys.argv[sys.argv.index("--gate") + 1])
    except Exception: pass

HOOKS = ["질문형","단언형","비교형","한정형","가격강조","감성·공감","위협형","FOMO형"]
PRESETS = ["showcase","punchy","calm","data"]

def load_csv(p):
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def num(x):
    try: return float(str(x).replace(",","").strip() or 0)
    except Exception: return 0.0

# ① 작성 스크립트(review MD)의 후킹 선언 분포
written = collections.Counter()
for md in sorted(glob.glob("promo/review/*.md")):
    if not re.match(r"\d{3}_", os.path.basename(md)): continue
    hook = ""
    for raw in open(md, encoding="utf-8"):
        s = raw.strip().lstrip("-* ").strip()
        if s.startswith("후킹"):
            hook = s.split(":",1)[1].strip(); break
    written[hook or "(미선언)"] += 1

man = load_csv("promo/_manifest.csv")
res = load_csv("promo/_results.csv")
by_outfile = {r["outfile"]: r for r in man if r.get("outfile")}

print("="*60)
print(" promo 생성 근거 패널   (게이트 = %d 누적조회)" % GATE)
print("="*60)

print("\n① 작성된 스크립트 후킹 분포 (review MD %d편)" % sum(written.values()))
for h in HOOKS + ["(미선언)"]:
    if written.get(h): print("   %-8s %d편" % (h, written[h]))

print("\n② 렌더 분포 (manifest %d행)" % len(man))
rc = collections.Counter((r.get("hook_pattern") or "(미기록)", r.get("preset") or "?") for r in man)
if not man: print("   (렌더 기록 없음)")
for (h,p),n in sorted(rc.items()): print("   %-8s / %-9s %d편" % (h,p,n))

print("\n③ 후킹 축 성과 (results %d건)" % len(res))
agg = collections.defaultdict(lambda:{"n":0,"v":0.0,"l":0.0})
joined = 0
for r in res:
    m = by_outfile.get((r.get("outfile") or "").strip())
    if not m: continue
    joined += 1
    h = m.get("hook_pattern") or "(미기록)"
    a = agg[h]; a["n"]+=1; a["v"]+=num(r.get("views")); a["l"]+=num(r.get("likes"))
if not joined:
    print("   성과 데이터 0건 → 업로드+운영일지 기록 후 채워짐. (지금은 성과 가중 미적용)")
else:
    print("   %-8s %4s %9s %9s %7s %s" % ("후킹","편수","누적조회","평균조회","참여율","판정"))
    for h,a in sorted(agg.items(), key=lambda kv:-(kv[1]["v"]/max(kv[1]["n"],1))):
        eng = a["l"]/a["v"] if a["v"] else 0
        flag = "" if a["v"]>=GATE else " ←표본부족"
        print("   %-8s %4d %9d %9.0f %6.1f%%%s" % (h,a["n"],a["v"],a["v"]/a["n"],eng*100,flag))

print("\n④ 다음 생성 제안 — 미커버 (후킹×프리셋) 셀")
covered = set((r.get("hook_pattern"), r.get("preset")) for r in man)
gaps = [(h,p) for h in HOOKS for p in PRESETS if (h,p) not in covered]
print("   총 %d/%d 셀 미커버. 우선 후보:" % (len(gaps), len(HOOKS)*len(PRESETS)))
for h,p in gaps[:8]: print("     - %s / %s" % (h,p))

print("\n※ 인사이트 시트(유튜브_인사이트·메타_인사이트) Top 후킹 가중은 생성 시 Claude가 반영(시트는 Drive로 읽음).")
print("   성과 데이터가 게이트를 넘기 전까지 '반영'은 인사이트+커버리지 기준이며, 성과 가중은 0이다(노이즈 회피).")
