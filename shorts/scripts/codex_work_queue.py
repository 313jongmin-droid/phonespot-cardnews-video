# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS = ROOT / "cardnews"
ARTICLES = CARDNEWS / "articles"
IMAGES = CARDNEWS / "images"
OUTPUT = CARDNEWS / "output"
DESK = ROOT / "CODEX_VIDEO_DESK"
RESULTS = DESK / "RESULTS"
QUEUE = DESK / "WORK_QUEUE"


COLUMNS = [
    "date",
    "slug",
    "title",
    "article_status",
    "image_status",
    "cardnews_status",
    "video_script_status",
    "illustration_request_status",
    "render_status",
    "review_status",
    "assignee",
    "publish_youtube",
    "publish_instagram",
    "publish_tiktok",
    "result_folder",
    "notes",
    "updated_at",
]

PRESERVE_COLUMNS = {
    "review_status",
    "assignee",
    "publish_youtube",
    "publish_instagram",
    "publish_tiktok",
    "notes",
}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def count_images(slug: str) -> int:
    root = IMAGES / slug
    if not root.exists():
        return 0
    count = 0
    for index in range(1, 6):
        if (root / f"{index}.png").exists() or (root / f"{index}.jpg").exists():
            count += 1
    return count


def count_cards(slug: str) -> int:
    root = OUTPUT / slug
    if not root.exists():
        return 0
    return len(list(root.rglob("card_*.jpg"))) + len(list(root.rglob("card_*.png")))


def article_title(slug: str) -> str:
    data = read_json(ARTICLES / f"{slug}.json")
    return str(data.get("title") or data.get("headline") or "")


def newest_mtime(paths: list[Path]) -> float:
    values = []
    for path in paths:
        try:
            if path.exists():
                values.append(path.stat().st_mtime)
        except OSError:
            pass
    return max(values) if values else 0.0


def render_folder(slug: str) -> str:
    if not RESULTS.exists():
        return ""
    candidates = []
    for path in RESULTS.iterdir():
        if path.is_dir() and slug in path.name:
            mp4 = path / f"{path.name}.mp4"
            if mp4.exists():
                candidates.append(path)
    if not candidates:
        return ""
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return str(latest)


def illustration_status(slug: str) -> str:
    data = read_json(OUTPUT / slug / "codex_illustration_requests.json")
    if not data:
        return "요청서 없음"
    requests = data.get("requests") or []
    gaps = data.get("uncovered_gaps") or []
    if requests:
        return f"신규 {len(requests)}개"
    if gaps:
        return f"경고 {len(gaps)}개"
    return "없음"


def collect_slugs() -> list[str]:
    names: set[str] = set()
    for root in (ARTICLES, IMAGES, OUTPUT):
        if not root.exists():
            continue
        if root == ARTICLES:
            names.update(path.stem for path in root.glob("*.json"))
        else:
            names.update(path.name for path in root.iterdir() if path.is_dir())
    return sorted(names)


def load_existing() -> dict[str, dict]:
    path = QUEUE / "phonespot_work_queue.json"
    rows = read_json(path).get("rows") if path.exists() else []
    if not isinstance(rows, list):
        return {}
    return {str(row.get("slug") or ""): row for row in rows if row.get("slug")}


def row_for(slug: str, existing: dict[str, dict]) -> dict:
    article = ARTICLES / f"{slug}.json"
    image_count = count_images(slug)
    card_count = count_cards(slug)
    out = OUTPUT / slug
    captions = out / "captions.md"
    script = out / "shorts_script.json"
    rendered = render_folder(slug)
    mtime = newest_mtime([article, IMAGES / slug, out, captions, script, Path(rendered) if rendered else out])
    date_text = time.strftime("%Y.%m.%d", time.localtime(mtime)) if mtime else ""

    row = {
        "date": date_text,
        "slug": slug,
        "title": article_title(slug),
        "article_status": "있음" if article.exists() else "없음",
        "image_status": f"{image_count}/5" if image_count else "없음",
        "cardnews_status": f"완료 {card_count}장" if captions.exists() and card_count else ("카드만 있음" if card_count else "대기"),
        "video_script_status": "있음" if script.exists() else "없음",
        "illustration_request_status": illustration_status(slug),
        "render_status": "완료" if rendered else "없음",
        "review_status": "",
        "assignee": "",
        "publish_youtube": "",
        "publish_instagram": "",
        "publish_tiktok": "",
        "result_folder": rendered,
        "notes": "",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    previous = existing.get(slug) or {}
    for column in PRESERVE_COLUMNS:
        if previous.get(column):
            row[column] = previous[column]
    return row


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# PhoneSpot 작업 큐",
        "",
        f"- 생성 시각: {datetime.now().isoformat(timespec='seconds')}",
        f"- 총 항목: {len(rows)}",
        "",
        "| 날짜 | 슬러그 | 카드뉴스 | 영상 | 일러스트 | 검수 | 발행 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows[:80]:
        publish = "/".join([
            row.get("publish_youtube") or "-",
            row.get("publish_instagram") or "-",
            row.get("publish_tiktok") or "-",
        ])
        lines.append(
            "| {date} | `{slug}` | {card} | {video} | {illust} | {review} | {publish} |".format(
                date=row.get("date", ""),
                slug=row.get("slug", ""),
                card=row.get("cardnews_status", ""),
                video=row.get("render_status", ""),
                illust=row.get("illustration_request_status", ""),
                review=row.get("review_status") or "-",
                publish=publish,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def refresh() -> list[dict]:
    existing = load_existing()
    rows = [row_for(slug, existing) for slug in collect_slugs()]
    rows.sort(key=lambda row: (row.get("date") or "", row.get("slug") or ""), reverse=True)
    QUEUE.mkdir(parents=True, exist_ok=True)
    write_json(QUEUE / "phonespot_work_queue.json", {"version": 1, "rows": rows, "updated_at": datetime.now().isoformat(timespec="seconds")})
    write_csv(QUEUE / "phonespot_work_queue.csv", rows)
    write_tsv(QUEUE / "phonespot_work_queue.tsv", rows)
    write_markdown(QUEUE / "phonespot_work_queue.md", rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    rows = refresh()
    print(f"[work_queue] rows={len(rows)}")
    print(f"[work_queue] json={QUEUE / 'phonespot_work_queue.json'}")
    print(f"[work_queue] csv={QUEUE / 'phonespot_work_queue.csv'}")
    print(f"[work_queue] tsv={QUEUE / 'phonespot_work_queue.tsv'}")
    if args.open:
        import os
        os.startfile(QUEUE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
