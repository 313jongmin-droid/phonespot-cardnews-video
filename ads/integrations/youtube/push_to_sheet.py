"""Push YouTube Analytics results to the managed sheet, tab '유튜브'.

Policy (per ads/MANUAL.md + sheet_structure.md):
  - '유튜브' sheet, columns A:I are the SNS log area
  - A date / B format / C topic / D link / E views / F likes / G subs / H memo / I note
  - K~P is auto-aggregated by sheet formulas -> NEVER touch
  - H is user-entered free text -> never overwrite

Dedup key: video_id extracted from column D (https://youtu.be/<video_id>).
  If video_id already in sheet: update E,F,G,I only (preserve A,B,C,D,H).
  If new: append a new row with A..G and I (H left blank).

Auth: service account JSON at _secrets/sheets_service_account.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent
_DEFAULT_SA = _PROJECT_ROOT / "_secrets" / "sheets_service_account.json"
_DEFAULT_SHEET_ID = "1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI"
_DEFAULT_TAB = "유튜브"

DATA_START_ROW = 2
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import fetch_analytics  # noqa: E402


class SheetPushError(RuntimeError):
    pass


def iso8601_duration_seconds(s):
    if not s:
        return 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    se = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + se


def format_iso_to_kdate(s):
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        return s[:10]


def extract_video_id_from_url(url):
    if not url:
        return ""
    m = re.search(r"youtu\.be/([A-Za-z0-9_\-]{8,})", url)
    if m:
        return m.group(1)
    m = re.search(r"youtube\.com/shorts/([A-Za-z0-9_\-]{8,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]v=([A-Za-z0-9_\-]{8,})", url)
    if m:
        return m.group(1)
    return ""


def build_sheet_service(sa_path):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as e:
        raise SheetPushError(
            "google-auth libs missing. pip install google-api-python-client google-auth (%s)" % e
        )
    if not sa_path.exists():
        raise SheetPushError(
            "Service account JSON not found: %s. Place at _secrets/sheets_service_account.json"
            % sa_path
        )
    creds = service_account.Credentials.from_service_account_file(
        str(sa_path), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def get_channel_subscribers(channel_id):
    creds_path = _PROJECT_ROOT / "upload" / "tokens" / "yt_analytics_token.json"
    cs_path = _PROJECT_ROOT / "upload" / "tokens" / "yt_client_secret.json"
    creds = fetch_analytics._build_credentials(cs_path, creds_path)
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=creds)
    r = youtube.channels().list(part="statistics", id=channel_id).execute()
    items = r.get("items", [])
    if not items:
        return 0
    return int(items[0]["statistics"].get("subscriberCount", 0))


def read_existing_rows(sheet_svc, spreadsheet_id, tab):
    rng = "%s!A%d:I" % (tab, DATA_START_ROW)
    r = sheet_svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=rng,
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()
    return r.get("values", [])


def build_video_id_to_row_index(existing_rows):
    out = {}
    for i, row in enumerate(existing_rows):
        if len(row) < 4:
            continue
        link = row[3] if row[3] else ""
        vid = extract_video_id_from_url(str(link))
        if vid:
            out[vid] = DATA_START_ROW + i
    return out


def format_for_sheet(v, subscribers):
    vid = v.get("video_id", "")
    dur_sec = iso8601_duration_seconds(v.get("duration_iso", ""))
    is_short = dur_sec > 0 and dur_sec <= 60

    a_date = format_iso_to_kdate(v.get("published_at", ""))
    b_format = "네이티브_쇼츠" if is_short else "네이티브_피드"
    c_topic = v.get("title", "")[:80]
    d_link = "https://youtu.be/" + vid if vid else ""
    e_views = int(v.get("views", 0))
    f_likes = int(v.get("likes", 0))
    g_subs = int(subscribers or 0)

    avg_pct = v.get("avg_view_percentage", 0)
    avg_dur = v.get("avg_view_duration_sec", 0)
    i_note = ""
    if avg_pct or avg_dur:
        i_note = "%.0f%% retention - %.0fs - cmt%d" % (
            avg_pct, avg_dur, int(v.get("comments", 0))
        )
    return [a_date, b_format, c_topic, d_link, e_views, f_likes, g_subs, i_note]


def apply_updates(sheet_svc, spreadsheet_id, tab, updates):
    if not updates:
        return 0
    data = []
    for row_num, cells in updates:
        a_g = cells[:7]
        i_only = [cells[7]]
        data.append({
            "range": "%s!A%d:G%d" % (tab, row_num, row_num),
            "majorDimension": "ROWS",
            "values": [a_g],
        })
        data.append({
            "range": "%s!I%d:I%d" % (tab, row_num, row_num),
            "majorDimension": "ROWS",
            "values": [i_only],
        })
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    sheet_svc.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()
    return len(updates)


def apply_appends(sheet_svc, spreadsheet_id, tab, appends):
    if not appends:
        return 0
    rows = []
    for cells in appends:
        row = list(cells[:7]) + [""] + [cells[7]]
        rows.append(row)
    body = {"majorDimension": "ROWS", "values": rows}
    sheet_svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="%s!A:I" % tab,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    return len(appends)


def main():
    p = argparse.ArgumentParser(description="Push YouTube Analytics to managed sheet")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--max-videos", type=int, default=200)
    p.add_argument("--spreadsheet-id", default=_DEFAULT_SHEET_ID)
    p.add_argument("--tab", default=_DEFAULT_TAB)
    p.add_argument("--sa-path", default=str(_DEFAULT_SA))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("[1/4] fetching YouTube analytics...", file=sys.stderr)
    data = fetch_analytics.fetch_all(days=args.days, max_videos=args.max_videos)
    videos = data.get("videos", [])
    channel_id = data.get("channel_id", "")
    channel_title = data.get("channel_title", "")
    print("  channel: %s (%d videos)" % (channel_title, len(videos)), file=sys.stderr)
    if not videos:
        print("[STOP] no videos", file=sys.stderr)
        return 0

    print("[2/4] fetching subscriber count...", file=sys.stderr)
    try:
        subs = get_channel_subscribers(channel_id)
        print("  subscribers: %d" % subs, file=sys.stderr)
    except Exception as e:
        print("  [WARN] sub fetch failed (%s)" % e, file=sys.stderr)
        subs = 0

    print("[3/4] reading existing sheet rows...", file=sys.stderr)
    sheet_svc = build_sheet_service(Path(args.sa_path))
    existing = read_existing_rows(sheet_svc, args.spreadsheet_id, args.tab)
    vid_to_row = build_video_id_to_row_index(existing)
    print("  existing rows: %d, video_ids: %d"
          % (len(existing), len(vid_to_row)), file=sys.stderr)

    updates = []
    appends = []
    for v in videos:
        vid = v.get("video_id", "")
        if not vid:
            continue
        cells = format_for_sheet(v, subs)
        if vid in vid_to_row:
            updates.append((vid_to_row[vid], cells))
        else:
            appends.append(cells)

    print("[4/4] planned: %d updates, %d appends"
          % (len(updates), len(appends)), file=sys.stderr)

    if args.dry_run:
        print("\n[DRY-RUN] sample (max 5):", file=sys.stderr)
        for cells in appends[:5]:
            print("  APPEND:", cells, file=sys.stderr)
        for row_num, cells in updates[:5]:
            print("  UPDATE row %d:" % row_num, cells, file=sys.stderr)
        print("\n[DRY-RUN] not writing.", file=sys.stderr)
        return 0

    n_up = apply_updates(sheet_svc, args.spreadsheet_id, args.tab, updates)
    n_ap = apply_appends(sheet_svc, args.spreadsheet_id, args.tab, appends)
    print("\n[OK] updates=%d  appends=%d" % (n_up, n_ap), file=sys.stderr)

    print(json.dumps({
        "channel_id": channel_id,
        "channel_title": channel_title,
        "subscribers": subs,
        "videos_processed": len(videos),
        "updates": n_up,
        "appends": n_ap,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
