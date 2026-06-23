# 선호 보이스 (Higgsfield TTS)

> `generate_audio(model=text2speech_v2_elevenlabs, voice_type=preset, voice_id=...)`

| 이름 | gender | voice_id | 용도 메모 |
|---|---|---|---|
| Roman | male | 7e63ac18-5fcd-4aba-8078-a86d4e11c127 | 002 나레이션. 차분한 남성 |

- 한국어: ElevenLabs 다국어 모델이라 한글 텍스트를 읽음. **발음·억양 자연스러움은 종민 청취 확인 필요**(외국 음색 위험).
- 음악=`sonilo_music`(duration 필수) / 효과음=`mirelo_text_to_audio`. 비용 ≈ TTS 0.15cr/문장, BGM ~1cr/15s, SFX 0.5cr.
