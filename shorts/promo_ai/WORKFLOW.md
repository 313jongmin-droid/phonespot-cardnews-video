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
- **★ 크레딧 보고 룰 (종민, 2026-06-24)**: 모든 Higgsfield `generate_video`/`generate_image`/`generate_audio` 호출 **직후 `balance` 조회 → 잔액(credits)을 종민에게 매번 보고**. preflight(`get_cost`)와 별개로, 실제 차감된 뒤 남은 잔액을 명시할 것.
- **★ 컨셉은 이미지로 먼저 확정 (2026-06-24, 종민) — 크레딧 절약 핵심**: 인물·의상·톤·구도 등 비주얼 컨셉은 `generate_image`(nano_banana_pro = **2cr**, 영상 4초 6cr의 1/3)로 **먼저 이미지로 확정**한다. 마음에 들 때까지 이미지만 재생성(2cr씩) → 확정되면 그 이미지를 `start_image`(medias role)로 **영상화**. **컨셉 확인용으로 영상(6cr)을 재생성하지 말 것.** 보너스: 확정 이미지를 start_image로 쓰면 컷 간 **인물 일관성**도 확보된다. (004 호구썰에서 여성 인물·의상을 영상으로 4번 재생성 = 24cr 낭비 → 이미지로 했으면 8cr이면 됐던 교훈.)

**3. 한글 자막 = 무조건 ffmpeg 후처리 (영상 in-image 한글 ❌).**
- Kling 생성 영상은 한글 글자가 깨짐 → 프롬프트에 한글 텍스트 넣지 말 것. 영상은 비주얼만, **한글은 .ass 자막으로 후처리 burn**.
- 폰트: `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` (Noto Sans CJK KR, sandbox 기본 존재).
- **배경 텍스트도 흐리게 (2026-06-24, 종민)**: 매장 간판·견적서 등 깨져도 되는 텍스트는 프롬프트에 `NO readable Korean text, background signage blurred and out of focus` 명시 → **또렷한 한글이 애초에 안 생겨 깨짐이 안 보임**. 모든 컷 기본 적용.
- **정확해야 하는 한글**(가격·UI·슬로건·자막)은 영상에 맡기지 말고 ① ffmpeg `.ass` 자막/오버레이 후처리 또는 ② **GPT Image 2 합성**(Higgsfield 웹 Inpaint, 점원+0원카드 방식 = 002 검증). 텍스트 렌더는 GPT Image 2가 가장 정확.

**4. CDN 다운로드 함정 (현재 유일 병목).**
- sandbox(bash)는 Higgsfield cloudfront(`*.cloudfront.net`) 직접 다운로드 **403 차단**(프록시 allowlist). curl/wget 불가.
- → **종민이 위젯/링크에서 영상 다운로드 → 워크스페이스 폴더(또는 업로드)로 전달**해야 ffmpeg 가능. `job_display`의 `results.rawUrl`을 종민에게 전달.

**5. 빌드 명령 (실증, sandbox).**
- 정규화: `ffmpeg -i sN.mp4 -vf "scale=1080:1920,fps=30,setsar=1" -an -c:v libx264 -crf 18 -pix_fmt yuv420p nN.mp4`
- concat(copy): `ffmpeg -f concat -safe 0 -i list.txt -c copy body.mp4`
- 자막: `.ass`(PlayRes 1080x1920, Style Fontsize·Alignment·Outline) → `ffmpeg -i body.mp4 -vf "ass=subs.ass" -preset veryfast -crf 20 ...`.
- ★★ **viral 자막 강제 규칙 (2026-06-24, 종민 — 어기지 말 것)**: **Alignment 5(정중앙)** + **Fontsize 130~150 대형** + 화면 한가운데 박기. Outline 5~6 두껍게(검정), 무음시청자가 1초에 읽히게. **하단 소형 자막(Alignment 2 / MarginV 큰 값 / Fontsize 60~70) 금지.** 핵심 단어만 오렌지 `{\c&H0B4BF7&}`(BGR) 강조. (004 1차에서 하단 66pt로 깔았다가 "쓰레기" 반려 — 반복 금지.)
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
- **결과물 (슬러그별 폴더 = 영상+캡션 한 묶음)**: `out_promo_ai/<slug>/` 폴더 안에 ① 영상 `<slug>_<len>s_<YYYYMMDD_HHMM>.mp4`(덮어쓰기 ❌, 타임스탬프 누적) ② SNS 캡션 `<slug>_captions.md`(틱톡·유튜브·인스타, caption_template 룰). 이전 버전은 `out_promo_ai/<slug>/_archive/`. 최신본은 INDEX에 기록. **★ 렌더 마무리 시 이 슬러그 폴더를 만들어 영상+캡션을 함께 둔다.**
- **자산(재사용)**: `assets/references/store`(매장)·`/products`(제품) · `assets/audio/{bgm,sfx,narration}` · `shots/<slug>/`(생성 원본컷) · `assets/voices.md`(보이스ID).
- **인덱스**: `concepts/INDEX.md` = 전체 영상 1표(중복 회피·성과 학습). 신규 빌드 시 1줄 추가. 20편↑이면 시트 승격.
- **캡션·사전승낙서 (SNS 발행)**: 각 영상 `<slug>_captions.md`(틱톡·유튜브·인스타) = caption_template 룰 적용. **사전승낙서 URL 정본 = `shorts/promo_ai/_brand.json` `precon_url`** (한국 통신판매법상 SNS 광고성 게시물 마지막 줄 `[사전승낙서] <url>` 필수). 현재값 `https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1` (2026-06-24, 종민). 캡션 작성 시 자동 삽입.

---

## ★ viral vs ad 트랙 차이 (2026-06-24, 종민) — 트랙이 구조를 결정한다

슬러그의 `track`(viral / ad)은 단순 분류가 아니라 **성공 지표(KPI)가 다르다 = 영상 구조 전체가 반대로 간다.** 빌드 시작 전 트랙부터 못 박을 것.

| 축 | **viral (바이럴)** | **ad (홍보용)** |
|---|---|---|
| 1순위 KPI | 조회수·공유·댓글·저장 | 전환(매장 유입·상담) |
| 조회수 실패 시 | **= 실패** (존재 이유 없음) | **무관** (유료 광고로 도달 확보하니까) |
| 브랜드 노출 | 뒤로 뺀다. 끝 자막 0.5~1초 / 은근히 | 전면. 반복 CTA |
| 후킹 | 공감·어그로·반전 (폰스팟 무관해도 됨) | 제품·혜택·가격 |
| 엔딩 | **댓글 유발 질문** ("너넨 얼마 주고 샀어?") | 명확한 행동유도 (링크·방문·상담) |
| 대본 톤 | 1인칭 썰·친구 톤, 반말 | 정보·신뢰, 존댓말 |
| 배포 | 유기적(알고리즘) | 유료 집행 |

**원칙: 한 영상이 둘 다 잘하려 하면 둘 다 실패한다.** viral에 CTA를 박으면 광고 냄새로 조회수가 죽고, ad에 후킹만 있으면 전환이 안 된다. 트랙을 먼저 정하고 그 골격만 따른다.

- **viral 골격**: 어그로/정보형 후킹(1초) → 공감 스토리 → 반전 → **댓글 유발**. 브랜드 = 끝 자막 1줄.
- **ad 골격**: 문제 제기 → 혜택·차별점 → 신뢰 근거 → 강한 CTA. 브랜드 = 전면.
- 템플릿 분리(예정): `concepts/_template_viral_hogu.md` / `concepts/_template_ad.md` (각 7비트 골격 + 가변 슬롯표). 슬롯만 바꿔 시리즈 양산(편당 신규 컷 0~2개 + 나레이션).
- 호구썰 viral 7비트 골격: 후킹("이 말 들으면 호구") → 상황 → 빌드업(수법) → 전환(트리거) → 반전(0원·정찰제) → 현타 → 댓글유발+브랜드자막. 슬롯 = 제품 / 호구수법 / 화자 / 전환트리거.

---

## ★★ viral 영상 후처리 룰 (2026-06-29, 종민 컨펌 — 004로 확립, 재사용 정본)

### 1. 나레이션(보이스)
- **한국어 네이티브 preset = Hana 하나뿐**(성우톤). 영어권 preset(Quinn/Ava/Zoe/Skye)은 한국어 발음 어색. `cozy_voice`(CosyVoice)에 영어권 voice 넣으면 **영어 발음**으로 읽음 → 한국어엔 한국어 네이티브 보이스 필수.
- **일반인 톤 = 음성 클론**만이 답. 단 **STARTER 플랜은 voice clone 한도 0**(`create_voice` → "Voice limit reached", 커스텀 보이스 0개인데도) → Plus/Ultra 업그레이드 또는 로컬 GPU CosyVoice2 필요.
- 클론 샘플 = **Common Voice 한국어(CC0, 상업가능)**. KSS는 CC-NC(비상업) 탈락. sandbox는 HF·CDN 403이라 못 받음 → 종민이 받아 `media_upload_widget`으로 업로드(채팅 업로드분은 Higgsfield로 못 보냄).
- 004 최종 채택 = **Quinn**(preset). TTS 실측 0.15cr/문장.
- **속도: TTS 자체 조절 없음 → ffmpeg `atempo`.** 004 채택 = **1.35배속**(1.6은 빠름, 1.4 무난).

### 2. 자막 (★ 종민 핵심 룰)
- **자막 = 나레이션 전문 일치**(요약 금지).
- **청크화**: 한 번에 다 띄우지 말 것. 짧은 청크로 쪼개 **순차 등장**(콩트/썰 리듬). 비트(문장)를 청크 수로 시간 균등 배분.
- 위치 = Alignment 5(정중앙), 대형. 긴 청크는 104~116pt. Outline 6.
- 강조어(호구·공짜 등) 오렌지 `{\c&H0B4BF7&}`(BGR), 선택적.

### 3. 타이포 효과 (.ass, Remotion 대체)
- 타이포 task는 **Remotion**이라 실사 ffmpeg 파이프라인에 직접 못 붙음 → `.ass` 태그로 결만 재현(80% 수준).
- **★ 효과는 핵심 포인트에만**(전체 청크의 ~20%, 004는 18청크 중 4곳). 나머지는 페이드만(`\fad`) → 효과 들어간 데가 강조됨.
- **★ 같은 효과 연속 금지. 슬라이드(`\move`) 금지(종민).**
- 사용 효과 = **punch**(스케일 작→큰, 충격) / **glitch**(`\frz` 지터+`\blur`, "혼란·외계어" 문맥) / **pop**(스케일 폭발, 반전 펀치라인) / **shake**(`\frz` 진동, 현타). **문맥 매칭 필수**.
- 004 적용: 호구=punch / 외계어=glitch / 공짜=pop / 너넨얼마=shake.

### 4. 영상 모션
- **켄번스 줌(`zoompan`)** — 후킹·반전 강, 나머지 약. 맥락 포인트만, 막 넣지 말 것. ★ `zoompan` 전 `fps=30` 먼저 안 맞추면 길이 깨짐(입력 fps≠30이면 출력 짧아짐).
- 컷 경계 = **fade in/out 0.12s**(길이 보존). `xfade`는 겹침만큼 길이 줄어 나레이션 싱크 깨짐 → 회피.
- 엔딩 페이드인.

### 5. 입싱크 / 컷 / 글래머
- **kling = 보이스오버(audio 입력 X)** → 입모양 안 맞음. 말하는 정면 컷 회피, **입 다문 컷/B-roll + 보이스오버**. (A-roll 말하는 얼굴 최소, 표정·상황 B-roll 위주.)
- **Wan 2.7 립싱크 = start_image+audio 조합 2회 실패**(audio가 reference_images로 섞임). `dubbing`은 영상 기존음성 번역 전용이라 부적합.
- **글래머 전 컷 유지**(머리~힙·깊은 U넥, 입 다물어도 몸매). 자막 중앙배치가 가슴 가리면 청크 1줄로 완화.
- 인물 일관성 = AI 한계로 컷마다 미묘차이. 같은 reference media_id(`82abdf0f`)로 완화. 배경 통일도 도움(004 B1 집→매장).

### 6. 비용/환경
- **영상 kling `sound:"off"` 명시 필수**(off=6cr/4s, on=8cr → +2cr 낭비).
- 이미지 먼저(nano 2cr)로 글래머 확정 → 영상화(컷당 4s 6cr / 3s 4.5cr).
- sandbox = CDN·HF·Higgsfield업로드 전부 403 차단 → 영상·오디오는 종민이 다운로드/위젯 업로드. **ffmpeg 합성은 sandbox에서 가능**.
- 빌드 파이프라인: 나레이션 atempo+concat → 세그먼트(정규화+trim/slow+zoom+fade) → concat body → `.ass` 청크자막 burn + 나레이션 mix → 최종.

### 7. 산출물·git 위생 (2026-06-29, 자체점검 확립)
- **영상(.mp4)·오디오(.mp3/.wav) = `.gitignore` 전역 비추적**(재생성 가능·용량). git 추적·전파 대상 = 캡션·concept·WORKFLOW·INDEX **md만**.
- **검증 프레임 = `out_promo_ai/<slug>/_chk*`·`_insp*` 폴더**(png) → `.gitignore` 차단. **발행 전 삭제**(sandbox 권한 밖이라 종민이 탐색기에서).
- 구버전 영상 = `out_promo_ai/<slug>/_archive/`로, 최신본만 INDEX 기록(타임스탬프 누적, 덮어쓰기 ❌).
- **캡션(`<slug>_captions.md`)은 최종 영상 버전과 톤·내용 일치 유지** — 영상 갱신 시 캡션도 같이 갱신(004는 v9 7비트 썰톤+댓글유발로 정합).
- ★ **푸시는 영역 지정**: `git add shorts/promo_ai .gitignore`. **`git add -A` 금지** — repo에 줄끝(CRLF/LF) 미커밋 변경(.bat/.ps1 다수)이 상존해 의도 안 한 것까지 딸려감(STEP7 리포위생 연동).
