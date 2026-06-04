

## 34. TTS-caption lockstep
- Display captions are no longer independent summaries.
- Every non-CTA display sequence is rebuilt from its TTS narration in order without omissions or additions.
- Sentence periods may be hidden visually. Pronunciation dictionary changes spoken copy only.
- Existing visual, CTA, Korean, and source-image-once contracts remain active.

## 36. Inline caption highlights are disabled
- Inferred inline caption highlighting looked like an error when keyword matching was inaccurate.
- Keep screen-caption text uniform. Do not restore automatic orange or yellow word coloring.
- Keep PhoneSpot orange for structural brand accents, CTA elements, and infographics.

## 37. Fixed caption font and independent visual rhythm
- Do not shrink Casual screen-caption text to fit a long chunk. Keep 72px typography stable.
- Split long narration conservatively while preserving lossless TTS-caption lockstep and Korean grammar boundaries.
- Caption changes and visual changes use separate timelines. Source images should not flash past because a sentence was split for readability.
- CTA, illustrations, logos, mascots, and infographics stay static.

## 37. Korean caption compiler V2
- Screen captions keep a fixed 72px Pretendard type size.
- Python splitting protects Korean semantic bundles: currency units, legal article references, and model names.
- Remotion line layout uses real browser font measurements instead of raw character counts.
- The runner blocks renders when protected Korean bundles are split.
- Keep V1 backups until 002, 004, 005, and 006 comparison renders are approved.

## 38. Illustration Scout V2
- Scout requests are no longer limited to nine predefined missing files.
- Audit the current semantic visual quality and suggest up to three reusable GPT Plus editorial illustrations per video.
- Prefer broadly reusable concepts. Avoid article-specific dates, prices, names, and logos.
- Existing rendering, source-image-once, CTA, Korean caption, and TTS rules remain unchanged.

## 39. Illustration Scout V2.1 migration pack
- Add reusable data-transfer, messenger-backup, and secure-app-reregistration illustration requests.
- If semantic fallback illustrations remain uncovered, report them instead of silently saying no new image is needed.
- Rendering remains available; uncovered gaps are quality warnings for the next library-growth pass.
