

## 2026-06-01 - TTS-caption lockstep
- Added a shared Korean narration splitter.
- Rebuilt display chunks from section TTS instead of preserving mismatched card-news summaries.
- Added fail-closed validation for TTS/caption/display content equality.

## 2026-06-02 - Inline caption highlights disabled
- Disabled inferred orange highlights in the active Casual Remotion captions.
- Disabled legacy yellow inline subtitle highlights as a fallback safeguard.
- Preserved PhoneSpot orange in brand accents, CTA elements, and infographics.

## 2026-06-02 - Fixed caption font and independent visual rhythm
- Replaced variable Casual caption sizing with a stable 72px size.
- Tightened Korean TTS-caption chunk targets without changing narration content.
- Added TTS WordBoundary timing warnings and a fail-closed lower bound.
- Decoupled source-image dwell time from faster caption changes.

## Korean caption compiler V2
- Applied: 20260602_162829
- Experiment: semantic Korean bundles + Pretendard pixel measurements + fixed 72px captions.
- Rollback: RUN_ROLLBACK_CODEX_KOREAN_CAPTION_COMPILER_V2.bat

## Illustration Scout V2
- Applied: 20260602_192630
- Scope: Scout prompts and illustration tag DB seeds only. Renderer unchanged.
- Rollback: RUN_ROLLBACK_CODEX_ILLUSTRATION_SCOUT_V2.bat

## Illustration Scout V2.1 migration pack
- Applied: 20260602_193815
- Scope: data-transfer reusable prompts and uncovered semantic-gap report.
- Rollback: RUN_ROLLBACK_CODEX_ILLUSTRATION_SCOUT_V21_TRANSFER.bat
