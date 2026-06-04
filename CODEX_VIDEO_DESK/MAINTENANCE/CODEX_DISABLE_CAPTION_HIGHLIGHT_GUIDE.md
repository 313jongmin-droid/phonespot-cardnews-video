# Codex Caption Display Color Contract

## Decision

Screen-caption text uses one readable text color only.

- Do not infer or render orange inline caption highlights.
- Do not restore legacy yellow inline subtitle highlights.
- Keep PhoneSpot orange for structural brand accents, CTA elements, headers, and infographics.

## Reason

Keyword-based emphasis can color the wrong phrase. When that happens, the emphasis looks like an output error instead of an intentional design choice.

## Install

Run:

`RUN_APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.bat`

This updates the shared Remotion caption components and performs a TypeScript check.
