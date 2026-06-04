"""Entry point for analyze_patterns.py (main 부분이 host file-size limit 로 잘려서 분리)."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import analyze_patterns as ap


def run(dry_run: bool = False, exclude_days: int = None):
    if exclude_days is None:
        exclude_days = ap.EXCLUDE_RECENT_DAYS

    print("[1/4] sheet read...", file=sys.stderr)
    rows = ap.read_sheet_rows(
        ap._DEFAULT_SA, ap._DEFAULT_SHEET_ID, ap._DEFAULT_TAB
    )
    print("  total %d rows" % len(rows), file=sys.stderr)

    print("[2/4] filter (D-%d+)..." % exclude_days, file=sys.stderr)
    kept, recent, invalid = ap.filter_for_analysis(rows, exclude_days)
    print(
        "  target: %d (excluded recent %d, invalid %d)"
        % (len(kept), len(recent), len(invalid)),
        file=sys.stderr,
    )

    print("[3/4] analyze...", file=sys.stderr)
    analysis = ap.analyze(kept)

    print("[4/4] render guide...", file=sys.stderr)
    guide_md = ap.render_guide(analysis, len(recent), len(invalid))

    if dry_run:
        print(guide_md)
        return

    ap._GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ap._GUIDE_PATH.write_text(guide_md, encoding="utf-8")
    ap._DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    ap._DATA_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "exclude_days": exclude_days,
                "excluded_recent": len(recent),
                "excluded_invalid": len(invalid),
                "analysis": analysis,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("[OK] guide: %s" % ap._GUIDE_PATH, file=sys.stderr)
    print("[OK] data: %s" % ap._DATA_PATH, file=sys.stderr)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--exclude-days", type=int, default=None)
    args = p.parse_args()
    run(dry_run=args.dry_run, exclude_days=args.exclude_days)
