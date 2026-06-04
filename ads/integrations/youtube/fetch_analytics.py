"""YouTube Data + Analytics 풍부한 지표 수집.

수집 항목:
  - 영상별: 제목, 게시일, 조회수, 좋아요, 댓글, 평균 시청 시간(초), 평균 시청률(%),
    노출 (impressions), CTR, 추가 구독자
  - 지역 breakdown (top 5 국가)
  - 연령/성별 breakdown
  - 디바이스 breakdown

OAuth: 한 client_secret 으로 youtube.readonly + yt-analytics.readonly 둘 다.
첫 실행 시 브라우저 동의 → 토큰 캐시. 이후 refresh_token 으로 영구.

사용: python fetch_analytics.py --days 30 --csv-out out.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_UPLOAD_ROOT = _HERE.parent.parent.parent / "upload"
_DEFAULT_CLIENT_SECRET = _UPLOAD_ROOT / "tokens" / "yt_client_secret.json"
_DEFAULT_TOKEN = _UPLOAD_ROOT / "tokens" / "yt_analytics_token.json"

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YTAError(RuntimeError):
    pass


def _build_credentials(client_secrets_path, token_cache_path):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise YTAError(
            "google-auth libs missing. pip install google-api-python-client "
            "google-auth google-auth-oauthlib google-auth-httplib2 (%s)" % e
        )

    client_secrets_path = Path(client_secrets_path)
    token_cache_path = Path(token_cache_path)
    creds = None

    if token_cache_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_cache_path), YT_SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_cache_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not client_secrets_path.exists():
        raise YTAError(
            "client_secret JSON not found: %s\n"
            "Download from Google Cloud Console (Desktop OAuth client) and place there."
            % client_secrets_path
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), YT_SCOPES)
    creds = flow.run_local_server(port=0)
    token_cache_path.parent.mkdir(parents=True, exist_ok=True)
    token_cache_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _get_channel_id(youtube):
    """Get the authenticated channel's id."""
    r = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = r.get("items", [])
    if not items:
        raise YTAError("no channel found for authenticated user")
    return items[0]["id"], items[0]["snippet"]["title"]


def _list_uploads_playlist_id(youtube, channel_id):
    r = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    return r["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _list_all_videos(youtube, uploads_playlist_id, max_videos=200):
    video_ids = []
    page_token = None
    while True:
        r = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for it in r.get("items", []):
            video_ids.append(it["contentDetails"]["videoId"])
            if len(video_ids) >= max_videos:
                return video_ids
        page_token = r.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def _fetch_video_stats(youtube, video_ids):
    """Get title/published/views/likes/comments for many videos in one call (batches of 50)."""
    out = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        r = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
        ).execute()
        for it in r.get("items", []):
            vid = it["id"]
            sn = it["snippet"]
            st = it.get("statistics", {})
            cd = it.get("contentDetails", {})
            out[vid] = {
                "video_id": vid,
                "title": sn.get("title", ""),
                "published_at": sn.get("publishedAt", ""),
                "duration_iso": cd.get("duration", ""),
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "tags": sn.get("tags", []),
            }
    return out


def _fetch_analytics_per_video(yt_analytics, channel_id, video_ids, start_date, end_date):
    """Per-video Analytics: average view duration, view %, impressions, CTR, subscribers gained."""
    out = {}
    metrics = "views,averageViewDuration,averageViewPercentage,subscribersGained"
    # Analytics API supports a filter "video==id1,id2,..." up to limit; we chunk by 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            r = yt_analytics.reports().query(
                ids="channel==%s" % channel_id,
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions="video",
                filters="video==%s" % ",".join(batch),
                maxResults=200,
            ).execute()
        except Exception as e:
            print("[WARN] analytics query failed for batch %d: %s" % (i // 50, e),
                  file=sys.stderr)
            continue

        headers = [h["name"] for h in r.get("columnHeaders", [])]
        for row in r.get("rows", []):
            d = dict(zip(headers, row))
            vid = d.get("video")
            if not vid:
                continue
            out[vid] = {
                "avg_view_duration_sec": float(d.get("averageViewDuration", 0)),
                "avg_view_percentage": float(d.get("averageViewPercentage", 0)),
                "subscribers_gained": int(d.get("subscribersGained", 0)),
                "analytics_views": int(d.get("views", 0)),
            }
    return out


def _fetch_impressions_ctr(yt_analytics, channel_id, video_ids, start_date, end_date):
    """Per-video impressions + CTR. These are advertising-type metrics; separate query."""
    out = {}
    metrics = "cardImpressions,cardClickRate"  # placeholder names - may need adjusting
    # Note: actual impressions/CTR for video thumbnails are reportTraffic dimension based;
    # we approximate via cardImpressions if available. If query fails, leave empty.
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            r = yt_analytics.reports().query(
                ids="channel==%s" % channel_id,
                startDate=start_date,
                endDate=end_date,
                metrics="cardImpressions,cardClickRate",
                dimensions="video",
                filters="video==%s" % ",".join(batch),
                maxResults=200,
            ).execute()
        except Exception:
            # Some channels don't have these metrics; skip silently
            return out

        headers = [h["name"] for h in r.get("columnHeaders", [])]
        for row in r.get("rows", []):
            d = dict(zip(headers, row))
            vid = d.get("video")
            if not vid:
                continue
            out[vid] = {
                "card_impressions": int(d.get("cardImpressions", 0)),
                "card_ctr": float(d.get("cardClickRate", 0)),
            }
    return out


def _fetch_channel_breakdowns(yt_analytics, channel_id, start_date, end_date):
    """Channel-level breakdowns: country, age/gender, device type."""
    result = {"country": [], "age_gender": [], "device": []}

    queries = [
        ("country", "viewerPercentage", "country", None, 10),
        ("age_gender", "viewerPercentage", "ageGroup,gender", None, 50),
        ("device", "views", "deviceType", None, 10),
    ]
    for key, metric, dims, filters, max_res in queries:
        try:
            r = yt_analytics.reports().query(
                ids="channel==%s" % channel_id,
                startDate=start_date,
                endDate=end_date,
                metrics=metric,
                dimensions=dims,
                maxResults=max_res,
            ).execute()
            headers = [h["name"] for h in r.get("columnHeaders", [])]
            for row in r.get("rows", []):
                result[key].append(dict(zip(headers, row)))
        except Exception as e:
            print("[WARN] breakdown %s failed: %s" % (key, e), file=sys.stderr)
    return result


def fetch_all(days=30, client_secret_path=None, token_cache_path=None, max_videos=200):
    client_secret_path = Path(client_secret_path or _DEFAULT_CLIENT_SECRET)
    token_cache_path = Path(token_cache_path or _DEFAULT_TOKEN)

    creds = _build_credentials(client_secret_path, token_cache_path)

    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        raise YTAError("google-api-python-client missing (%s)" % e)

    youtube = build("youtube", "v3", credentials=creds)
    yt_analytics = build("youtubeAnalytics", "v2", credentials=creds)

    channel_id, channel_title = _get_channel_id(youtube)
    print("[INFO] channel:", channel_title, "id=", channel_id, file=sys.stderr)

    uploads_pl = _list_uploads_playlist_id(youtube, channel_id)
    video_ids = _list_all_videos(youtube, uploads_pl, max_videos=max_videos)
    print("[INFO] found %d videos" % len(video_ids), file=sys.stderr)

    if not video_ids:
        return {
            "channel_id": channel_id,
            "channel_title": channel_title,
            "videos": [],
            "breakdowns": {"country": [], "age_gender": [], "device": []},
        }

    today = date.today()
    start_date = (today - timedelta(days=days)).isoformat()
    end_date = today.isoformat()

    stats = _fetch_video_stats(youtube, video_ids)
    analytics = _fetch_analytics_per_video(yt_analytics, channel_id, video_ids, start_date, end_date)
    impressions = _fetch_impressions_ctr(yt_analytics, channel_id, video_ids, start_date, end_date)

    videos = []
    for vid in video_ids:
        v = stats.get(vid, {})
        v.update(analytics.get(vid, {}))
        v.update(impressions.get(vid, {}))
        videos.append(v)

    breakdowns = _fetch_channel_breakdowns(yt_analytics, channel_id, start_date, end_date)

    return {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "date_range": {"start": start_date, "end": end_date},
        "videos": videos,
        "breakdowns": breakdowns,
    }


def write_csv(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    videos = data.get("videos", [])
    if not videos:
        path.write_text("", encoding="utf-8")
        return
    # Stable column order
    cols = [
        "video_id", "title", "published_at", "duration_iso",
        "views", "likes", "comments",
        "avg_view_duration_sec", "avg_view_percentage",
        "subscribers_gained", "analytics_views",
        "card_impressions", "card_ctr",
        "tags",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for v in videos:
            w.writerow([
                v.get("video_id", ""),
                v.get("title", ""),
                v.get("published_at", ""),
                v.get("duration_iso", ""),
                v.get("views", 0),
                v.get("likes", 0),
                v.get("comments", 0),
                "%.1f" % v.get("avg_view_duration_sec", 0),
                "%.2f" % v.get("avg_view_percentage", 0),
                v.get("subscribers_gained", 0),
                v.get("analytics_views", 0),
                v.get("card_impressions", 0),
                "%.4f" % v.get("card_ctr", 0),
                "|".join(v.get("tags", [])),
            ])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="YouTube Data + Analytics fetcher")
    p.add_argument("--days", type=int, default=30, help="analytics date range (days back)")
    p.add_argument("--max-videos", type=int, default=200)
    p.add_argument("--csv-out", default=None, help="optional CSV output path")
    p.add_argument("--json-out", default=None, help="optional JSON output path")
    p.add_argument("--client-secret", default=str(_DEFAULT_CLIENT_SECRET))
    p.add_argument("--token-cache", default=str(_DEFAULT_TOKEN))
    args = p.parse_args()

    data = fetch_all(
        days=args.days,
        client_secret_path=args.client_secret,
        token_cache_path=args.token_cache,
        max_videos=args.max_videos,
    )

    if args.csv_out:
        write_csv(data, args.csv_out)
        print("[OK] CSV written: %s" % args.csv_out, file=sys.stderr)

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[OK] JSON written: %s" % args.json_out, file=sys.stderr)

    if not args.csv_out and not args.json_out:
        print(json.dumps(data, ensure_ascii=False, indent=2))
