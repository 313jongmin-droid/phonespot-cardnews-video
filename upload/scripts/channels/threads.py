"""Threads (Meta) text-only publish.

API reference: https://developers.facebook.com/docs/threads/posts

Text-only post flow (2 steps):
  1) Create container:
     POST https://graph.threads.net/v1.0/{user_id}/threads
       ?media_type=TEXT&text={caption}&access_token={token}
     -> creation_id
  2) Publish:
     POST https://graph.threads.net/v1.0/{user_id}/threads_publish
       ?creation_id={creation_id}&access_token={token}
     -> media_id (the published thread)

Limits:
  - Text <= 500 characters
  - Daily limit ~250 posts (per Meta docs)
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests  # type: ignore

# Make sibling imports work whether called as module or script
_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from caption_parser import parse_captions_file, substitute_tokens  # noqa: E402
from utils.env_loader import require_keys  # noqa: E402


THREADS_GRAPH = "https://graph.threads.net/v1.0"
MAX_CAPTION_CHARS = 500


class ThreadsError(RuntimeError):
    pass


def publish_text(user_id: str, access_token: str, text: str, timeout: int = 30) -> str:
    """Publish a text-only thread. Returns the published media id."""
    if not text or not text.strip():
        raise ThreadsError("text is empty")
    if len(text) > MAX_CAPTION_CHARS:
        raise ThreadsError(
            "caption too long: %d > %d chars" % (len(text), MAX_CAPTION_CHARS)
        )

    # 1) Create container
    create_url = "%s/%s/threads" % (THREADS_GRAPH, user_id)
    r = requests.post(
        create_url,
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": access_token,
        },
        timeout=timeout,
    )
    if r.status_code != 200:
        raise ThreadsError(
            "container create failed: HTTP %d %s" % (r.status_code, r.text[:300])
        )
    creation_id = r.json().get("id")
    if not creation_id:
        raise ThreadsError("no creation_id in response: %s" % r.text[:300])

    # 2) Publish
    publish_url = "%s/%s/threads_publish" % (THREADS_GRAPH, user_id)
    r2 = requests.post(
        publish_url,
        params={
            "creation_id": creation_id,
            "access_token": access_token,
        },
        timeout=timeout,
    )
    if r2.status_code != 200:
        raise ThreadsError(
            "publish failed: HTTP %d %s" % (r2.status_code, r2.text[:300])
        )
    media_id = r2.json().get("id")
    if not media_id:
        raise ThreadsError("no media_id in publish response: %s" % r2.text[:300])
    return media_id


def publish_from_slug(slug: str, assets_root, dry_run: bool = False) -> dict:
    """Entry point for orchestrator.

    Reads captions.md, extracts threads section, substitutes tokens, validates
    length. If dry_run, returns the preview dict without calling the API.
    Otherwise reads THREADS_USER_ID and THREADS_ACCESS_TOKEN from env and posts.
    """
    assets_root = Path(assets_root)
    # Real folder layout (2026-05-28 reorg): cardnews/output/<slug>/captions.md
    captions_md = assets_root / "cardnews" / "output" / slug / "captions.md"
    if not captions_md.exists():
        # Fallback to legacy layout (output/<slug>/) if user hasn't migrated
        legacy = assets_root / "output" / slug / "captions.md"
        if legacy.exists():
            captions_md = legacy
        else:
            raise ThreadsError(
                "captions.md not found: %s (also tried %s)" % (captions_md, legacy)
            )

    all_caps = parse_captions_file(captions_md)
    if "threads" not in all_caps:
        raise ThreadsError(
            "no 'threads' section in captions.md. Found: %s"
            % list(all_caps.keys())
        )
    text = substitute_tokens(all_caps["threads"])

    result = {
        "slug": slug,
        "captions_md": str(captions_md),
        "char_count": len(text),
        "within_limit": len(text) <= MAX_CAPTION_CHARS,
        "text_preview": text[:120].replace("\n", " "),
        "dry_run": dry_run,
    }

    if dry_run:
        return result

    keys = require_keys(["THREADS_USER_ID", "THREADS_ACCESS_TOKEN"])
    media_id = publish_text(keys["THREADS_USER_ID"], keys["THREADS_ACCESS_TOKEN"], text)
    result["media_id"] = media_id
    return result


if __name__ == "__main__":
    import argparse, json

    p = argparse.ArgumentParser(description="Threads text-only publish")
    p.add_argument("--slug", required=True)
    p.add_argument(
        "--assets-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="phonespot_cardnews root",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    out = publish_from_slug(args.slug, args.assets_root, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
