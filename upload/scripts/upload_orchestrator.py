"""Upload orchestrator - channel selection + dry-run + sequential publish.

See ../PROJECT_INSTRUCTIONS_UPLOAD.md (section 10) for principles:
  1) Never publish 5 channels simultaneously - one at a time
  2) Preview caption + get explicit user consent before publishing
  3) Always dry-run first
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from caption_parser import parse_captions_file, substitute_tokens  # noqa: E402
from utils.env_loader import load_env  # noqa: E402

SUPPORTED_CHANNELS = ["threads", "instagram", "youtube", "tiktok", "naver_blog"]


def _pick_ext(ratio_dir):
    """Auto-detect card image extension (.jpg / .png / .jpeg)."""
    if not ratio_dir.exists():
        return "jpg"
    for ext in ("jpg", "png", "jpeg"):
        if (ratio_dir / ("card_1." + ext)).exists():
            return ext
    return "jpg"


def _resolve_paths(slug, project_root):
    out = project_root / "output" / slug
    e1 = _pick_ext(out / "1x1")
    e4 = _pick_ext(out / "4x5")
    e9 = _pick_ext(out / "9x16")
    return {
        "output_dir": out,
        "captions_md": out / "captions.md",
        "cards_1x1": [out / "1x1" / ("card_%d.%s" % (i, e1)) for i in range(1, 7)],
        "cards_4x5": [out / "4x5" / ("card_%d.%s" % (i, e4)) for i in range(1, 7)],
        "cards_9x16": [out / "9x16" / ("card_%d.%s" % (i, e9)) for i in range(1, 7)],
        "video_mp4": out / "video.mp4",
        "card_ext_1x1": e1,
        "card_ext_4x5": e4,
        "card_ext_9x16": e9,
    }


def _validate_inputs(channels, paths):
    errors = []
    if not paths["output_dir"].exists():
        errors.append("output dir missing: " + str(paths["output_dir"]))
        return errors
    if not paths["captions_md"].exists():
        errors.append("captions.md missing: " + str(paths["captions_md"]))
    chset = set(channels)
    if chset & {"threads", "instagram"}:
        miss = [p for p in paths["cards_1x1"] if not p.exists()]
        if miss:
            errors.append("1x1 cards missing (%d): %s..." % (len(miss), miss[0].name))
    if chset & {"naver_blog"}:
        miss = [p for p in paths["cards_4x5"] if not p.exists()]
        if miss:
            errors.append("4x5 cards missing (%d): %s..." % (len(miss), miss[0].name))
    if (chset & {"youtube", "tiktok"}) and not paths["video_mp4"].exists():
        errors.append("video.mp4 missing: " + str(paths["video_mp4"]))
    return errors


def main():
    ap = argparse.ArgumentParser(description="Phonespot SNS upload orchestrator")
    ap.add_argument("--slug", required=True, help="slug of output/<slug>/")
    ap.add_argument("--channels", required=True,
                    help="comma-separated. Supported: " + ",".join(SUPPORTED_CHANNELS))
    ap.add_argument("--dry-run", action="store_true",
                    help="validate inputs/captions without calling any API")
    ap.add_argument("--project-root",
                    default=str(Path(__file__).resolve().parents[2]),
                    help="phonespot_cardnews root path")
    args = ap.parse_args()

    load_env()

    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    unknown = [c for c in channels if c not in SUPPORTED_CHANNELS]
    if unknown:
        sys.stderr.write("[ERR] unknown channels: %s\n" % unknown)
        sys.stderr.write("      supported: %s\n" % SUPPORTED_CHANNELS)
        return 2

    project_root = Path(args.project_root).resolve()
    paths = _resolve_paths(args.slug, project_root)

    print("[INFO] slug =", args.slug)
    print("[INFO] project_root =", project_root)
    print("[INFO] output_dir =", paths["output_dir"])
    print("[INFO] channels =", channels)
    print("[INFO] dry-run =", args.dry_run)
    print("[INFO] card ext: 1x1=.%s 4x5=.%s 9x16=.%s" % (
        paths["card_ext_1x1"], paths["card_ext_4x5"], paths["card_ext_9x16"]))

    # For dry-run, allow missing assets (video.mp4 in particular) so we can preview.
    # For real publish, validate strictly.
    if not args.dry_run:
        errs = _validate_inputs(channels, paths)
        if errs:
            sys.stderr.write("\n[ERR] input validation failed:\n")
            for e in errs:
                sys.stderr.write("  - " + e + "\n")
            return 1
        print("\n[OK] inputs validated.")
    else:
        print("\n[DRY-RUN] skipping strict input validation.")

    if paths["captions_md"].exists():
        caps = parse_captions_file(paths["captions_md"])
        print("[INFO] captions.md sections found:", list(caps.keys()))
        for ch in channels:
            if ch not in caps:
                print("  [WARN] section '%s' missing in captions.md" % ch)
                continue
            body = substitute_tokens(caps[ch])
            preview = body[:120].replace("\n", " ")
            print("  [%s] (%d chars) %s..." % (ch, len(body), preview))

    # Channel dispatch
    rc = 0
    for ch in channels:
        print("\n--- channel: %s ---" % ch)
        if ch == "threads":
            try:
                from channels.threads import publish_from_slug as threads_publish
                out = threads_publish(args.slug, project_root, dry_run=args.dry_run)
                if args.dry_run:
                    print("[DRY-RUN OK] threads: %d chars, within_limit=%s"
                          % (out["char_count"], out["within_limit"]))
                else:
                    print("[OK] threads published. media_id=%s" % out.get("media_id"))
            except Exception as e:
                sys.stderr.write("[FAIL] threads: %s\n" % e)
                rc = 3
        elif ch == "youtube":
            try:
                from channels.youtube import publish_from_slug as youtube_publish
                out = youtube_publish(args.slug, project_root, dry_run=args.dry_run)
                if args.dry_run:
                    print("[DRY-RUN OK] youtube: title=%d chars, desc=%d chars, tags=%d, video_exists=%s"
                          % (out["title_chars"], out["description_chars"], out["tag_count"], out["video_exists"]))
                else:
                    print("[OK] youtube uploaded. video_id=%s url=%s"
                          % (out.get("video_id"), out.get("url")))
            except Exception as e:
                sys.stderr.write("[FAIL] youtube: %s\n" % e)
                rc = 3
        else:
            sys.stderr.write("[STUB] '%s' channel publish not implemented yet\n" % ch)

    return rc


if __name__ == "__main__":
    sys.exit(main())
