# 주제 -> 타이포(promo) 초안 MD 자동 생성 (TOPIC_TO_PROMO 스펙).
# 우선순위: Gemini(gemini-2.5-flash, _secrets/gemini_key.txt) 로 한글 카피 작성 -> 실패/키없음이면 템플릿 폴백.
# 비트 스타일/효과음은 스펙 고정(오프닝 oversize/whoosh · 훅 kinetic/whoosh · 팩트1 glitch/tick ·
#   팩트2 kinetic-box/ding · 팩트3 swiss/pop · CTA kinetic-box/ding) -> Gemini는 '카피만' 작성(안정).
# 출력 끝줄: "OK <NNN> <label> <preset>"  (패널이 파싱해서 promo_render 로 이어붙임)
# 규칙: NNN = 기존 promo/*.json 최대+1 / label = ASCII 한 토큰(언더스코어 금지, HANDOFF 슬러그 인코딩).
# usage:
#   py scripts/promo_generate.py "<주제 한 줄/제목>" [--preset showcase|punchy|data|calm] [--label <ascii>] [--slug <article_slug>]
import sys, os, re, json, glob, subprocess, hashlib, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"
GEMINI_KEY = ROOT / "_secrets" / "gemini_key.txt"
MODEL = os.environ.get("PHONESPOT_GEMINI_TEXT_MODEL", "gemini-2.5-flash")
PRESETS = ("showcase", "punchy", "data", "calm")

# 비트별 고정 스타일/효과음 (스펙 §3 / GUIDE_BEST_TYPO_AD §2)
BEATS = [
    ("오프닝", "oversize", "whoosh"),
    ("훅", "kinetic", "whoosh"),
    ("팩트1", "glitch", "tick"),
    ("팩트2", "kinetic-box", "ding"),
    ("팩트3", "swiss", "pop"),
    ("CTA", "kinetic-box", "ding"),
]

def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

def ascii_token(text, fallback):
    s = re.sub(r"[^a-zA-Z0-9]+", "", (text or "").strip().lower())  # 언더스코어/공백 전부 제거 = 한 토큰
    # 한글만 있는 주제는 ASCII가 비거나 'vs' 같은 잔재만 남음 -> 3자 미만이면 해시 폴백.
    return s[:16] if len(s) >= 3 else fallback

def next_nnn():
    mx = 0
    for f in glob.glob(str(SHORTS / "promo" / "[0-9][0-9][0-9]_*.json")):
        m = re.match(r"(\d{3})_", os.path.basename(f))
        if m:
            mx = max(mx, int(m.group(1)))
    return "%03d" % (mx + 1)

def topic_title(topic, slug):
    # article slug 주면 제목을 articles/<slug>.json 에서 시도
    if slug:
        for p in (ROOT / "cardnews" / "articles").glob(f"{slug}*.json"):
            try:
                d = json.load(open(p, encoding="utf-8"))
                return d.get("title_short") or d.get("video_title") or (d.get("cards", [{}])[0].get("headline", "")) or topic
            except Exception:
                pass
    return topic

# ---------- Gemini 카피 생성 ----------
def gemini_copy(title):
    try:
        key = GEMINI_KEY.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not key.startswith("AIza"):
        return None
    prompt = (
        "너는 휴대폰성지 '폰스팟'(광교점, 정찰제) 타이포 광고 카피라이터다. 아래 주제로 9:16 무음 타이포 광고의 "
        "한글 자막 카피를 JSON으로만 출력하라. 규칙: (1) 가격/지원금 숫자 금지, 경쟁사 지목 금지, '안양' 금지. "
        "(2) 사운드오프 가독 — 각 화면 토막은 2~6자, 한 비트당 토막 최대 3개. (3) 브랜드 강점만: 정찰제·즉시조회·"
        "그대로 개통·비대면 견적·호갱방지·광교점. (4) 원형숫자(①) 금지, 평문. "
        "출력 JSON 스키마: {\"preset\":\"showcase|punchy|data|calm\",\"title\":\"8자 이내\","
        "\"hook_type\":\"질문형|비교형|반전형|공감형\",\"label\":\"english one word lowercase\","
        "\"opening\":{\"line1\":\"\",\"line2\":\"\"},\"hook\":[\"\",\"\",\"\"],\"fact1\":[\"\",\"\",\"\"],"
        "\"fact2\":[\"\",\"\",\"\"],\"fact3\":[\"\",\"\",\"\"],\"cta\":[\"\",\"\"]}. JSON 외 텍스트 금지.\n주제: " + title
    )
    url = ("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?key=" + key)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        obj = json.loads(text)
        return obj
    except Exception:
        return None

# ---------- 스마트 템플릿 (무LLM): 주제 키워드 -> 브랜드 앵글 자동 선택 + 비트별 변주 풀 ----------
# 규제 안전: 가격/지원금 숫자 X, 경쟁사 지목 X, '안양' X. 카피는 기존 검증 스크립트에서 정리.
# 앵글 순서 = 탐지 우선순위(구체 앵글 먼저, jeongchalje는 기본 폴백이라 맨 끝).
ANGLES = {
    "bumonim": {  # 부모님폰
        "preset": "calm", "hook_type": "공감형",
        "keywords": ["부모님", "효도", "가족", "어르신", "엄마", "아빠"],
        "title": ["부모님 폰", "효도폰"],
        "opening": [("부모님 폰,", "대신 알아볼 때"), ("부모님", "폰 바꿀 때")],
        "hook": [["혹시", "호갱 될까", "걱정"], ["멀리 사는", "부모님", "폰 걱정"]],
        "fact1": [["매장 가면", "어려운 말", "헷갈림"], ["어르신 혼자", "가면", "불안"]],
        "fact2": [["멀리 안 가도", "집에서", "확인"], ["가격도", "미리", "투명하게"]],
        "fact3": [["카톡으로", "대신", "알아보기"], ["조회부터", "개통까지", "대신"]],
        "cta": [["부모님 폰도", "안심"], ["효도폰도", "폰스팟"]],
    },
    "hogaeng": {  # 호갱방지
        "preset": "punchy", "hook_type": "위협형",
        "keywords": ["호갱", "사기", "속", "조건", "할부", "공짜", "함정", "주의", "당하"],
        "title": ["호갱 방지", "속지 마세요"],
        "opening": [("휴대폰 살 때", "이건 하지 마세요"), ("공개된 가격,", "믿어도 될까?")],
        "hook": [["모르고 사면", "호갱", "됩니다"], ["싸다고 올려놓고", "막상 가면", "말 바뀜"]],
        "fact1": [["할부 개월", "길게 늘려", "싸 보이게"], ["'공짜'라는 말", "조건부터", "확인"]],
        "fact2": [["폰스팟은", "조건도", "먼저 공개"], ["폰스팟은", "정찰제", "말 안 바뀜"]],
        "fact3": [["보이는 가격", "그대로", "개통"], ["숨은 조건", "없이", "투명"]],
        "cta": [["호갱 안 되려면", "폰스팟"], ["속지 말고", "폰스팟"]],
    },
    "nosangdam": {  # 상담 강요 없음
        "preset": "punchy", "hook_type": "반전형",
        "keywords": ["상담", "오세요", "강요", "방문", "일단"],
        "title": ["상담 강요 없음", "가격부터"],
        "opening": [("가격 물어보면", "'일단 오세요'"), ("휴대폰 살 때", "상담부터 그만")],
        "hook": [["물어보면", "'일단 오세요'", "가격은?"], ["상담만", "한참", "진 빠짐"]],
        "fact1": [["가격 궁금해도", "오라고만", "하고"], ["상담 받아야", "가격", "알려줌?"]],
        "fact2": [["폰스팟은", "상담 강요", "없이"], ["폰스팟은", "가격부터", "바로"]],
        "fact3": [["조회부터", "개통까지", "간편"], ["오라는 말", "없이", "투명"]],
        "cta": [["상담 그만", "폰스팟"], ["가격부터", "폰스팟"]],
    },
    "compare": {  # 발품 vs 조회
        "preset": "data", "hook_type": "비교형",
        "keywords": ["발품", "비교", "돌", "여러 곳", " vs", "어디서"],
        "title": ["발품 vs 조회", "비교 끝"],
        "opening": [("매장 세 곳", "vs 조회 한 번"), ("발품", "vs 조회")],
        "hook": [["발품 한참", "vs", "조회 한 번"], ["여러 곳 돌까", "한 번에", "볼까"]],
        "fact1": [["매장마다", "말이", "다르고"], ["돌아다니면", "시간만", "버림"]],
        "fact2": [["폰스팟은", "한 번에", "비교 끝"], ["조회 한 번", "으로", "끝"]],
        "fact3": [["발품 그만", "조회로", "간편"], ["집에서", "비대면", "비교"]],
        "cta": [["발품 그만", "폰스팟"], ["조회로 끝", "폰스팟"]],
    },
    "bidaemyeon": {  # 비대면 견적
        "preset": "showcase", "hook_type": "질문형",
        "keywords": ["비대면", "온라인", "집에서", "원격", "카톡", "택배", "전국", "방구석"],
        "title": ["비대면 견적", "집에서 조회"],
        "opening": [("휴대폰 사러", "매장 꼭 가야 해?"), ("집에서", "휴대폰 조회")],
        "hook": [["매장 돌고", "줄 서고", "꼭?"], ["발품 안 팔아도", "집에서", "바로"]],
        "fact1": [["발품 팔아도", "말은 제각각", "시간 낭비"], ["매장까지", "가서", "상담만"]],
        "fact2": [["폰스팟은", "집에서", "비대면 조회"], ["카톡으로", "바로", "견적"]],
        "fact3": [["조회부터", "개통까지", "카톡으로"], ["전국", "어디서나", "비대면"]],
        "cta": [["휴대폰도 이제", "비대면"], ["집에서 편하게", "폰스팟"]],
    },
    "jeongchalje": {  # 정찰제 (기본 폴백)
        "preset": "showcase", "hook_type": "비교형",
        "keywords": ["정찰", "정가", "가격", "투명", "흥정", "공개", "그대로"],
        "title": ["휴대폰도 정찰제", "가격 그대로"],
        "opening": [("세상 모든 건", "가격표가 있어요"), ("휴대폰도", "정찰제로")],
        "hook": [["편의점", "마트", "다 정가"], ["다른 건 다", "정가표", "휴대폰만?"]],
        "fact1": [["근데 휴대폰만", "왜", "흥정?"], ["매장마다", "부르는 게", "값?"]],
        "fact2": [["폰스팟은", "가격", "먼저 공개"], ["폰스팟은", "정찰제", "흥정 없음"]],
        "fact3": [["조회한 그대로", "투명하게", "개통까지"], ["숨은 비용", "없이", "그대로"]],
        "cta": [["휴대폰도 이제", "폰스팟"], ["투명한 가격", "폰스팟"]],
    },
}

def _pick(variants, seed):
    if not variants:
        return variants
    h = int(hashlib.sha1((seed or "x").encode("utf-8")).hexdigest(), 16)
    return variants[h % len(variants)]

def template_copy(title):
    t = (title or "").lower()
    angle = "jeongchalje"
    for name, a in ANGLES.items():
        if any(k in t for k in a["keywords"]):
            angle = name
            break
    a = ANGLES[angle]
    op = _pick(a["opening"], title)
    return {
        "preset": a["preset"], "title": _pick(a["title"], title), "hook_type": a["hook_type"],
        "label": angle,
        "opening": {"line1": op[0], "line2": op[1]},
        "hook": _pick(a["hook"], (title or "") + "h"),
        "fact1": _pick(a["fact1"], (title or "") + "1"),
        "fact2": _pick(a["fact2"], (title or "") + "2"),
        "fact3": _pick(a["fact3"], (title or "") + "3"),
        "cta": _pick(a["cta"], (title or "") + "c"),
    }

def clean_chunks(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:3]
    return [str(v).strip()] if v else []

def build_md(nnn, label, c):
    preset = c.get("preset") if c.get("preset") in PRESETS else "showcase"
    title = (c.get("title") or label)[:12]
    hook_type = c.get("hook_type") or "질문형"
    op = c.get("opening") or {}
    lines = [f"# {nnn} {label}", f"- preset: {preset}", f"- title: {title}", f"- 후킹: {hook_type}", ""]
    # 오프닝
    lines += ["## 오프닝", f"- line1: {op.get('line1','')}", f"- line2: {op.get('line2','')}",
              "- 스타일: oversize", "- 효과음: whoosh", ""]
    for sec, style, sfx, keyname in [("훅", "kinetic", "whoosh", "hook"),
                                     ("팩트1", "glitch", "tick", "fact1"),
                                     ("팩트2", "kinetic-box", "ding", "fact2"),
                                     ("팩트3", "swiss", "pop", "fact3"),
                                     ("CTA", "kinetic-box", "ding", "cta")]:
        chunks = clean_chunks(c.get(keyname))
        lines += [f"## {sec}", f"- 스타일: {style}", f"- 효과음: {sfx}",
                  f"- 화면: {' | '.join(chunks)}", ""]
    return "\n".join(lines) + "\n", preset

def main():
    topic = next((a for a in sys.argv[1:] if not a.startswith("--")), "")
    if not topic and not arg("--slug"):
        print("usage: promo_generate.py \"<주제>\" [--preset P] [--label L] [--slug article_slug]")
        sys.exit(1)
    slug = arg("--slug")
    title = topic_title(topic, slug)

    c = gemini_copy(title) or template_copy(title)
    src = "gemini" if (c and c.get("label") is not None and c is not None) else "template"
    # preset override
    pre_ov = arg("--preset")
    if pre_ov in PRESETS:
        c["preset"] = pre_ov
    # label 결정 (언더스코어 금지 단일 토큰)
    label = arg("--label") or c.get("label") or slug or title
    label = ascii_token(label, "topic" + hashlib.sha1((title or "x").encode("utf-8")).hexdigest()[:5])

    nnn = next_nnn()
    md, preset = build_md(nnn, label, c)
    review = SHORTS / "promo" / "review"
    review.mkdir(parents=True, exist_ok=True)
    md_path = review / f"{nnn}_{label}.md"
    md_path.write_text(md, encoding="utf-8")

    # md2json 등록 (cwd=shorts)
    r = subprocess.run([sys.executable, "scripts/promo_md2json.py", str(int(nnn))],
                       cwd=str(SHORTS), capture_output=True, text=True, timeout=30)
    ok_json = (SHORTS / "promo" / f"{nnn}_{label}.json").exists()
    print(f"[generate] src={src} md={md_path.name} json={'OK' if ok_json else 'FAIL'} ({r.stdout.strip()})")
    print(f"OK {nnn} {label} {preset}")

if __name__ == "__main__":
    main()
