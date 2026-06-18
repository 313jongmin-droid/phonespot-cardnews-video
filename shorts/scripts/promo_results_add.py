# promo 성과 1행 수동 추가(폴백). 보통은 Claude가 관리시트 '유튜브'/'인스타' 탭에서 일괄 기입.
# usage: py scripts\promo_results_add.py <outfile> <platform> <views> <likes> [url] [slug] [preset]
import sys, os, csv, datetime
if len(sys.argv) < 5:
    print("usage: promo_results_add.py <outfile> <platform: youtube|instagram> <views> <likes> [url] [slug] [preset]")
    sys.exit(1)
outfile, platform, views, likes = sys.argv[1:5]
url    = sys.argv[5] if len(sys.argv) > 5 else ""
slug   = sys.argv[6] if len(sys.argv) > 6 else ""
preset = sys.argv[7] if len(sys.argv) > 7 else ""
cols = ["pull_date","platform","outfile","slug","preset","url","views","likes"]
path = "promo/_results.csv"
new = not os.path.exists(path)
with open(path, "a", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    if new: w.writeheader()
    w.writerow({"pull_date": datetime.date.today().isoformat(), "platform": platform,
                "outfile": outfile, "slug": slug, "preset": preset,
                "url": url, "views": views, "likes": likes})
print("results +1:", outfile, platform, views, "views", likes, "likes")
