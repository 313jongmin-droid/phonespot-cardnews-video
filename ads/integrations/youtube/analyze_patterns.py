"""YouTube pattern analyzer → content_guide.md. Filters D-2+ videos."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent
_DEFAULT_SA = _PROJECT_ROOT / "_secrets" / "sheets_service_account.json"
_DEFAULT_SHEET_ID = "1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI"
_DEFAULT_TAB = "유튜브"
_GUIDE_DIR = _PROJECT_ROOT / "cardnews" / "_state"
_GUIDE_PATH = _GUIDE_DIR / "content_guide.md"
_DATA_PATH = _GUIDE_DIR / "content_guide_data.json"

DATA_START_ROW = 2
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# 필터: 발행 후 N일 이상 지난 영상만 분석
EXCLUDE_RECENT_DAYS = 2  # D-2 미만 (=48h 미만) 제외

# 키워드 카테고리 (제목 분석용)
# wwdc 카테고리 제거 (apple 의 부분집합 → 중복 카운팅 방지)
KEYWORD_CATEGORIES = {
    "apple": ["apple", "애플", "iphone", "아이폰", "ios", "ipad", "ipados", "wwdc", "siri"],
    "samsung": ["galaxy", "갤럭시", "samsung", "삼성", "one ui", "원ui", "oneui", "z폴드", "z플립", "s26", "s25"],
    "telecom": ["통신", "skt", "kt", "lg u", "공시지원금", "선택약정", "위약금", "요금제", "5g"],
    "security": ["보이스피싱", "스미싱", "사기", "보안", "도난", "잠금", "분실"],
    "ai": ["ai", "인공지능", "지능"],
    "price": ["가격", "할인", "특가", "원", "만원", "비용"],
    "question_hook": ["?", "왜", "어떻게", "vs", "비교", "차이"],
    "urgency": ["오늘", "내일", "지금", "임박", "마감", "급증", "발표"],
    "info_summary": ["정리", "총정리", "총정리한", "요약", "5가지", "정리합니다"],
}

# 카테고리 추천 임계값
MIN_SAMPLE_SIZE = 3  # N < 3 카테고리는 추천에서 제외 (통계적 무의미)


class AnalyzeError(RuntimeError):
    pass


# ============ Sheet I/O ============

def read_sheet_rows(sa_path, spreadsheet_id, tab):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as e:
        raise AnalyzeError(
            "google-auth libs missing. pip install google-api-python-client google-auth (%s)" % e
        )
    if not Path(sa_path).exists():
        raise AnalyzeError("service account JSON not found: %s" % sa_path)

    creds = service_account.Credentials.from_service_account_file(
        str(sa_path), scopes=SCOPES
    )
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

    rng = "%s!A%d:I" % (tab, DATA_START_ROW)
    r = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=rng,
        valueRenderOption="FORMATTED_VALUE",
    ).execute()
    return r.get("values", [])


# ============ Filtering ============

def parse_date(s):
    """시트의 A열은 YYYY-MM-DD 형식 또는 한글 형식."""
    if not s:
        return None
    s = str(s).strip()
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            return None
    # 2026. 6. 2
    m = re.match(r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            return None
    return None


def filter_for_analysis(rows, exclude_days=EXCLUDE_RECENT_DAYS):
    today = datetime.now().date()
    cutoff = today - timedelta(days=exclude_days)
    kept = []
    excluded_recent = []
    excluded_invalid = []
    for row in rows:
        if len(row) < 5:
            excluded_invalid.append(row)
            continue
        pub_date = parse_date(row[0])
        if pub_date is None:
            excluded_invalid.append(row)
            continue
        if pub_date > cutoff:
            excluded_recent.append(row)
        else:
            kept.append((pub_date, row))
    return kept, excluded_recent, excluded_invalid


# ============ Pattern analysis ============

def parse_views(s):
    if s is None:
        return 0
    try:
        return int(str(s).replace(",", ""))
    except ValueError:
        return 0


def parse_retention_from_note(s):
    """I열 비고 형식: '40% retention - 24s - cmt1' → 40.0 반환.
    100 초과는 데이터 이상치로 보고 None 반환 (반복 시청자 등으로 가끔 100+ 나옴)."""
    if not s:
        return None
    m = re.match(r"(\d+)\s*%", str(s))
    if m:
        v = float(m.group(1))
        if v > 100.0:
            # clamp to 100 - 데이터 이상치 (100% 초과는 비정상)
            return 100.0
        return v
    return None


def has_keyword(title, keywords):
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() in title_lower:
            return True
    return False


def has_number(title):
    """제목에 구체 숫자 포함 여부 (단 단순 #Shorts 제외)."""
    cleaned = re.sub(r"#shorts", "", title, flags=re.IGNORECASE)
    return bool(re.search(r"\d", cleaned))


def title_length(title):
    # #Shorts 제외하고 셈
    return len(re.sub(r"#\w+", "", str(title)).strip())


def analyze(rows_filtered):
    """rows_filtered: [(date, row)] — row = [A날짜, B포맷, C주제, D링크, E조회수, F좋아요, G구독자, H메모, I비고]"""
    if not rows_filtered:
        return None

    videos = []
    for pub_date, row in rows_filtered:
        title = str(row[2]) if len(row) > 2 else ""
        link = str(row[3]) if len(row) > 3 else ""
        views = parse_views(row[4]) if len(row) > 4 else 0
        likes = parse_views(row[5]) if len(row) > 5 else 0
        note = str(row[8]) if len(row) > 8 else ""
        retention = parse_retention_from_note(note)
        videos.append({
            "date": pub_date.isoformat(),
            "title": title,
            "link": link,
            "views": views,
            "likes": likes,
            "retention": retention,
        })

    # 정렬 (views 내림차순)
    videos.sort(key=lambda v: v["views"], reverse=True)
    n = len(videos)

    # 상위 25% / 하위 25%
    q = max(1, n // 4)
    top = videos[:q]
    bottom = videos[-q:]

    avg = lambda lst, k: (sum(v[k] for v in lst if v.get(k) is not None) / max(1, len(lst))) if lst else 0
    avg_views_top = avg(top, "views")
    avg_views_bot = avg(bottom, "views")
    avg_views_all = avg(videos, "views")

    median = videos[n // 2]["views"] if n > 0 else 0

    # 키워드별 평균 reach (N<MIN_SAMPLE_SIZE 카테고리는 통계적 무의미라 제외)
    keyword_stats = {}
    for cat, kws in KEYWORD_CATEGORIES.items():
        with_kw = [v for v in videos if has_keyword(v["title"], kws)]
        without_kw = [v for v in videos if not has_keyword(v["title"], kws)]
        if len(with_kw) >= MIN_SAMPLE_SIZE and without_kw:
            keyword_stats[cat] = {
                "count_with": len(with_kw),
                "count_without": len(without_kw),
                "avg_views_with": round(avg(with_kw, "views"), 1),
                "avg_views_without": round(avg(without_kw, "views"), 1),
                "lift_pct": round((avg(with_kw, "views") - avg(without_kw, "views"))
                                  / max(1, avg(without_kw, "views")) * 100, 1),
                "examples_top": [v["title"][:60] for v in with_kw[:2]],
            }

    # 숫자 포함 여부
    with_num = [v for v in videos if has_number(v["title"])]
    without_num = [v for v in videos if not has_number(v["title"])]
    number_stat = None
    if with_num and without_num:
        number_stat = {
            "count_with": len(with_num),
            "count_without": len(without_num),
            "avg_views_with": round(avg(with_num, "views"), 1),
            "avg_views_without": round(avg(without_num, "views"), 1),
            "lift_pct": round((avg(with_num, "views") - avg(without_num, "views"))
                              / max(1, avg(without_num, "views")) * 100, 1),
        }

    # 제목 길이 분포
    length_buckets = {
        "0-20": [], "21-30": [], "31-40": [], "41-50": [], "51+": [],
    }
    for v in videos:
        L = title_length(v["title"])
        if L <= 20: length_buckets["0-20"].append(v)
        elif L <= 30: length_buckets["21-30"].append(v)
        elif L <= 40: length_buckets["31-40"].append(v)
        elif L <= 50: length_buckets["41-50"].append(v)
        else: length_buckets["51+"].append(v)
    length_stat = {
        k: {
            "count": len(vs),
            "avg_views": round(avg(vs, "views"), 1) if vs else 0,
            "reliable": len(vs) >= MIN_SAMPLE_SIZE,
        }
        for k, vs in length_buckets.items()
    }

    # 상위 5편 자동 패턴 추출
    top5_patterns = analyze_top_patterns(top[:5])

    # 시청률 (retention) 데이터가 있는 영상만
    with_ret = [v for v in videos if v.get("retention") is not None]
    avg_retention = round(avg(with_ret, "retention"), 1) if with_ret else None

    return {
        "total_videos": n,
        "avg_views_all": round(avg_views_all, 1),
        "median_views": median,
        "avg_views_top25": round(avg_views_top, 1),
        "avg_views_bot25": round(avg_views_bot, 1),
        "top_videos": [{"title": v["title"], "views": v["views"], "link": v["link"]} for v in top[:5]],
        "bottom_videos": [{"title": v["title"], "views": v["views"], "link": v["link"]} for v in bottom[:5]],
        "top5_patterns": top5_patterns,
        "keyword_stats": keyword_stats,
        "number_stat": number_stat,
        "length_stat": length_stat,
        "avg_retention_pct": avg_retention,
        "retention_sample_size": len(with_ret),
    }


def analyze_top_patterns(top_videos):
    """상위 N편의 자동 패턴 추출 — 키워드 외 형식 특징."""
    if not top_videos:
        return None
    n = len(top_videos)
    emoji_re = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF☀-➿]")
    lengths = [title_length(v["title"]) for v in top_videos]
    emoji_counts = [len(emoji_re.findall(v["title"])) for v in top_videos]
    with_num = sum(1 for v in top_videos if has_number(v["title"]))
    with_compare = sum(1 for v in top_videos
                       if any(w in v["title"] for w in ["vs", "VS", "비교", "차이"]))
    with_question = sum(1 for v in top_videos if "?" in v["title"])
    return {
        "n": n,
        "avg_title_length": round(sum(lengths) / max(1, n), 1),
        "title_length_min": min(lengths) if lengths else 0,
        "title_length_max": max(lengths) if lengths else 0,
        "avg_emoji_count": round(sum(emoji_counts) / max(1, n), 1),
        "videos_with_emoji": sum(1 for c in emoji_counts if c > 0),
        "videos_with_number": with_num,
        "videos_with_compare": with_compare,
        "videos_with_question": with_question,
    }


# ============ Guide rendering ============

def confidence_level(n):
    if n < 50:
        return "낮음 — 참고용 (50+ 권장)"
    elif n < 200:
        return "중간 — 가설 검증 단계"
    elif n < 500:
        return "높음"
    return "매우 높음"


def render_guide(analysis, excluded_recent_n, excluded_invalid_n):
    if analysis is None:
        return "# YouTube 가이드\n\n분석 가능한 영상 없음.\n"

    lines = []
    a = analysis
    lines.append("# 폰스팟 유튜브 콘텐츠 학습 가이드")
    lines.append("")
    lines.append("> 자동 갱신: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("> 표본: %d개 영상 (D-%d 이상 발행분 기준)" % (a["total_videos"], EXCLUDE_RECENT_DAYS))
    lines.append("> 신뢰도: %s" % confidence_level(a["total_videos"]))
    lines.append("> 제외: 최근 %d편 (48h 미만) + 무효 %d편" % (excluded_recent_n, excluded_invalid_n))
    lines.append("")
    lines.append("## 1. 기본 통계")
    lines.append("")
    lines.append("- 전체 평균 조회수: **%.0f회**" % a["avg_views_all"])
    lines.append("- 중앙값: **%d회**" % a["median_views"])
    lines.append("- 상위 25%% 평균: **%.0f회**" % a["avg_views_top25"])
    lines.append("- 하위 25%% 평균: **%.0f회**" % a["avg_views_bot25"])
    if a["avg_retention_pct"] is not None:
        lines.append("- 평균 시청률: **%.1f%%** (표본 %d편)" % (a["avg_retention_pct"], a["retention_sample_size"]))
    lines.append("")

    lines.append("## 2. 키워드 카테고리별 reach")
    lines.append("")
    lines.append("| 카테고리 | 포함 평균 | 미포함 평균 | 리프트 | 예시 |")
    lines.append("|---|---|---|---|---|")
    sorted_kws = sorted(a["keyword_stats"].items(), key=lambda x: -x[1]["lift_pct"])
    for cat, s in sorted_kws:
        examples = " / ".join(s["examples_top"]) if s["examples_top"] else "-"
        lines.append("| `%s` (%d편) | %.0f | %.0f | **%+.0f%%** | %s |" % (
            cat, s["count_with"], s["avg_views_with"], s["avg_views_without"], s["lift_pct"], examples
        ))
    lines.append("")

    if a["number_stat"]:
        s = a["number_stat"]
        lines.append("## 3. 제목 숫자 포함 여부")
        lines.append("")
        lines.append("- 숫자 포함 (%d편): 평균 %.0f회" % (s["count_with"], s["avg_views_with"]))
        lines.append("- 숫자 없음 (%d편): 평균 %.0f회" % (s["count_without"], s["avg_views_without"]))
        lines.append("- 리프트: **%+.0f%%**" % s["lift_pct"])
        lines.append("")

    lines.append("## 4. 제목 길이별 reach")
    lines.append("")
    lines.append("| 길이 | 영상 수 | 평균 조회수 |")
    lines.append("|---|---|---|")
    for k in ["0-20", "21-30", "31-40", "41-50", "51+"]:
        s = a["length_stat"][k]
        lines.append("| %s자 | %d편 | %.0f |" % (k, s["count"], s["avg_views"]))
    lines.append("")

    lines.append("## 5. 상위 5편 (가장 잘 된 영상)")
    lines.append("")
    for v in a["top_videos"]:
        lines.append("- **%d회** — %s" % (v["views"], v["title"][:70]))
    lines.append("")

    lines.append("## 6. 하위 5편 (안 된 영상)")
    lines.append("")
    for v in a["bottom_videos"]:
        lines.append("- **%d회** — %s" % (v["views"], v["title"][:70]))
    lines.append("")

    # 다음 영상 체크리스트 (데이터 기반 자동 생성)
    lines.append("## 7. 다음 영상 작성 체크리스트")
    lines.append("")
    # 리프트 +20% 이상 키워드만 추천
    recommended = [(cat, s) for cat, s in sorted_kws if s["lift_pct"] >= 20]
    avoid = [(cat, s) for cat, s in sorted_kws if s["lift_pct"] <= -20]

    if recommended:
        lines.append("**포함 권장 (리프트 +20% 이상)**:")
        for cat, s in recommended:
            lines.append("- [ ] `%s` 카테고리 키워드 (리프트 %+.0f%%)" % (cat, s["lift_pct"]))
    if avoid:
        lines.append("")
        lines.append("**피하기 (리프트 -20% 이하)**:")
        for cat, s in avoid:
            lines.append("- [ ] `%s` 패턴 회피 (리프트 %+.0f%%)" % (cat, s["lift_pct"]))
    if a["number_stat"] and a["number_stat"]["lift_pct"] >= 10:
        lines.append("")
        lines.append("- [ ] 제목에 구체 숫자 포함 (리프트 %+.0f%%)" % a["number_stat"]["lift_pct"])

    # 최적 제목 길이 (N>=MIN_SAMPLE_SIZE 인 구간만)
    reliable_lengths = {k: v for k, v in a["length_stat"].items() if v.get("reliable")}
    if reliable_lengths:
        best_len = max(reliable_lengths.items(), key=lambda x: x[1]["avg_views"])
        lines.append("")
        lines.append("- [ ] 제목 길이 권장 구간: **%s자** (%d편 평균 %.0f회)"
                     % (best_len[0], best_len[1]["count"], best_len[1]["avg_views"]))
    lines.append("")

    # 상위 5편 자동 패턴 (키워드 외 형식 특징)
    tp = a.get("top5_patterns")
    if tp:
        lines.append("## 8. 상위 5편 자동 패턴 (키워드 외 형식 특징)")
        lines.append("")
        lines.append("- 제목 길이 평균: **%.1f자** (범위 %d~%d자)"
                     % (tp["avg_title_length"], tp["title_length_min"], tp["title_length_max"]))
        lines.append("- 이모지 평균: **%.1f개** (이모지 쓴 영상 %d/%d편)"
                     % (tp["avg_emoji_count"], tp["videos_with_emoji"], tp["n"]))
        lines.append("- 숫자 포함: **%d/%d편**" % (tp["videos_with_number"], tp["n"]))
        lines.append("- 비교(vs/차이): **%d/%d편**" % (tp["videos_with_compare"], tp["n"]))
        lines.append("- 질문(?): **%d/%d편**" % (tp["videos_with_question"], tp["n"]))
        lines.append("")
        lines.append("→ 다음 영상 작성 시 위 형식 특징을 의도적으로 적용해 보기")
    lines.append("")

    # 9. Claude 후보 추천 규칙 (간략판 - size 제약)
    positive_cats = [(c, s) for c, s in sorted_kws if s["lift_pct"] >= 0]
    negative_cats = [(c, s) for c, s in sorted_kws if s["lift_pct"] <= -20]
    lines.append("## 9. Claude 추천 규칙")
    lines.append("")
    lines.append("- 카테고리당 안전 1 + 도전 1 = 최대 2개 후보 제시")
    lines.append("- 안전 = 가이드 패턴 (22자, 이모지, 시의성)")
    lines.append("- 도전 = 새 형식·새 후크 (가이드 외)")
    lines.append("- 사용자 선택 비율: 안전 70 + 도전 30")
    if positive_cats:
        lines.append("- 추천: " + ", ".join([c for c, _ in positive_cats[:5]]))
    if negative_cats:
        lines.append("- 회피: " + ", ".join([c for c, _ in negative_cats]))
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 분석 한계 (정직 표기)")
    lines.append("")
    lines.append("- 표본 %d개. 통계적 유의성 약함 (200+ 권장)" % a["total_videos"])
    lines.append("- 발행 시간/요일/썸네일 같은 변수는 통제 안 됨")
    lines.append("- 상관관계 ≠ 인과관계. 가설 검증 단계로 활용")
    lines.append("- 자동 갱신: 영상 업로드 직후 또는 매일 새벽")
    lines.append("")
    return "\n".join(lines)


# ============ Main ============

def main():
    p = argparse.ArgumentParser(description="YouTube 영상 패턴 분석 → content_guide.md")
    p.add_argument("--spreadsheet-id", default=_DEFAULT_SHEET_ID)
    p.add_argument("--tab", default=_DEFAULT_TAB)
    p.add_argument("--sa-path", default=str(_DEFAULT_SA))
    p.add_argument("--exclude-days", type=int, default=EXCLUDE_RECENT_DAYS)
    p.add_argument("--guide-out", default=str(_GUIDE_PATH))
    p.add_argument("--data-out", default=str(_DATA_PATH))
    p.add_argument("--dry-run", action="store_true", help="stdout only, no file")
    args = p.parse_args()

    print("[1/4] sheet read...", file=sys.stderr)
    rows = read_sheet_rows(args.sa_path, args.spreadsheet_id, args.tab)
    print("  total %d rows" % len(rows), file=sys.stderr)

    print("[2/4] filter (D-%d+)..." % args.exclude_days, file=sys.stderr)
    kept, excluded_recent, excluded_invalid = filter_for_analysis(rows, args.exclude_days)
    print("  analyze target: %d (excluded: recent %d, invalid %d)"
          % (len(kept), len(excluded_recent), len(excluded_invalid)), file=sys.stderr)

    print("[3/4] pattern analyze...", file=sys.stderr)
    analysis = analyze(kept)

    print("[4/4] guide generate...", file=sys.stderr)
    guide_md = render_guide(analysis, len(excluded_recent), len(excluded_invalid))

    if args.dry_run:
        print(guide_md)
        return 0

    Path(args.guide_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.guide_out).write_text(guide_md, encoding="utf-8")
    Path(args.data_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.data_out).write_text(
        json.dumps({
            "generated_at": datetime.now().isoformat(),
            "exclude_days": args.exclude_days,
            "excluded_recent_count": len(excluded_recent),
            "excluded_invalid_count": len(excluded_invalid),
            "analysis": analysis,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("\n[OK] guide: %s" % args.guide_out, file=sys.stderr)
    print("[OK] data backup: %s" % args.data_out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main()) 파일 X")
    args = p.parse_args()

    print("[1/4] 시트 읽기...", file=sys.stderr)
    rows = read_sheet_rows(args.sa_path, args.spreadsheet_id, args.tab)
    print("  총 %d행" % len(rows), file=sys.stderr)

    print("[2/4] 필터링 (D-%d 이상)..." % args.exclude_days, file=sys.stderr)
    kept, excluded_recent, excluded_invalid = filter_for_analysis(rows, args.exclude_days)
    print("  분석 대상: %d편 (제외: 최근 %d, 무효 %d)"
          % (len(kept), len(excluded_recent), len(excluded_invalid)), file=sys.stderr)

    print("[3/4] 패턴 분석...", file=sys.stderr)
    analysis = analyze(kept)

    print("[4/4] 가이드 생성...", file=sys.stderr)
    guide_md = render_guide(analysis, len(excluded_recent), len(excluded_invalid))

    if args.dry_run:
        print(guide_md)
        return 0

    Path(args.guide_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.guide_out).write_text(guide_md, encoding="utf-8")
    Path(args.data_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.data_out).write_text(
        json.dumps({
            "generated_at": datetime.now().isoformat(),
            "exclude_days": args.exclude_days,
            "excluded_recent_count": len(excluded_recent),
            "excluded_invalid_count": len(excluded_invalid),
            "analysis": analysis,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("\n[OK] 가이드 작성: %s" % args.guide_out, file=sys.stderr)
    print("[OK] 데이터 백업: %s" % args.data_out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
