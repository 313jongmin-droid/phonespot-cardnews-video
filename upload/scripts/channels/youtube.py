"""YouTube Data API v3 - Shorts upload.

Setup (one-time, user does this):
  1) https://console.cloud.google.com/ -> new project
  2) Enable "YouTube Data API v3"
  3) Create OAuth 2.0 Client ID (Desktop application)
  4) Download client_secret.json -> save as upload/tokens/yt_client_secret.json
  5) First run opens browser for OAuth consent (one-time)
     Token cached at upload/tokens/yt_token.json (refresh_token used after)

Shorts criteria:
  - Video <= 60 seconds
  - 9:16 aspect ratio (e.g. 1080x1920)
  - Adding #Shorts to title/description is recommended

Quota:
  - Daily total 10,000
  - videos.insert costs 1,600 -> max 6 uploads/day
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from caption_parser import parse_captions_file, substitute_tokens  # noqa: E402


YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_TITLE_CHARS = 100
MAX_DESCRIPTION_CHARS = 5000
MAX_TAG_CHARS = 30
MAX_TAGS_TOTAL_CHARS = 500
DEFAULT_CATEGORY_ID = "22"  # People & Blogs


class YouTubeError(RuntimeError):
    pass


def _truncate_title(line: str) -> str:
    """Trim a first-line candidate down to <=100 chars without cutting mid-word too crudely."""
    line = line.strip()
    if len(line) <= MAX_TITLE_CHARS:
        return line
    cut = line[:MAX_TITLE_CHARS].rstrip()
    # Avoid trailing partial bracket characters
    for ch in ("】", "[", "(", "·", "-"):
        if cut.endswith(ch):
            cut = cut[:-1].rstrip()
    return cut


def _extract_metadata(text: str) -> dict:
    """Pull title (first non-empty line), tags (hashtag line), and description (full body)."""
    lines = [ln for ln in text.splitlines()]
    # First non-empty line as title candidate
    title_raw = ""
    for ln in lines:
        if ln.strip():
            title_raw = ln.strip()
            break
    title = _truncate_title(title_raw)

    # Hashtag line: scan from bottom for a line starting with '#' that has multiple tags
    tags = []
    for ln in reversed(lines):
        s = ln.strip()
        if s.startswith("#") and s.count("#") >= 2:
            for tok in re.findall(r"#([\w가-힣\d_]+)", s):
                if len(tok) <= MAX_TAG_CHARS:
                    tags.append(tok)
            break

    # Enforce total tag chars
    acc = 0
    pruned = []
    for t in tags:
        if acc + len(t) + 1 > MAX_TAGS_TOTAL_CHARS:
            break
        pruned.append(t)
        acc += len(t) + 1
    tags = pruned

    description = text.strip()
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS - 1] + "…"

    return {"title": title, "description": description, "tags": tags}


def _build_credentials(client_secrets_path: Path, token_cache_path: Path):
    """Build OAuth credentials. First call opens browser; subsequent calls refresh silently."""
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError as e:
        raise YouTubeError(
            "google-auth libs missing. pip install google-api-python-client "
            "google-auth google-auth-oauthlib google-auth-httplib2 (%s)" % e
        )

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
        raise YouTubeError(
            "client_secret JSON not found: %s\n"
            "Download from Google Cloud Console OAuth client and place at that path."
            % client_secrets_path
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path), YT_SCOPES
    )
    creds = flow.run_local_server(port=0)
    token_cache_path.parent.mkdir(parents=True, exist_ok=True)
    token_cache_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_short(
    video_path,
    title: str,
    description: str,
    tags,
    privacy: str = "public",
    category_id: str = DEFAULT_CATEGORY_ID,
    client_secrets_path = None,
    token_cache_path = None,
) -> str:
    """Upload a video as a Short. Returns video_id."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise YouTubeError("video file not found: %s" % video_path)

    # Defaults: upload/tokens/yt_client_secret.json and upload/tokens/yt_token.json
    upload_root = _HERE.parent.parent  # upload/
    if client_secrets_path is None:
        client_secrets_path = upload_root / "tokens" / "yt_client_secret.json"
    if token_cache_path is None:
        token_cache_path = upload_root / "tokens" / "yt_token.json"

    creds = _build_credentials(Path(client_secrets_path), Path(token_cache_path))

    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from googleapiclient.errors import HttpError  # type: ignore
    except ImportError as e:
        raise YouTubeError("google-api-python-client missing (%s)" % e)

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

    try:
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
        video_id = response.get("id", "")

        # Post-upload hook: 시트 sync + 가이드 갱신 (실패해도 throw 안 함)
        if video_id:
            _run_post_upload_hooks()
        return video_id
    except HttpError as e:
        raise YouTubeError("YouTube API error: %s" % e)


def _run_post_upload_hooks():
    """업로드 직후 자동: push_to_sheet.py + analyze_patterns.py 호출.
    영상 업로드 후 시트는 즉시 sync, 가이드는 D-2 이상 영상만 보니까 새 영상 영향 X."""
    import subprocess
    project_root = _HERE.parent.parent.parent  # phonespot_cardnews/
    scripts = [
        project_root / "ads" / "integrations" / "youtube" / "push_to_sheet.py",
        project_root / "ads" / "integrations" / "youtube" / "analyze_patterns.py",
    ]
    for s in scripts:
        if not s.exists():
            print("[post-hook] skip (not found): %s" % s.name, file=sys.stderr)
            continue
        try:
            subprocess.run(
                [sys.executable, str(s)],
                cwd=str(project_root),
                check=False,
                timeout=300,
            )
            print("[post-hook] %s OK" % s.name, file=sys.stderr)
        except Exception as e:
            print("[post-hook] %s failed: %s" % (s.name, e), file=sys.stderr)


def publish_from_slug(slug: str, assets_root, dry_run: bool = False, privacy: str = "public") -> dict:
    """Entry point for orchestrator.

    Reads captions.md youtube section -> extracts metadata.
    Reads output/<slug>/video.mp4. Uploads as Short.
    """
    assets_root = Path(assets_root)
    captions_md = assets_root / "output" / slug / "captions.md"
    if not captions_md.exists():
        raise YouTubeError("captions.md not found: %s" % captions_md)
    video_path = assets_root / "output" / slug / "video.mp4"

    all_caps = parse_captions_file(captions_md)
    if "youtube" not in all_caps:
        raise YouTubeError(
            "no 'youtube' section in captions.md. Found: %s" % list(all_caps.keys())
        )
    text = substitute_tokens(all_caps["youtube"])
    meta = _extract_metadata(text)

    # Auto-append #Shorts to title if not present and there's room
    if "#shorts" not in meta["title"].lower() and len(meta["title"]) + 8 <= MAX_TITLE_CHARS:
        meta["title"] = meta["title"] + " #Shorts"

    result = {
        "slug": slug,
        "captions_md": str(captions_md),
        "video_path": str(video_path),
        "video_exists": video_path.exists(),
        "title": meta["title"],
        "title_chars": len(meta["title"]),
        "description_chars": len(meta["description"]),
        "tags": meta["tags"],
        "tag_count": len(meta["tags"]),
        "dry_run": dry_run,
    }

    if dry_run:
        return result

    if not video_path.exists():
        raise YouTubeError(
            "video.mp4 not found at %s -- SHORTS task must produce it first" % video_path
        )

    video_id = upload_short(
        video_path,
        title=meta["title"],
        description=meta["description"],
        tags=meta["tags"],
        privacy=privacy,
    )
    result["video_id"] = video_id
    result["url"] = "https://youtu.be/" + video_id if video_id else None
    return result


if __name__ == "__main__":
    import argparse, json

    p = argparse.ArgumentParser(description="YouTube Shorts upload")
    p.add_argument("--slug", required=True)
    p.add_argument(
        "--assets-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="phonespot_cardnews root",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--privacy", default="public", choices=["public", "unlisted", "private"]
    )
    args = p.parse_args()

    out = publish_from_slug(args.slug, args.assets_root, dry_run=args.dry_run, privacy=args.privacy)
    print(json.dumps(out, ensure_ascii=False, indent=2))
