# PhoneSpot Codex Illustration Tag DB

## Purpose

Reduce repetitive illustration choices while preserving accepted render behavior.

## What changes

- Adds tags and keywords for reusable illustration PNG files.
- Records one recent-use snapshot per slug.
- Automatic mappings prefer semantic matches that have appeared less recently.
- GPT Plus illustration requests are recorded in the same history.

## What does not change

- Existing manually curated `chunk_visuals`.
- Screen captions.
- Narration.
- Remotion visual components.
- Claude cardnews folders and runners.

## Install

Double-click:

`RUN_APPLY_CODEX_ILLUSTRATION_TAG_DB.bat`

## Daily controls

Inside:

`C:\backup\phonespot_cardnews\CODEX_VIDEO_DESK`

- `11_OPEN_ILLUSTRATION_TAG_DB.bat`
- `12_REFRESH_ILLUSTRATION_TAG_DB.bat`

## Data files

- `shorts/config/illustration_tag_db.json`
- `shorts/codex/illustration_usage_history.json`
- `shorts/codex/ILLUSTRATION_TAG_DB.md`

Edit tags in JSON when an illustration should serve a broader or narrower topic.

