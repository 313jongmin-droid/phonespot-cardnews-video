# QUALITY_RULES

> 렌더·TTS·SNS 업로드 품질 기준. 렌더 후 `verify_video_quality.py`로 자동 검사.

---

## 영상 인코딩 기준

### SNS 호환성
- **픽셀 포맷**: `yuv420p` 필수
  - SNS 플랫폼(인스타·틱톡·유튜브 Shorts)이 다른 포맷이면 안 받거나 재인코딩하면서 품질 저하
  - Remotion 기본값 OK. 별도 옵션 안 건드리면 자동 yuv420p
- **컨테이너**: mp4
- **오디오 코덱**: AAC

### 해상도 / 비율
- **1080×1920** (9:16 세로형)
- **30fps** 또는 60fps (Remotion 기본 30 OK)

### 비트레이트 / 품질
- **Remotion 렌더 CRF 18~20 권장** (낮을수록 고품질, 파일 큼)
- **1080×1920 영상이 5Mbps 이하면 낮은 품질로 간주** → 재렌더
- **50초 내외 쇼츠가 5MB 이하면 비정상** (CRF 너무 높음 또는 인코딩 오류 의심)

---

## TTS 기준

### 엔진
- **edge-tts** 사용 (무료, Microsoft Azure Edge 기반)
- 설치 확인: `py -m pip show edge-tts`

### 기본 보이스
- **`ko-KR-SunHiNeural`** (기본, 여성 자연스러움)

### 보이스 비교용 후보
- `ko-KR-InJoonNeural` (남성)
- `ko-KR-HyunsuNeural` (남성, 다른 톤)

→ 토픽 분위기에 따라 비교 샘플 생성: `py scripts\tts_voice_test.py`

### 속도 (rate)
- **`+35%` ~ `+45%`** 우선 검토
- 너무 빠르면 신뢰감 저하 (광고 톤 느낌)
- 너무 느리면 60초 쇼츠에 콘텐츠 부족

### 볼륨
- React 컴포넌트에서 무리하게 2배 올리지 말 것 (오디오 클리핑 위험)
- 가능하면 **오디오 파일 자체를 loudness normalize** (ffmpeg `loudnorm` 필터)
- 표준 LUFS: -14 LUFS (SNS 일반)

### 청크당 길이
- 1.5~3초 권장
- 5초 초과 청크 = TTS·자막 분할 재검토 필요

---

## 폰트 / 텍스트

### Pretendard 로딩 확인
- 빌드 시 Pretendard CDN(jsdelivr) 또는 로컬 폰트 로딩 확인
- 자막에서 폰트 깨지면 영상 전체 신뢰도 ↓
- 확인 방법: 첫 청크 자막이 정상 폰트로 표시되는지 미리보기

### 자막 가독성
- 글자 크기: 1080×1920에서 70~120px 권장
- stroke 또는 box 배경으로 모든 배경에서 읽힘 보장

---

## 빌드 후 검증 — `verify_video_quality.py`

```cmd
py scripts\verify_video_quality.py <mp4 path>
```

검사 항목 (자동):
- [ ] 픽셀 포맷 = `yuv420p`
- [ ] 해상도 = 1080×1920
- [ ] 길이 = 30~70초 권장 (쇼츠 표준)
- [ ] 비트레이트 ≥ 5 Mbps
- [ ] 파일 크기 ≥ 5 MB (50초 기준)
- [ ] 오디오 트랙 존재 + AAC
- [ ] 첫 프레임 / 마지막 프레임 검은 화면 X

실패 항목 있으면 → 재렌더 또는 재인코딩.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 파일 크기 5MB 미만 | CRF 너무 높음 (저품질) | Remotion config에서 CRF 18~20으로 |
| 인스타 업로드 시 깨짐 | yuv420p 아님 | Remotion 기본값 확인, 커스텀 옵션 X |
| TTS 음량 작음/큼 | normalize 안 됨 | ffmpeg `loudnorm` 필터 적용 |
| TTS 속도 어색 | rate 값 부적절 | +35~+45% 범위 안에서 조정 |
| 자막 폰트 깨짐 | Pretendard 로딩 실패 | 네트워크 / 로컬 폰트 폴백 확인 |
| 첫 프레임 검정 | 인트로 이미지 로딩 지연 | 빌드 전 `copy_assets.py` 완료 확인 |
| 청크 끝 잘림 | 청크 duration 부족 | shorts_script.json `duration_sec` 조정 |
