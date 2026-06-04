# last_review

> 마지막 영상 리뷰 기록. 빌드 후 사장님 검토 결과를 AI 또는 사람이 갱신.

---

```yaml
date:           ""              # 예: 2026-05-28 09:10
slug:           ""              # 예: galaxy_price_hike_europe_2026
reviewed_file:  ""              # 예: out/galaxy_price_hike_europe_2026.mp4
visual_issues:  []              # 시각 이슈 (예: "같은 일러스트 2회 반복", "마스코트 과다")
caption_issues: []              # 자막 이슈 (예: "iOS 단독 분리 됨", "5번째 청크 길이 초과")
tts_issues:     []              # TTS 이슈 (예: "WWDC 발음 어색", "속도 너무 빠름")
encoding_issues: []             # 인코딩 이슈 (예: "비트레이트 4Mbps로 낮음")
overall_verdict: ""             # ok / needs_fix / reject
next_fix:       ""              # 다음 빌드에서 우선 수정할 항목 1~2개
```

---

## 채우기 가이드

- **date** — ISO 형식 (`YYYY-MM-DD HH:MM`)
- **slug / reviewed_file** — 검토 대상 영상
- **issues** — 카테고리별 리스트. 없으면 `[]`. 있으면 짧고 구체적으로
- **overall_verdict**:
  - `ok` — 그대로 발행 가능
  - `needs_fix` — 작은 수정 후 재렌더
  - `reject` — 처음부터 다시 (visual 콘셉트 / 청크 분할 등 근본 문제)
- **next_fix** — 가장 우선 고칠 항목 1~2개. 다음 빌드 사이클의 입력이 됨.

---

## 카테고리별 체크 예시

### visual_issues
- 같은 PNG가 영상 안에서 2회 이상 등장
- 동적 데이터(숫자·날짜)가 PNG에 박혀 있음
- 마스코트가 영상당 3회 이상 등장
- 로고가 잘리거나 비율 깨짐
- 첫/마지막 프레임 검은 화면

### caption_issues
- 영문/숫자 약어 단독 분리 (iOS·NFC·5G 등)
- 청크 길이 25자 초과
- 강조 단어가 청크당 3개 이상 (과다)
- 종결어미 단조로움 ("~합니다" 반복)
- 자막과 TTS 어긋남

### tts_issues
- 약어를 글자 단위로 어색하게 읽음
- 속도가 너무 빠르거나 느림
- 음량이 너무 작거나 클리핑됨
- 보이스 톤이 콘텐츠와 안 맞음

### encoding_issues
- pixel_format ≠ yuv420p
- 비트레이트 < 5 Mbps
- 파일 크기 < 5 MB (50초 기준)
- 해상도 ≠ 1080×1920
- 오디오 트랙 누락

---

## 예시

```yaml
date:           2026-05-28 09:10
slug:           galaxy_price_hike_europe_2026
reviewed_file:  out/galaxy_price_hike_europe_2026.mp4
visual_issues:
  - "calendar.png이 청크 2, 청크 5에서 2회 사용됨"
  - "마스코트가 3회 등장 (1회로 줄이기)"
caption_issues:
  - "청크 7에서 'iOS 26.6'을 'iOS' / '26.6'으로 분리"
tts_issues:
  - "WWDC를 '더블유 더블유 디 씨'로 너무 느리게 읽음"
encoding_issues: []
overall_verdict: needs_fix
next_fix:        "calendar.png 1회로 줄이고, 청크 7 'iOS 26.6' 묶음 + WWDC 발음 짧게"
```
