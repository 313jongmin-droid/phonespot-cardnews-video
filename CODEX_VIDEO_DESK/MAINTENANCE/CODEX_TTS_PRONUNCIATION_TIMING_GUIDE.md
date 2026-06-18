# PhoneSpot Codex TTS Pronunciation + Timing Layer

## Goal

Improve pronunciation and caption/visual transition timing without changing authored narration.

## Safety contract

- `tts` in the cardnews output is never rewritten.
- Screen captions are never rewritten.
- The pronunciation dictionary is applied only to a temporary spoken copy.
- WordBoundary timing is runtime metadata in `shorts/public/shorts_script.json`.
- If WordBoundary data is unavailable, Remotion automatically uses the existing character-weight timing.

## Install

One-time setup: double-click:

`RUN_INSTALL_CODEX_TTS_DESK_BUTTONS.bat`

Then use the operational desk:

`C:\backup\phonespot_cardnews\CODEX_VIDEO_DESK`

Buttons:

- `08_APPLY_TTS_PRONUNCIATION_TIMING.bat`
- `09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat`
- `10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat`

The installer backs up changed shared files, installs the layer, and runs Python and TypeScript checks.

## Edit pronunciation

After installation:

`C:\backup\phonespot_cardnews\shorts\config\tts_pronunciation.json`

Example:

```json
{"match": "WWDC", "spoken": "더블유 더블유 디 씨"}
```

The left side is article text. The right side is speech-only text.

## Inspect one render

Render one familiar slug with:

`C:\backup\phonespot_cardnews\shorts\run_codex_casual.bat`

Inspect:

- Acronym pronunciation.
- Natural narration remains unchanged.
- Screen transition timing feels closer to spoken word boundaries.
- No caption chunk is shorter than roughly one second unless the whole section is very short.

Runtime report:

`C:\backup\phonespot_cardnews\shorts\public\audio\tts_manifest.json`

## Rollback

Every changed shared file receives:

`.bak_tts_timing_YYYYMMDD_HHMMSS`

Restore those files only if the sample narration becomes worse.
