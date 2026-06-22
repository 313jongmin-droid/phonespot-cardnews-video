"""자동 청크 매핑 + shorts_script.json 박기.

메모리 패턴 (feedback_visual_mapping_patterns.md) 키워드 매칭 기반.
Claude 대화 없이 동작.

흐름:
1. output/ 의 새 [OK] 슬러그 감지 (shorts_script.json 없는 거)
2. articles 본문 청크 분할 + 키워드 매핑
3. shorts_script.json 박기 (_auto_polish: True)
4. 신규 일러스트 필요 시 pending_illustrations.log 기록

품질 ★★★ — 종민님 검수 권장.
"""
import json
import re
import sys
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/
articles_dir = cardnews_root / "articles"
images_dir = cardnews_root / "images"
output_dir = cardnews_root / "output"
illust_dir = project_root / "public" / "assets" / "illustrations"

# 라이브러리에 실제 존재하는 일러스트 (PNG 파일)
available_illusts = set()
if illust_dir.exists():
    for p in illust_dir.glob("*.png"):
        available_illusts.add(p.stem)

# 키워드 → visual 매핑 (메모리 feedback-visual-mapping-patterns.md 기반)
KEYWORD_MAP = [
    # 우선순위: 구체적 키워드부터
    ("애플페이", "image:logos/apple.png"),
    ("아이폰", "image:logos/apple.png"),
    ("Apple", "image:logos/apple.png"),
    ("애플", "image:logos/apple.png"),
    ("갤럭시 Z 폴드", "illust:foldable"),
    ("Z폴드", "illust:foldable"),
    ("Z플립", "illust:foldable"),
    ("폴더블", "illust:foldable"),
    ("갤럭시", "image:logos/samsung.png"),
    ("삼성페이", "image:logos/samsung.png"),
    ("삼성전자", "image:logos/samsung.png"),
    ("삼성", "image:logos/samsung.png"),
    ("SKT", "image:logos/skt.png"),
    ("KT", "image:logos/kt.png"),
    ("LG U+", "image:logos/lgu.png"),
    ("LGU", "image:logos/lgu.png"),
    # 키워드
    ("팁스터", "illust:newspaper"),
    ("기자", "illust:newspaper"),
    ("보도했습니다", "illust:newspaper"),
    ("외신", "illust:newspaper"),
    ("전망", "illust:forecast"),
    ("예측", "illust:forecast"),
    ("예정", "illust:forecast"),
    ("인터뷰", "illust:microphone"),
    ("발표", "illust:microphone"),
    ("발열", "illust:heat_release"),
    ("열 처리", "illust:heat_release"),
    ("티타늄", "illust:ti_decrease"),
    ("알루미늄", "illust:aluminum_label"),
    ("액체 금속", "illust:liquid_titanium"),
    ("Gemini", "illust:gemini"),
    ("챗봇", "illust:chatbot"),
    ("챗GPT", "illust:chatbot"),
    ("AI 비서", "illust:samsung_ai"),
    ("Siri", "illust:samsung_ai"),
    ("AI", "illust:samsung_ai"),
    ("전략", "illust:meeting_room"),
    ("검토 중", "illust:meeting_room"),
    ("회의", "illust:meeting_room"),
    ("개발자회의", "illust:meeting_room"),
    ("WWDC", "illust:meeting_room"),
    ("상품권", "illust:gift_voucher"),
    ("보상금", "illust:gift_voucher"),
    ("통장", "illust:bank_account"),
    ("잔액", "illust:bank_account"),
    ("제외", "illust:prohibit"),
    ("금지", "illust:prohibit"),
    ("차단", "illust:prohibit"),
    ("보안", "illust:lock"),
    ("잠금", "illust:lock"),
    ("암호", "illust:lock"),
    ("비밀번호", "illust:password"),
    ("생체인증", "illust:biometric"),
    ("지문", "illust:biometric"),
    ("페이스ID", "illust:biometric"),
    ("터치ID", "illust:biometric"),
    ("마감", "illust:clock"),
    ("기한", "illust:clock"),
    ("스마트폰", "illust:smartphone"),
    ("상승", "illust:chart_up"),
    ("호전", "illust:chart_up"),
    ("하락", "illust:chart_down"),
    ("NFC", "illust:nfc_pay"),
    ("비접촉", "illust:nfc_pay"),
    ("동등", "illust:handshake"),
    ("협약", "illust:handshake"),
    ("매장", "illust:store"),
    ("가게", "illust:store"),
    ("경고", "illust:warning"),
    ("위험", "illust:warning"),
    ("주의", "illust:warning"),
    ("메모리", "illust:memory_chip"),
    ("RAM", "illust:memory_chip"),
    ("램가격", "illust:memory_chip"),
    ("노트북", "illust:appliance"),
    ("게임 콘솔", "illust:appliance"),
    ("전자제품", "illust:appliance"),
    ("방패", "illust:shield"),
    ("악성 공격", "illust:shield"),
    ("업데이트", "illust:final_update"),
    ("주가", "illust:stock_chart"),
    ("목표주가", "illust:stock_chart"),
    ("시총", "illust:market_cap"),
    ("시가총액", "illust:market_cap"),
    ("인상", "illust:price_hike"),
    ("로그아웃", "illust:logout"),
    ("초기화", "illust:reset"),
    ("리셋", "illust:reset"),
    ("클라우드 백업", "illust:cloud_backup"),
    ("클라우드", "illust:cloud_backup"),
]

MASCOTS = ["surprised", "satisfied", "suspicious", "smirk", "serious", "wink", "excited", "confused", "shocked", "thinking", "sleepy", "angry"]


def split_caption(text, max_chars=24):
    """build_script.py 의 split_caption 복사."""
    text = text.replace("\n", " ").strip()
    if not text:
        return []
    def _n(s):
        return len(s.replace(" ", ""))
    def _word_chunks(s):
        words = s.split()
        tokens = []
        i = 0
        while i < len(words):
            cur = words[i]
            while _n(cur) <= 2 and i + 1 < len(words):
                i += 1
                cur = cur + " " + words[i]
            tokens.append(cur)
            i += 1
        out, c = [], ""
        for t in tokens:
            merged = (c + " " + t).strip() if c else t
            if _n(merged) > max_chars and c:
                out.append(c)
                c = t
            else:
                c = merged
        if c:
            out.append(c)
        return out
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    for sent in sentences:
        if _n(sent) <= max_chars:
            chunks.append(sent)
            continue
        clauses = re.split(r"(?<=[,;])\s+", sent)
        clauses = [c.strip() for c in clauses if c.strip()]
        for cl in clauses:
            if _n(cl) <= max_chars:
                chunks.append(cl)
            else:
                chunks.extend(_word_chunks(cl))
    return chunks


def parse_headline(hl):
    emph = re.findall(r'<span class="hl">(.*?)</span>', hl)
    clean = re.sub(r'</?span[^>]*>', '', hl)
    lines = [l.strip() for l in clean.split("\n") if l.strip()]
    return lines, emph


def map_visual(chunk_text, used, available_images, idx, k, total_chunks):
    """단일 청크 매핑. used 에 있으면 다음 후보 시도. 모든 매핑은 한 영상 내 unique."""
    # 1) 키워드 매칭
    for keyword, visual in KEYWORD_MAP:
        if keyword.lower() in chunk_text.lower():
            # illust:variant 검증 — 라이브러리에 실제 있는지
            if visual.startswith("illust:"):
                v = visual.split(":", 1)[1]
                if v not in available_illusts:
                    continue  # 라이브러리에 없으면 skip → 다음 키워드
            if visual not in used:
                return visual

    # 2) GPT 이미지 풀에서 순환
    for img in available_images:
        v = f"image:{img}"
        if v not in used:
            return v

    # 3) 마스코트 (마지막 청크일 때 우선)
    if k == total_chunks - 1:
        for emotion in ["serious", "satisfied", "surprised", "thinking", "smirk", "suspicious"]:
            v = f"mascot:{emotion}"
            if v not in used:
                return v

    # 4) 신규 일러스트 필요 표시
    return None  # 호출자가 신규 알림 처리


def auto_polish(slug, force=False):
    art_path = articles_dir / f"{slug}.json"
    out_path = output_dir / slug / "shorts_script.json"
    if not art_path.exists():
        return False, "no article"
    if out_path.exists() and not force:
        return False, "shorts_script.json exists (skip)"

    art = json.load(open(art_path, encoding="utf-8"))
    cards = art.get("cards", [])
    if len(cards) < 2:
        return False, "no cards[]"

    # 이미지 풀
    available_images = []
    img_subdir = images_dir / slug
    if img_subdir.exists():
        for i in range(1, 20):
            p = img_subdir / f"{i}.png"
            if p.exists():
                available_images.append(p.name)
        if not available_images:
            for p in sorted(img_subdir.glob("gpt_*.png")):
                available_images.append(p.name)
    if not available_images:
        return False, "no images"

    title = art.get("title", slug).split(" / ")[0].strip()  # " / "만 분리 (날짜 "6/8" 보존)
    src_line = art.get("source_line", "").replace("출처:", "").strip()
    src_short = src_line.split("·")[0].strip() if src_line else ""

    used = set()
    pending_keywords = []  # 신규 일러스트 필요 키워드

    def build_sec(card, idx, total, is_cta=False):
        if is_cta:
            chunks = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]
            visuals = [{"type": "illust", "value": "smartphone"}, {"type": "logo", "value": None}]
            # smartphone 가 이미 사용됐으면 gift_voucher
            if "illust:smartphone" in used:
                visuals[0] = {"type": "illust", "value": "gift_voucher"}
            used.add(f"illust:{visuals[0]['value']}")
            tts = "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."
        else:
            body = card.get("body", "").strip()
            chunks = split_caption(body)
            visuals = []
            for k, c in enumerate(chunks):
                v = map_visual(c, used, available_images, idx, k, len(chunks))
                if v is None:
                    # 폴백: 가장 만만한 image
                    v = f"image:{available_images[(idx + k) % len(available_images)]}"
                    pending_keywords.append(f"{slug} {idx}/{k}: {c[:30]}")
                used.add(v)
                # parse type:value
                t, val = v.split(":", 1)
                visuals.append({"type": t, "value": val})
            tts = body

        lines, emph = parse_headline(card.get("headline", ""))
        d = {
            "tts": tts,
            "caption_body": lines[:2] if len(lines) >= 2 else (lines + [""])[:2],
            "caption_emphasis": emph,
            "headline_lines": [
                {"text": lines[0] if lines else ""},
                {"text": lines[1] if len(lines) > 1 else "", "accent": True},
            ],
            "meta": card.get("source", src_short),
            "topic": "뉴스",
            "background_image": available_images[idx % len(available_images)],
            "caption_chunks": chunks,
            "chunk_visuals": visuals,
            "stat": {"label": "", "value": "", "note": ""},
        }
        if is_cta:
            d["kakao"] = "@휴대폰성지폰스팟"
            d["location"] = "내 손 안의 성지찾기, 폰스팟"
            d["litt"] = "litt.ly/phonespot"
        return d

    n = len(cards)
    hook = build_sec(cards[0], 0, n)
    cta = build_sec(cards[-1], n - 1, n, is_cta=True)
    facts = []
    for i in range(1, n - 1):
        f = build_sec(cards[i], i, n)
        f["id"] = f"fact_{i}"
        facts.append(f)

    script = {
        "slug": slug,
        "title_short": title,
        "video_title": title,
        "publication_date": art.get("publication_date", ""),
        "sources": src_line,
        "channel_name": "휴대폰성지 폰스팟",
        "channel_tagline": "휴대폰성지 IT 브리핑",
        "opening": {"line1": "휴대폰성지 IT 브리핑", "line2": title},
        "hook": hook,
        "facts": facts,
        "cta": cta,
        "_auto_polish": True,
        "_auto_polish_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "_note": "auto_polish.py 자동 매핑 (메모리 패턴 기반). 종민님 검수 권장.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(script, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 신규 일러스트 필요 키워드 로그
    if pending_keywords:
        log = project_root / "pending_illustrations.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"\n# {slug} ({datetime.datetime.now().isoformat()})\n")
            for kw in pending_keywords:
                f.write(f"  - {kw}\n")

    return True, f"OK ({len(facts)+2} sequences, {len(pending_keywords)} pending)"


# 메인: 새 [OK] 슬러그 자동 처리
if __name__ == "__main__":
    force = "--force" in sys.argv
    target_slug = None
    for a in sys.argv[1:]:
        if a != "--force" and not a.startswith("--"):
            target_slug = a
            break

    if target_slug:
        targets = [target_slug]
    else:
        # 새 [OK] 슬러그 자동 감지
        targets = []
        for art in articles_dir.glob("*.json"):
            slug = art.stem
            try:
                j = json.load(open(art, encoding="utf-8"))
                if not isinstance(j.get("cards"), list) or len(j["cards"]) < 2:
                    continue
            except Exception:
                continue
            if not (images_dir / slug).exists():
                continue
            out = output_dir / slug / "shorts_script.json"
            if force or not out.exists():
                targets.append(slug)

    print(f"[auto_polish] target slugs: {len(targets)}")
    for slug in targets:
        ok, msg = auto_polish(slug, force=force)
        flag = "[OK]" if ok else "[SKIP]"
        print(f"  {flag} {slug}: {msg}")
