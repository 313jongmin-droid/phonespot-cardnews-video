# 현재 public/shorts_script.json 에 맞는 음악 트랙을 골라 music_src 기록.
# 우선순위: script.music(명시 파일) > script.mood > preset→mood. 같은 무드는 slug 번호로 로테이션.
import json, glob, os, re, sys
MOOD_BY_PRESET = {"showcase": "confident", "punchy": "upbeat", "calm": "calm", "data": "minimal"}
# 인자: argv[1]=preset(렌더할 프리셋), argv[2]=slug(로테이션 번호). bat에서 넘겨줌.
arg_preset = sys.argv[1] if len(sys.argv) > 1 else None
arg_slug = sys.argv[2] if len(sys.argv) > 2 else None
sp = "public/shorts_script.json"
d = json.load(open(sp, encoding="utf-8"))
mdir = "public/music"
chosen = ""
explicit = d.get("music")
if explicit and os.path.exists(os.path.join(mdir, explicit)):
    chosen = explicit
else:
    preset = arg_preset or d.get("preset", "showcase")
    mood = d.get("mood") or MOOD_BY_PRESET.get(preset, "upbeat")
    tracks = sorted(os.path.basename(f) for f in glob.glob(os.path.join(mdir, f"{mood}_*.mp3")))
    if not tracks:
        # 해당 무드 곡이 없을 때: 전체 *.mp3가 아니라 '정상 무드 파일'에서만 fallback.
        # sting(opening_sting/cta_sting)·규칙위반 파일명이 BGM으로 잡히는 오염 방지. 그래도 없으면 음악 off.
        MOODS = set(MOOD_BY_PRESET.values())
        tracks = sorted(os.path.basename(f) for f in glob.glob(os.path.join(mdir, "*.mp3"))
                        if os.path.basename(f).split("_", 1)[0] in MOODS)
    if tracks:
        m = re.match(r"(\d+)", str(arg_slug or d.get("slug", "0")))
        idx = (int(m.group(1)) if m else 0) % len(tracks)
        chosen = tracks[idx]
# 파일명 끝 __NN = 시작 초 (예: confident_02__70.mp3 -> 70초부터). 없으면 0.
start = 0
sm = re.search(r"__(\d+)\.mp3$", chosen) if chosen else None
if sm:
    start = int(sm.group(1))
d["music_src"] = ("music/" + chosen) if chosen else ""
d["music_start"] = start
json.dump(d, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("music:", d["music_src"] or "(none - public/music/ 비어있음)", "start:", start)
