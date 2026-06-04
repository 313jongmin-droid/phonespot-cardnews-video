# promo_ai 빌드 워크플로 (Claude + Higgsfield)

> 컨셉 기획서 (`concepts/<slug>.md`) → Higgsfield API 호출 → ffmpeg 합치기 → 최종 mp4

---

## Step 0 — 사전 점검

```python
# Claude 가 자동 호출
mcp__83aadcc7-...__balance()
# → 현재 credits 확인. 부족하면 show_plans_and_credits()
```

```python
# 모델 사양 확인
mcp__83aadcc7-...__models_explore(action="get", model_id="kling3_0")
# → aspect_ratios, durations, parameters, medias[].roles 확인
```

## Step 1 — 컨셉 기획서 작성 (사람 또는 Claude)

위치: `shorts/promo_ai/concepts/<slug>.md`

필수 섹션:
- 메타 (slug, duration, aspect, model)
- 스토리보드 (시퀀스 분할)
- Shot 별: 비주얼 / 카메라 / 자막 / SFX / Kling prompt (영문)

참고 템플릿: `concepts/001_gwanggyo_visit.md`

## Step 2 — preflight cost 점검

각 shot 별로 호출 전 cost 확인:

```python
mcp__83aadcc7-...__generate_video(
  params={
    "model": "kling3_0",
    "prompt": "<영문 prompt>",
    "aspect_ratio": "9:16",
    "duration": 5,
    "get_cost": True
  }
)
# → 실제 호출 안 하고 cost 반환
```

전체 shot cost 합산 → 종민님 결제 판단.

## Step 3 — Shot 별 생성

### Option A: Kling 3.0 멀티샷 (1순위, 효율적)

15초 한 번에 3-5 cut 생성 가능. 한 prompt 안에 시퀀스 분할 명시.

```python
mcp__83aadcc7-...__generate_video(
  params={
    "model": "kling3_0",
    "prompt": "Vertical 9:16, 15-second commercial in 3 scenes: SCENE 1 (5s) ... SCENE 2 (5s) ... SCENE 3 (5s) ...",
    "aspect_ratio": "9:16",
    "duration": 15,
    "mode": "pro"  # std / pro / 4k
  }
)
```

장점: 한 번에 자연스럽게 연결. 비용 효율.
단점: 컷별 미세 수정 불가능.

### Option B: Shot 별 개별 생성 (수정 자유도 ↑)

각 shot 5초씩 따로 생성 후 ffmpeg 합치기.

```python
# Shot 1 (5초)
job1 = mcp__83aadcc7-...__generate_video(
  params={"model": "kling3_0", "prompt": "<Shot 1 prompt>",
          "aspect_ratio": "9:16", "duration": 5}
)

# Shot 1 의 마지막 프레임을 Shot 2 의 start_image 로 (연속성)
job2 = mcp__83aadcc7-...__generate_video(
  params={"model": "kling3_0", "prompt": "<Shot 2 prompt>",
          "aspect_ratio": "9:16", "duration": 5,
          "medias": [{"role": "start_image", "value": "<job1 id>"}]}
)

# Shot 3 동일
```

장점: 각 cut 수정 자유.
단점: 비용 3배. cut 간 연결 자연스럽지 않을 수 있음.

### Option C: 핵심 이미지 먼저 → 영상화 (가장 보수적)

```python
# 1) 키비주얼 이미지 1장 generate_image
img = mcp__83aadcc7-...__generate_image(
  params={"model": "marketing_studio_image", "prompt": "<비주얼 묘사>",
          "aspect_ratio": "9:16"}
)

# 2) 그 이미지를 start_image 로 image-to-video
vid = mcp__83aadcc7-...__generate_video(
  params={"model": "kling3_0", "prompt": "<motion 묘사>",
          "duration": 5, "medias": [{"role": "start_image", "value": img.id}]}
)
```

장점: 이미지 단계에서 톤 컨펌 가능 (저비용 실패).
단점: 추가 단계 = 추가 시간.

## Step 4 — 결과 저장

```python
# 생성 완료 후 다운로드
# show_generations 로 job ID 확인 → 결과 URL 받기
mcp__83aadcc7-...__show_generations()
# 또는 직접 결과 URL 확인 (호출 후 응답에 포함)
```

저장 위치: `shorts/promo_ai/shots/<slug>/shot{N}.mp4`

## Step 5 — ffmpeg 합치기

```bash
# 1) cut 합치기
ffmpeg -f concat -safe 0 -i shots_list.txt -c copy shots_concat.mp4

# 2) BGM 오버레이 (선택)
ffmpeg -i shots_concat.mp4 -i bgm.mp3 -filter_complex \
  "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -shortest out.mp4

# 3) 자막 (선택)
ffmpeg -i out.mp4 -vf "subtitles=captions.srt:force_style='FontName=Pretendard,FontSize=80,PrimaryColour=&Hffffff,OutlineColour=&H1A1A1A,Outline=4'" out_final.mp4

# 4) 1080×1920 보장 + yuv420p (SNS 호환)
ffmpeg -i out_final.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
  -pix_fmt yuv420p -c:v libx264 -crf 18 -c:a aac -movflags +faststart final.mp4
```

최종 출력: `shorts/promo_ai/out_promo_ai/<slug>_15s.mp4`

## Step 6 — 검토 + 발행

- `upload/` 또는 `upload_promo_ai/` 에 복사
- SNS 직접 업로드 (수동)
- 결과 기록: `concepts/<slug>.md` 마지막에 "최종 빌드: YYYYMMDD, cost: NN credits, 만족도: N/5" 추가

## 운영 룰

1. **preflight 필수** — 호출 전 cost 확인 안 하면 결제 낭비
2. **Shot 1 만 먼저 생성** — 톤 확인 후 Shot 2,3 진행 (실패 비용 최소화)
3. **재생성 1회 이상이면 prompt 점검** — 같은 prompt 로 3번 재생성 = 비용 폭증
4. **MCP 호출 결과 (job_id, URL) 보관** — `shorts/promo_ai/shots/<slug>/_jobs.json` 에 기록
5. **결제는 종민님 결정** — Claude 가 자동 결제 X. balance 부족 시 즉시 stop + 보고

## 미구현 (다음 단계)

- [ ] `scripts/promo_ai_build.py` — 컨셉 md → MCP 호출 자동화
- [ ] `scripts/promo_ai_concat.py` — shots/*.mp4 → final.mp4 ffmpeg 자동화
- [ ] `run_promo_ai.bat` — 1편 빌드 단축 진입점
- [ ] `concepts/_template.md` — 신규 컨셉 템플릿
- [ ] BGM/SFX 라이브러리 (`shorts/promo_ai/assets/audio/`)
- [ ] 자막 SRT 자동 생성 (컨셉 md 의 자막 → .srt)

## 관련

- 컨셉 기획: `concepts/001_gwanggyo_visit.md`
- 트랙 메뉴얼: `README.md`
- 브랜드 정보: `_brand.json`
- 메모리: [[phonespot-video-project]]
