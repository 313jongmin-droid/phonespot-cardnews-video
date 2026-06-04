# Codex Fixed Caption Font and Visual Rhythm

## Goal

Keep screen captions readable without shrinking typography or making source images flash past too quickly.

## Contract

- Casual screen-caption typography is fixed at `72px`.
- Long narration is split conservatively at Korean grammar boundaries instead of reducing font size.
- Caption timing follows edge-tts `WordBoundary` metadata.
- Caption windows below `650ms` block rendering. Windows below `1100ms` are reported.
- Visual changes are independent from caption changes and normally hold for about `2.2~4.2s`.
- CTA visuals, illustrations, logos, mascots, and infographics remain static.
- Existing Korean, fixed CTA, TTS-caption lockstep, source-image-once, and illustration contracts remain active.

## Install

Run:

`RUN_APPLY_CODEX_FIXED_CAPTION_RHYTHM.bat`

The installer backs up changed shared files, performs Python syntax checks, and runs TypeScript validation.

## Roll back

If the rendered result is not better, run:

`RUN_ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.bat`

If rollback is clicked before installation, it exits safely with `Nothing to roll back`.
