# promo 성과 집계 — manifest(변주) + _results.csv(성과) 조인 후 축별 풀링·게이트·랭킹.
# 성과 출처: 관리시트 '유튜브'/'인스타' 운영 일지의 조회수·좋아요(사람 수기). promo_ingest 가 _results.csv로 떨굼.
# 핵심: 개별 영상은 노출 작아 노이즈 → 후킹/프리셋/스타일 '축'으로 합산해야 신호가 선다(설계서 §5).
# usage: py scripts\promo_score.py [--gate 5000]
import csv, os, sys, collections

GATE = 5000
if "--gate" in sys.argv:
    try: GATE = int(sys.argv[sys.argv.index("--gate") + 1])
    except Exception: pass

MAN = "promo/_manifest.csv"
RES = "promo/_results.csv"

def load_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

man = load_csv(MAN)
res = load_csv(RES)
by_outfile = {r["outfile"]: r for r in man if r.get("outfile")}

def num(x):
    try: return float(str(x).replace(",", "").strip() or 0)
    except Exception: return 0.0

# 조인: _results 의 outfile → manifest 행. 없으면 slug+preset 로 근접 매칭.
joined = []
unmatched = []
for r in res:
    of = (r.get("outfile") or "").strip()
    m = by_outfile.get(of)
    if not m:
        # fallback: outfile 비면 slug/preset 로
        sp = (r.get("slug") or "", r.get("preset") or "")
        cand = [x for x in man if x.get("slug") == sp[0] and (not sp[1] or x.get("preset") == sp[1])]
        m = cand[0] if cand else None
    if not m:
        unmatched.append(of or r.get("slug") or "(?)"); continue
    joined.append({
        "outfile": m["outfile"], "platform": r.get("platform", ""),
        "views": num(r.get("views")), "likes": num(r.get("likes")),
        "hook_pattern": m.get("hook_pattern") or "(미지정)",
        "preset": m.get("preset") or "(?)",
        "styles": [s.split(":")[-1] for s in (m.get("styles") or "").split(";") if ":" in s],
    })

print("=" * 56)
print(" promo 성과 집계  | 게이트(축 누적조회) = %d" % GATE)
print(" manifest %d행 / results %d행 / 조인 %d건 / 미매칭 %d건"
      % (len(man), len(res), len(joined), len(unmatched)))
print("=" * 56)
if not joined:
    print("\n성과 데이터 0건. 업로드→관리시트('유튜브'/'인스타') 기록→promo_ingest 후 다시 실행.")
    print("(시트 운영일지 '비고'에 outfile 또는 slug 기재해야 귀속됨 — 설계서 §4)")
    sys.exit(0)

def pool(axis_fn):
    agg = collections.defaultdict(lambda: {"n": 0, "views": 0.0, "likes": 0.0})
    for j in joined:
        for key in axis_fn(j):
            a = agg[key]; a["n"] += 1; a["views"] += j["views"]; a["likes"] += j["likes"]
    out = []
    for k, a in agg.items():
        eng = (a["likes"] / a["views"]) if a["views"] else 0
        out.append((k, a["n"], a["views"], a["views"] / a["n"], eng, a["views"] >= GATE))
    return sorted(out, key=lambda x: (-x[3], -x[4]))  # 평균조회 desc, 참여율 desc

def show(title, rows):
    print("\n[%s]" % title)
    print("  %-14s %4s %10s %10s %8s %s" % ("값", "편수", "누적조회", "평균조회", "참여율", "판정"))
    for k, n, sv, av, eng, gated in rows:
        flag = "" if gated else "  ← 표본부족(<게이트, 순위 신뢰X)"
        print("  %-14s %4d %10d %10.0f %7.1f%% %s" % (k, n, sv, av, eng * 100, flag))

show("후킹 패턴", pool(lambda j: [j["hook_pattern"]]))
show("프리셋",   pool(lambda j: [j["preset"]]))
show("스타일",   pool(lambda j: list(set(j["styles"]))))

gated_axes = [k for k, n, sv, av, eng, g in pool(lambda j: [j["hook_pattern"]]) if g]
print("\n요약: 게이트 통과한 후킹 축 %d개. 통과 축만 '이김' 판단에 사용." % len(gated_axes))
print("⚠ 표본부족 축의 순위는 노이즈 — 데이터 더 쌓고 판단(설계서 §5/§9).")
