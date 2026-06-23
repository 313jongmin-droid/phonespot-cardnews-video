# promo_ai 빌드 워크플로 (Claude + Higgsfield)

> 컨셉 기획서 (`concepts/<slug>.md`) → Higgsfield API 호출 → ffmpeg 합치기 → 최종 mp4

---

## ★ 실증 검증 (2026-06-22, 002 광고용 1편 완주) — 여기부터 읽어라

이 트랙이 실전에서 처음 끝까지 돌아간 기록. 추정 아닌 실측.

**1. 결제/플랜 게이트 (가장 중요 — README 미해결 "Plus/Ultra 결제" 해소).**
- free 플랜 + 크레딧 top-up 충전만으로는 **MCP 영상 생성 불가** → `generate_video` 에러 `"Requires basic plan or higher"`. preflight(`get_cost:true`)는 통과하나 실제 제출에서 막힘.
- 이 워크스페이스(individual)는 **크레딧 단건 top-up 자체가 비활성**(`show_plans_and_credits` → `topups:[]`, "not available"). 즉 크레딧 ≠ 생성권한, **구독 플랜 필수**.
- **STARTER $19/270cr 구독이면 MCP Kling 3.0 정상 작동**(실증, `balance`의 `subscription_plan_type:"starter"` 확인). MCP `show_plans`는 PLUS+만 권하지만, 웹 COMPARE PLANS 표 = Kling 3.0 720p: Starter 432편 → STARTER로 충분. **단 Seedance 2.0(일반)은 STARTER 제외**, Kling 3.0·Seedance 2.0 Fast는 포함.
- 룰: 자동 결제 ❌. 막히면 `balance` + `show_plans_and_credits`로 종민 계정 실제 상태 조회 후 보고. STARTER가 최저·최저리스크($19, 월·연 동가).

**2. 실측 cost (kling3_0, std, sound=off, 9:16).**
- 3s=4.5cr / 4s=6cr / 5s=7.5cr (≈1.5cr/s). 무음(`sound:"off"`)이 더 쌈 → 콩트는 무음+자막이라 항상 off.
- 002 1편(3컷 11초)=**16.5cr**. STARTER 270cr/월 ≈ 영상 18편. cr당 ~$0.07 → 1편 ~$1.2.
- ffmpeg 합치기·자막·엔딩 = **크레딧 0**(로컬 처리).

**3. 한글 자막 = 무조건 ffmpeg 후처리 (영상 in-image 한글 ❌).**
- Kling 생성 영상은 한글 글자가 깨짐 → 프롬프트에 한글 텍스트 넣지 말 것. 영상은 비주얼만, **한글은 .ass 자막으로 후처리 burn**.
- 폰트: `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` (Noto Sans CJK KR, sandbox 기본 존재).

**4. CDN 다운로드 함정 (현재 유일 병목).**
- sandbox(bash)는 Higgsfield cloudfront(`*.cloudfront.net`) 직접 다운로드 **403 차단**(프록시 allowlist). curl/wget 불가.
- → **종민이 위젯/링크에서 영상 다운로드 → 워크스페이스 폴더(또는 업로드)로 전달**해야 ffmpeg 가능. `job_display`의 `results.rawUrl`을 종민에게 전달.

**5. 빌드 명령 (실증, sandbox).**
- 정규화: `ffmpeg -i sN.mp4 -vf "scale=1080:1920,fps=30,setsar=1" -an -c:v libx264 -crf 18 -pix_fmt yuv420p nN.mp4`
- concat(copy): `ffmpeg -f concat -safe 0 -i list.txt -c copy body.mp4`
- 자막: `.ass`(PlayRes 1080x1920, Style Fontsize·Alignment·Outline) → `ffmpeg -i body.mp4 -vf "ass=subs.ass" -preset veryfast -crf 20 ...`. 중앙배치=Alignment 5, 크게=Fontsize 136.
- CTA 엔딩: `ffmpeg -f lavfi -i color=c=0x0A0A0A:s=1080x1920:d=4:r=30 -vf "drawtext=fontfile=$FONT:text='정찰제':fontcolor=0xF74B0B:fontsize=200:x=(w-tw)/2:y=640, ..."` (브랜드 오렌지 `#F74B0B`).
- **함정: bash 45초 타임아웃** → ffmpeg 단계를 쪼개 실행(정규화 / 자막 burn / 엔딩 / 최종 따로), `-preset veryfast`로 속도.

**6. 결과물.** `shorts/promo_ai/out_promo_ai/002_ad_jeongchalje_15s.mp4` (15s, 1080x1920, 30fps). 순서=마트→부조리→폰스팟→CTA. 무음(BGM 미적용 = 음원 수급은 종민).

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
 
---

## 명명·분류 규칙 (2026-06-23)

- **슬러그**: `NNN_<ad|viral>_<theme>` (예 `002_ad_jeongchalje` / `003_viral_jeongchalje`). 카드뉴스 `NNN_type_topic` 철학 계승.
  - track = ad(광고·전환) / viral(바이럴·조회). theme = 정찰제·효도폰·가족·첫폰·갤vs아이폰·비대면·단통법·매장방문(README §6).
  - **타겟·시즌·채널은 폴더 ❌** → `concepts/INDEX.md` 표 컬럼으로만(다축이라 폴더 쪼개면 중복·이동 지옥).
- **결과물**: `out_promo_ai/<slug>_<len>s.mp4` (예 `002_ad_jeongchalje_15s.mp4`). 중간본은 `out_promo_ai/_archive_versions/`.
- **자산(재사용)**: `assets/references/store`(매장)·`/products`(제품) · `assets/audio/{bgm,sfx,narration}` · `shots/<slug>/`(생성 원본컷) · `assets/voices.md`(보이스ID).
- **인덱스**: `concepts/INDEX.md` = 전체 영상 1표(중복 회피·성과 학습). 신규 빌드 시 1줄 추가. 20편↑이면 시트 승격.
