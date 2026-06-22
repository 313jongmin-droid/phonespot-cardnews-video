# promo 업로드 키트 — 렌더된 mp4 + SEO 텍스트(youtube/instagram)를 한 폴더로 묶는다.
# "복붙해서 같이 업로드" 용. 결과: promo/out/<slug>_upload/ 안에 영상 + 텍스트 동거.
# usage: promo_uploadkit.py <nn> [outfile.mp4]
#   - outfile 주면 그 영상 사용, 없으면 promo/out/<slug>_*.mp4 중 최신.
#   - 텍스트(promo/upload/<slug>/*.txt)가 없으면 브랜드 보일러플레이트로 골격 생성(후킹은 TODO).
import sys, os, glob, json, shutil

nn = sys.argv[1] if len(sys.argv) > 1 else ""
outfile_arg = sys.argv[2] if len(sys.argv) > 2 else ""
if not nn:
    print("usage: promo_uploadkit.py <nn> [outfile.mp4]"); sys.exit(1)

# slug = promo/<nn>_*.json 의 파일명(= nn_label)
cands = sorted(glob.glob(f"promo/{int(nn):03d}_*.json"))
if not cands:
    cands = sorted(glob.glob(f"promo/{nn}_*.json"))
if not cands:
    print(f"[uploadkit] {nn}: JSON 없음"); sys.exit(0)
slug = os.path.splitext(os.path.basename(cands[0]))[0]

# 영상 찾기
mp4 = ""
if outfile_arg and os.path.exists(outfile_arg):
    mp4 = outfile_arg
else:
    vids = sorted(glob.glob(f"promo/out/{slug}_*.mp4"), key=os.path.getmtime)
    mp4 = vids[-1] if vids else ""

dest = f"promo/out/{slug}_upload"
os.makedirs(dest, exist_ok=True)

# 텍스트 복사(없으면 골격 생성)
txt_dir = f"promo/upload/{slug}"
copied = []
for name in ("youtube.txt", "instagram.txt"):
    src = os.path.join(txt_dir, name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dest, name)); copied.append(name)

if not copied:
    # 브랜드 보일러플레이트 골격(후킹/본문은 사람·Claude가 채움)
    b = {}
    try: b = json.load(open("promo/_brand.json", encoding="utf-8"))
    except Exception: pass
    kakao = b.get("kakao", "@휴대폰성지폰스팟")
    litt = b.get("litt", "litt.ly/phonespot")
    loc = b.get("location", "광교호수공원 B1-47")
    vidname = os.path.basename(mp4) if mp4 else f"{slug}_*.mp4"
    yt = (f"[영상 파일] promo/out/{vidname}\n\n========== 제목 (복붙) ==========\n[SEO 후킹 제목 — 핵심 키워드 포함]\n\n"
          f"========== 설명 (복붙) ==========\n[2~3문장 요약 + 매장 강점]\n\n휴대폰성지 폰스팟\n- 위치: 경기도 수원시 영통구 광교호수공원로 20 B1-47호\n"
          f"- 카카오톡: {kakao}\n- 링크: {litt}\n\n#Shorts #폰스팟 #휴대폰성지폰스팟 #광교휴대폰 #정찰제\n\n[사전승낙서] (사전승낙서 URL 붙여넣기)\n")
    ig = (f"[영상 파일] promo/out/{vidname}\n\n========== 캡션 (복붙) ==========\n[이모지 + 첫 줄 후킹]\n\n→ [요점1]\n→ [요점2]\n→ [요점3]\n\n"
          f"💬 휴대폰성지 폰스팟 1:1 상담\n📍 {loc}\n🔗 프로필 링크 → {litt}\n\n"
          f"#폰스팟 #휴대폰성지폰스팟 #휴대폰성지 #광교 #광교휴대폰 #수원휴대폰 #비대면개통 #온라인개통 #전국배송 #정찰제 #휴대폰꿀팁 #핸드폰성지\n\n[사전승낙서] (사전승낙서 URL 붙여넣기)\n")
    open(os.path.join(dest, "youtube.txt"), "w", encoding="utf-8").write(yt)
    open(os.path.join(dest, "instagram.txt"), "w", encoding="utf-8").write(ig)
    copied = ["youtube.txt(골격)", "instagram.txt(골격)"]

# 영상 복사
if mp4:
    shutil.copy2(mp4, os.path.join(dest, os.path.basename(mp4)))
    print(f"[uploadkit] {dest}\\  <- {os.path.basename(mp4)} + {', '.join(copied)}")
else:
    print(f"[uploadkit] {dest}\\  (영상 없음 — 텍스트만: {', '.join(copied)})")
