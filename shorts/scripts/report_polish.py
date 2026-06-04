"""오늘 자동 박힌 슬러그 청크 매핑을 텔레그램으로 리포트.

scripts/telegram_notify.py 의 send() 활용. 카드뉴스 시스템과 동일 봇 (@PLauto_claude_bot).

사용:
  python scripts/report_polish.py        # 오늘 _auto_polish 된 슬러그 전체
  python scripts/report_polish.py <slug> # 특정 슬러그

종민님 새벽 자동화 직후 호출. 아침에 폰에서 매핑 확인.
"""
import json
import sys
import datetime
from pathlib import Path

# 카드뉴스 시스템의 telegram_notify 모듈 활용
project_root = Path(__file__).parent.parent
repo_root = project_root.parent  # phonespot_cardnews/
cardnews_root = repo_root / "cardnews"  # phonespot_cardnews/cardnews/
sys.path.insert(0, str(repo_root / "automation" / "scripts"))  # telegram_notify, chrome_chatgpt

try:
    from telegram_notify import send  # type: ignore
except ImportError:
    def send(msg):
        print(f"[telegram disabled] {msg[:200]}")
        return False

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

output_dir = cardnews_root / "output"
pending_log = project_root / "pending_illustrations.log"


def format_chunk_visuals(chunks, visuals):
    """청크별 매핑을 짧은 텍스트로."""
    out = []
    for k, (c, v) in enumerate(zip(chunks, visuals), 1):
        t = v.get("type")
        val = v.get("value")
        if t == "image":
            vstr = f"📷 {val}"
        elif t == "illust":
            vstr = f"🎨 {val}"
        elif t == "mascot":
            vstr = f"😀 {val}"
        elif t == "stat":
            num = val.get("number", "") if isinstance(val, dict) else ""
            vstr = f"🔢 {num}"
        elif t == "compare":
            vstr = "↔ compare"
        elif t == "timeline":
            n = len((val or {}).get("items", []))
            vstr = f"📅 timeline×{n}"
        elif t == "calendar":
            d = (val or {}).get("day", "")
            vstr = f"📆 {d}"
        elif t == "bankaccount":
            a = (val or {}).get("amount", "")
            vstr = f"💰 ₩{a}"
        elif t == "logo":
            vstr = "🏷 logo"
        elif t == "pricebar":
            vstr = "💱 pricebar"
        else:
            vstr = t
        # 청크 텍스트 짧게 (40자)
        ct = c if len(c) <= 40 else c[:38] + "…"
        out.append(f"  {k}. {ct}\n     → {vstr}")
    return "\n".join(out)


def report_slug(slug):
    sp = output_dir / slug / "shorts_script.json"
    if not sp.exists():
        return None
    j = json.load(open(sp, encoding="utf-8"))

    lines = []
    lines.append(f"<b>📌 {slug}</b>")
    lines.append(f"제목: {j.get('video_title', '')}")
    lines.append("")

    labels = ["HOOK"] + [f"FACT{i}" for i in range(1, len(j.get("facts", []))+1)] + ["CTA"]
    all_secs = [j.get("hook", {})] + j.get("facts", []) + [j.get("cta", {})]

    for lbl, sec in zip(labels, all_secs):
        chunks = sec.get("caption_chunks", [])
        visuals = sec.get("chunk_visuals", [])
        if not chunks:
            continue
        lines.append(f"<b>[{lbl}]</b>")
        lines.append(format_chunk_visuals(chunks, visuals))
        lines.append("")

    # 통계
    from collections import Counter
    types = Counter(cv.get("type") for s in all_secs for cv in s.get("chunk_visuals", []))
    lines.append(f"<i>합계: {dict(types)}</i>")
    if j.get("_auto_polish"):
        lines.append("⚠️ 자동 매핑 (검수 권장)")

    return "\n".join(lines)


def main():
    targets = sys.argv[1:]
    if not targets:
        # 오늘 _auto_polish 된 슬러그 (최근 6시간 내)
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=6)
        targets = []
        for d in output_dir.iterdir():
            if not d.is_dir():
                continue
            sp = d / "shorts_script.json"
            if not sp.exists():
                continue
            try:
                j = json.load(open(sp, encoding="utf-8"))
                if not j.get("_auto_polish"):
                    continue
                ts = j.get("_auto_polish_at", "")
                if ts:
                    polished_at = datetime.datetime.fromisoformat(ts)
                    if polished_at < cutoff:
                        continue
                targets.append(d.name)
            except Exception:
                continue

    if not targets:
        print("[report] 오늘 박힌 자동 슬러그 없음")
        return

    # 헤더
    header = f"🎬 <b>새벽 영상 매핑 리포트</b>\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n슬러그 {len(targets)}개\n"
    send(header)

    # 슬러그별 메시지 (텔레그램 4096자 한도)
    for slug in targets:
        msg = report_slug(slug)
        if msg:
            if len(msg) > 3800:
                msg = msg[:3800] + "\n…(중략)"
            send(msg)

    # pending 일러스트 알림
    if pending_log.exists():
        content = pending_log.read_text(encoding="utf-8").strip()
        if content:
            send(f"⚠️ <b>신규 일러스트 필요</b>\n<pre>{content[-3500:]}</pre>")


if __name__ == "__main__":
    main()
